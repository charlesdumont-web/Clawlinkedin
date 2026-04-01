"""
Client LinkedIn avec authentification OAuth2 PKCE et API de publication.
"""
import base64
import hashlib
import json
import os
import secrets
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import requests
from rich.console import Console

console = Console()

TOKENS_FILE = Path(".tokens.json")
LINKEDIN_AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
LINKEDIN_API_BASE = "https://api.linkedin.com/v2"
SCOPES = "openid profile w_member_social"


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """Serveur HTTP local pour capturer le callback OAuth2."""

    auth_code = None
    error = None

    def do_GET(self):
        params = parse_qs(urlparse(self.path).query)
        if "code" in params:
            OAuthCallbackHandler.auth_code = params["code"][0]
            self._respond("Authentification réussie ! Vous pouvez fermer cet onglet.")
        elif "error" in params:
            OAuthCallbackHandler.error = params.get("error_description", ["Erreur inconnue"])[0]
            self._respond(f"Erreur : {OAuthCallbackHandler.error}")
        else:
            self._respond("Callback reçu mais aucun code trouvé.")

    def _respond(self, message: str):
        html = f"""<!DOCTYPE html><html><body style="font-family:sans-serif;text-align:center;padding:50px">
        <h2>✅ {message}</h2><p>Retournez dans votre terminal.</p></body></html>"""
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode())

    def log_message(self, format, *args):
        pass  # Silences les logs du serveur HTTP


def _generate_pkce_pair() -> tuple[str, str]:
    """Génère un code_verifier et code_challenge pour PKCE."""
    code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()
    digest = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return code_verifier, code_challenge


def _load_tokens() -> dict | None:
    """Charge les tokens sauvegardés."""
    if TOKENS_FILE.exists():
        try:
            return json.loads(TOKENS_FILE.read_text())
        except (json.JSONDecodeError, IOError):
            return None
    return None


def _save_tokens(tokens: dict):
    """Sauvegarde les tokens."""
    TOKENS_FILE.write_text(json.dumps(tokens, indent=2))


def authenticate() -> dict:
    """
    Lance le flux OAuth2 PKCE LinkedIn.
    Ouvre le navigateur, attend le callback, retourne les tokens.
    """
    client_id = os.getenv("LINKEDIN_CLIENT_ID")
    client_secret = os.getenv("LINKEDIN_CLIENT_SECRET")
    redirect_uri = os.getenv("LINKEDIN_REDIRECT_URI", "http://localhost:8080/callback")

    if not client_id or not client_secret:
        raise ValueError(
            "LINKEDIN_CLIENT_ID et LINKEDIN_CLIENT_SECRET doivent être définis dans .env"
        )

    # Vérifier si un token valide existe
    tokens = _load_tokens()
    if tokens and tokens.get("access_token"):
        # Vérifier que le token fonctionne encore
        try:
            profile = get_profile(tokens["access_token"])
            console.print(f"[green]✓ Connecté en tant que {profile.get('name', 'utilisateur')}[/green]")
            return tokens
        except requests.HTTPError:
            console.print("[yellow]Token expiré, reconnexion...[/yellow]")

    code_verifier, code_challenge = _generate_pkce_pair()
    state = secrets.token_urlsafe(16)

    parsed_redirect = urlparse(redirect_uri)
    port = parsed_redirect.port or 8080

    # Construire l'URL d'autorisation
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": SCOPES,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    auth_url = f"{LINKEDIN_AUTH_URL}?{urlencode(params)}"

    # Réinitialiser les valeurs du handler
    OAuthCallbackHandler.auth_code = None
    OAuthCallbackHandler.error = None

    # Démarrer le serveur local
    server = HTTPServer(("localhost", port), OAuthCallbackHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    console.print(f"\n[bold cyan]Ouverture du navigateur pour l'authentification LinkedIn...[/bold cyan]")
    console.print(f"Si le navigateur ne s'ouvre pas, allez sur :\n[link]{auth_url}[/link]\n")
    webbrowser.open(auth_url)

    # Attendre le callback (timeout 120s)
    timeout = 120
    start = time.time()
    while not OAuthCallbackHandler.auth_code and not OAuthCallbackHandler.error:
        if time.time() - start > timeout:
            server.shutdown()
            raise TimeoutError("Timeout de l'authentification LinkedIn (120s)")
        time.sleep(0.5)

    server.shutdown()

    if OAuthCallbackHandler.error:
        raise RuntimeError(f"Erreur OAuth LinkedIn : {OAuthCallbackHandler.error}")

    # Échanger le code contre un token
    token_data = {
        "grant_type": "authorization_code",
        "code": OAuthCallbackHandler.auth_code,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "client_secret": client_secret,
        "code_verifier": code_verifier,
    }

    resp = requests.post(LINKEDIN_TOKEN_URL, data=token_data)
    resp.raise_for_status()
    tokens = resp.json()

    # Récupérer le profil pour stocker l'ID utilisateur
    profile = get_profile(tokens["access_token"])
    tokens["person_id"] = profile.get("sub") or profile.get("id")
    tokens["name"] = profile.get("name", "")

    _save_tokens(tokens)
    console.print(f"[green]✓ Authentification réussie ! Bonjour {tokens['name']} 👋[/green]")
    return tokens


def get_profile(access_token: str) -> dict:
    """Récupère le profil LinkedIn de l'utilisateur connecté."""
    # Essai avec OpenID userinfo (pour les apps avec scope openid)
    resp = requests.get(
        "https://api.linkedin.com/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    if resp.status_code == 200:
        return resp.json()

    # Fallback sur /me
    resp = requests.get(
        f"{LINKEDIN_API_BASE}/me",
        headers={
            "Authorization": f"Bearer {access_token}",
            "X-Restli-Protocol-Version": "2.0.0",
        },
    )
    resp.raise_for_status()
    return resp.json()


def create_post(access_token: str, person_id: str, text: str) -> dict:
    """
    Publie un post texte sur LinkedIn.

    Args:
        access_token: Token OAuth2
        person_id: ID LinkedIn de l'utilisateur (URN)
        text: Contenu du post (max 3000 caractères)

    Returns:
        Réponse de l'API LinkedIn avec l'ID du post créé
    """
    if not person_id.startswith("urn:li:person:"):
        person_id = f"urn:li:person:{person_id}"

    if len(text) > 3000:
        raise ValueError(f"Le post dépasse 3000 caractères ({len(text)} caractères)")

    payload = {
        "author": person_id,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text},
                "shareMediaCategory": "NONE",
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        },
    }

    resp = requests.post(
        f"{LINKEDIN_API_BASE}/ugcPosts",
        json=payload,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
        },
    )
    resp.raise_for_status()

    # L'ID du post est dans le header X-RestLi-Id
    post_id = resp.headers.get("X-RestLi-Id") or resp.headers.get("x-restli-id")
    return {"post_id": post_id, "status": "published", "text_preview": text[:100]}
