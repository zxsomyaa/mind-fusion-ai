"""Small reusable widgets shared across screens."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QFrame, QGraphicsDropShadowEffect, QPushButton, QVBoxLayout, QWidget

from data import COLORS as C


class Chip(QPushButton):
    """A pill-shaped toggle button, used for onboarding choices
    (country, conditions, habits, goals) and anywhere else we need a
    multi/single-select set of options."""

    def __init__(self, label, parent=None):
        super().__init__(label, parent)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self._apply_style()
        self.toggled.connect(self._apply_style)

    def _apply_style(self):
        if self.isChecked():
            self.setStyleSheet(f"""
                QPushButton {{
                    background: {C['primary_pale']};
                    color: {C['primary']};
                    border: 2px solid {C['primary']};
                    border-radius: 16px;
                    padding: 8px 16px;
                    font-weight: 600;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: {C['surface']};
                    color: {C['text']};
                    border: 2px solid {C['border']};
                    border-radius: 16px;
                    padding: 8px 16px;
                    font-weight: 400;
                }}
                QPushButton:hover {{ border-color: {C['primary_light']}; }}
                QPushButton:disabled {{
                    background: {C['bg']}; color: {C['text_muted']};
                    border: 2px dashed {C['border']};
                }}
            """)


class Card(QFrame):
    """A rounded, bordered content box - the workhorse container used on
    almost every tab (matches the .card look from the web version)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        # QLabel is itself a QFrame subclass in Qt, so a bare "QFrame { ... }"
        # rule here would cascade onto every plain QLabel placed inside this
        # card too, boxing each line of text. Scoping to #card by object name
        # keeps the border/background on this widget only.
        self.setObjectName("card")
        self.setStyleSheet(
            f"QFrame#card {{ background:{C['surface']}; border:1px solid {C['border']}; border-radius:16px; }}"
        )
        self.layout_ = QVBoxLayout(self)
        self.layout_.setContentsMargins(20, 18, 20, 18)
        self.layout_.setSpacing(10)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setXOffset(0)
        shadow.setYOffset(4)
        shadow.setColor(QColor(139, 94, 60, 40))  # soft warm shadow, matches the web app's card shadow
        self.setGraphicsEffect(shadow)


TONE_COLOURS = {"high": None, "mid": "#D4A017", "low": "#E07A5F"}   # 'high' uses the theme's sage


def tone_colour(tone):
    """Colour for a meal-balance tone ('high' / 'mid' / 'low')."""
    return TONE_COLOURS.get(tone) or C["sage"]


def rgba(colour, alpha):
    """A translucent version of a colour, as a stylesheet value. (Not '#RRGGBBAA':
    Qt reads 8-digit hex as #AARRGGBB, which silently scrambles the colour.)"""
    c = QColor(colour)
    return f"rgba({c.red()}, {c.green()}, {c.blue()}, {alpha})"


def score_badge(text, tone, size=46):
    """A round badge with a short text (e.g. a meal's balance score) in a tone colour."""
    from PySide6.QtWidgets import QLabel
    badge = QLabel(text)
    badge.setFixedSize(size, size)
    badge.setAlignment(Qt.AlignCenter)
    colour = tone_colour(tone)
    badge.setStyleSheet(
        f"background:{rgba(colour, 0.18)}; color:{colour}; border:2px solid {colour}; "
        f"border-radius:{size // 2}px; font-weight:800; font-size:{size // 3}px;"
    )
    return badge


def pill(text, background=None, colour=None):
    """A small rounded text tag."""
    from PySide6.QtWidgets import QLabel
    label = QLabel(text)
    label.setStyleSheet(
        f"background:{background or C['primary_pale']}; color:{colour or C['primary']}; "
        f"border-radius:12px; padding:4px 12px; font-size:12px; font-weight:600;"
    )
    return label


class StatCard(Card):
    """A headline number: small label on top, big value, and an optional
    change line underneath ('▲ +3' green, '▼ -2' red, grey when unchanged)."""

    def __init__(self, label, value, delta=None, sign=None, parent=None):
        from PySide6.QtWidgets import QLabel
        super().__init__(parent)
        self.layout_.setContentsMargins(18, 14, 18, 14)
        self.layout_.setSpacing(2)
        caption = QLabel(label)
        caption.setStyleSheet(f"color:{C['text_muted']}; font-size:12px; font-weight:600;")
        self.value_label = QLabel(value)
        self.value_label.setStyleSheet(f"color:{C['text']}; font-size:26px; font-weight:800;")
        self.layout_.addWidget(caption)
        self.layout_.addWidget(self.value_label)
        self.delta_label = QLabel("")
        if delta:
            arrow = {1: "▲ ", -1: "▼ "}.get(sign, "")
            colour = {1: C["sage"], -1: "#E07A5F"}.get(sign, C["text_muted"])
            self.delta_label.setText(f"{arrow}{delta} vs previous")
            self.delta_label.setStyleSheet(f"color:{colour}; font-size:11px; font-weight:600;")
        else:
            self.delta_label.setText(" ")     # keeps every card the same height
            self.delta_label.setStyleSheet("font-size:11px;")
        self.layout_.addWidget(self.delta_label)


class _ClickableFrame(QFrame):
    """A frame that reports clicks (and Enter / Space when focused)."""

    clicked = Signal()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
            self.clicked.emit()
        else:
            super().keyPressEvent(event)


class CollapsibleSection(QWidget):
    """A dropdown: a header row ('▸ Title' plus a one-line summary while closed)
    that shows or hides its content when clicked. Add content with add_widget()."""

    toggled = Signal(bool)   # True when opened

    def __init__(self, title, summary="", open_=False, parent=None):
        from PySide6.QtWidgets import QHBoxLayout, QLabel
        super().__init__(parent)
        self.setObjectName("flowHost")      # transparent, so it sits cleanly inside a card
        self._open = open_
        self._summary_text = summary

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(8)

        self.header = _ClickableFrame()
        self.header.setObjectName("sectionHeader")
        self.header.setCursor(Qt.PointingHandCursor)
        self.header.setFocusPolicy(Qt.StrongFocus)
        self.header.clicked.connect(self.toggle)
        row = QHBoxLayout(self.header)
        row.setContentsMargins(14, 10, 14, 10)
        self.arrow = QLabel()
        self.arrow.setFixedWidth(14)
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("font-size:13px; font-weight:700;")
        self.summary_label = QLabel(summary)
        self.summary_label.setStyleSheet(f"color:{C['text_muted']}; font-size:12px;")
        for label in (self.arrow, self.title_label, self.summary_label):
            label.setAttribute(Qt.WA_TransparentForMouseEvents)   # clicks fall through to the header
        row.addWidget(self.arrow)
        row.addWidget(self.title_label)
        row.addStretch()
        row.addWidget(self.summary_label)
        outer.addWidget(self.header)

        self.body = QWidget()
        self.body.setObjectName("flowHost")
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(4, 0, 4, 4)
        self.body_layout.setSpacing(8)
        outer.addWidget(self.body)
        self._apply()

    def add_widget(self, widget):
        self.body_layout.addWidget(widget)

    def is_open(self):
        return self._open

    def set_open(self, open_):
        if open_ != self._open:
            self._open = open_
            self._apply()
            self.toggled.emit(open_)

    def toggle(self):
        self.set_open(not self._open)

    def _apply(self):
        self.arrow.setText("▾" if self._open else "▸")
        self.arrow.setStyleSheet(f"color:{C['primary']}; font-size:13px; font-weight:700;")
        self.body.setVisible(self._open)
        self.summary_label.setVisible(not self._open and bool(self._summary_text))   # summary only while closed
