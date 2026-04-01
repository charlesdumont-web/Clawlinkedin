"""
Planificateur de publications LinkedIn.
Gère le stockage et l'exécution des posts planifiés.
"""
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.table import Table

console = Console()

POSTS_FILE = Path("data/posts.json")


def _load_posts() -> list[dict]:
    """Charge les posts planifiés depuis le fichier JSON."""
    if not POSTS_FILE.exists():
        return []
    try:
        return json.loads(POSTS_FILE.read_text())
    except (json.JSONDecodeError, IOError):
        return []


def _save_posts(posts: list[dict]):
    """Sauvegarde les posts planifiés."""
    POSTS_FILE.parent.mkdir(exist_ok=True)
    POSTS_FILE.write_text(json.dumps(posts, indent=2, ensure_ascii=False))


def add_scheduled_post(content: str, scheduled_at: str) -> dict:
    """
    Ajoute un post à la file de planification.

    Args:
        content: Texte du post LinkedIn
        scheduled_at: Date/heure ISO 8601 (ex: "2024-01-15T09:00:00")

    Returns:
        Le post planifié avec son ID
    """
    # Valider et normaliser la date
    try:
        dt = datetime.fromisoformat(scheduled_at)
    except ValueError as e:
        raise ValueError(f"Format de date invalide : {scheduled_at}. Utilisez ISO 8601 (ex: 2024-01-15T09:00:00)") from e

    if dt < datetime.now():
        raise ValueError(f"La date {scheduled_at} est dans le passé")

    post = {
        "id": str(uuid.uuid4())[:8],
        "content": content,
        "scheduled_at": dt.isoformat(),
        "status": "scheduled",
        "created_at": datetime.now().isoformat(),
        "published_at": None,
        "linkedin_post_id": None,
    }

    posts = _load_posts()
    posts.append(post)
    posts.sort(key=lambda p: p["scheduled_at"])
    _save_posts(posts)

    return post


def list_scheduled_posts(status: Optional[str] = None) -> list[dict]:
    """
    Liste les posts planifiés.

    Args:
        status: Filtrer par statut ("scheduled", "published", "failed", None=tous)
    """
    posts = _load_posts()
    if status:
        posts = [p for p in posts if p["status"] == status]
    return posts


def cancel_post(post_id: str) -> bool:
    """
    Annule un post planifié.

    Returns:
        True si trouvé et annulé, False sinon
    """
    posts = _load_posts()
    for post in posts:
        if post["id"] == post_id and post["status"] == "scheduled":
            post["status"] = "cancelled"
            _save_posts(posts)
            return True
    return False


def mark_published(post_id: str, linkedin_post_id: str):
    """Marque un post comme publié."""
    posts = _load_posts()
    for post in posts:
        if post["id"] == post_id:
            post["status"] = "published"
            post["published_at"] = datetime.now().isoformat()
            post["linkedin_post_id"] = linkedin_post_id
            _save_posts(posts)
            return
    raise ValueError(f"Post {post_id} introuvable")


def mark_failed(post_id: str, error: str):
    """Marque un post comme échoué."""
    posts = _load_posts()
    for post in posts:
        if post["id"] == post_id:
            post["status"] = "failed"
            post["error"] = error
            _save_posts(posts)
            return


def get_due_posts() -> list[dict]:
    """Retourne les posts dont la date de publication est atteinte."""
    now = datetime.now()
    posts = _load_posts()
    return [
        p for p in posts
        if p["status"] == "scheduled"
        and datetime.fromisoformat(p["scheduled_at"]) <= now
    ]


def display_scheduled_posts():
    """Affiche un tableau des posts planifiés."""
    posts = list_scheduled_posts()

    if not posts:
        console.print("[yellow]Aucun post dans la file de publication.[/yellow]")
        return

    table = Table(title="📅 File de publication LinkedIn", show_lines=True)
    table.add_column("ID", style="dim", width=10)
    table.add_column("Date planifiée", style="cyan", width=20)
    table.add_column("Statut", width=12)
    table.add_column("Aperçu du post", width=50)

    status_styles = {
        "scheduled": "[yellow]⏰ planifié[/yellow]",
        "published": "[green]✅ publié[/green]",
        "failed": "[red]❌ échoué[/red]",
        "cancelled": "[dim]🚫 annulé[/dim]",
    }

    for post in posts:
        dt = datetime.fromisoformat(post["scheduled_at"])
        date_str = dt.strftime("%d/%m/%Y %H:%M")
        preview = post["content"][:80].replace("\n", " ") + ("..." if len(post["content"]) > 80 else "")
        status = status_styles.get(post["status"], post["status"])
        table.add_row(post["id"], date_str, status, preview)

    console.print(table)
