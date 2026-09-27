"""Journal tab - a writing prompt, a text box with live mood detection,
and a list of past entries stored in SQLite."""

import random
from datetime import datetime

from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QScrollArea, QTextEdit, QVBoxLayout, QWidget,
)

from data import COLORS as C, JOURNAL_PROMPTS, MOODS, detect_mood
from ui.widgets import Card


class JournalTab(QWidget):
    def __init__(self, db, user_id, on_go_to_chat=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.user_id = user_id
        self.on_go_to_chat = on_go_to_chat
        self.prompt_idx = random.randrange(len(JOURNAL_PROMPTS))

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(14)

        title = QLabel("Journal")
        title.setStyleSheet(f"font-size:22px; font-weight:700; color:{C['primary']};")
        outer.addWidget(title)

        prompt_card = Card()
        self.prompt_label = QLabel(f'"{JOURNAL_PROMPTS[self.prompt_idx]}"')
        self.prompt_label.setWordWrap(True)
        self.prompt_label.setStyleSheet(f"font-size:15px; color:{C['text']}; font-style:italic;")
        prompt_card.layout_.addWidget(self.prompt_label)
        next_prompt_btn = QPushButton("Show another ↺")
        next_prompt_btn.setObjectName("ghost")
        next_prompt_btn.clicked.connect(self._next_prompt)
        prompt_card.layout_.addWidget(next_prompt_btn)
        outer.addWidget(prompt_card)

        self.text_box = QTextEdit()
        self.text_box.setPlaceholderText("Start writing here… no pressure, no judgment.")
        self.text_box.setMinimumHeight(150)
        self.text_box.textChanged.connect(self._update_live_mood)
        outer.addWidget(self.text_box)

        self.live_mood_label = QLabel("")
        self.live_mood_label.setVisible(False)
        outer.addWidget(self.live_mood_label)

        btn_row = QHBoxLayout()
        self.saved_label = QLabel("")
        self.saved_label.setStyleSheet(f"color:{C['sage']};")
        btn_row.addWidget(self.saved_label)
        btn_row.addStretch()

        share_btn = QPushButton("Share with companion →")
        share_btn.setObjectName("ghost")
        share_btn.clicked.connect(self._share_with_ai)
        btn_row.addWidget(share_btn)

        save_btn = QPushButton("Save entry")
        save_btn.clicked.connect(self._save_entry)
        btn_row.addWidget(save_btn)
        outer.addLayout(btn_row)

        filter_row = QHBoxLayout()
        heading = QLabel("Past entries")
        heading.setStyleSheet("font-size:15px; font-weight:700;")
        filter_row.addWidget(heading)
        filter_row.addStretch()
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("🔍 Search entries…")
        self.search_box.setFixedWidth(220)
        self.search_box.textChanged.connect(self._load_entries)
        filter_row.addWidget(self.search_box)
        self.mood_filter = QComboBox()
        self.mood_filter.addItem("All moods", None)
        for key, meta in MOODS.items():
            self.mood_filter.addItem(f"{meta['emoji']} {meta['label']}", key)
        self.mood_filter.currentIndexChanged.connect(self._load_entries)
        filter_row.addWidget(self.mood_filter)
        outer.addLayout(filter_row)

        self.empty_label = QLabel("")
        self.empty_label.setStyleSheet(f"color:{C['text_muted']}; font-style:italic;")
        outer.addWidget(self.empty_label)
        self.entries_scroll = QScrollArea()
        self.entries_scroll.setWidgetResizable(True)
        self.entries_container = QWidget()
        self.entries_layout = QVBoxLayout(self.entries_container)
        self.entries_layout.addStretch()
        self.entries_scroll.setWidget(self.entries_container)
        outer.addWidget(self.entries_scroll, stretch=1)

        self._load_entries()

    def _next_prompt(self):
        self.prompt_idx = (self.prompt_idx + 1) % len(JOURNAL_PROMPTS)
        self.prompt_label.setText(f'"{JOURNAL_PROMPTS[self.prompt_idx]}"')

    def _update_live_mood(self):
        text = self.text_box.toPlainText()
        if len(text.strip()) > 10:
            mood = detect_mood(text)
            self.live_mood_label.setText(f"{mood['emoji']} {mood['label']} - detected as you write")
            self.live_mood_label.setStyleSheet(
                f"background:{mood['bg']}; color:{mood['color']}; border-radius:10px; padding:4px 10px;"
            )
            self.live_mood_label.setVisible(True)
        else:
            self.live_mood_label.setVisible(False)

    def _save_entry(self):
        text = self.text_box.toPlainText().strip()
        if not text:
            return
        mood = detect_mood(text)
        self.db.add_journal_entry(self.user_id, JOURNAL_PROMPTS[self.prompt_idx], text, mood["mood"])
        self.db.add_mood_entry(self.user_id, mood["mood"])
        self.text_box.clear()
        self.saved_label.setText("✓ Entry saved")
        self._load_entries()

    def _share_with_ai(self):
        text = self.text_box.toPlainText().strip()
        if text and self.on_go_to_chat:
            self.on_go_to_chat(text)

    def _load_entries(self):
        while self.entries_layout.count() > 1:
            item = self.entries_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        entries = self.db.get_journal_entries(self.user_id)
        query = self.search_box.text().strip().lower()
        mood_key = self.mood_filter.currentData()
        if query:
            entries = [e for e in entries if query in e["text"].lower() or query in (e["prompt"] or "").lower()]
        if mood_key:
            entries = [e for e in entries if e["mood"] == mood_key]

        if entries:
            self.empty_label.setText("")
        elif query or mood_key:
            self.empty_label.setText("No entries match that search.")
        else:
            self.empty_label.setText("Nothing here yet - your saved entries will show up below.")
        for entry in entries:
            self.entries_layout.insertWidget(self.entries_layout.count() - 1, self._entry_card(entry))

    def _entry_card(self, entry):
        card = Card()
        when = datetime.fromtimestamp(entry["timestamp"] / 1000).strftime("%b %d, %H:%M")
        header = QHBoxLayout()
        meta = MOODS.get(entry["mood"], {})
        mood_lbl = QLabel(f"{meta.get('emoji', '')} {meta.get('label', entry['mood'] or '')} · {when}")
        mood_lbl.setStyleSheet(f"color:{C['text_muted']}; font-size:11px;")
        header.addWidget(mood_lbl)
        header.addStretch()
        delete_btn = QPushButton("×")
        delete_btn.setObjectName("iconBtn")
        delete_btn.setToolTip("Delete this entry")
        delete_btn.clicked.connect(lambda: self._delete_entry(entry["id"]))
        header.addWidget(delete_btn)
        card.layout_.addLayout(header)

        if entry.get("prompt"):
            prompt_lbl = QLabel(f'"{entry["prompt"]}"')
            prompt_lbl.setStyleSheet(f"color:{C['text_muted']}; font-style:italic; font-size:11px;")
            prompt_lbl.setWordWrap(True)
            card.layout_.addWidget(prompt_lbl)

        text = entry["text"]
        body = QLabel(text[:200] + "…" if len(text) > 200 else text)
        body.setWordWrap(True)
        card.layout_.addWidget(body)
        return card

    def _delete_entry(self, entry_id):
        self.db.delete_journal_entry(entry_id)
        self._load_entries()
