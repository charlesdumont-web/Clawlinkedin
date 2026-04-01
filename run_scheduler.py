#!/usr/bin/env python3
"""
Démon de planification autonome.

Lance ce script en arrière-plan pour que les posts planifiés
soient publiés automatiquement à leur heure.

Usage:
    python run_scheduler.py
    # ou en arrière-plan :
    nohup python run_scheduler.py > scheduler.log 2>&1 &
"""
import json
import os
import time
from datetime import datetime

import schedule
from dotenv import load_dotenv
from rich.console import Console

load_dotenv()

from agent import linkedin_client, scheduler

console = Console()


def publish_due_posts():
    """Publie les posts arrivés à échéance."""
    due = scheduler.get_due_posts()
    if not due:
        return

    console.print(f"[cyan]{datetime.now().strftime('%H:%M:%S')} — {len(due)} post(s) à publier[/cyan]")

    # Charger les tokens LinkedIn
    tokens = linkedin_client._load_tokens()
    if not tokens:
        console.print("[red]❌ Pas de token LinkedIn. Lance 'python main.py --auth' d'abord.[/red]")
        return

    for post in due:
        try:
            result = linkedin_client.create_post(
                access_token=tokens["access_token"],
                person_id=tokens["person_id"],
                text=post["content"],
            )
            scheduler.mark_published(post["id"], result["post_id"])
            console.print(f"[green]✅ Post {post['id']} publié ! LinkedIn ID: {result['post_id']}[/green]")
        except Exception as e:
            scheduler.mark_failed(post["id"], str(e))
            console.print(f"[red]❌ Échec post {post['id']} : {e}[/red]")


def main():
    console.print("[bold cyan]🤖 Démon de planification LinkedIn démarré[/bold cyan]")
    console.print("[dim]Vérification toutes les minutes. Ctrl+C pour arrêter.[/dim]\n")

    # Vérification immédiate au démarrage
    publish_due_posts()

    # Planifier les vérifications toutes les minutes
    schedule.every(1).minutes.do(publish_due_posts)

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[dim]Démon arrêté.[/dim]")
