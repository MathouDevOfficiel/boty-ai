# main.py
import tkinter as tk
import threading
import webbrowser
import re

import requests
from io import BytesIO
from PIL import Image, ImageTk

from brain import (
    ConversationState,
    detect_intent,
    should_use_web,
    generate_local_reply,
    build_web_query,
    INTENT_RESEARCH,
)
from web_search import search_web

# ---------- Couleurs & styles ----------
BG_MAIN = "#020617"        # fond chat
BG_WINDOW = "#0f172a"      # fond fenêtre
BG_USER = "#22c55e"        # bulle utilisateur
FG_USER = "#020617"
BG_BOT = "#1f2937"         # bulle bot
FG_BOT = "#e5e7eb"
FONT_TEXT = ("Segoe UI", 10)
FONT_BUTTON = ("Segoe UI", 9, "bold")


class BotyAIApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Boty AI - Web Chat intelligent")
        self.root.geometry("900x600")
        self.root.configure(bg=BG_WINDOW)

        # état de la conversation (mémoire courte, pas de DB)
        self.state = ConversationState()
        self.state.knowledge = None
        self.last_mode = None          # "image" ou "text"
        self.last_image_question = None

        # pour garder les images en mémoire
        self.inline_images: list[ImageTk.PhotoImage] = []

        # wrap dynamique (responsive)
        self.wrap_width = 650
        self.root.bind("<Configure>", self.on_resize)

        # ---- Zone de chat scrollable ----
        main_frame = tk.Frame(self.root, bg=BG_WINDOW)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.chat_canvas = tk.Canvas(
            main_frame,
            bg=BG_MAIN,
            highlightthickness=0
        )
        self.chat_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(
            main_frame,
            orient="vertical",
            command=self.chat_canvas.yview
        )
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.chat_canvas.configure(yscrollcommand=scrollbar.set)

        self.chat_frame = tk.Frame(self.chat_canvas, bg=BG_MAIN)
        self.chat_canvas.create_window((0, 0), window=self.chat_frame, anchor="nw")

        self.chat_frame.bind(
            "<Configure>",
            lambda e: self.chat_canvas.configure(
                scrollregion=self.chat_canvas.bbox("all")
            )
        )

        # ---- Entrée utilisateur + bouton ----
        bottom_frame = tk.Frame(self.root, bg=BG_WINDOW)
        bottom_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        self.entry = tk.Entry(
            bottom_frame,
            bg="#1e293b",
            fg="#e5e7eb",
            insertbackground="#ffffff",
            font=FONT_TEXT,
            relief=tk.FLAT
        )
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10), ipady=6)
        self.entry.bind("<Return>", self.on_send)

        self.send_button = tk.Button(
            bottom_frame,
            text="Envoyer",
            command=self.on_send,
            bg="#22c55e",
            fg="#0b1120",
            activebackground="#16a34a",
            activeforeground="#0b1120",
            relief=tk.FLAT,
            padx=20,
            pady=6,
        )
        self.send_button.pack(side=tk.RIGHT)

        # Message d'accueil
        self.add_system_message(
            "Salut, je suis Boty AI 🤖\n"
            "- Je réponds en local pour les trucs simples (salut, heure, calculs...).\n"
            "- Pour le reste, je cherche sur le web quand c'est utile.\n"
            "- Si tu demandes une image / photo : je te donne 1 phrase + 1 image.\n"
            "- Si la réponse contient du code ```...```, je te le mets dans un bloc copiable."
        )

    # ---------- Gestion taille / scroll ----------

    def on_resize(self, event):
        # adapte la largeur de wrap à la fenêtre
        w = max(event.width - 220, 300)
        self.wrap_width = w

    def _scroll_to_bottom(self):
        self.chat_canvas.update_idletasks()
        self.chat_canvas.yview_moveto(1.0)

    # ---------- Création de bulles ----------

    def _create_bubble(self, from_user: bool) -> tk.Frame:
        """
        Crée un conteneur de bulle (sans texte) côté user ou bot.
        On pourra y mettre texte + image + code + liens dans le même bloc.
        """
        outer = tk.Frame(self.chat_frame, bg=BG_MAIN)
        if from_user:
            outer.pack(anchor="e", pady=4, padx=10, fill="x")
            side = "right"
            bg = BG_USER
        else:
            outer.pack(anchor="w", pady=4, padx=10, fill="x")
            side = "left"
            bg = BG_BOT

        bubble = tk.Frame(outer, bg=bg, bd=0)
        bubble.pack(side=side, padx=5, pady=2, ipadx=1, ipady=1)
        self._scroll_to_bottom()
        return bubble

    def add_user_message(self, message: str):
        bubble = self._create_bubble(from_user=True)
        label = tk.Label(
            bubble,
            text=message,
            bg=BG_USER,
            fg=FG_USER,
            wraplength=self.wrap_width,
            justify="right",
            font=FONT_TEXT
        )
        label.pack(padx=10, pady=6)
        self._scroll_to_bottom()

    def add_bot_message(self, message: str):
        bubble = self._create_bubble(from_user=False)
        label = tk.Label(
            bubble,
            text=message,
            bg=BG_BOT,
            fg=FG_BOT,
            wraplength=self.wrap_width,
            justify="left",
            font=FONT_TEXT
        )
        label.pack(padx=10, pady=6)
        self._scroll_to_bottom()

    def add_system_message(self, message: str):
        outer = tk.Frame(self.chat_frame, bg=BG_MAIN)
        outer.pack(anchor="c", pady=6)
        label = tk.Label(
            outer,
            text=message,
            bg=BG_MAIN,
            fg="#9ca3af",
            font=("Segoe UI", 9),
            justify="center"
        )
        label.pack()
        self._scroll_to_bottom()

    # ---------- Éléments dans une bulle bot ----------

    def _add_text_in_bubble(self, bubble: tk.Frame, text: str):
        label = tk.Label(
            bubble,
            text=text,
            bg=BG_BOT,
            fg=FG_BOT,
            wraplength=self.wrap_width,
            justify="left",
            font=FONT_TEXT
        )
        label.pack(padx=10, pady=(6, 4), anchor="w")

    def _add_image_in_bubble(self, bubble: tk.Frame, url: str, max_size=(320, 320)):
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            img_data = BytesIO(resp.content)
            pil_img = Image.open(img_data)
        except Exception as e:
            self._add_text_in_bubble(bubble, f"(Impossible de charger l'image : {e})")
            return

        pil_img.thumbnail(max_size)
        tk_img = ImageTk.PhotoImage(pil_img)
        self.inline_images.append(tk_img)

        img_label = tk.Label(bubble, image=tk_img, bg=BG_BOT)
        img_label.image = tk_img
        img_label.pack(padx=10, pady=(2, 6), anchor="w")

    def copy_to_clipboard(self, code: str):
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(code)
        except Exception:
            pass

    def _add_code_block(self, bubble: tk.Frame, code: str, lang: str | None):
        """Affiche un bloc de code avec un bouton 'Copier'."""
        frame = tk.Frame(bubble, bg="#020617", bd=1, relief=tk.SOLID)
        frame.pack(padx=10, pady=(4, 6), anchor="w", fill="x")

        header = tk.Frame(frame, bg="#020617")
        header.pack(fill="x")

        lang_text = lang if lang else "code"
        lang_lbl = tk.Label(
            header,
            text=lang_text,
            bg="#020617",
            fg="#9ca3af",
            font=("Segoe UI", 8, "italic")
        )
        lang_lbl.pack(side="left", padx=(6, 0), pady=(4, 2))

        copy_btn = tk.Button(
            header,
            text="Copier",
            command=lambda c=code: self.copy_to_clipboard(c),
            bg="#1e293b",
            fg="#e5e7eb",
            activebackground="#334155",
            activeforeground="#e5e7eb",
            bd=0,
            padx=6,
            pady=2,
            font=("Segoe UI", 8),
            cursor="hand2"
        )
        copy_btn.pack(side="right", padx=(0, 6), pady=(4, 2))

        code_lbl = tk.Label(
            frame,
            text=code,
            bg="#020617",
            fg="#e5e7eb",
            font=("Consolas", 9),
            justify="left",
            anchor="w",
            wraplength=self.wrap_width - 40
        )
        code_lbl.pack(padx=6, pady=(0, 6), anchor="w")

    def _add_link_row(self, bubble: tk.Frame, title: str, url: str, is_youtube: bool):
        """Ajoute un lien stylé (texte cliquable) dans la bulle."""
        if is_youtube:
            icon = "▶"
            fg = "#f97373"
        else:
            icon = "🔗"
            fg = "#22c55e"

        frame = tk.Frame(bubble, bg=BG_BOT)
        frame.pack(anchor="w", padx=10, pady=(2, 2))

        label = tk.Label(
            frame,
            text=f"{icon} {title}",
            bg="#111827",
            fg=fg,
            font=FONT_BUTTON,
            cursor="hand2",
            wraplength=self.wrap_width - 60,
            justify="left",
            padx=8,
            pady=4,
        )
        label.pack()

        def open_link(event, u=url):
            webbrowser.open(u)

        label.bind("<Button-1>", open_link)

    def _extract_youtube_id(self, url: str):
        m = re.search(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{6,})", url)
        return m.group(1) if m else None

    def _add_youtube_thumb(self, bubble: tk.Frame, url: str):
        vid = self._extract_youtube_id(url)
        if not vid:
            return
        thumb_url = f"https://img.youtube.com/vi/{vid}/hqdefault.jpg"
        try:
            resp = requests.get(thumb_url, timeout=10)
            resp.raise_for_status()
            img_data = BytesIO(resp.content)
            pil_img = Image.open(img_data)
            pil_img.thumbnail((320, 180))
            tk_img = ImageTk.PhotoImage(pil_img)
            self.inline_images.append(tk_img)

            lbl = tk.Label(bubble, image=tk_img, bg=BG_BOT, cursor="hand2")
            lbl.image = tk_img
            lbl.pack(padx=10, pady=(0, 6), anchor="w")

            def open_yt(event, u=url):
                webbrowser.open(u)

            lbl.bind("<Button-1>", open_yt)
        except Exception:
            pass

    # ---------- Parsing texte + code ----------

    def render_text_with_code(self, bubble: tk.Frame, text: str):
        """
        Découpe le texte sur les blocs ```lang\ncode``` et affiche :
        - texte normal dans _add_text_in_bubble
        - code dans _add_code_block (copiable)
        """
        if "```" not in text:
            self._add_text_in_bubble(bubble, text.strip())
            return

        pattern = re.compile(r"```(?:([a-zA-Z0-9_+#\-]+)\n)?(.*?)```", re.DOTALL)
        pos = 0
        found = False

        for m in pattern.finditer(text):
            found = True
            pre = text[pos:m.start()]
            if pre.strip():
                self._add_text_in_bubble(bubble, pre.strip())

            lang = m.group(1) or ""
            code = (m.group(2) or "").strip("\n")
            if code.strip():
                self._add_code_block(bubble, code, lang)

            pos = m.end()

        if not found:
            self._add_text_in_bubble(bubble, text.strip())
            return

        tail = text[pos:]
        if tail.strip():
            self._add_text_in_bubble(bubble, tail.strip())

    def add_web_answer_block(self, summary: str, is_image_query: bool, sources, images):
        """
        Crée UNE SEULE bulle pour la réponse web :
        - texte (avec blocs de code si présents)
        - éventuellement 1 image
        - éventuellement des liens
        """
        bubble = self._create_bubble(from_user=False)

        # Texte principal
        if is_image_query:
            text_to_show = self._one_sentence(summary) or summary or ""
        else:
            text_to_show = summary or "Je n'ai pas trouvé de réponse très claire."

        self.render_text_with_code(bubble, text_to_show)

        # Image uniquement si requête d'image
        if is_image_query and images:
            self._add_image_in_bubble(bubble, images[0])

        # Liens : seulement si ce n'est PAS une requête d'image
        if (not is_image_query) and sources:
            lbl = tk.Label(
                bubble,
                text="Liens utiles :",
                bg=BG_BOT,
                fg="#9ca3af",
                font=("Segoe UI", 9, "italic"),
                justify="left"
            )
            lbl.pack(padx=10, pady=(2, 2), anchor="w")

            for src in sources[:5]:
                title = src.get("title") or src.get("url") or "Lien"
                url = src.get("url")
                if not url:
                    continue
                is_yt = ("youtube.com" in url) or ("youtu.be" in url)
                self._add_link_row(bubble, title, url, is_youtube=is_yt)
                if is_yt:
                    self._add_youtube_thumb(bubble, url)

        self._scroll_to_bottom()

    # ---------- Logique principale ----------

    def set_loading(self, loading: bool):
        if loading:
            self.send_button.config(state=tk.DISABLED, text="⏳")
        else:
            self.send_button.config(state=tk.NORMAL, text="Envoyer")

    def on_send(self, event=None):
        user_text = self.entry.get().strip()
        if not user_text:
            return

        self.add_user_message(user_text)
        self.entry.delete(0, tk.END)

        if user_text.lower() in ("quit", "exit"):
            self.root.destroy()
            return

        lower_text = user_text.lower()

        # Détection requêtes d'image (affiche image uniquement dans ces cas)
        image_keywords = ["image", "photo", "drapeau", "logo", "fond d'écran"]
        base_is_image_query = any(k in lower_text for k in image_keywords)

        # précision sur une image précédente
        is_image_followup = False
        if (not base_is_image_query) and self.last_mode == "image":
            if len(lower_text.split()) <= 15:
                is_image_followup = True

        is_image_query = base_is_image_query or is_image_followup

        # Détection d'intent
        intent = detect_intent(user_text, self.state)

        # Réponses locales (salut, heure, calcul...) -> pas de web
        local_reply = generate_local_reply(user_text, self.state, intent)
        if local_reply is not None and not should_use_web(intent):
            self.add_bot_message(local_reply)
            return

        # Recherche web si nécessaire
        if should_use_web(intent):
            # Reformulation pour Tavily
            if is_image_query and is_image_followup and self.last_image_question:
                message_for_query = (
                    "L'utilisateur cherche une image.\n"
                    f"Sujet initial : {self.last_image_question}.\n"
                    f"Nouvelle précision : {user_text}.\n"
                    "Trouve une image qui correspond bien à cette précision."
                )
                query = build_web_query(message_for_query, self.state, intent)
            else:
                query = build_web_query(user_text, self.state, intent)

            if intent == INTENT_RESEARCH:
                self.state.last_user_question = user_text

            # mémoriser le mode
            if is_image_query:
                self.last_mode = "image"
                if not is_image_followup:
                    self.last_image_question = user_text
            else:
                self.last_mode = "text"

            self.add_bot_message("Je cherche sur le web... 🔍")
            self.set_loading(True)

            threading.Thread(
                target=self.run_web_search,
                args=(query, user_text, is_image_query),
                daemon=True,
            ).start()
            return

        # sinon : pas de web, pas de réponse locale utile
        if local_reply is not None:
            self.add_bot_message(local_reply)
        else:
            self.add_bot_message(
                "Je ne suis pas sûr de ce que tu veux dire. "
                "Essaye de poser une question plus précise 🙂"
            )

    def _one_sentence(self, text: str) -> str:
        """Retourne seulement la première phrase d'un texte."""
        if not text:
            return ""
        text = text.strip()
        parts = re.split(r'(?<=[\.!?])\s+', text, maxsplit=1)
        first = parts[0].strip()
        if first and first[-1] not in ".!?":
            first += "."
        return first

    def run_web_search(self, query: str, original_question: str, is_image_query: bool):
        """Thread pour appeler Tavily sans bloquer l'UI."""
        try:
            result = search_web(query)
        except Exception as e:
            result = {
                "summary": f"Erreur interne en cherchant sur le web : {e}",
                "sources": [],
                "images": [],
            }

        def update_ui():
            self.set_loading(False)

            if not isinstance(result, dict):
                text = str(result)
                self.state.last_answer = text
                self.add_bot_message(text)
                return

            summary = result.get("summary", "") or ""
            sources = result.get("sources") or []
            images = result.get("images") or []

            self.state.last_answer = summary
            # Une seule bulle qui contient tout (texte + code éventuel + image éventuelle + liens)
            self.add_web_answer_block(summary, is_image_query, sources, images)

        self.root.after(0, update_ui)


def main():
    root = tk.Tk()
    app = BotyAIApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
