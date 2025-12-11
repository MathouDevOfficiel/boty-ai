<<<<<<< HEAD
# server.py
from flask import Flask, request, jsonify, send_from_directory
from brain import (
    ConversationState,
    detect_intent,
    should_use_web,
    generate_local_reply,
    build_web_query,
    INTENT_RESEARCH,
)
from web_search import search_web
import re

app = Flask(__name__, static_folder=".", static_url_path="")

# état global (pour une seule personne, c'est OK)
state = ConversationState()
state.knowledge = None
state.last_mode = None
state.last_image_question = None


@app.route("/")
def index():
    return send_from_directory(".", "index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(force=True)
    user_text = (data.get("message") or "").strip()

    if not user_text:
        return jsonify({"error": "empty message"}), 400

    # Quitter (si tu veux plus tard)
    if user_text.lower() in ("quit", "exit"):
        return jsonify({"reply": "Fermeture du chat (côté web, à gérer).", "mode": "local"})

    lower_text = user_text.lower()

    # --- détection requête d'image ---
    image_keywords = ["image", "photo", "drapeau", "logo", "fond d'écran"]
    base_is_image_query = any(k in lower_text for k in image_keywords)

    is_image_followup = False
    if (not base_is_image_query) and getattr(state, "last_mode", None) == "image":
        # phrase courte = précision probable
        if len(lower_text.split()) <= 15:
            is_image_followup = True

    is_image_query = base_is_image_query or is_image_followup

    # --- détection d'intent ---
    intent = detect_intent(user_text, state)

    # --- réponse locale (salut, heure, calcul...) ---
    local_reply = generate_local_reply(user_text, state, intent)
    if local_reply is not None and not should_use_web(intent):
        state.last_answer = local_reply
        return jsonify({
            "mode": "local",
            "text": local_reply,
            "is_image_query": False,
            "sources": [],
            "images": [],
        })

    # --- si on doit utiliser le web ---
    if should_use_web(intent):
        # reformulation pour Tavily
        if is_image_query and is_image_followup and state.last_image_question:
            message_for_query = (
                "L'utilisateur cherche une image.\n"
                f"Sujet initial : {state.last_image_question}.\n"
                f"Nouvelle précision : {user_text}.\n"
                "Trouve une image qui correspond bien à cette précision."
            )
            query = build_web_query(message_for_query, state, intent)
        else:
            query = build_web_query(user_text, state, intent)

        if intent == INTENT_RESEARCH:
            state.last_user_question = user_text

        # mémoriser le mode
        if is_image_query:
            state.last_mode = "image"
            if not is_image_followup:
                state.last_image_question = user_text
        else:
            state.last_mode = "text"

        # appel Tavily via web_search
        try:
            result = search_web(query)
        except Exception as e:
            result = {
                "summary": f"Erreur interne en cherchant sur le web : {e}",
                "sources": [],
                "images": [],
            }

        if not isinstance(result, dict):
            txt = str(result)
            state.last_answer = txt
            return jsonify({
                "mode": "web",
                "text": txt,
                "is_image_query": is_image_query,
                "sources": [],
                "images": [],
            })

        summary = result.get("summary", "") or ""
        sources = result.get("sources") or []
        images = result.get("images") or []

        state.last_answer = summary

        return jsonify({
            "mode": "web",
            "text": summary,
            "is_image_query": is_image_query,
            "sources": sources,
            "images": images,
        })

    # --- sinon, pas de web et pas de vraie réponse locale ---
    if local_reply is not None:
        state.last_answer = local_reply
        return jsonify({
            "mode": "local",
            "text": local_reply,
            "is_image_query": False,
            "sources": [],
            "images": [],
        })

    fallback = "Je ne suis pas sûr de ce que tu veux dire. Essaye de poser une question plus précise 🙂"
    state.last_answer = fallback
    return jsonify({
        "mode": "local",
        "text": fallback,
        "is_image_query": False,
        "sources": [],
        "images": [],
    })


if __name__ == "__main__":
    # installe Flask avant :  py -3.12 -m pip install flask
    app.run(host="127.0.0.1", port=5000, debug=True)

=======
# server.py
from flask import Flask, request, jsonify, send_from_directory
from brain import (
    ConversationState,
    detect_intent,
    should_use_web,
    generate_local_reply,
    build_web_query,
    INTENT_RESEARCH,
)
from web_search import search_web
import re

app = Flask(__name__, static_folder=".", static_url_path="")

# état global (pour une seule personne, c'est OK)
state = ConversationState()
state.knowledge = None
state.last_mode = None
state.last_image_question = None


@app.route("/")
def index():
    return send_from_directory(".", "index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(force=True)
    user_text = (data.get("message") or "").strip()

    if not user_text:
        return jsonify({"error": "empty message"}), 400

    # Quitter (si tu veux plus tard)
    if user_text.lower() in ("quit", "exit"):
        return jsonify({"reply": "Fermeture du chat (côté web, à gérer).", "mode": "local"})

    lower_text = user_text.lower()

    # --- détection requête d'image ---
    image_keywords = ["image", "photo", "drapeau", "logo", "fond d'écran"]
    base_is_image_query = any(k in lower_text for k in image_keywords)

    is_image_followup = False
    if (not base_is_image_query) and getattr(state, "last_mode", None) == "image":
        # phrase courte = précision probable
        if len(lower_text.split()) <= 15:
            is_image_followup = True

    is_image_query = base_is_image_query or is_image_followup

    # --- détection d'intent ---
    intent = detect_intent(user_text, state)

    # --- réponse locale (salut, heure, calcul...) ---
    local_reply = generate_local_reply(user_text, state, intent)
    if local_reply is not None and not should_use_web(intent):
        state.last_answer = local_reply
        return jsonify({
            "mode": "local",
            "text": local_reply,
            "is_image_query": False,
            "sources": [],
            "images": [],
        })

    # --- si on doit utiliser le web ---
    if should_use_web(intent):
        # reformulation pour Tavily
        if is_image_query and is_image_followup and state.last_image_question:
            message_for_query = (
                "L'utilisateur cherche une image.\n"
                f"Sujet initial : {state.last_image_question}.\n"
                f"Nouvelle précision : {user_text}.\n"
                "Trouve une image qui correspond bien à cette précision."
            )
            query = build_web_query(message_for_query, state, intent)
        else:
            query = build_web_query(user_text, state, intent)

        if intent == INTENT_RESEARCH:
            state.last_user_question = user_text

        # mémoriser le mode
        if is_image_query:
            state.last_mode = "image"
            if not is_image_followup:
                state.last_image_question = user_text
        else:
            state.last_mode = "text"

        # appel Tavily via web_search
        try:
            result = search_web(query)
        except Exception as e:
            result = {
                "summary": f"Erreur interne en cherchant sur le web : {e}",
                "sources": [],
                "images": [],
            }

        if not isinstance(result, dict):
            txt = str(result)
            state.last_answer = txt
            return jsonify({
                "mode": "web",
                "text": txt,
                "is_image_query": is_image_query,
                "sources": [],
                "images": [],
            })

        summary = result.get("summary", "") or ""
        sources = result.get("sources") or []
        images = result.get("images") or []

        state.last_answer = summary

        return jsonify({
            "mode": "web",
            "text": summary,
            "is_image_query": is_image_query,
            "sources": sources,
            "images": images,
        })

    # --- sinon, pas de web et pas de vraie réponse locale ---
    if local_reply is not None:
        state.last_answer = local_reply
        return jsonify({
            "mode": "local",
            "text": local_reply,
            "is_image_query": False,
            "sources": [],
            "images": [],
        })

    fallback = "Je ne suis pas sûr de ce que tu veux dire. Essaye de poser une question plus précise 🙂"
    state.last_answer = fallback
    return jsonify({
        "mode": "local",
        "text": fallback,
        "is_image_query": False,
        "sources": [],
        "images": [],
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Pour Render / Railway
    app.run(host="0.0.0.0", port=port)
