# brain.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import re
from datetime import datetime


# ---------- Intents ----------

INTENT_SMALLTALK = "smalltalk"
INTENT_TIME = "time"
INTENT_MATH = "math"
INTENT_RESEARCH = "research"
INTENT_FOLLOWUP_MORE = "followup_more"
INTENT_OTHER = "other"


@dataclass
class ConversationState:
    """État simple de la conversation (mémoire courte)."""
    last_user_question: Optional[str] = None
    last_answer: Optional[str] = None
    knowledge: object | None = None  # pas utilisé dans cette version, mais conservé pour compatibilité


# ---------- Détection d'intention ----------

def detect_intent(text: str, state: ConversationState) -> str:
    """
    Essaie de deviner ce que l'utilisateur veut :
    - smalltalk (salut, ça va...)
    - time (heure)
    - math (calcul simple)
    - followup_more (explique plus...)
    - research (question d'info)
    - other (vague)
    """
    t = text.lower().strip()

    # Follow-up "explique plus", "en détail", etc.
    if state.last_answer:
        if any(kw in t for kw in ["explique plus", "détaille", "en détail", "développe", "et pour"]):
            return INTENT_FOLLOWUP_MORE

    # Smalltalk
    if any(kw in t for kw in ["salut", "bonjour", "slt", "cc", "coucou", "yo", "wesh", "hey"]):
        return INTENT_SMALLTALK

    if any(kw in t for kw in ["ça va", "ca va", "comment tu vas", "comment sa va"]):
        return INTENT_SMALLTALK

    # Heure
    if any(kw in t for kw in ["heure", "il est quelle heure", "quelle heure est il", "quelle heure est-il"]):
        return INTENT_TIME

    # Calcul simple : présence de chiffres + opérateurs
    if re.search(r"\d", t) and re.search(r"[+\-*/x]", t):
        return INTENT_MATH

    # Questions de type "comment", "pourquoi", "c'est quoi", etc. -> recherche
    question_words = [
        "comment ", "pourquoi", "c est quoi", "c'est quoi",
        "qui est", "qu est ce que", "qu'est ce que", "qu'est-ce que",
        "où ", "ou ", "recette", "histoire", "définition", "definition",
        "tutoriel", "tuto", "explique", "explique moi"
    ]
    if any(kw in t for kw in question_words) or t.endswith("?"):
        return INTENT_RESEARCH

    # Phrases un peu longues (> 4 mots) -> probablement une demande d'info
    if len(t.split()) >= 4:
        return INTENT_RESEARCH

    # Très court et vague -> autre (on répondra en demandant des précisions)
    return INTENT_OTHER


# ---------- Quand utiliser le web ? ----------

def should_use_web(intent: str) -> bool:
    """
    Indique si on doit utiliser Tavily.
    On évite le web pour smalltalk, heure, maths, etc.
    """
    return intent in (INTENT_RESEARCH, INTENT_FOLLOWUP_MORE)


# ---------- Réponses locales (sans web) ----------

def generate_local_reply(text: str, state: ConversationState, intent: str) -> Optional[str]:
    """
    Donne une réponse locale si possible.
    Si on retourne None -> le main ira éventuellement sur le web.
    """
    t = text.lower().strip()

    # Smalltalk
    if intent == INTENT_SMALLTALK:
        if any(kw in t for kw in ["ça va", "ca va"]):
            return "Ça va bien, merci 😄 Et toi ?"
        if any(kw in t for kw in ["comment tu vas", "comment sa va"]):
            return "Je vais très bien, merci 🙌 Et toi, ça va ?"
        # salut simple
        return "Salut 😄 Comment puis-je t'aider ?"

    # Heure (on prend simplement l'heure locale de la machine)
    if intent == INTENT_TIME:
        now = datetime.now()
        return f"Chez moi il est environ {now.strftime('%H:%M')}."

    # Calcul simple
    if intent == INTENT_MATH:
        expr = t
        # on enlève quelques mots parasites
        expr = re.sub(r"(combien fait|ça fait combien|ca fait combien|fait|=|\?)", "", expr)
        expr = expr.replace("x", "*").replace(":", "/")
        # garder uniquement chiffres, opérateurs et espaces
        if not re.fullmatch(r"[0-9+\-*/().\s]+", expr):
            return "Je ne suis pas sûr du calcul. Réécris juste l'opération, par ex : 12+5*3"
        try:
            result = eval(expr, {"__builtins__": {}}, {})
        except Exception:
            return "Je n'ai pas réussi à faire ce calcul."
        return f"{expr.strip()} = {result}"

    # Follow-up "explique plus" : on laisse le web/logiciel gérer
    if intent == INTENT_FOLLOWUP_MORE:
        # on ne répond pas localement, on laissera le web (ou une autre logique) détailler
        return None

    # Autre / vague
    if intent == INTENT_OTHER:
        # si c'est très court -> demande de précision
        if len(t.split()) <= 3:
            return "Tu peux préciser ce que tu veux exactement ? 🙂"
        # sinon, on pourrait passer au web, donc None
        return None

    # INTENT_RESEARCH -> pas de réponse locale, on laisse Tavily faire
    return None


# ---------- Construction de la requête web ----------

def build_web_query(text: str, state: ConversationState, intent: str) -> str:
    """
    Transforme la question de l'utilisateur en requête Tavily plus claire et plus courte.
    C'est ici que le bot a l'air plus "intelligent" dans sa façon de chercher.
    """
    raw = text.strip()
    t = raw.lower().strip()

    # Follow-up "explique plus" sur une réponse précédente
    if intent == INTENT_FOLLOWUP_MORE and state.last_user_question and state.last_answer:
        # On reformule : on demande plus de détails sur la même chose
        return (
            f"Explique plus en détail : {state.last_user_question}. "
            f"Réponse précédente : {state.last_answer}. "
            f"L'utilisateur demande maintenant : {raw}."
        )

    # Recettes / cuisine
    if "cookie" in t or "cookies" in t:
        if any(kw in t for kw in ["recette", "faire", "cuisiner", "préparer"]):
            return "recette de cookies maison simples en français, étapes détaillées"
    if "marmiton" in t or "marmithon" in t:
        return "site Marmiton recette cookies"

    # Drapeau / image (même si l'image est gérée ailleurs, la requête reste utile)
    if "drapeau" in t and "franc" in t:
        return "drapeau français explication couleurs bleu blanc rouge histoire"

    # Questions du type "c'est quoi X"
    m = re.search(r"(c'est quoi|c est quoi|qu'est ce que|qu est ce que)\s+(.*)", t)
    if m:
        sujet = m.group(2)
        return f"explication simple de {sujet} en français"

    # Questions du type "qui est X"
    m = re.search(r"qui est\s+(.*)", t)
    if m:
        personne = m.group(1)
        return f"qui est {personne}, biographie courte en français"

    # "Comment faire / comment X"
    if t.startswith("comment "):
        return f"{raw} tutoriel simple en français"

    # Si on a une ancienne question et que l'utilisateur précise un peu :
    if state.last_user_question and len(t.split()) <= 6:
        return (
            f"Complément d'information sur : {state.last_user_question}. "
            f"L'utilisateur ajoute : {raw}."
        )

    # Par défaut : on envoie la question telle quelle
    # (Tavily se débrouille, mais on garde la question brute)
    return raw
