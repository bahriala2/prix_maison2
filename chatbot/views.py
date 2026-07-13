from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .models import ChatMessage
from .services import LLMError, ask_llm, get_llm_config, tester_connexion


@login_required
def chat(request):
    historique = list(ChatMessage.objects.filter(utilisateur=request.user))

    if request.method == "POST":
        if "effacer" in request.POST:
            ChatMessage.objects.filter(utilisateur=request.user).delete()
            return redirect("chatbot:chat")

        if "tester" in request.POST:
            resultat = tester_connexion()
            if resultat.startswith("✅"):
                messages.success(request, resultat)
            else:
                messages.error(request, resultat)
            return redirect("chatbot:chat")

        question = request.POST.get("question", "").strip()
        if question:
            ChatMessage.objects.create(utilisateur=request.user, role="user", contenu=question)
            try:
                reponse = ask_llm(question, historique=historique)
                ChatMessage.objects.create(utilisateur=request.user, role="assistant", contenu=reponse)
            except LLMError as exc:
                messages.error(request, str(exc))
            return redirect("chatbot:chat")

    config = get_llm_config()
    cle = config["api_key"]
    return render(
        request,
        "chatbot/chat.html",
        {
            "historique": historique,
            "llm_model": config["model"],
            "llm_base_url": config["base_url"],
            "cle_detectee": bool(cle),
            "cle_masquee": f"{cle[:12]}…{cle[-4:]} ({len(cle)} caractères)" if cle else "",
            "mode_local": "openrouter" not in config["base_url"],
        },
    )
