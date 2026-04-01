"""
Gestion du profil de marque et du style rédactionnel.
Stocke et charge le profil personnalisé de l'utilisateur pour générer
du contenu toujours cohérent avec son identité professionnelle.
"""
import json
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

console = Console()

BRAND_FILE = Path("data/brand.json")


def load_brand_profile() -> dict:
    """Charge le profil de marque depuis le fichier JSON."""
    if not BRAND_FILE.exists():
        return {}
    try:
        return json.loads(BRAND_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, IOError):
        return {}


def save_brand_profile(profile: dict):
    """Sauvegarde le profil de marque."""
    BRAND_FILE.parent.mkdir(exist_ok=True)
    BRAND_FILE.write_text(json.dumps(profile, indent=2, ensure_ascii=False), encoding="utf-8")


def get_brand_context_for_prompt(profile: dict) -> str:
    """
    Génère un bloc de contexte de marque à injecter dans les prompts Claude.
    Retourne une chaîne vide si le profil est vide.
    """
    if not profile:
        return ""

    sections = []

    # Identité
    identity_parts = []
    if profile.get("name"):
        identity_parts.append(f"Nom : {profile['name']}")
    if profile.get("role"):
        identity_parts.append(f"Rôle : {profile['role']}")
    if profile.get("company"):
        identity_parts.append(f"Entreprise/Secteur : {profile['company']}")
    if profile.get("tagline"):
        identity_parts.append(f"Tagline : {profile['tagline']}")
    if identity_parts:
        sections.append("## Identité professionnelle\n" + "\n".join(identity_parts))

    # Audience et valeurs
    if profile.get("target_audience"):
        sections.append(f"## Audience cible\n{profile['target_audience']}")

    if profile.get("values"):
        sections.append("## Valeurs et positionnement\n" + "\n".join(f"- {v}" for v in profile["values"]))

    if profile.get("content_pillars"):
        sections.append(
            "## Piliers de contenu (sujets principaux)\n"
            + "\n".join(f"- {p}" for p in profile["content_pillars"])
        )

    # Style rédactionnel
    style = profile.get("style", {})
    if style:
        style_lines = []
        if style.get("tone"):
            style_lines.append(f"Ton : {style['tone']}")
        if style.get("formality"):
            style_lines.append(f"Registre : {style['formality']}")
        if style.get("sentence_style"):
            style_lines.append(f"Structure des phrases : {style['sentence_style']}")
        if style.get("emoji_usage"):
            style_lines.append(f"Emojis : {style['emoji_usage']}")
        if style.get("post_length"):
            style_lines.append(f"Longueur préférée des posts : {style['post_length']}")
        if style.get("uses_personal_stories") is not None:
            val = "Oui" if style["uses_personal_stories"] else "Non"
            style_lines.append(f"Partage d'histoires personnelles : {val}")
        if style.get("special_formatting"):
            style_lines.append(f"Mise en forme spéciale : {style['special_formatting']}")
        if style_lines:
            sections.append("## Style rédactionnel\n" + "\n".join(style_lines))

    # Éléments de signature
    signature = profile.get("signature", {})
    if signature:
        sig_lines = []
        if signature.get("opening_hooks"):
            hooks = "\n".join(f'  - "{h}"' for h in signature["opening_hooks"])
            sig_lines.append(f"Accroches favorites :\n{hooks}")
        if signature.get("cta_phrases"):
            ctas = "\n".join(f'  - "{c}"' for c in signature["cta_phrases"])
            sig_lines.append(f"Call-to-action habituels :\n{ctas}")
        if signature.get("vocabulary_to_use"):
            sig_lines.append(f"Vocabulaire à utiliser : {', '.join(signature['vocabulary_to_use'])}")
        if signature.get("vocabulary_to_avoid"):
            sig_lines.append(f"Vocabulaire à éviter : {', '.join(signature['vocabulary_to_avoid'])}")
        if signature.get("structural_pattern"):
            sig_lines.append(f"Schéma de structure : {signature['structural_pattern']}")
        if sig_lines:
            sections.append("## Éléments de signature\n" + "\n".join(sig_lines))

    # Hashtags
    if profile.get("hashtags"):
        sections.append("## Hashtags de marque\n" + " ".join(f"#{h.lstrip('#')}" for h in profile["hashtags"]))

    # Exemples de posts
    if profile.get("post_examples"):
        examples = "\n\n---\n\n".join(profile["post_examples"])
        sections.append(f"## Exemples de tes meilleurs posts (référence de style)\n{examples}")

    # Sujets à éviter
    if profile.get("topics_to_avoid"):
        sections.append(
            "## Sujets à NE PAS aborder\n"
            + "\n".join(f"- {t}" for t in profile["topics_to_avoid"])
        )

    if not sections:
        return ""

    return (
        "\n\n---\n\n# PROFIL DE MARQUE PERSONNALISÉ\n\n"
        + "\n\n".join(sections)
        + "\n\n---\n\n"
        + "**IMPORTANT : Génère tous les posts en respectant strictement ce profil de marque, "
        "le style rédactionnel et les exemples fournis ci-dessus.**"
    )


def display_brand_profile(profile: dict):
    """Affiche le profil de marque de façon lisible."""
    if not profile:
        console.print("[yellow]Aucun profil de marque configuré.[/yellow]")
        console.print("[dim]Lance 'setup' pour créer ton profil.[/dim]")
        return

    table = Table(title="🎨 Profil de Marque & Style", show_lines=True, border_style="cyan")
    table.add_column("Section", style="bold cyan", width=22)
    table.add_column("Valeur", width=55)

    def add_row(section: str, value):
        if not value:
            return
        if isinstance(value, list):
            display = "\n".join(f"• {v}" for v in value) if value else "—"
        else:
            display = str(value)
        table.add_row(section, display)

    add_row("Nom", profile.get("name"))
    add_row("Rôle", profile.get("role"))
    add_row("Entreprise/Secteur", profile.get("company"))
    add_row("Tagline", profile.get("tagline"))
    add_row("Audience cible", profile.get("target_audience"))
    add_row("Valeurs", profile.get("values"))
    add_row("Piliers de contenu", profile.get("content_pillars"))

    style = profile.get("style", {})
    if style:
        style_summary = []
        if style.get("tone"):
            style_summary.append(f"Ton : {style['tone']}")
        if style.get("formality"):
            style_summary.append(f"Registre : {style['formality']}")
        if style.get("emoji_usage"):
            style_summary.append(f"Emojis : {style['emoji_usage']}")
        if style.get("post_length"):
            style_summary.append(f"Longueur : {style['post_length']}")
        add_row("Style", "\n".join(style_summary))

    sig = profile.get("signature", {})
    if sig.get("cta_phrases"):
        add_row("CTA habituels", sig["cta_phrases"])
    if sig.get("vocabulary_to_avoid"):
        add_row("Vocab à éviter", sig["vocabulary_to_avoid"])

    if profile.get("hashtags"):
        add_row("Hashtags de marque", " ".join(f"#{h.lstrip('#')}" for h in profile["hashtags"]))

    if profile.get("post_examples"):
        add_row(f"Exemples ({len(profile['post_examples'])})", "[dim]Posts de référence chargés[/dim]")

    if profile.get("topics_to_avoid"):
        add_row("Sujets à éviter", profile["topics_to_avoid"])

    console.print(table)


def run_setup_wizard() -> dict:
    """
    Assistant de configuration guidé pour créer ou mettre à jour le profil de marque.
    """
    existing = load_brand_profile()

    console.print(
        Panel(
            "[bold]🎨 Configuration du Profil de Marque & Style[/bold]\n\n"
            "Ce profil sera utilisé pour générer du contenu LinkedIn qui te ressemble vraiment.\n"
            "[dim]Appuie sur Entrée pour garder la valeur actuelle (affichée entre crochets).[/dim]",
            border_style="cyan",
        )
    )

    def ask(prompt: str, key: str, default: str = "") -> str:
        current = existing.get(key, default)
        placeholder = f" [dim]({current})[/dim]" if current else ""
        result = Prompt.ask(f"  {prompt}{placeholder}", default=current)
        return result.strip()

    def ask_list(prompt: str, key: str) -> list[str]:
        current = existing.get(key, [])
        current_str = ", ".join(current)
        placeholder = f" [dim]({current_str})[/dim]" if current else ""
        result = Prompt.ask(
            f"  {prompt} [dim](séparés par des virgules){placeholder}[/dim]",
            default=current_str,
        )
        if not result.strip():
            return []
        return [v.strip() for v in result.split(",") if v.strip()]

    profile = dict(existing)

    # === SECTION 1 : IDENTITÉ ===
    console.print("\n[bold cyan]1. Identité professionnelle[/bold cyan]")
    profile["name"] = ask("Ton nom complet", "name")
    profile["role"] = ask("Ton titre/rôle (ex: CEO de..., Développeur senior...)", "role")
    profile["company"] = ask("Ton entreprise ou secteur", "company")
    profile["tagline"] = ask("Tagline personnelle (ex: J'aide les PME à adopter l'IA)", "tagline")

    # === SECTION 2 : AUDIENCE & CONTENU ===
    console.print("\n[bold cyan]2. Audience & Piliers de contenu[/bold cyan]")
    profile["target_audience"] = ask(
        "Décris ton audience cible (ex: directeurs RH de PME, devs juniors...)",
        "target_audience",
    )
    profile["values"] = ask_list(
        "Tes valeurs professionnelles (ex: transparence, innovation, humilité)",
        "values",
    )
    profile["content_pillars"] = ask_list(
        "Tes piliers de contenu - sujets principaux (ex: IA, management, startups)",
        "content_pillars",
    )

    # === SECTION 3 : STYLE RÉDACTIONNEL ===
    console.print("\n[bold cyan]3. Style rédactionnel[/bold cyan]")

    style = dict(existing.get("style", {}))

    tone_options = ["inspirant", "éducatif", "provocateur", "personnel", "analytique", "humoristique"]
    console.print(f"  Options de ton : {', '.join(tone_options)}")
    style["tone"] = ask("Ton principal", "tone") if "tone" not in profile.get("style", {}) else ask("Ton principal", "tone", profile.get("style", {}).get("tone", ""))

    formality_options = ["très informel (tutoiement, argot)", "informel", "professionnel", "très formel"]
    console.print(f"  Options : {', '.join(formality_options)}")
    current_formality = existing.get("style", {}).get("formality", "")
    formality_raw = Prompt.ask(f"  Registre de langue [dim]({current_formality})[/dim]", default=current_formality)
    style["formality"] = formality_raw.strip()

    emoji_options = ["aucun", "très peu (1-2 par post)", "modéré (3-5)", "beaucoup"]
    console.print(f"  Options emojis : {', '.join(emoji_options)}")
    current_emoji = existing.get("style", {}).get("emoji_usage", "")
    emoji_raw = Prompt.ask(f"  Utilisation des emojis [dim]({current_emoji})[/dim]", default=current_emoji)
    style["emoji_usage"] = emoji_raw.strip()

    length_options = ["court (<300 car.)", "moyen (300-800)", "long (800-1500)", "très long (>1500)"]
    console.print(f"  Options longueur : {', '.join(length_options)}")
    current_length = existing.get("style", {}).get("post_length", "")
    length_raw = Prompt.ask(f"  Longueur préférée des posts [dim]({current_length})[/dim]", default=current_length)
    style["post_length"] = length_raw.strip()

    sentence_options = ["phrases courtes et percutantes", "phrases moyennes équilibrées", "phrases longues et détaillées"]
    console.print(f"  Options : {', '.join(sentence_options)}")
    current_sent = existing.get("style", {}).get("sentence_style", "")
    sent_raw = Prompt.ask(f"  Style de phrases [dim]({current_sent})[/dim]", default=current_sent)
    style["sentence_style"] = sent_raw.strip()

    current_stories = existing.get("style", {}).get("uses_personal_stories", True)
    style["uses_personal_stories"] = Confirm.ask(
        "  Tu partages des histoires personnelles dans tes posts ?",
        default=current_stories,
    )

    profile["style"] = style

    # === SECTION 4 : SIGNATURE ===
    console.print("\n[bold cyan]4. Éléments de signature[/bold cyan]")
    signature = dict(existing.get("signature", {}))

    console.print("  Exemples d'accroches : 'La vérité que personne ne dit...', 'J'ai fait une erreur...'")
    current_hooks = existing.get("signature", {}).get("opening_hooks", [])
    hooks_raw = Prompt.ask(
        f"  Tes accroches/ouvertures préférées [dim]({', '.join(current_hooks)})[/dim]",
        default=", ".join(current_hooks),
    )
    signature["opening_hooks"] = [h.strip() for h in hooks_raw.split(",") if h.strip()]

    console.print("  Exemples de CTA : 'Qu'en pensez-vous ?', 'Partagez votre expérience ↓'")
    current_ctas = existing.get("signature", {}).get("cta_phrases", [])
    ctas_raw = Prompt.ask(
        f"  Tes call-to-action habituels [dim]({', '.join(current_ctas)})[/dim]",
        default=", ".join(current_ctas),
    )
    signature["cta_phrases"] = [c.strip() for c in ctas_raw.split(",") if c.strip()]

    current_vocab_use = existing.get("signature", {}).get("vocabulary_to_use", [])
    vocab_use_raw = Prompt.ask(
        f"  Vocabulaire/expressions à utiliser [dim]({', '.join(current_vocab_use)})[/dim]",
        default=", ".join(current_vocab_use),
    )
    signature["vocabulary_to_use"] = [v.strip() for v in vocab_use_raw.split(",") if v.strip()]

    current_vocab_avoid = existing.get("signature", {}).get("vocabulary_to_avoid", [])
    vocab_avoid_raw = Prompt.ask(
        f"  Expressions/mots à éviter [dim]({', '.join(current_vocab_avoid)})[/dim]",
        default=", ".join(current_vocab_avoid),
    )
    signature["vocabulary_to_avoid"] = [v.strip() for v in vocab_avoid_raw.split(",") if v.strip()]

    profile["signature"] = signature

    # === SECTION 5 : HASHTAGS ===
    console.print("\n[bold cyan]5. Hashtags & exclusions[/bold cyan]")
    profile["hashtags"] = ask_list(
        "Hashtags de marque à toujours inclure (sans #)",
        "hashtags",
    )
    profile["topics_to_avoid"] = ask_list(
        "Sujets à ne JAMAIS aborder",
        "topics_to_avoid",
    )

    # === SECTION 6 : EXEMPLES DE POSTS ===
    console.print("\n[bold cyan]6. Exemples de tes meilleurs posts[/bold cyan]")
    console.print(
        "  [dim]Coller tes meilleurs posts permet à l'agent de capturer ton style exact.\n"
        "  Tape chaque post puis Entrée, puis 'fin' quand terminé.[/dim]"
    )

    existing_examples = existing.get("post_examples", [])
    if existing_examples:
        console.print(f"  [dim]{len(existing_examples)} exemple(s) déjà enregistré(s)[/dim]")
        if not Confirm.ask("  Veux-tu ajouter de nouveaux exemples ?", default=False):
            profile["post_examples"] = existing_examples
        else:
            examples = list(existing_examples)
            console.print("  [dim]Colle ton post et appuie sur Entrée deux fois. Tape 'fin' pour terminer.[/dim]")
            while True:
                lines = []
                while True:
                    line = Prompt.ask("  ", default="")
                    if line.strip().lower() == "fin":
                        break
                    if line == "" and lines and lines[-1] == "":
                        break
                    lines.append(line)
                post_text = "\n".join(lines).strip()
                if not post_text or post_text.lower() == "fin":
                    break
                examples.append(post_text)
                console.print(f"  [green]✓ Exemple {len(examples)} ajouté[/green]")
                if not Confirm.ask("  Ajouter un autre exemple ?", default=False):
                    break
            profile["post_examples"] = examples
    else:
        examples = []
        if Confirm.ask("  Veux-tu ajouter des exemples de tes posts LinkedIn ? (recommandé)", default=True):
            console.print("  [dim]Colle chaque post et appuie sur Entrée. Tape 'fin' pour terminer.[/dim]")
            while True:
                lines = []
                while True:
                    line = Prompt.ask("  ", default="")
                    if line.strip().lower() == "fin":
                        break
                    if line == "" and lines and lines[-1] == "":
                        break
                    lines.append(line)
                post_text = "\n".join(lines).strip()
                if not post_text or post_text.lower() == "fin":
                    break
                examples.append(post_text)
                console.print(f"  [green]✓ Exemple {len(examples)} ajouté[/green]")
                if not Confirm.ask("  Ajouter un autre exemple ?", default=False):
                    break
        profile["post_examples"] = examples

    # Sauvegarder
    save_brand_profile(profile)
    console.print("\n[green]✅ Profil de marque sauvegardé ![/green]")
    display_brand_profile(profile)

    return profile


def update_field(field_path: str, value) -> dict:
    """
    Met à jour un champ spécifique du profil.

    Args:
        field_path: Chemin du champ (ex: "style.tone", "name", "hashtags")
        value: Nouvelle valeur

    Returns:
        Profil mis à jour
    """
    profile = load_brand_profile()
    keys = field_path.split(".")

    if len(keys) == 1:
        profile[keys[0]] = value
    elif len(keys) == 2:
        if keys[0] not in profile:
            profile[keys[0]] = {}
        profile[keys[0]][keys[1]] = value
    else:
        raise ValueError(f"Chemin trop profond : {field_path}")

    save_brand_profile(profile)
    return profile
