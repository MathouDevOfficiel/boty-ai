# web_search.py
import re
import requests

# --------- CONFIG TAVILY ---------
TAVILY_API_KEY = "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"
TAVILY_ENDPOINT = "https://api.tavily.com/search"


def _clean(text: str) -> str:
    """Nettoie un peu le texte (espaces multiples, etc.)."""
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def search_web(query: str) -> dict:
    """
    Appelle Tavily directement via HTTP avec un timeout
    et renvoie un dict :
    {
      "summary": "texte résumé",
      "sources": [{"title": ..., "url": ...}, ...],
      "images": ["url_image1", "url_image2", ...]
    }
    """

    if not TAVILY_API_KEY.strip():
        return {
            "summary": "Erreur Tavily : aucune clé API configurée.",
            "sources": [],
            "images": [],
        }

    payload = {
        "api_key": TAVILY_API_KEY,
        "query": query,
        "search_depth": "basic",
        "include_answer": True,
        "max_results": 5,
        "include_images": True,
    }

    # 1) Appel HTTP avec timeout
    try:
        resp = requests.post(TAVILY_ENDPOINT, json=payload, timeout=15)
    except Exception as e:
        return {
            "summary": f"Erreur Tavily (connexion) : {e}",
            "sources": [],
            "images": [],
        }

    # 2) Code HTTP pas 200
    if resp.status_code != 200:
        try:
            data = resp.json()
        except Exception:
            data = resp.text
        return {
            "summary": f"Erreur Tavily {resp.status_code} : {data}",
            "sources": [],
            "images": [],
        }

    # 3) Décodage JSON
    try:
        data = resp.json()
    except Exception as e:
        return {
            "summary": f"Erreur Tavily (JSON) : {e}",
            "sources": [],
            "images": [],
        }

    answer = data.get("answer")
    results = data.get("results") or []

    sources: list[dict] = []
    images: list[str] = []

    # 🔹 images globales (top-level)
    top_images = data.get("images") or []
    for img in top_images:
        if isinstance(img, str):
            images.append(img)
        elif isinstance(img, dict) and "url" in img:
            images.append(img["url"])

    # 🔹 sources + images dans chaque résultat
    for r in results:
        url = r.get("url")
        title = r.get("title") or url or "Lien"
        if url:
            sources.append({"title": title, "url": url})

        imgs = r.get("images") or []
        for img in imgs:
            if isinstance(img, str):
                images.append(img)
            elif isinstance(img, dict) and "url" in img:
                images.append(img["url"])

    summary = None
    if isinstance(answer, str) and answer.strip():
        summary = _clean(answer)
    else:
        for r in results:
            content = r.get("content") or r.get("raw_content") or ""
            if isinstance(content, str) and content.strip():
                text = _clean(content)
                if len(text) > 700:
                    text = text[:700].rsplit(" ", 1)[0] + "..."
                summary = text
                break

    if not summary:
        summary = "Je n'ai pas réussi à trouver une réponse claire sur le web."

    return {
        "summary": summary,
        "sources": sources,
        "images": images,
    }
