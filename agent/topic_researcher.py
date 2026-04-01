"""
Recherche de sujets tendance pour LinkedIn.
Utilise Claude avec le tool web_search pour trouver des sujets pertinents
dans le secteur de l'utilisateur.
"""
import json
import os
from datetime import datetime
from typing import Optional

import anthropic
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

console = Console()


def _get_client() -> anthropic.Anthropic:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY non défini dans .env")
    return anthropic.Anthropic(api_key=api_key)


def research_trending_topics(
    industry: str,
    content_pillars: Optional[list[str]] = None,
    count: int = 10,
    language: str = "fr",
) -> list[dict]:
    """
    Recherche les sujets tendance sur LinkedIn dans un secteur donné.

    Args:
        industry: Secteur/domaine à explorer (ex: "intelligence artificielle", "RH", "startup")
        content_pillars: Piliers de contenu de l'utilisateur pour filtrer la pertinence
        count: Nombre de sujets à retourner
        language: Langue des résultats ("fr" ou "en")

    Returns:
        Liste de sujets avec titre, description, type de post suggéré, et source
    """
    client = _get_client()
    lang_instr = "en français" if language == "fr" else "in English"
    pillars_context = ""
    if content_pillars:
        pillars_context = f"\nSes piliers de contenu : {', '.join(content_pillars)}"

    today = datetime.now().strftime("%d %B %Y")

    search_prompt = f"""Tu es un veilleur de contenu expert LinkedIn.

Date du jour : {today}
Secteur à analyser : {industry}{pillars_context}
Langue de réponse : {lang_instr}

Effectue des recherches web pour trouver :
1. Les sujets et débats chauds du moment dans {industry}
2. Les actualités récentes qui font réagir les professionnels
3. Les questions récurrentes que se posent les gens du secteur
4. Les erreurs communes ou mythes à déconstruire
5. Les nouvelles tendances/outils/pratiques qui émergent

Pour chaque sujet trouvé, propose une IDÉE DE POST LinkedIn créative et engageante.

Retourne EXACTEMENT {count} idées de posts au format JSON :
```json
[
  {{
    "title": "Titre court et accrocheur du sujet",
    "description": "Contexte et angle proposé pour le post (2-3 phrases)",
    "post_type": "storytelling|insight|liste|conseil|question|données",
    "hook": "Première phrase d'accroche proposée pour le post",
    "hashtags": ["hashtag1", "hashtag2", "hashtag3"],
    "source_context": "D'où vient ce sujet / quelle actualité le justifie"
  }}
]
```

Assure-toi que les sujets sont VRAIMENT d'actualité et pertinents pour LinkedIn aujourd'hui."""

    console.print(f"\n[cyan]🔍 Recherche de sujets tendance en cours pour : {industry}...[/cyan]\n")

    # Utiliser Claude avec web search
    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=4096,
        tools=[
            {"type": "web_search_20260209", "name": "web_search"},
        ],
        messages=[{"role": "user", "content": search_prompt}],
        thinking={"type": "adaptive"},
    )

    # Extraire le JSON de la réponse
    full_text = ""
    for block in response.content:
        if block.type == "text":
            full_text += block.text

    # Parser le JSON
    topics = _parse_topics_from_response(full_text, count)

    if topics:
        _display_topics(topics, industry)
    else:
        console.print("[yellow]Impossible de parser les résultats. Voici la réponse brute :[/yellow]")
        console.print(Panel(full_text[:1000], border_style="yellow"))

    return topics


def _parse_topics_from_response(text: str, expected_count: int) -> list[dict]:
    """Extrait et parse les topics JSON depuis la réponse de Claude."""
    # Chercher un bloc JSON dans la réponse
    import re

    # Chercher ```json ... ``` ou juste le tableau JSON
    patterns = [
        r"```json\s*([\s\S]*?)\s*```",
        r"```\s*([\[{][\s\S]*?)\s*```",
        r"(\[[\s\S]*\])",
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text, re.MULTILINE)
        for match in matches:
            try:
                data = json.loads(match)
                if isinstance(data, list) and data:
                    # Valider la structure minimale
                    valid = []
                    for item in data:
                        if isinstance(item, dict) and "title" in item:
                            valid.append({
                                "title": item.get("title", ""),
                                "description": item.get("description", ""),
                                "post_type": item.get("post_type", "insight"),
                                "hook": item.get("hook", ""),
                                "hashtags": item.get("hashtags", []),
                                "source_context": item.get("source_context", ""),
                            })
                    if valid:
                        return valid[:expected_count]
            except json.JSONDecodeError:
                continue

    return []


def _display_topics(topics: list[dict], industry: str):
    """Affiche les sujets trouvés dans un tableau."""
    table = Table(
        title=f"💡 {len(topics)} idées de posts LinkedIn — {industry}",
        show_lines=True,
        border_style="cyan",
    )
    table.add_column("#", style="dim", width=3)
    table.add_column("Sujet", style="bold", width=30)
    table.add_column("Type", style="cyan", width=14)
    table.add_column("Accroche proposée", width=40)

    type_emojis = {
        "storytelling": "📖",
        "insight": "💡",
        "liste": "🔢",
        "conseil": "🎯",
        "question": "❓",
        "données": "📊",
    }

    for i, topic in enumerate(topics, 1):
        emoji = type_emojis.get(topic["post_type"], "📝")
        table.add_row(
            str(i),
            topic["title"],
            f"{emoji} {topic['post_type']}",
            topic.get("hook", topic["description"][:80]),
        )

    console.print(table)


def get_content_ideas_from_news(
    keywords: list[str],
    language: str = "fr",
) -> list[dict]:
    """
    Recherche des actualités récentes liées aux mots-clés et génère des idées de posts.

    Args:
        keywords: Mots-clés pour la recherche
        language: Langue des résultats

    Returns:
        Liste d'idées de posts basées sur l'actualité
    """
    client = _get_client()
    lang_instr = "en français" if language == "fr" else "in English"
    keywords_str = ", ".join(keywords)
    today = datetime.now().strftime("%d %B %Y")

    prompt = f"""Date : {today}
Recherche les dernières actualités et discussions autour de : {keywords_str}
Langue de réponse : {lang_instr}

Pour chaque actualité pertinente trouvée, propose comment en faire un post LinkedIn engageant.
L'angle doit être personnel et apporter de la valeur (pas juste partager l'info).

Retourne 5 idées au format JSON :
```json
[
  {{
    "news_headline": "Titre de l'actualité source",
    "linkedin_angle": "Comment aborder ce sujet pour LinkedIn (angle personnel, leçon, opinion)",
    "post_type": "storytelling|insight|liste|conseil|question|données",
    "hook": "Première phrase d'accroche",
    "why_timely": "Pourquoi c'est pertinent MAINTENANT"
  }}
]
```"""

    console.print(f"\n[cyan]📰 Recherche d'actualités pour : {keywords_str}...[/cyan]\n")

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=2048,
        tools=[{"type": "web_search_20260209", "name": "web_search"}],
        messages=[{"role": "user", "content": prompt}],
    )

    full_text = "".join(block.text for block in response.content if block.type == "text")
    ideas = _parse_news_ideas(full_text)

    if ideas:
        _display_news_ideas(ideas, keywords_str)

    return ideas


def _parse_news_ideas(text: str) -> list[dict]:
    """Parse les idées basées sur les actualités."""
    import re

    patterns = [r"```json\s*([\s\S]*?)\s*```", r"(\[[\s\S]*\])"]

    for pattern in patterns:
        matches = re.findall(pattern, text, re.MULTILINE)
        for match in matches:
            try:
                data = json.loads(match)
                if isinstance(data, list):
                    return data
            except json.JSONDecodeError:
                continue
    return []


def _display_news_ideas(ideas: list[dict], keywords: str):
    """Affiche les idées basées sur l'actualité."""
    table = Table(
        title=f"📰 Idées basées sur l'actualité — {keywords}",
        show_lines=True,
        border_style="yellow",
    )
    table.add_column("#", style="dim", width=3)
    table.add_column("Actualité", width=28)
    table.add_column("Angle LinkedIn", width=35)
    table.add_column("Pourquoi maintenant", width=25)

    for i, idea in enumerate(ideas, 1):
        table.add_row(
            str(i),
            idea.get("news_headline", "")[:60],
            idea.get("linkedin_angle", "")[:80],
            idea.get("why_timely", "")[:50],
        )

    console.print(table)
