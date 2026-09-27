"""Affirmations tab - browse a deck of affirmations, favorite the ones
that land, favorites saved per-account in SQLite."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from data import AFFIRMATIONS, COLORS as C
from ui.widgets import Card


class AffirmTab(QWidget):
    def __init__(self, db, user_id, parent=None):
        super().__init__(parent)
        self.db = db
        self.user_id = user_id
        self.idx = 0

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(14)
        title = QLabel("Affirmations")
        title.setStyleSheet(f"font-size:22px; font-weight:700; color:{C['primary']};")
        outer.addWidget(title)
        outer.addWidget(self._muted("Words worth sitting with. Take what feels true today."))

        card = Card()
        # scoped to #card only - a bare "QFrame { ... }" rule would cascade onto
        # the QLabel children below too, since QLabel is itself a QFrame subclass
        card.setStyleSheet(
            f"QFrame#card {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 {C['primary_pale']}, "
            f"stop:1 {C['sage_pale']}); border:1px solid {C['border']}; border-radius:20px; }}"
        )
        self.affirmation_label = QLabel()
        self.affirmation_label.setWordWrap(True)
        self.affirmation_label.setAlignment(Qt.AlignCenter)
        self.affirmation_label.setStyleSheet("font-size:18px; padding:24px;")
        card.layout_.addWidget(self.affirmation_label)

        nav_row = QHBoxLayout()
        prev_btn = QPushButton("‹")
        prev_btn.setObjectName("iconBtn")
        prev_btn.clicked.connect(self._prev)
        self.fav_btn = QPushButton("♡")
        self.fav_btn.setObjectName("iconBtn")
        self.fav_btn.clicked.connect(self._toggle_fav)
        next_btn = QPushButton("›")
        next_btn.setObjectName("iconBtn")
        next_btn.clicked.connect(self._next)
        nav_row.addStretch()
        nav_row.addWidget(prev_btn)
        nav_row.addWidget(self.fav_btn)
        nav_row.addWidget(next_btn)
        nav_row.addStretch()
        card.layout_.addLayout(nav_row)

        self.counter_label = QLabel()
        self.counter_label.setAlignment(Qt.AlignCenter)
        self.counter_label.setStyleSheet(f"color:{C['text_muted']}; font-size:11px;")
        card.layout_.addWidget(self.counter_label)

        outer.addWidget(card)

        outer.addWidget(QLabel("Saved ♥"))
        self.favs_scroll = QScrollArea()
        self.favs_scroll.setWidgetResizable(True)
        self.favs_container = QWidget()
        self.favs_layout = QVBoxLayout(self.favs_container)
        self.favs_layout.addStretch()
        self.favs_scroll.setWidget(self.favs_container)
        outer.addWidget(self.favs_scroll, stretch=1)

        self._render()

    def _muted(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color:{C['text_muted']};")
        return lbl

    def _render(self):
        current = AFFIRMATIONS[self.idx]
        self.affirmation_label.setText(f'"{current["text"]}"')
        self.counter_label.setText(f"{self.idx + 1} of {len(AFFIRMATIONS)}")

        fav_ids = self.db.get_favorite_ids(self.user_id)
        is_fav = current["id"] in fav_ids
        self.fav_btn.setText("♥" if is_fav else "♡")
        self.fav_btn.setStyleSheet("color:#E07A5F; background:#FCEEE9;" if is_fav else "")

        self._render_favorites(fav_ids)

    def _render_favorites(self, fav_ids):
        while self.favs_layout.count() > 1:
            item = self.favs_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for fav_id in fav_ids:
            aff = next((a for a in AFFIRMATIONS if a["id"] == fav_id), None)
            if not aff:
                continue
            card = Card()
            row = QHBoxLayout()
            text_lbl = QLabel(f'"{aff["text"]}"')
            text_lbl.setWordWrap(True)
            row.addWidget(text_lbl, stretch=1)
            remove_btn = QPushButton("♥")
            remove_btn.setObjectName("iconBtn")
            remove_btn.setStyleSheet("color:#E07A5F; background:#FCEEE9;")
            remove_btn.clicked.connect(lambda _c, aid=aff["id"]: self._toggle_fav_by_id(aid))
            row.addWidget(remove_btn)
            card.layout_.addLayout(row)
            self.favs_layout.insertWidget(self.favs_layout.count() - 1, card)

    def _prev(self):
        self.idx = (self.idx - 1) % len(AFFIRMATIONS)
        self._render()

    def _next(self):
        self.idx = (self.idx + 1) % len(AFFIRMATIONS)
        self._render()

    def _toggle_fav(self):
        self.db.toggle_favorite(self.user_id, AFFIRMATIONS[self.idx]["id"])
        self._render()

    def _toggle_fav_by_id(self, affirmation_id):
        self.db.toggle_favorite(self.user_id, affirmation_id)
        self._render()
