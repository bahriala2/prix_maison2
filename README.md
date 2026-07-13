# DTPCSSO — Gestion du bureau d'ordre, des demandes d'achat et des marchés

Application web (Django) pour la digitalisation du bureau d'ordre, le suivi
des courriers entrants et sortants, des demandes d'achat signées par le
directeur, des approbations et des marchés publics d'une administration
territoriale.

## Fonctionnalités

- **Bureau d'ordre** : listes séparées des courriers entrants et sortants
  avec recherche par colonne et lignes cliquables, numéro d'ordre
  automatique, statuts, historique des actions, correspondances liées
  (liaison manuelle + suggestions automatiques par thème, référence ou
  interlocuteur), autocomplétion des émetteurs/récepteurs.
- **Scan intelligent** : import d'un document scanné (PDF ou image), OCR et
  extraction automatique (émetteur, récepteur, objet, référence, date,
  urgence, résumé) avec pré-remplissage de la fiche, toujours vérifié par
  l'agent avant enregistrement.
- **Demandes d'achat** : deux circuits de validation — « avec accords »
  (DCP et autres directions) et « locale » (signature du directeur
  uniquement) — approbations, suivi des demandes signées, enregistrement au
  bureau d'ordre et transmission au service achat.
- **Marchés** : suivi des consultations, attributions, notifications et
  clôtures.
- **Assistant intelligent (chatbot)** : répond en français aux questions sur
  les courriers arrivés/envoyés et leur contenu, les demandes d'achat et les
  marchés, comme un agent du bureau d'ordre qui connaît tous les dossiers
  (via OpenRouter, ou un LLM local avec LM Studio).
- **Tableau de bord** : indicateurs clés et alertes de retard.
- **Rôles** : administrateur, agent bureau d'ordre, chef de service,
  directeur, service achat, service financier, audit.

---

## Installation locale (sur n'importe quelle machine)

L'application fonctionne entièrement en local, sans hébergement internet.
Par défaut elle utilise une base de données **SQLite** (un simple fichier,
rien à installer).

### 1. Prérequis

| Logiciel | Version | Téléchargement |
|---|---|---|
| Python | 3.11 ou plus récent | https://www.python.org/downloads/ |
| Git (optionnel) | récent | https://git-scm.com/downloads |

> **Windows** : pendant l'installation de Python, cochez impérativement la
> case **« Add Python to PATH »**.

### 2. Récupérer le code

Avec git :

```bash
git clone https://github.com/bahriala2/bureau-d-ordre.git
cd bureau-d-ordre
```

Ou sans git : sur la page GitHub du dépôt, cliquez **Code → Download ZIP**,
décompressez l'archive puis ouvrez un terminal dans le dossier obtenu.

### 3. Créer l'environnement virtuel et installer les dépendances

**Windows (invite de commandes ou PowerShell) :**

```bat
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

**Linux / macOS :**

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

> Si l'installation de `psycopg2-binary` échoue, vous pouvez l'ignorer : il
> ne sert que pour PostgreSQL, inutile en local. Supprimez simplement sa
> ligne dans `requirements.txt` et relancez la commande.

### 4. Initialiser la base de données et les comptes

```bash
python manage.py migrate
python manage.py seed_demo
```

`seed_demo` crée les services, des données d'exemple et les comptes
suivants (mot de passe commun : **`Demo1234!`**) :

| Identifiant | Rôle |
|---|---|
| `admin` | Administrateur (accès complet) |
| `agent.bo` | Agent bureau d'ordre |
| `chef.info` | Chef de service |
| `directeur` | Directeur |
| `service.achat` | Service achat |
| `service.financier` | Service financier |
| `audit` | Consultation / audit |

Pour créer votre propre compte administrateur :

```bash
python manage.py createsuperuser
```

### 5. Lancer l'application

```bash
python manage.py runserver
```

Ouvrez ensuite votre navigateur sur **http://127.0.0.1:8000** et
connectez-vous (par exemple `admin` / `Demo1234!`).

Pour rendre l'application accessible aux autres postes du réseau local :

```bash
python manage.py runserver 0.0.0.0:8000
```

puis, depuis les autres postes : `http://ADRESSE-IP-DU-PC:8000`
(exemple : `http://192.168.1.10:8000`). Pensez à autoriser le port 8000
dans le pare-feu de la machine.

### 6. (Optionnel) Activer l'OCR — analyse automatique des documents scannés

Sans cette étape, l'application fonctionne normalement mais la saisie des
courriers reste manuelle. Pour activer l'extraction automatique :

**Windows :**

1. Installez Tesseract OCR : https://github.com/UB-Mannheim/tesseract/wiki
   (pendant l'installation, cochez le pack de langue **French**).
2. Installez Poppler (pour les PDF) : https://github.com/oschwartz10612/poppler-windows/releases
   — décompressez puis ajoutez le dossier `bin` au PATH.
3. Si Tesseract n'est pas dans le PATH, ajoutez son dossier d'installation
   (ex. `C:\Program Files\Tesseract-OCR`) au PATH.

**Linux (Debian/Ubuntu) :**

```bash
sudo apt install tesseract-ocr tesseract-ocr-fra poppler-utils
```

**macOS :**

```bash
brew install tesseract tesseract-lang poppler
```

Redémarrez ensuite `python manage.py runserver` : le bouton « Analyser le
document » remplira automatiquement la fiche du courrier.

### 7. (Optionnel) Activer l'assistant intelligent (chatbot)

L'onglet **🤖 Assistant** répond aux questions sur les courriers, demandes
d'achat et marchés en s'appuyant sur un LLM. Deux options :

**Option A — OpenRouter (recommandée pour commencer)**

1. Créez une clé API sur https://openrouter.ai/keys
2. Définissez les variables d'environnement avant de lancer le serveur :

   **Windows :**
   ```bat
   set OPENROUTER_API_KEY=sk-or-v1-xxxxxxxx
   python manage.py runserver
   ```

   **Linux / macOS :**
   ```bash
   export OPENROUTER_API_KEY=sk-or-v1-xxxxxxxx
   python manage.py runserver
   ```

   Le modèle par défaut est **gratuit**
   (`meta-llama/llama-3.3-70b-instruct:free`). La variable `LLM_MODEL`
   accepte n'importe quel modèle OpenRouter si vous souhaitez en changer
   (ex. `openai/gpt-4o-mini`, `anthropic/claude-3.5-haiku`...).
   Pour les modèles `:free`, activez « Enable free endpoints » dans
   https://openrouter.ai/settings/privacy si OpenRouter renvoie une erreur
   « No endpoints found ».

**Option B — LLM 100 % local avec LM Studio (aucune connexion internet)**

1. Installez LM Studio : https://lmstudio.ai
2. Téléchargez-y un modèle (ex. Llama 3.1 8B Instruct) et démarrez le
   serveur local (onglet « Developer » → Start Server, port 1234 par défaut)
3. Lancez l'application avec :

   ```bash
   export LLM_BASE_URL=http://localhost:1234/v1
   export LLM_MODEL=nom-du-modele-charge-dans-lmstudio
   python manage.py runserver
   ```

Sans configuration, l'onglet Assistant reste accessible mais affiche un
message expliquant comment configurer la clé.

### Utilisation quotidienne (après la première installation)

```bash
cd bureau-d-ordre
venv\Scripts\activate        # Windows  (ou : source venv/bin/activate)
python manage.py runserver
```

### Problèmes fréquents

| Symptôme | Solution |
|---|---|
| `python` introuvable (Windows) | Réinstallez Python en cochant « Add Python to PATH », ou utilisez `py` à la place de `python` |
| `Permission denied` sur venv (PowerShell) | Exécutez `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` puis réessayez |
| « OCR indisponible sur ce serveur » | Suivez l'étape 6 (installation de Tesseract et Poppler) |
| Page inaccessible depuis un autre poste | Lancez avec `0.0.0.0:8000` et ouvrez le port 8000 dans le pare-feu |
| Repartir de zéro (vider les données) | Supprimez le fichier `db.sqlite3` puis relancez `migrate` et `seed_demo` |

### Où sont stockées les données ?

- **Base de données** : fichier `db.sqlite3` à la racine du projet —
  sauvegardez ce fichier régulièrement (copie simple).
- **Documents scannés / pièces jointes** : dossier `media/` à la racine du
  projet — à sauvegarder également.

---

## Configuration avancée (variables d'environnement)

Facultatif en local — les valeurs par défaut conviennent.

| Variable | Rôle | Défaut |
|---|---|---|
| `DJANGO_SECRET_KEY` | Clé secrète Django | valeur de développement |
| `DJANGO_DEBUG` | Mode debug | `True` |
| `DJANGO_ALLOWED_HOSTS` | Hôtes autorisés (séparés par des virgules) | `*` |
| `DATABASE_ENGINE` | `postgresql` pour utiliser PostgreSQL | SQLite |
| `DATABASE_NAME`, `DATABASE_USER`, `DATABASE_PASSWORD`, `DATABASE_HOST`, `DATABASE_PORT` | Connexion PostgreSQL | — |
| `OPENROUTER_API_KEY` (ou `LLM_API_KEY`) | Clé API pour l'assistant | — |
| `LLM_BASE_URL` | URL de l'API LLM (OpenRouter ou LM Studio) | `https://openrouter.ai/api/v1` |
| `LLM_MODEL` | Modèle utilisé par l'assistant | `openai/gpt-4o-mini` |

## Hébergement en ligne (optionnel)

Le dépôt contient aussi tout le nécessaire pour un hébergement sur
**Render** (`render.yaml`, `Dockerfile` avec OCR intégré) : créez un compte
sur https://render.com, **New → Blueprint**, sélectionnez ce dépôt. Voir
les fichiers `render.yaml` et `Dockerfile` pour le détail. Fonctionne aussi
sur Railway ou Fly.io (`Procfile` fourni).

## Sécurité

Les comptes créés par `seed_demo` sont des comptes de **démonstration à
mots de passe publics**. Pour une utilisation réelle : changez tous les
mots de passe (Administration → Utilisateurs), supprimez les comptes
inutiles et créez les comptes réels de vos agents avec leurs rôles.
