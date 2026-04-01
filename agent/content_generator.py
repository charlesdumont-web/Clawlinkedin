"""
Génération de contenu LinkedIn via Claude Opus 4.6.
Utilise le streaming pour une expérience interactive.
"""
import os
from typing import Optional

import anthropic
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel

console = Console()

SYSTEM_PROMPT = """Tu es un expert en personal branding et content marketing LinkedIn.
Tu aides à créer du contenu LinkedIn authentique, engageant et professionnel.

## Règles pour les posts LinkedIn

**Format et structure :**
- Commence par une accroche forte (1-2 lignes qui donnent envie de cliquer "Voir plus")
- Structure claire avec des sauts de ligne pour la lisibilité
- Maximum 3000 caractères (sweet spot : 150-400 caractères pour du trafic, 1000-1500 pour de l'engagement)
- Utilise des emojis avec parcimonie (2-4 maximum par post)
- Terminer par une question ou un call-to-action pour encourager les commentaires

**Ton et style :**
- Authentique et personnel, pas corporate
- Direct et concret, évite le jargon vide de sens
- Partage de valeur réelle : insights, apprentissages, expériences
- Première personne ("je", "nous") pour plus d'authenticité

**Types de posts performants :**
- 📖 Storytelling : raconte une expérience personnelle avec une leçon
- 💡 Insight : partage une observation ou apprentissage contre-intuitif
- 🔢 Liste : "5 choses que j'ai apprises sur X"
- ❓ Question : stimule le débat sur un sujet de ton secteur
- 🎯 Conseil actionnable : tip pratique immédiatement utilisable
- 📊 Données : chiffre surprenant + analyse + implication

**Hashtags :**
- 3-5 hashtags pertinents à la fin
- Mix de hashtags larges (#leadership) et de niche (#promptengineering)

Contexte professionnel de l'utilisateur : {professional_context}
Langue : {language}

Génère du contenu toujours adapté au secteur et à l'audience de l'utilisateur.
"""


def _get_client() -> anthropic.Anthropic:
    """Retourne le client Anthropic initialisé."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY non défini dans .env")
    return anthropic.Anthropic(api_key=api_key)


def generate_post(
    topic: str,
    post_type: str = "insight",
    tone: str = "professionnel et authentique",
    additional_context: str = "",
) -> str:
    """
    Génère un post LinkedIn sur un sujet donné.

    Args:
        topic: Sujet du post
        post_type: Type de post (storytelling, insight, liste, question, conseil, données)
        tone: Ton souhaité
        additional_context: Contexte supplémentaire fourni par l'utilisateur

    Returns:
        Le contenu du post LinkedIn généré
    """
    professional_context = os.getenv("PROFESSIONAL_CONTEXT", "professionnel polyvalent")
    language = os.getenv("POST_LANGUAGE", "fr")
    lang_instruction = "en français" if language == "fr" else "in English"

    client = _get_client()

    system = SYSTEM_PROMPT.format(
        professional_context=professional_context,
        language=lang_instruction,
    )

    user_message = f"""Génère un post LinkedIn de type "{post_type}" sur le sujet suivant :

**Sujet :** {topic}
**Ton :** {tone}
**Langue :** {lang_instruction}
{f"**Contexte supplémentaire :** {additional_context}" if additional_context else ""}

Génère UNIQUEMENT le contenu du post (prêt à copier-coller), sans commentaires ni explications."""

    console.print(f"\n[cyan]✍️ Génération du post en cours...[/cyan]\n")

    full_content = ""

    with Live(console=console, refresh_per_second=10) as live:
        with client.messages.stream(
            model="claude-opus-4-6",
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": user_message}],
            thinking={"type": "adaptive"},
        ) as stream:
            for text in stream.text_stream:
                full_content += text
                live.update(
                    Panel(
                        Markdown(full_content),
                        title="[bold cyan]Post LinkedIn généré[/bold cyan]",
                        border_style="cyan",
                        padding=(1, 2),
                    )
                )

    char_count = len(full_content)
    style = "green" if char_count <= 1500 else "yellow" if char_count <= 3000 else "red"
    console.print(f"[{style}]📊 {char_count} caractères[/{style}] (max LinkedIn : 3000)")

    return full_content


def generate_weekly_plan(
    themes: list[str],
    posts_per_week: int = 3,
) -> list[dict]:
    """
    Génère un plan de contenu pour la semaine.

    Args:
        themes: Liste de thèmes pour la semaine
        posts_per_week: Nombre de posts par semaine (défaut: 3)

    Returns:
        Liste de posts avec leur type et contenu suggéré
    """
    professional_context = os.getenv("PROFESSIONAL_CONTEXT", "professionnel polyvalent")
    language = os.getenv("POST_LANGUAGE", "fr")
    lang_instruction = "en français" if language == "fr" else "in English"

    client = _get_client()

    system = SYSTEM_PROMPT.format(
        professional_context=professional_context,
        language=lang_instruction,
    )

    themes_str = "\n".join(f"- {t}" for t in themes)
    post_types = ["storytelling", "insight", "liste", "conseil", "question", "données"]

    user_message = f"""Crée un plan de contenu LinkedIn pour la semaine.

**Thèmes disponibles :**
{themes_str}

**Nombre de posts :** {posts_per_week} posts cette semaine
**Langue :** {lang_instruction}

Pour chaque post, fournis :
1. Le TYPE de post (parmi : {', '.join(post_types)})
2. Le JOUR suggéré (Lundi, Mardi, Mercredi, Jeudi, Vendredi)
3. L'HEURE suggérée (optimale pour l'engagement LinkedIn)
4. Le CONTENU COMPLET du post (prêt à publier)

Sépare chaque post par "---POST---"
Format pour chaque post :
TYPE: [type]
JOUR: [jour]
HEURE: [heure]
---
[contenu complet du post]"""

    console.print(f"\n[cyan]📅 Génération du plan de contenu pour {posts_per_week} posts...[/cyan]\n")

    full_response = ""

    with Live(console=console, refresh_per_second=10) as live:
        with client.messages.stream(
            model="claude-opus-4-6",
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": user_message}],
            thinking={"type": "adaptive"},
        ) as stream:
            for text in stream.text_stream:
                full_response += text
                live.update(
                    Panel(
                        Markdown(full_response),
                        title="[bold cyan]Plan de contenu hebdomadaire[/bold cyan]",
                        border_style="cyan",
                        padding=(1, 2),
                    )
                )

    # Parser les posts du plan
    posts = []
    raw_posts = full_response.split("---POST---")
    for raw in raw_posts:
        raw = raw.strip()
        if not raw:
            continue
        try:
            lines = raw.split("\n")
            post_type = next((l.replace("TYPE:", "").strip() for l in lines if l.startswith("TYPE:")), "insight")
            day = next((l.replace("JOUR:", "").strip() for l in lines if l.startswith("JOUR:")), "Lundi")
            hour = next((l.replace("HEURE:", "").strip() for l in lines if l.startswith("HEURE:")), "09:00")

            # Le contenu est tout ce qui suit "---"
            separator_idx = raw.find("\n---\n")
            content = raw[separator_idx + 4:].strip() if separator_idx != -1 else raw

            posts.append({
                "type": post_type,
                "day": day,
                "hour": hour,
                "content": content,
            })
        except Exception:
            continue

    return posts


def refine_post(original_post: str, feedback: str) -> str:
    """
    Affine un post existant selon les retours de l'utilisateur.

    Args:
        original_post: Le post original à améliorer
        feedback: Les instructions de modification

    Returns:
        La version améliorée du post
    """
    professional_context = os.getenv("PROFESSIONAL_CONTEXT", "professionnel polyvalent")
    language = os.getenv("POST_LANGUAGE", "fr")
    lang_instruction = "en français" if language == "fr" else "in English"

    client = _get_client()

    system = SYSTEM_PROMPT.format(
        professional_context=professional_context,
        language=lang_instruction,
    )

    user_message = f"""Voici un post LinkedIn à améliorer :

---
{original_post}
---

**Instructions de modification :** {feedback}

Génère UNIQUEMENT la version améliorée du post, sans commentaires."""

    console.print(f"\n[cyan]✏️ Amélioration du post en cours...[/cyan]\n")

    full_content = ""

    with Live(console=console, refresh_per_second=10) as live:
        with client.messages.stream(
            model="claude-opus-4-6",
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": user_message}],
        ) as stream:
            for text in stream.text_stream:
                full_content += text
                live.update(
                    Panel(
                        Markdown(full_content),
                        title="[bold cyan]Post amélioré[/bold cyan]",
                        border_style="cyan",
                        padding=(1, 2),
                    )
                )

    return full_content
