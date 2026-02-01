from __future__ import annotations

import json
from datetime import datetime
from typing import Optional, List

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QAction, QDesktopServices
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QComboBox, QTextEdit, QMessageBox, QSplitter, QScrollArea
)
from PySide6.QtCore import QUrl

from lawmate_app.config import AppConfig
from lawmate_app.db import Database
from lawmate_app.llm.providers import make_provider
from lawmate_app.llm.prompts import SYSTEM_BASE, make_user_prompt
from lawmate_app.models import LawmateAnswer
from lawmate_app.rag.justice_api import search_recent_decisions, decisions_to_sources
from lawmate_app.utils import (
    heuristic_risk_score,
    traffic_light_from_score,
    normalize_text,
    infer_category,
)
from lawmate_app.ui.widgets import ChatBubble
from lawmate_app.llm.ollama_setup import OllamaSetupWorker

AUTO_CATEGORY = "Auto (rozpoznat oblast)"
CATEGORIES = [AUTO_CATEGORY, "Trestní právo", "Občanské právo", "Právní řád ČR (obecně)"]

def format_answer(ans: LawmateAnswer) -> str:
    def bullet(items: List[str]) -> str:
        return "".join([f"• {i}<br>" for i in items]) if items else "—<br>"

    html = ""
    html += f"<b>Shrnutí:</b><br>{ans.summary}<br><br>"
    html += "<b>Co udělat teď:</b><br>" + bullet(ans.what_to_do_now) + "<br>"
    html += "<b>Co si připravit:</b><br>" + bullet(ans.what_to_prepare) + "<br>"
    html += "<b>Důležité zákony / paragrafy:</b><br>" + bullet(ans.relevant_laws) + "<br>"
    html += "<b>Lhůty:</b><br>" + bullet(ans.important_deadlines) + "<br>"
    html += "<b>Kdy kontaktovat právníka:</b><br>" + bullet(ans.when_to_contact_lawyer) + "<br>"
    html += "<b>Poznámky:</b><br>" + bullet(ans.notes) + "<br>"

    if ans.sources:
        html += "<b>Zdroje (orientačně):</b><br>"
        for s in ans.sources:
            html += f"• <a href='{s.url}'>{s.title}</a> – {s.why_relevant}<br>"
        html += "<br>"

    html += "<i>Upozornění: Lawmate není advokát. Odpověď je orientační a nemusí být úplná.</i>"
    return html

class Worker(QThread):
    done = Signal(object, str, str)  # (LawmateAnswer|Exception, light, sources_json)

    def __init__(self, cfg: AppConfig, category: str, question: str):
        super().__init__()
        self.cfg = cfg
        self.category = category
        self.question = question

    def run(self) -> None:
        try:
            decisions = search_recent_decisions(
                self.question,
                lookback_days=self.cfg.justice_lookback_days,
                max_items_per_day=self.cfg.justice_max_items_per_day,
            )
            sources = decisions_to_sources(decisions)
            sources_block = json.dumps(sources, ensure_ascii=False, indent=2) if sources else "[]"

            provider = make_provider(self.cfg)
            user_prompt = make_user_prompt(self.category, self.question, sources_block)
            ans = provider.generate(SYSTEM_BASE, user_prompt)

            heur = heuristic_risk_score(self.question, self.category)
            heur_light = traffic_light_from_score(heur)

            order = {"green": 0, "yellow": 1, "red": 2}
            if order[heur_light] > order[ans.traffic_light]:
                ans.traffic_light = heur_light
                ans.risk_score = max(ans.risk_score, heur)

            sources_json = json.dumps([s.model_dump() for s in ans.sources], ensure_ascii=False)
            self.done.emit(ans, ans.traffic_light, sources_json)
        except Exception as e:
            self.done.emit(e, "red", "[]")

class MainWindow(QMainWindow):
    def __init__(self, cfg: AppConfig, db: Database):
        super().__init__()
        self.cfg = cfg
        self.db = db
        self.current_session_id: Optional[int] = None

        self.setWindowTitle("Lawmate – AI právní poradce")

        act_new = QAction("Nový chat", self)
        act_new.triggered.connect(self.new_chat)

        act_del = QAction("Smazat chat", self)
        act_del.triggered.connect(self.delete_current_chat)

        act_lawyer = QAction("Najít advokáta (ČAK)", self)
        act_lawyer.triggered.connect(self.open_lawyer_search)

        menu = self.menuBar().addMenu("Menu")
        menu.addAction(act_new)
        menu.addAction(act_del)
        menu.addSeparator()
        menu.addAction(act_lawyer)

        root = QWidget()
        self.setCentralWidget(root)
        main = QHBoxLayout(root)
        main.setContentsMargins(10, 10, 10, 10)

        splitter = QSplitter(Qt.Horizontal)
        main.addWidget(splitter)

        # LEFT (history)
        left = QWidget()
        left_l = QVBoxLayout(left)
        left_l.setContentsMargins(0, 0, 0, 0)
        left_l.setSpacing(8)

        left_l.addWidget(QLabel("<b>Historie</b>"))
        self.sessions_list = QListWidget()
        self.sessions_list.itemClicked.connect(self.on_session_clicked)
        left_l.addWidget(self.sessions_list, 1)

        btn_new = QPushButton("+ Nový chat")
        btn_new.clicked.connect(self.new_chat)
        btn_del = QPushButton("Smazat")
        btn_del.clicked.connect(self.delete_current_chat)
        left_l.addWidget(btn_new)
        left_l.addWidget(btn_del)

        # RIGHT (chat)
        right = QWidget()
        right_l = QVBoxLayout(right)
        right_l.setContentsMargins(0, 0, 0, 0)
        right_l.setSpacing(8)

        top = QHBoxLayout()
        top.addWidget(QLabel("Oblast:"))
        self.category_cb = QComboBox()
        self.category_cb.addItems(CATEGORIES)
        self.category_cb.setCurrentIndex(0)
        top.addWidget(self.category_cb)

        top.addStretch(1)
        provider_name = cfg.llm_provider
        if cfg.llm_provider == "ollama" and "ollama.com" in cfg.ollama_base_url.lower():
            provider_name = "ollama-cloud"
        top.addWidget(QLabel(f"Provider: {provider_name}"))
        btn_lawyer = QPushButton("Najít advokáta")
        btn_lawyer.clicked.connect(self.open_lawyer_search)
        top.addWidget(btn_lawyer)

        right_l.addLayout(top)

        self.chat_container = QWidget()
        self.chat_l = QVBoxLayout(self.chat_container)
        self.chat_l.setContentsMargins(0, 0, 0, 0)
        self.chat_l.setSpacing(10)
        self.chat_l.addStretch(1)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(self.chat_container)
        right_l.addWidget(self.scroll, 1)

        bottom = QHBoxLayout()
        self.input = QTextEdit()
        self.input.setPlaceholderText("Napiš problém… (bez osobních údajů)")
        self.input.setFixedHeight(90)
        self.input.setStyleSheet(
            """
            QTextEdit{
                background:#ffffff;
                color:#111;
                border:1px solid #444;
                border-radius:10px;
                padding:8px;
                font-size:13px;
            }
            """
        )
        self.send_btn = QPushButton("Odeslat")
        self.send_btn.clicked.connect(self.on_send)
        bottom.addWidget(self.input, 1)
        bottom.addWidget(self.send_btn)
        right_l.addLayout(bottom)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([260, 840])

        self.refresh_sessions()
        self.new_chat()

        # Auto-setup Ollama on first run (start server + pull model if missing)
        self._setup_worker: Optional[OllamaSetupWorker] = None
        self._setup_in_progress = False
        self._maybe_setup_ollama()

    def _maybe_setup_ollama(self) -> None:
        """If user chose Ollama, try to make everything ready automatically.

        This removes the need to manually run `ollama pull ...` outside of the app.
        """
        if self.cfg.llm_provider != "ollama":
            return

        # Avoid running setup multiple times
        if self._setup_in_progress:
            return

        self._setup_in_progress = True
        self.send_btn.setEnabled(False)
        self.send_btn.setText("Nastavuji…")

        # Do not spam the chat with setup messages (keeps the chat area tall).
        # Instead, show it in the status bar + on the send button.
        setup_txt = (
            "Nastavuji Ollamu…" if "ollama.com" not in self.cfg.ollama_base_url.lower() else "Nastavuji Ollama Cloud…"
        )
        try:
            self.statusBar().showMessage(setup_txt)
        except Exception:
            pass

        self._setup_worker = OllamaSetupWorker(self.cfg)
        self._setup_worker.progress.connect(self._on_setup_progress)
        self._setup_worker.finished_ok.connect(self._on_setup_ok)
        self._setup_worker.finished_error.connect(self._on_setup_error)
        self._setup_worker.start()

    def _on_setup_progress(self, line: str) -> None:
        # Lightweight feedback: update the send button text
        if line:
            self.send_btn.setText("Nastavuji…")

    def _on_setup_ok(self, message: str) -> None:
        self._setup_in_progress = False
        self.send_btn.setEnabled(True)
        self.send_btn.setText("Odeslat")
        # Status only (no extra bubbles)
        try:
            self.statusBar().showMessage(f"✅ {message}", 6000)
        except Exception:
            pass

    def _on_setup_error(self, message: str) -> None:
        self._setup_in_progress = False
        self.send_btn.setEnabled(True)
        self.send_btn.setText("Odeslat")
        # Status only (no extra bubbles)
        try:
            self.statusBar().showMessage(f"⚠️ {message}")
        except Exception:
            pass

    def open_lawyer_search(self) -> None:
        QDesktopServices.openUrl(QUrl("https://vyhledavac.cak.cz/"))

    def refresh_sessions(self) -> None:
        self.sessions_list.clear()
        for s in self.db.list_sessions():
            item = QListWidgetItem(f"{s['title']}\n({s['category']})")
            item.setData(Qt.UserRole, s["id"])
            self.sessions_list.addItem(item)

    def clear_chat_ui(self) -> None:
        while self.chat_l.count() > 0:
            it = self.chat_l.takeAt(0)
            w = it.widget()
            if w is not None:
                w.deleteLater()
        self.chat_l.addStretch(1)

    def load_session(self, session_id: int) -> None:
        self.current_session_id = session_id
        self.clear_chat_ui()
        msgs = self.db.get_messages(session_id)
        for m in msgs:
            self.add_bubble(m["role"], m["content"], m.get("traffic_light"))
        self.scroll.verticalScrollBar().setValue(self.scroll.verticalScrollBar().maximum())

    def add_system_intro(self) -> None:
        if not self.current_session_id:
            return
        # Intro is intentionally NOT stored into chat.
        # It used to create large "welcome" bubbles that made the chat area too small.
        # (User can still see guidance via the placeholder text and status bar.)
        return

    def new_chat(self) -> None:
        # Při založení nového chatu ještě nemáme žádný dotaz, takže oblast
        # necháme na vybranou hodnotu (nebo AUTO) a rozpoznání uděláme až
        # při odeslání první zprávy.
        category = self.category_cb.currentText()
        # Make the title unique so deleting a chat is visually obvious in history.
        title = datetime.now().strftime("Chat %d.%m.%Y %H:%M:%S")
        sid = self.db.create_session(title, category)
        self.refresh_sessions()
        self.load_session(sid)
        self.send_btn.setEnabled(True)
        self.input.setEnabled(True)
        # No welcome bubble: keep maximum room for actual answers.

    
    def delete_current_chat(self) -> None:
        """Delete the currently opened chat and immediately remove it from the history list."""
        if not self.current_session_id:
            return

        reply = QMessageBox.question(
            self,
            "Smazat chat",
            "Opravdu smazat tento chat? (Smaže se historie zpráv.)",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        deleted_id = int(self.current_session_id)
        self.db.delete_session(deleted_id)

        # Clear current view
        self.current_session_id = None
        self.clear_chat_ui()
        self.statusBar().showMessage("✅ Chat byl smazán.", 3000)

        # Refresh history list and load another chat if available.
        self.refresh_sessions()

        if self.sessions_list.count() > 0:
            self.sessions_list.setCurrentRow(0)
            item = self.sessions_list.item(0)
            sid = item.data(Qt.UserRole)
            if sid:
                self.load_session(int(sid))
        else:
            # No chats left – user must create a new one.
            self.send_btn.setEnabled(False)
            self.input.setEnabled(False)


    def on_session_clicked(self, item: QListWidgetItem) -> None:
        sid = item.data(Qt.UserRole)
        if sid:
            self.load_session(int(sid))

    def add_bubble(self, role: str, html: str, traffic_light: Optional[str] = None) -> None:
        stretch_index = self.chat_l.count() - 1
        self.chat_l.insertWidget(stretch_index, ChatBubble(role, html, traffic_light))

    def on_send(self) -> None:
        if not self.current_session_id:
            return

        question = normalize_text(self.input.toPlainText())
        if not question:
            return

        selected = self.category_cb.currentText()

        # Automatické rozpoznání oblasti (když je vybrané AUTO)
        if selected == AUTO_CATEGORY:
            category = infer_category(question)
            idx = self.category_cb.findText(category)
            if idx >= 0:
                self.category_cb.setCurrentIndex(idx)
        else:
            category = selected

        self.db.add_message(self.current_session_id, "user", question)
        self.add_bubble("user", question)
        self.input.clear()

        self.send_btn.setEnabled(False)
        self.send_btn.setText("…")

        self.add_bubble("assistant", "Pracuju na odpovědi…", traffic_light="yellow")
        self.worker = Worker(self.cfg, category, question)
        self.worker.done.connect(self.on_done)
        self.worker.start()

    def on_done(self, result: object, light: str, sources_json: str) -> None:
        if isinstance(result, Exception):
            msg = f"Nastala chyba: <b>{type(result).__name__}</b><br>{str(result)}<br><br>Tip: zkontroluj `.env` a provider."
            self.db.add_message(self.current_session_id, "assistant", msg, traffic_light="red", sources_json="[]")
        else:
            ans: LawmateAnswer = result
            html = format_answer(ans)
            self.db.add_message(self.current_session_id, "assistant", html, traffic_light=light, sources_json=sources_json)

        self.load_session(self.current_session_id)

        self.send_btn.setEnabled(True)
        self.send_btn.setText("Odeslat")
