"""Chat tab - talks to the local LLM, detects mood from what you type,
and surfaces a few personalised recommendation cards after each message."""

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QComboBox, QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QTextEdit,
    QVBoxLayout, QWidget,
)

from ai_client import chat_ai
from data import (
    CHAT_LANGUAGES, COLORS as C, CRISIS_FALLBACK, MOOD_FALLBACKS, MOODS, SUPPORT_RESOURCES, default_chat_language,
    detect_crisis, detect_mood, get_personalized_recs, language_instruction, whisper_language,
)
from ui.flow_layout import FlowLayout
from ui.camera_dialog import CameraDialog
from voice import MicRecorder, TranscribeWorker
from workers import FnWorker


def build_system_prompt(profile, language=None):
    """The instructions sent to the model. `language` is the reply language chosen on
    the Chat page (a code from CHAT_LANGUAGES); None means the default for this profile."""
    cond_labels = ", ".join(profile.get("conditions", [])) or "none mentioned"
    goal_labels = ", ".join(profile.get("goals", [])) or "general wellbeing"
    if language is None:
        language = default_chat_language(profile.get("language"))

    prompt = f"""You are a warm, caring wellbeing companion. You speak like a trusted, thoughtful friend - not a therapist, not a chatbot.

About the person you're talking with:
- Health conditions: {cond_labels}
- Wellbeing goals: {goal_labels}
- Age group: {profile.get('age_group') or 'not specified'}

Your tone and style:
- Conversational and genuine, never scripted or clinical.
- Respond to the specific thing they said - not to a general category.
- 3-5 sentences. Never use bullet points.
- Never begin with "I hear you", "I understand", "That sounds", or any formulaic opener.
- Vary your openers. Ask a follow-up occasionally but not every single message.
- Reference actual details they've shared. Be present with them.
- If they seem distressed, gently acknowledge it before anything else.
- They may write in Hinglish (Hindi typed in English letters, e.g. "mujhe dar lagta hai" means "I feel scared") or mix languages. Understand it as the language it is, not as English."""

    instruction = language_instruction(language)
    if instruction:
        prompt += "\n\n" + instruction
    return prompt


class MessageBubble(QFrame):
    def __init__(self, role, content, mood=None, is_offline=False, parent=None):
        super().__init__(parent)
        is_user = role == "user"
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        bubble = QLabel(content + ("\n(offline response)" if is_offline else ""))
        bubble.setWordWrap(True)
        bubble.setMaximumWidth(480)
        bg = C["primary"] if is_user else C["surface"]
        fg = C["on_primary"] if is_user else C["text"]
        border = "none" if is_user else f"1px solid {C['border']}"
        bubble.setStyleSheet(
            f"background:{bg}; color:{fg}; border:{border}; border-radius:14px; padding:10px 14px;"
        )

        if is_user:
            layout.addStretch()
            layout.addWidget(bubble)
            if mood:
                mood_lbl = QLabel(mood["emoji"])
                mood_lbl.setStyleSheet(f"background:{mood['bg']}; border-radius:14px; padding:4px;")
                layout.addWidget(mood_lbl)
        else:
            avatar = QLabel("🌿")
            avatar.setStyleSheet(f"background:{C['sage_pale']}; border-radius:17px; padding:6px;")
            layout.addWidget(avatar)
            layout.addWidget(bubble)
            layout.addStretch()


class RecCard(QFrame):
    def __init__(self, rec, parent=None):
        super().__init__(parent)
        # scoped to #recCard - QLabel is a QFrame subclass, so a bare
        # "QFrame { ... }" rule here would also box the body QLabel below
        self.setObjectName("recCard")
        self.setStyleSheet(
            f"QFrame#recCard {{ background:{C['surface']}; border:1px solid {C['border']}; border-radius:12px; }}"
        )
        layout = QVBoxLayout(self)
        header = QPushButton(f"{rec['emoji']}  {rec['title']}")
        header.setCheckable(True)
        header.setStyleSheet(
            f"text-align:left; background:none; border:none; color:{C['text']}; font-weight:600; padding:4px;"
        )
        body = QLabel(rec["body"])
        body.setWordWrap(True)
        body.setStyleSheet(f"color:{C['text_muted']}; font-size:11px; padding:0 4px 4px;")
        body.setVisible(False)
        header.toggled.connect(body.setVisible)
        layout.addWidget(header)
        layout.addWidget(body)


class ChatInput(QTextEdit):
    """Enter sends the message; Shift+Enter inserts a new line."""

    submitted = Signal()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter) and not (event.modifiers() & Qt.ShiftModifier):
            self.submitted.emit()
            return
        super().keyPressEvent(event)


class ChatTab(QWidget):
    def __init__(self, db, user_id, profile, get_ai_config, parent=None, on_open_support=None):
        super().__init__(parent)
        self.on_open_support = on_open_support
        self.db = db
        self.user_id = user_id
        self.profile = profile
        self.get_ai_config = get_ai_config  # callable -> latest ai_config dict
        self.connected = None
        self.messages = []  # list of {"role", "content"}
        self.last_rec_id = None
        self._worker = None

        self.recorder = MicRecorder()
        self.recording = False
        self._transcribe_worker = None

        root = QHBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(20)

        left = QVBoxLayout()
        left.setSpacing(12)
        root.addLayout(left, stretch=3)

        self.crisis_banner = QFrame()
        self.crisis_banner.setObjectName("crisisBanner")
        self.crisis_banner.setStyleSheet(
            "QFrame#crisisBanner { background:#FCEEE9; border:1px solid #F4B8AA; border-radius:12px; }"
        )
        crisis_layout = QVBoxLayout(self.crisis_banner)
        self.crisis_text = QLabel("")
        self.crisis_text.setWordWrap(True)
        self.crisis_text.setStyleSheet("color:#8A2F1B; background:transparent;")
        crisis_layout.addWidget(self.crisis_text)
        crisis_btns = QHBoxLayout()
        open_support = QPushButton("Open support resources")
        open_support.clicked.connect(lambda: self.on_open_support and self.on_open_support())
        dismiss = QPushButton("Dismiss")
        dismiss.setObjectName("ghost")
        dismiss.clicked.connect(lambda: self.crisis_banner.setVisible(False))
        crisis_btns.addWidget(open_support)
        crisis_btns.addWidget(dismiss)
        crisis_btns.addStretch()
        crisis_layout.addLayout(crisis_btns)
        self.crisis_banner.setVisible(False)
        left.addWidget(self.crisis_banner)

        self.offline_banner = QLabel("Local AI not detected - start Ollama or LM Studio, then check settings.")
        self.offline_banner.setStyleSheet(
            "background:#FEF3E6; border:1px solid #F4C97A; color:#9B6000; border-radius:10px; padding:8px 12px;"
        )
        self.offline_banner.setVisible(False)
        left.addWidget(self.offline_banner)

        self.greeting = QLabel(f"Hello, {profile.get('name', 'friend')}\n\nHow are you feeling today? Share anything on your mind.")
        self.greeting.setWordWrap(True)
        self.greeting.setAlignment(Qt.AlignCenter)
        self.greeting.setStyleSheet(
            f"background:{C['surface']}; border-radius:16px; padding:32px; color:{C['text_muted']}; font-size:14px;"
        )
        left.addWidget(self.greeting)

        starters = ["I'm feeling anxious", "Help me wind down for sleep", "I had a rough day",
                    "I want to feel more motivated"]
        self.starter_row = QWidget()
        self.starter_row.setObjectName("flowHost")
        flow = FlowLayout(self.starter_row, h_spacing=8, v_spacing=8)
        for text in starters:
            chip = QPushButton(text)
            chip.setObjectName("ghost")
            chip.setCursor(Qt.PointingHandCursor)
            chip.clicked.connect(lambda _c, t=text: self._send_text(t))
            flow.addWidget(chip)
        left.addWidget(self.starter_row)

        self.clear_btn = QPushButton("Clear chat")
        self.clear_btn.setObjectName("linkButton")
        self.clear_btn.setCursor(Qt.PointingHandCursor)
        self.clear_btn.setVisible(False)
        self.clear_btn.clicked.connect(self._clear_chat)

        bar = QHBoxLayout()
        bar.setSpacing(8)
        bar.addWidget(QLabel("🌐  Reply in"))
        self.language_combo = QComboBox()
        self.language_combo.setToolTip("The language the companion answers in - change it any time")
        self.language_combo.setMinimumWidth(250)
        for lang in CHAT_LANGUAGES:
            self.language_combo.addItem(lang["name"], lang["code"])
        self.language = self._load_language()
        self.language_combo.setCurrentIndex(max(0, self.language_combo.findData(self.language)))
        self.language_combo.currentIndexChanged.connect(self._on_language_changed)
        bar.addWidget(self.language_combo)
        bar.addStretch()
        bar.addWidget(self.clear_btn)
        left.addLayout(bar)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.messages_container = QWidget()
        self.messages_layout = QVBoxLayout(self.messages_container)
        self.messages_layout.addStretch()
        self.scroll.setWidget(self.messages_container)
        left.addWidget(self.scroll, stretch=1)

        self.mood_badge = QLabel("")
        self.mood_badge.setVisible(False)
        left.addWidget(self.mood_badge)

        self.camera_preview = QLabel()
        self.camera_preview.setVisible(False)
        self.camera_preview.setStyleSheet(f"border:1px solid {C['border']}; border-radius:10px; padding:2px;")
        left.addWidget(self.camera_preview)

        self.assist_status = QLabel("")
        self.assist_status.setWordWrap(True)
        self.assist_status.setVisible(False)
        self.assist_status.setStyleSheet(f"color:{C['text_muted']}; font-size:12px; padding:2px 0;")
        left.addWidget(self.assist_status)

        input_row = QHBoxLayout()
        self.input_box = ChatInput()
        self.input_box.submitted.connect(self._send)
        self.input_box.setPlaceholderText("Share what's on your mind…  (Enter to send, Shift+Enter for a new line)")
        self.input_box.setFixedHeight(60)
        input_row.addWidget(self.input_box)

        btn_col = QVBoxLayout()
        self.mic_btn = QPushButton("🎤")
        self.mic_btn.setToolTip("Speech to text (local Whisper model)")
        self.mic_btn.setObjectName("iconBtn")
        self.mic_btn.clicked.connect(self._toggle_recording)
        btn_col.addWidget(self.mic_btn)

        self.camera_btn = QPushButton("📷")
        self.camera_btn.setToolTip("Open the camera to check your mood (live preview)")
        self.camera_btn.setObjectName("iconBtn")
        self.camera_btn.clicked.connect(self._check_camera_mood)
        btn_col.addWidget(self.camera_btn)
        input_row.addLayout(btn_col)

        self.send_btn = QPushButton("Send ↑")
        self.send_btn.clicked.connect(self._send)
        input_row.addWidget(self.send_btn)
        left.addLayout(input_row)

        self.rec_panel = QVBoxLayout()
        rec_container = QWidget()
        rec_container.setLayout(self.rec_panel)
        rec_scroll = QScrollArea()
        rec_scroll.setWidgetResizable(True)
        rec_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        rec_scroll.setFixedWidth(280)
        rec_scroll.setWidget(rec_container)
        root.addWidget(rec_scroll, stretch=1)

        rec_title = QLabel("FOR YOU RIGHT NOW")
        rec_title.setStyleSheet(f"color:{C['text_muted']}; font-size:11px; font-weight:600;")
        self.rec_panel.addWidget(rec_title)
        self.rec_panel.addStretch()

        self._load_history()

    # -- reply language --------------------------------------------------------------

    def _language_key(self):
        return f"chat_language_{self.user_id}"

    def _load_language(self):
        saved = self.db.get_setting(self._language_key())
        if saved in {lang["code"] for lang in CHAT_LANGUAGES}:
            return saved
        return default_chat_language(self.profile.get("language"))

    def _on_language_changed(self, _index):
        self.language = self.language_combo.currentData()
        self.db.set_setting(self._language_key(), self.language)
        name = self.language_combo.currentText()
        self._show_assist_status(f"Replies will now be in: {name}" if self.language != "auto"
                                 else "Replies will follow the language you write in")

    def _load_history(self):
        for row in self.db.get_chat_messages(self.user_id):
            offline = row["mood"] == "offline"
            mood = MOODS.get(row["mood"]) and {"mood": row["mood"], **MOODS[row["mood"]]} if row["role"] == "user" else None
            self._append_bubble(row["role"], row["content"], mood=mood, is_offline=offline)
            if not offline:  # canned offline replies aren't part of the model's conversation
                self.messages.append({"role": row["role"], "content": row["content"]})
        if self.messages or self.messages_layout.count() > 1:
            self.greeting.setVisible(False)
            self.starter_row.setVisible(False)
            self.clear_btn.setVisible(True)

    def _clear_chat(self):
        self.db.clear_chat_messages(self.user_id)
        self.messages.clear()
        while self.messages_layout.count() > 1:
            item = self.messages_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.greeting.setVisible(True)
        self.starter_row.setVisible(True)
        self.clear_btn.setVisible(False)
        self.crisis_banner.setVisible(False)

    def _scroll_to_bottom(self):
        bar = self.scroll.verticalScrollBar()
        QTimer.singleShot(0, self.scroll, lambda: bar.setValue(bar.maximum()))

    def set_connected(self, connected):
        self.connected = connected
        self.offline_banner.setVisible(connected is False)

    def _send_text(self, text):
        self.input_box.setPlainText(text)
        self._send()

    def _crisis_lines(self):
        """First couple of crisis helplines for the user's country."""
        resources = SUPPORT_RESOURCES.get(self.profile.get("country") or "", SUPPORT_RESOURCES["DEFAULT"])
        return resources.get("crisis", [])[:2]

    def _show_crisis_banner(self):
        lines = [f"<b>{r['name']}</b>" + (f" - {r['contact']}" if r.get("contact") else "")
                 for r in self._crisis_lines()]
        self.crisis_text.setText(
            "<b>You're not alone.</b> If you're thinking about harming yourself, please reach out to someone "
            "right now:<br>" + "<br>".join(lines) +
            "<br>If you're in immediate danger, call your local emergency number."
        )
        self.crisis_banner.setVisible(True)

    def _send(self):
        text = self.input_box.toPlainText().strip()
        if not text or self.send_btn.text() == "Sending…":
            return

        self._crisis = detect_crisis(text)
        if self._crisis:
            self._show_crisis_banner()

        detected = detect_mood(text)
        self.db.add_mood_entry(self.user_id, detected["mood"])
        self._show_mood_badge(detected)
        self._refresh_recs(detected["mood"])

        self.messages.append({"role": "user", "content": text})
        self.db.add_chat_message(self.user_id, "user", text, detected["mood"])
        self.clear_btn.setVisible(True)
        self._append_bubble("user", text, mood=detected)
        self.input_box.clear()
        self.greeting.setVisible(False)
        self.starter_row.setVisible(False)

        self.send_btn.setText("Sending…")
        self.send_btn.setEnabled(False)

        api_messages = [{"role": m["role"], "content": m["content"]} for m in self.messages[-20:]]
        system_prompt = build_system_prompt(self.profile, self.language)
        config = self.get_ai_config()

        self._worker = FnWorker(lambda: chat_ai(config, api_messages, system_prompt))
        self._worker.finished_ok.connect(lambda reply: self._on_reply(reply, detected))
        self._worker.failed.connect(lambda _err: self._on_reply_failed(detected))
        self._worker.start()

    def _on_reply(self, reply, _detected):
        self.messages.append({"role": "assistant", "content": reply})
        self.db.add_chat_message(self.user_id, "assistant", reply)
        self._append_bubble("assistant", reply)
        self._finish_send()

    def _on_reply_failed(self, detected):
        fallback = CRISIS_FALLBACK if getattr(self, "_crisis", False) else \
            MOOD_FALLBACKS.get(detected["mood"], MOOD_FALLBACKS["calm"])
        self.db.add_chat_message(self.user_id, "assistant", fallback, "offline")
        self._append_bubble("assistant", fallback, is_offline=True)
        self._finish_send()

    def _finish_send(self):
        self.send_btn.setText("Send ↑")
        self.send_btn.setEnabled(True)

    def _append_bubble(self, role, content, mood=None, is_offline=False):
        bubble = MessageBubble(role, content, mood=mood, is_offline=is_offline)
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, bubble)
        self._scroll_to_bottom()

    def _show_mood_badge(self, mood):
        self.mood_badge.setText(f"{mood['emoji']}  Mood: {mood['label']}")
        self.mood_badge.setStyleSheet(
            f"background:{mood['bg']}; color:{mood['color']}; border-radius:12px; padding:5px 12px; font-weight:600;"
        )
        self.mood_badge.setVisible(True)

    def _refresh_recs(self, mood):
        recs = get_personalized_recs(self.profile, mood, self.last_rec_id)
        if recs:
            self.last_rec_id = recs[0]["id"]

        # clear old cards (keep the title label + trailing stretch)
        while self.rec_panel.count() > 2:
            item = self.rec_panel.takeAt(1)
            if item.widget():
                item.widget().deleteLater()

        for rec in recs:
            self.rec_panel.insertWidget(self.rec_panel.count() - 1, RecCard(rec))

    # -- Speech to text (local Whisper) --------------------------------

    def _toggle_recording(self):
        if not self.recording:
            try:
                self.recorder.start()
            except Exception as exc:  # noqa: BLE001 - mic permission / no device, surfaced to the user
                self._show_assist_status(f"Couldn't start recording: {exc}", is_error=True)
                return
            self.recording = True
            self.mic_btn.setText("⏹")
            self._show_assist_status("🎤 Recording… click again to stop.")
        else:
            audio = self.recorder.stop()
            self.recording = False
            self.mic_btn.setText("🎤")
            self._show_assist_status("Transcribing…")

            self._transcribe_worker = TranscribeWorker(audio, language=whisper_language(self.language))
            self._transcribe_worker.finished_ok.connect(self._on_transcribed)
            self._transcribe_worker.failed.connect(self._on_transcribe_failed)
            self._transcribe_worker.start()

    def _on_transcribed(self, text):
        if text:
            current = self.input_box.toPlainText()
            self.input_box.setPlainText((current + " " + text).strip())
        self._show_assist_status("")
        self.assist_status.setVisible(False)

    def _on_transcribe_failed(self, message):
        self._show_assist_status(f"Couldn't transcribe that: {message}", is_error=True)

    # -- Camera-based mood check -----------------------------------------

    def _check_camera_mood(self):
        """Opens the live camera window. The camera stays on, with a live
        picture, until the window is closed; a logged result comes back
        through mood_selected."""
        dialog = CameraDialog(self)
        dialog.mood_selected.connect(self._on_face_mood)
        dialog.exec()

    def _on_face_mood(self, result):
        mood = {"mood": result["mood"], **MOODS[result["mood"]]}
        self.db.add_mood_entry(self.user_id, mood["mood"])
        self._show_mood_badge(mood)
        self._refresh_recs(mood["mood"])
        self._show_assist_status(
            f"Camera detected: {result['fer_label']} ({round(result['confidence'] * 100)}% confidence)"
        )

        self._show_camera_snapshot(result.get("preview"))

    def _show_camera_snapshot(self, image):
        """Shows the camera picture under the mood badge - with the face boxed
        on success, or as-is when no face was found so you can see why."""
        if image is not None and not image.isNull():
            pixmap = QPixmap.fromImage(image).scaledToHeight(160, Qt.SmoothTransformation)
            self.camera_preview.setPixmap(pixmap)
            self.camera_preview.setVisible(True)

    def _show_assist_status(self, text, is_error=False):
        self.assist_status.setText(text)
        self.assist_status.setVisible(bool(text))
        self.assist_status.setStyleSheet(
            f"color:{'#E07A5F' if is_error else C['text_muted']}; font-size:12px; padding:2px 0;"
        )
