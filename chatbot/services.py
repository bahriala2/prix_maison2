"""Assistant intelligent du bureau d'ordre.

Le chatbot répond aux questions sur les courriers entrants/sortants, les
demandes d'achat et les marchés en deux étapes :

1. Récupération : les mots significatifs de la question servent à retrouver
   les enregistrements pertinents dans la base (courriers, demandes,
   marchés), sérialisés en contexte compact, complétés par des statistiques
   globales.
2. Génération : le contexte + l'historique de conversation sont envoyés à un
   LLM via une API compatible OpenAI.

Fournisseurs supportés (mêmes variables d'environnement) :
- OpenRouter (par défaut) : LLM_BASE_URL=https://openrouter.ai/api/v1,
  LLM_API_KEY=<clé openrouter>, LLM_MODEL=<ex: openai/gpt-4o-mini>
- LM Studio (LLM local)   : LLM_BASE_URL=http://localhost:1234/v1,
  LLM_API_KEY=lm-studio, LLM_MODEL=<modèle chargé dans LM Studio>
"""
import os
import re

import requests
from django.db.models import Count, Q

from achats.models import DemandeAchat
from courrier.models import STOPWORDS, Courrier, TypeCourrier
from marches.models import Marche

def _nettoyer_cle(valeur):
    """Neutralise les erreurs de saisie courantes dans la variable
    d'environnement : espaces, guillemets, préfixe « Bearer » superflu."""
    valeur = (valeur or "").strip().strip('"').strip("'").strip()
    if valeur.lower().startswith("bearer "):
        valeur = valeur[7:].strip()
    return valeur


def get_llm_config():
    """Lit la configuration LLM depuis l'environnement à chaque appel, afin
    qu'un changement de variable (Render, .env...) soit pris en compte sans
    modification du code. Modèle par défaut : gratuit sur OpenRouter."""
    base_url = os.environ.get("LLM_BASE_URL", "https://openrouter.ai/api/v1").strip().strip('"').strip("'")
    # Une URL en http:// vers OpenRouter provoque une redirection qui supprime
    # l'en-tête Authorization ("Missing Authentication header") : forcer https.
    if "openrouter.ai" in base_url:
        base_url = base_url.replace("http://", "https://")
    return {
        "base_url": base_url,
        "api_key": _nettoyer_cle(os.environ.get("LLM_API_KEY") or os.environ.get("OPENROUTER_API_KEY", "")),
        "model": os.environ.get("LLM_MODEL", "meta-llama/llama-3.3-70b-instruct:free").strip().strip('"').strip("'"),
        "timeout": int(os.environ.get("LLM_TIMEOUT", "60")),
    }

SYSTEM_PROMPT = """Tu es l'assistant virtuel du bureau d'ordre de la DTPCSSO
(application de gestion des courriers, demandes d'achat et marchés d'une
administration territoriale). Tu réponds comme un agent de bureau d'ordre
expérimenté qui connaît parfaitement les dossiers.

Règles :
- Réponds toujours en français, de façon claire et professionnelle.
- Appuie-toi UNIQUEMENT sur les données fournies dans le contexte ci-dessous.
- Cite les numéros d'ordre et références quand tu mentionnes un dossier.
- Si l'information demandée n'est pas dans le contexte, dis-le honnêtement et
  suggère d'utiliser la recherche par colonne des listes de courriers.
- Pour les questions statistiques, utilise la section STATISTIQUES."""


def _mots_significatifs(question, minimum=3):
    return [
        m.lower() for m in re.split(r"\W+", question)
        if len(m) >= minimum and m.lower() not in STOPWORDS
    ]


def _chercher(queryset, champs, mots, limit):
    if not mots:
        return queryset.none()
    q = Q()
    for mot in mots[:10]:
        for champ in champs:
            q |= Q(**{f"{champ}__icontains": mot})
    return queryset.filter(q).distinct()[:limit]


def _ligne_courrier(c):
    doc_texte = ""
    return (
        f"- [{c.numero_ordre}] {c.get_type_courrier_display()} du {c.date_courrier} | "
        f"émetteur: {c.emetteur} | récepteur: {c.recepteur} | objet: {c.objet} | "
        f"réf: {c.reference_externe or '—'} | service: {c.service} | "
        f"statut: {c.get_statut_display()} | urgence: {c.get_urgence_display()}"
        + (f" | résumé du contenu: {c.resume[:300]}" if c.resume else "")
        + doc_texte
    )


def _ligne_demande(d):
    return (
        f"- [{d.reference}] demande d'achat ({d.get_circuit_display()}) | service: {d.service_demandeur} | "
        f"objet: {d.objet} | type: {d.get_type_achat_display()} | montant estimatif: {d.montant_estimatif or '—'} | "
        f"statut: {d.get_statut_display()} | signature directeur: {d.date_signature_directeur or '—'} | "
        f"n° bureau d'ordre: {d.numero_ordre_bo or '—'}"
        + (f" | description: {d.description[:200]}" if d.description else "")
    )


def _ligne_marche(m):
    return (
        f"- [{m.reference}] marché | objet: {m.objet} | procédure: {m.get_type_procedure_display()} | "
        f"service: {m.service_demandeur} | fournisseur: {m.fournisseur or '—'} | montant: {m.montant or '—'} | "
        f"statut: {m.get_statut_display()} | lancement: {m.date_lancement or '—'} | clôture: {m.date_cloture or '—'}"
    )


def build_context(question, limit=12):
    """Construit le contexte documentaire pertinent pour la question."""
    mots = _mots_significatifs(question)

    courriers = _chercher(
        Courrier.objects.select_related("service").order_by("-date_courrier"),
        ["objet", "emetteur", "recepteur", "reference_externe", "resume", "numero_ordre"],
        mots, limit,
    )
    demandes = _chercher(
        DemandeAchat.objects.select_related("service_demandeur").order_by("-created_at"),
        ["objet", "description", "reference", "numero_ordre_bo"],
        mots, limit,
    )
    marches = _chercher(
        Marche.objects.select_related("service_demandeur").order_by("-created_at"),
        ["objet", "fournisseur", "reference"],
        mots, limit,
    )

    # Si la recherche ciblée ne trouve rien, fournir les dossiers récents
    if not courriers and not demandes and not marches:
        courriers = Courrier.objects.select_related("service").order_by("-date_courrier")[:limit]
        demandes = DemandeAchat.objects.select_related("service_demandeur").order_by("-created_at")[:5]
        marches = Marche.objects.select_related("service_demandeur").order_by("-created_at")[:5]

    stats_courriers = dict(
        Courrier.objects.values_list("type_courrier").annotate(total=Count("id"))
    )
    stats_statuts = list(
        Courrier.objects.values("statut").annotate(total=Count("id")).order_by("-total")
    )

    sections = ["=== STATISTIQUES ==="]
    sections.append(
        f"Courriers entrants: {stats_courriers.get(TypeCourrier.ENTRANT, 0)} | "
        f"Courriers sortants: {stats_courriers.get(TypeCourrier.SORTANT, 0)} | "
        f"Demandes d'achat: {DemandeAchat.objects.count()} | Marchés: {Marche.objects.count()}"
    )
    sections.append("Courriers par statut: " + ", ".join(f"{s['statut']}: {s['total']}" for s in stats_statuts))

    if courriers:
        sections.append("\n=== COURRIERS PERTINENTS ===")
        sections.extend(_ligne_courrier(c) for c in courriers)
    if demandes:
        sections.append("\n=== DEMANDES D'ACHAT PERTINENTES ===")
        sections.extend(_ligne_demande(d) for d in demandes)
    if marches:
        sections.append("\n=== MARCHÉS PERTINENTS ===")
        sections.extend(_ligne_marche(m) for m in marches)

    return "\n".join(sections)


class LLMError(Exception):
    pass


def tester_connexion():
    """Vérifie la clé auprès du fournisseur et retourne un diagnostic lisible.
    Pour OpenRouter, GET /key renvoie les informations de la clé si elle est
    valide ; pour un LLM local, GET /models vérifie que le serveur répond."""
    config = get_llm_config()
    if not config["api_key"] and "openrouter" in config["base_url"]:
        return "Aucune clé détectée dans l'environnement (OPENROUTER_API_KEY / LLM_API_KEY)."

    if "openrouter" in config["base_url"]:
        url = "https://openrouter.ai/api/v1/key"
    else:
        url = f"{config['base_url'].rstrip('/')}/models"

    try:
        r = requests.get(
            url,
            headers={"Authorization": f"Bearer {config['api_key'] or 'lm-studio'}"},
            timeout=20,
        )
    except requests.RequestException as exc:
        return f"Connexion impossible vers {url} : {exc}"

    if r.status_code == 200:
        return f"✅ Connexion réussie (HTTP 200). Clé valide sur {config['base_url']} — modèle configuré : {config['model']}."
    return f"❌ HTTP {r.status_code} sur {url} : {r.text[:300]}"


def ask_llm(question, historique=None):
    """Envoie la question au LLM avec le contexte documentaire et retourne la réponse."""
    config = get_llm_config()
    if not config["api_key"] and "openrouter" in config["base_url"]:
        raise LLMError(
            "Aucune clé API configurée. Définissez la variable d'environnement "
            "OPENROUTER_API_KEY (ou LLM_API_KEY) puis redémarrez l'application."
        )

    contexte = build_context(question)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT + "\n\n=== CONTEXTE DOCUMENTAIRE ===\n" + contexte},
    ]
    for m in (historique or [])[-10:]:
        messages.append({"role": m.role, "content": m.contenu})
    messages.append({"role": "user", "content": question})

    try:
        response = requests.post(
            f"{config['base_url'].rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {config['api_key'] or 'lm-studio'}",
                "Content-Type": "application/json",
            },
            json={"model": config["model"], "messages": messages, "temperature": 0.2},
            timeout=config["timeout"],
        )
    except requests.RequestException as exc:
        raise LLMError(f"Impossible de joindre le service LLM ({config['base_url']}) : {exc}") from exc

    if response.status_code != 200:
        raise LLMError(f"Erreur du service LLM (HTTP {response.status_code}) : {response.text[:300]}")

    data = response.json()
    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError) as exc:
        raise LLMError(f"Réponse inattendue du service LLM : {str(data)[:300]}") from exc
