#!/usr/bin/env python3
"""
Agent LinkedIn - Responsable des réseaux sociaux propulsé par Claude.

Lance l'agent interactif pour gérer tes publications LinkedIn.
"""
import json
import os
import sys
from pathlib import Path

import anthropic
import click
import schedule
import time
import threading
from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.rule import Rule
from rich.text import Text

# Charger les variables d'environnement
load_dotenv()

from agent import tools as agent_tools
from agent import linkedin_client, scheduler

console = Console()

AGENT_SYSTEM_PROMPT = """Tu es un responsable des réseaux sociaux expert, spécialisé dans LinkedIn.
Tu aides l'utilisateur à créer, planifier et publier du contenu LinkedIn engageant.

## Ton rôle
- Proposer des idées de posts adaptées au secteur de l'utilisateur
- Générer des posts LinkedIn de haute qualité via l'outil generate_linkedin_post
- Planifier les publications aux meilleures heures via schedule_post
- Publier directement sur LinkedIn via post_to_linkedin_now
- Maintenir un rythme régulier de publication (recommandé : 3-5 posts/semaine)

## Comportement
- Sois proactif : propose des idées de contenu même si l'utilisateur ne les demande pas
- Explique tes choix de format et timing
- Si l'utilisateur n'a pas d'idée, propose 3-5 sujets pertinents basés sur les tendances
- Encourage la régularité : rappelle l'importance d'un calendrier éditorial cohérent
- Parle toujours en français sauf si l'utilisateur écrit en anglais

## Meilleures heures de publication LinkedIn (heure française)
- Mardi-Jeudi : 9h, 12h, 17h30 (pics d'engagement)
- Lundi matin : 8h-9h (bonne visibilité)
- Vendredi : avant 14h (engagement baisse l'après-midi)
- Éviter : samedi, dimanche et après 20h

## Contexte utilisateur
{professional_context}

Commence par accueillir l'utilisateur chaleureusement et demande sur quoi il veut poster cette semaine
si aucune instruction n'est donnée.
"""


def run_scheduler_daemon(linkedin_tokens: dict | None):
    """Lance le démon de planification en arrière-plan."""
    def job():
        due_posts = scheduler.get_due_posts()
        for post in due_posts:
            if linkedin_tokens:
                try:
                    result = linkedin_client.create_post(
                        access_token=linkedin_tokens["access_token"],
                        person_id=linkedin_tokens["person_id"],
                        text=post["content"],
                    )
                    scheduler.mark_published(post["id"], result["post_id"])
                    console.print(f"\n[green]✅ Post {post['id']} publié automatiquement sur LinkedIn ![/green]")
                except Exception as e:
                    scheduler.mark_failed(post["id"], str(e))
                    console.print(f"\n[red]❌ Échec publication post {post['id']} : {e}[/red]")
            else:
                console.print(
                    f"\n[yellow]⚠️ Post {post['id']} arrivé à échéance mais pas de connexion LinkedIn.[/yellow]"
                    f"\nContenu : {post['content'][:100]}..."
                )

    schedule.every(1).minutes.do(job)

    def run():
        while True:
            schedule.run_pending()
            time.sleep(30)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()


def chat_loop(linkedin_tokens: dict | None = None):
    """Boucle de conversation principale avec l'agent."""
    professional_context = os.getenv("PROFESSIONAL_CONTEXT", "Non spécifié")
    language = os.getenv("POST_LANGUAGE", "fr")

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        console.print("[red]❌ ANTHROPIC_API_KEY non défini. Crée un fichier .env depuis .env.example[/red]")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    system = AGENT_SYSTEM_PROMPT.format(
        professional_context=professional_context or "Non spécifié (recommande à l'utilisateur de le configurer dans .env)"
    )

    messages = []
    # Message initial pour lancer la conversation
    messages.append({
        "role": "user",
        "content": "Bonjour ! Je suis prêt à gérer mes réseaux sociaux LinkedIn."
    })

    console.print(Rule("[bold cyan]Agent LinkedIn[/bold cyan]"))
    console.print(
        Panel(
            "[bold]Bienvenue dans ton agent LinkedIn ! 🚀[/bold]\n\n"
            "Je vais t'aider à créer et planifier tes posts LinkedIn.\n"
            "Tape [cyan]quit[/cyan] ou [cyan]exit[/cyan] pour quitter.\n"
            "Tape [cyan]posts[/cyan] pour voir ta file de publication.\n"
            "Tape [cyan]run[/cyan] pour exécuter les posts en attente.",
            border_style="cyan",
        )
    )

    if linkedin_tokens:
        console.print(f"[green]🔗 Connecté à LinkedIn en tant que {linkedin_tokens.get('name', 'utilisateur')}[/green]")
    else:
        console.print("[yellow]⚠️  Non connecté à LinkedIn. Tape 'auth' pour te connecter et publier directement.[/yellow]")

    console.print()

    # Lancer le démon de planification
    run_scheduler_daemon(linkedin_tokens)

    while True:
        # Input utilisateur
        try:
            user_input = Prompt.ask("\n[bold green]Toi[/bold green]").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]À bientôt ! 👋[/dim]")
            break

        if not user_input:
            continue

        # Commandes spéciales
        if user_input.lower() in ("quit", "exit", "q"):
            console.print("[dim]À bientôt ! 👋[/dim]")
            break

        if user_input.lower() == "posts":
            scheduler.display_scheduled_posts()
            continue

        if user_input.lower() == "auth":
            try:
                linkedin_tokens = linkedin_client.authenticate()
                console.print(f"[green]✅ Connecté en tant que {linkedin_tokens.get('name')}[/green]")
            except Exception as e:
                console.print(f"[red]❌ Erreur d'authentification : {e}[/red]")
            continue

        if user_input.lower() == "run":
            due = scheduler.get_due_posts()
            if not due:
                console.print("[yellow]Aucun post en attente de publication.[/yellow]")
            else:
                console.print(f"[cyan]{len(due)} post(s) à publier...[/cyan]")
                for post in due:
                    if linkedin_tokens:
                        try:
                            result = linkedin_client.create_post(
                                access_token=linkedin_tokens["access_token"],
                                person_id=linkedin_tokens["person_id"],
                                text=post["content"],
                            )
                            scheduler.mark_published(post["id"], result["post_id"])
                            console.print(f"[green]✅ Post {post['id']} publié ![/green]")
                        except Exception as e:
                            scheduler.mark_failed(post["id"], str(e))
                            console.print(f"[red]❌ Erreur : {e}[/red]")
                    else:
                        console.print(f"[yellow]Post {post['id']} prêt mais LinkedIn non connecté :[/yellow]")
                        console.print(Panel(post["content"][:200], border_style="yellow"))
            continue

        # Ajouter le message de l'utilisateur
        messages.append({"role": "user", "content": user_input})

        # Boucle d'appel à l'agent (avec exécution des outils)
        while True:
            response = client.messages.create(
                model="claude-opus-4-6",
                max_tokens=4096,
                system=system,
                tools=agent_tools.TOOLS,
                messages=messages,
                thinking={"type": "adaptive"},
            )

            # Ajouter la réponse de l'assistant à l'historique
            messages.append({"role": "assistant", "content": response.content})

            # Afficher le texte de l'agent
            text_blocks = [b for b in response.content if b.type == "text"]
            if text_blocks:
                agent_text = "\n".join(b.text for b in text_blocks)
                console.print(f"\n[bold cyan]Agent[/bold cyan]")
                console.print(Panel(Markdown(agent_text), border_style="cyan", padding=(0, 1)))

            # Si pas d'appel d'outil, fin du tour
            if response.stop_reason == "end_turn":
                break

            # Traiter les appels d'outils
            tool_use_blocks = [b for b in response.content if b.type == "tool_use"]
            if not tool_use_blocks:
                break

            tool_results = []
            for tool_use in tool_use_blocks:
                console.print(f"\n[dim]🔧 Exécution : {tool_use.name}...[/dim]")

                result = agent_tools.execute_tool(
                    tool_name=tool_use.name,
                    tool_input=tool_use.input,
                    linkedin_tokens=linkedin_tokens,
                )

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": json.dumps(result, ensure_ascii=False),
                })

            messages.append({"role": "user", "content": tool_results})


@click.command()
@click.option("--auth", is_flag=True, help="Se connecter à LinkedIn avant de démarrer")
@click.option("--no-auth", is_flag=True, help="Démarrer sans connexion LinkedIn (génération seulement)")
def main(auth: bool, no_auth: bool):
    """
    Agent LinkedIn - Ton responsable des réseaux sociaux IA.

    Génère, planifie et publie du contenu LinkedIn engageant
    avec l'aide de Claude.
    """
    console.print(
        Panel.fit(
            Text.from_markup(
                "[bold cyan]🤖 Agent LinkedIn[/bold cyan]\n"
                "[dim]Propulsé par Claude Opus 4.6[/dim]"
            ),
            border_style="cyan",
        )
    )

    # Vérifier la configuration
    if not os.getenv("ANTHROPIC_API_KEY"):
        console.print(
            "[red]❌ Configuration manquante !\n\n"
            "1. Copie .env.example vers .env\n"
            "2. Ajoute ta clé ANTHROPIC_API_KEY\n"
            "3. Optionnel : ajoute tes identifiants LinkedIn[/red]"
        )
        sys.exit(1)

    linkedin_tokens = None

    if not no_auth:
        # Essayer de charger les tokens existants
        existing_tokens = linkedin_client._load_tokens()
        if existing_tokens:
            try:
                profile = linkedin_client.get_profile(existing_tokens["access_token"])
                existing_tokens["person_id"] = profile.get("sub") or existing_tokens.get("person_id")
                linkedin_tokens = existing_tokens
            except Exception:
                pass

        if auth or (not linkedin_tokens and not no_auth):
            if not linkedin_tokens:
                client_id = os.getenv("LINKEDIN_CLIENT_ID")
                client_secret = os.getenv("LINKEDIN_CLIENT_SECRET")

                if client_id and client_secret:
                    if auth or Confirm.ask(
                        "\n[cyan]Veux-tu te connecter à LinkedIn pour publier directement ?[/cyan]",
                        default=False,
                    ):
                        try:
                            linkedin_tokens = linkedin_client.authenticate()
                        except Exception as e:
                            console.print(f"[yellow]⚠️ Connexion LinkedIn ignorée : {e}[/yellow]")
                else:
                    console.print(
                        "[dim]💡 Pour publier directement sur LinkedIn, ajoute "
                        "LINKEDIN_CLIENT_ID et LINKEDIN_CLIENT_SECRET dans .env[/dim]"
                    )

    # Lancer la boucle de conversation
    chat_loop(linkedin_tokens)


if __name__ == "__main__":
    main()
