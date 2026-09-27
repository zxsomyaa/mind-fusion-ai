"""Health tab - static, personalised tip cards for whatever conditions the
user picked during onboarding. No AI call needed, just a lookup table."""

from PySide6.QtWidgets import QLabel, QScrollArea, QVBoxLayout, QWidget

from data import COLORS as C, CONDITION_TIPS, HEALTH_CONDITIONS
from ui.widgets import Card


class HealthTab(QWidget):
    def __init__(self, profile, parent=None):
        super().__init__(parent)
        conditions = profile.get("conditions", [])

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        if not conditions:
            empty = QLabel(
                "🌿\n\nYour health profile\n\n"
                "You haven't added any health conditions yet. Head to onboarding to add them, "
                "and we'll show you personalised daily tips here."
            )
            empty.setWordWrap(True)
            empty.setStyleSheet(f"color:{C['text_muted']}; padding:48px; font-size:14px;")
            layout.addWidget(empty)
        else:
            title = QLabel("Your daily tips")
            title.setStyleSheet(f"font-size:22px; font-weight:700; color:{C['primary']};")
            layout.addWidget(title)

            known_ids = {h["id"] for h in HEALTH_CONDITIONS}
            for cond_id in conditions:
                if cond_id in known_ids:
                    meta = next(h for h in HEALTH_CONDITIONS if h["id"] == cond_id)
                    tips = CONDITION_TIPS.get(cond_id, [])
                    layout.addWidget(self._condition_card(meta["emoji"], meta["label"], tips))
                else:
                    layout.addWidget(self._custom_card(cond_id))

        layout.addStretch()
        scroll.setWidget(inner)
        outer.addWidget(scroll)

    def _condition_card(self, emoji, title, tips):
        card = Card()
        header = QLabel(f"{emoji}  {title}")
        header.setStyleSheet(f"font-size:16px; font-weight:700; color:{C['primary']};")
        card.layout_.addWidget(header)
        for i, tip in enumerate(tips, start=1):
            tip_lbl = QLabel(f"{i}.  {tip}")
            tip_lbl.setWordWrap(True)
            bg = C["bg"] if i % 2 else C["sage_pale"]
            tip_lbl.setStyleSheet(f"background:{bg}; border-radius:8px; padding:8px 10px; font-size:13px;")
            card.layout_.addWidget(tip_lbl)
        return card

    def _custom_card(self, name):
        card = Card()
        header = QLabel(f"💙  {name}")
        header.setStyleSheet(f"font-size:16px; font-weight:700; color:{C['primary']};")
        card.layout_.addWidget(header)
        msg = QLabel(
            f'We don\'t have preset tips for "{name}" yet, but your companion in the Chat tab '
            "can offer personalised guidance whenever you need it."
        )
        msg.setWordWrap(True)
        msg.setStyleSheet(f"color:{C['text_muted']}; font-style:italic; font-size:13px;")
        card.layout_.addWidget(msg)
        return card
