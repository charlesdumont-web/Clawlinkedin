"""
Définition des outils disponibles pour l'agent Claude.
Ces outils permettent à Claude d'interagir avec LinkedIn, le planificateur,
le profil de marque et la recherche de sujets.
"""
import json
import os
from datetime import datetime, timedelta
from typing import Any

from . import content_generator, linkedin_client, scheduler, brand_manager, topic_researcher

# Définitions des outils pour l'API Claude
TOOLS = [
    {
        "name": "generate_linkedin_post",
        "description": """Génère un post LinkedIn de haute qualité sur un sujet donné.
        Utilise Claude pour créer du contenu authentique et engageant adapté à l'audience LinkedIn.
        Retourne le contenu complet du post prêt à être publié.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "Sujet principal du post (ex: 'les erreurs de débutant en management', 'l'IA dans le recrutement')"
                },
                "post_type": {
                    "type": "string",
                    "enum": ["storytelling", "insight", "liste", "conseil", "question", "données"],
                    "description": "Type de format du post"
                },
                "tone": {
                    "type": "string",
                    "description": "Ton souhaité (ex: 'inspirant', 'éducatif', 'personnel et vulnérable')"
                },
                "additional_context": {
                    "type": "string",
                    "description": "Contexte ou informations supplémentaires à inclure dans le post"
                }
            },
            "required": ["topic"]
        }
    },
    {
        "name": "generate_weekly_plan",
        "description": """Génère un plan de contenu complet pour la semaine avec plusieurs posts LinkedIn.
        Crée des posts variés (types différents) adaptés aux jours et heures optimaux d'engagement.
        Retourne une liste de posts avec leur jour, heure et contenu suggérés.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "themes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Liste des thèmes/sujets à couvrir cette semaine"
                },
                "posts_per_week": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 7,
                    "description": "Nombre de posts à publier cette semaine (défaut: 3)"
                }
            },
            "required": ["themes"]
        }
    },
    {
        "name": "refine_post",
        "description": """Améliore un post LinkedIn existant selon les retours de l'utilisateur.
        Peut modifier le ton, la structure, la longueur, ajouter des hashtags, etc.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "original_post": {
                    "type": "string",
                    "description": "Le contenu original du post à améliorer"
                },
                "feedback": {
                    "type": "string",
                    "description": "Instructions détaillées sur les modifications à apporter"
                }
            },
            "required": ["original_post", "feedback"]
        }
    },
    {
        "name": "schedule_post",
        "description": """Planifie un post LinkedIn pour publication future.
        Ajoute le post à la file de publication avec une date et heure spécifiques.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "Contenu complet du post LinkedIn à planifier"
                },
                "scheduled_at": {
                    "type": "string",
                    "description": "Date et heure de publication au format ISO 8601 (ex: '2024-01-15T09:00:00')"
                }
            },
            "required": ["content", "scheduled_at"]
        }
    },
    {
        "name": "post_to_linkedin_now",
        "description": """Publie immédiatement un post sur LinkedIn.
        Nécessite une authentification LinkedIn préalable.
        Retourne l'ID du post créé si succès.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "Contenu complet du post LinkedIn à publier maintenant"
                }
            },
            "required": ["content"]
        }
    },
    {
        "name": "list_scheduled_posts",
        "description": """Affiche la liste des posts planifiés dans la file de publication.
        Retourne tous les posts avec leur statut (planifié, publié, échoué).""",
        "input_schema": {
            "type": "object",
            "properties": {
                "status_filter": {
                    "type": "string",
                    "enum": ["scheduled", "published", "failed", "all"],
                    "description": "Filtrer par statut (défaut: all)"
                }
            }
        }
    },
    {
        "name": "cancel_scheduled_post",
        "description": "Annule un post planifié qui n'a pas encore été publié.",
        "input_schema": {
            "type": "object",
            "properties": {
                "post_id": {
                    "type": "string",
                    "description": "L'ID du post planifié à annuler (8 caractères)"
                }
            },
            "required": ["post_id"]
        }
    },
    {
        "name": "setup_brand_profile",
        "description": """Lance l'assistant de configuration du profil de marque et de style.
        Permet de définir l'identité professionnelle, le style rédactionnel, les valeurs,
        les piliers de contenu, les hashtags, et des exemples de posts de référence.
        À utiliser quand l'utilisateur veut personnaliser le style des posts ou configurer sa marque.""",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_brand_profile",
        "description": """Affiche le profil de marque et style actuel de l'utilisateur.
        Montre toutes les informations configurées : identité, style, valeurs, hashtags, etc.""",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "update_brand_field",
        "description": """Met à jour un champ spécifique du profil de marque sans relancer tout l'assistant.
        Utile pour des modifications rapides comme changer les hashtags ou le ton.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "field_path": {
                    "type": "string",
                    "description": "Chemin du champ à modifier. Ex: 'name', 'style.tone', 'hashtags', 'content_pillars', 'tagline'"
                },
                "value": {
                    "description": "Nouvelle valeur (string, liste, ou objet selon le champ)"
                }
            },
            "required": ["field_path", "value"]
        }
    },
    {
        "name": "research_trending_topics",
        "description": """Recherche sur internet les sujets tendance dans un secteur pour trouver des idées de posts LinkedIn.
        Utilise la recherche web pour identifier les débats du moment, actualités récentes,
        et sujets qui génèrent de l'engagement dans le domaine de l'utilisateur.
        Retourne une liste d'idées de posts avec accroches et hashtags suggérés.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "industry": {
                    "type": "string",
                    "description": "Secteur ou domaine à explorer (ex: 'intelligence artificielle', 'ressources humaines', 'entrepreneuriat')"
                },
                "count": {
                    "type": "integer",
                    "minimum": 3,
                    "maximum": 20,
                    "description": "Nombre d'idées à générer (défaut: 8)"
                }
            },
            "required": ["industry"]
        }
    },
    {
        "name": "research_news_for_posts",
        "description": """Recherche les actualités récentes autour de mots-clés spécifiques et propose
        comment les transformer en posts LinkedIn engageants avec un angle personnel.
        Parfait pour réagir à l'actualité de son secteur.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "keywords": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Mots-clés à rechercher (ex: ['ChatGPT', 'emploi', 'IA générative'])"
                }
            },
            "required": ["keywords"]
        }
    },
]


def execute_tool(tool_name: str, tool_input: dict, linkedin_tokens: dict | None = None) -> Any:
    """
    Exécute un outil et retourne le résultat.

    Args:
        tool_name: Nom de l'outil à exécuter
        tool_input: Paramètres d'entrée de l'outil
        linkedin_tokens: Tokens LinkedIn (requis pour la publication)

    Returns:
        Résultat de l'outil (dict ou str)
    """
    if tool_name == "generate_linkedin_post":
        content = content_generator.generate_post(
            topic=tool_input["topic"],
            post_type=tool_input.get("post_type", "insight"),
            tone=tool_input.get("tone", "professionnel et authentique"),
            additional_context=tool_input.get("additional_context", ""),
        )
        return {"success": True, "content": content, "char_count": len(content)}

    elif tool_name == "generate_weekly_plan":
        posts = content_generator.generate_weekly_plan(
            themes=tool_input["themes"],
            posts_per_week=tool_input.get("posts_per_week", 3),
        )
        return {"success": True, "posts": posts, "count": len(posts)}

    elif tool_name == "refine_post":
        refined = content_generator.refine_post(
            original_post=tool_input["original_post"],
            feedback=tool_input["feedback"],
        )
        return {"success": True, "content": refined, "char_count": len(refined)}

    elif tool_name == "schedule_post":
        post = scheduler.add_scheduled_post(
            content=tool_input["content"],
            scheduled_at=tool_input["scheduled_at"],
        )
        return {
            "success": True,
            "post_id": post["id"],
            "scheduled_at": post["scheduled_at"],
            "message": f"Post planifié pour le {post['scheduled_at']} (ID: {post['id']})",
        }

    elif tool_name == "post_to_linkedin_now":
        if not linkedin_tokens:
            return {
                "success": False,
                "error": "Authentification LinkedIn requise. Lance 'auth' pour te connecter.",
            }
        try:
            result = linkedin_client.create_post(
                access_token=linkedin_tokens["access_token"],
                person_id=linkedin_tokens["person_id"],
                text=tool_input["content"],
            )
            return {
                "success": True,
                "post_id": result["post_id"],
                "message": f"Post publié avec succès sur LinkedIn ! (ID: {result['post_id']})",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    elif tool_name == "list_scheduled_posts":
        status_filter = tool_input.get("status_filter", "all")
        posts = scheduler.list_scheduled_posts(
            status=None if status_filter == "all" else status_filter
        )
        scheduler.display_scheduled_posts()
        return {
            "success": True,
            "count": len(posts),
            "posts": [
                {
                    "id": p["id"],
                    "scheduled_at": p["scheduled_at"],
                    "status": p["status"],
                    "preview": p["content"][:100],
                }
                for p in posts
            ],
        }

    elif tool_name == "cancel_scheduled_post":
        success = scheduler.cancel_post(tool_input["post_id"])
        return {
            "success": success,
            "message": f"Post {tool_input['post_id']} annulé." if success
                      else f"Post {tool_input['post_id']} introuvable ou déjà publié.",
        }

    elif tool_name == "setup_brand_profile":
        profile = brand_manager.run_setup_wizard()
        return {
            "success": True,
            "message": "Profil de marque configuré avec succès.",
            "summary": {
                "name": profile.get("name"),
                "role": profile.get("role"),
                "content_pillars": profile.get("content_pillars", []),
                "style_tone": profile.get("style", {}).get("tone"),
                "hashtags": profile.get("hashtags", []),
                "examples_count": len(profile.get("post_examples", [])),
            },
        }

    elif tool_name == "get_brand_profile":
        profile = brand_manager.load_brand_profile()
        brand_manager.display_brand_profile(profile)
        return {
            "success": True,
            "profile": profile,
            "configured": bool(profile),
        }

    elif tool_name == "update_brand_field":
        updated = brand_manager.update_field(
            field_path=tool_input["field_path"],
            value=tool_input["value"],
        )
        return {
            "success": True,
            "message": f"Champ '{tool_input['field_path']}' mis à jour.",
            "new_value": updated.get(tool_input["field_path"].split(".")[0]),
        }

    elif tool_name == "research_trending_topics":
        profile = brand_manager.load_brand_profile()
        language = os.getenv("POST_LANGUAGE", "fr")
        topics = topic_researcher.research_trending_topics(
            industry=tool_input["industry"],
            content_pillars=profile.get("content_pillars"),
            count=tool_input.get("count", 8),
            language=language,
        )
        return {
            "success": True,
            "count": len(topics),
            "topics": topics,
            "message": f"{len(topics)} idées de posts trouvées pour '{tool_input['industry']}'",
        }

    elif tool_name == "research_news_for_posts":
        language = os.getenv("POST_LANGUAGE", "fr")
        ideas = topic_researcher.get_content_ideas_from_news(
            keywords=tool_input["keywords"],
            language=language,
        )
        return {
            "success": True,
            "count": len(ideas),
            "ideas": ideas,
        }

    else:
        return {"success": False, "error": f"Outil inconnu : {tool_name}"}
