"""Support tab - crisis / mental health / physical health resources for the
user's country, with a global fallback list."""

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget

from data import COLORS as C, COUNTRIES, SUPPORT_RESOURCES
from ui.widgets import Card

SECTION_META = {
    "crisis":   ("🆘", "Crisis support"),
    "mental":   ("🧠", "Mental health"),
    "physical": ("🏥", "Physical health"),
}


class SupportTab(QWidget):
    def __init__(self, profile, parent=None):
        super().__init__(parent)
        country_code = profile.get("country") or "DEFAULT"
        resources = SUPPORT_RESOURCES.get(country_code, SUPPORT_RESOURCES["DEFAULT"])
        country_meta = next((c for c in COUNTRIES if c["code"] == country_code), None)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        title = QLabel("Support resources")
        title.setStyleSheet(f"font-size:22px; font-weight:700; color:{C['primary']};")
        layout.addWidget(title)

        sub_text = (
            f"Resources for {country_meta['flag']} {country_meta['name']}."
            if country_meta else "Global resources for wherever you are."
        )
        sub = QLabel(sub_text + " Reach out - help is closer than it may feel.")
        sub.setWordWrap(True)
        sub.setStyleSheet(f"color:{C['text_muted']};")
        layout.addWidget(sub)

        emergency = QLabel(
            "In immediate danger? Please call your local emergency services (999, 911, 112, or your "
            "country's number). These resources are for additional support, not emergencies."
        )
        emergency.setWordWrap(True)
        emergency.setStyleSheet(
            "background:#FEF3E6; border:1px solid #F4C97A; color:#9B6000; border-radius:10px; padding:10px 14px;"
        )
        layout.addWidget(emergency)

        for section in ("crisis", "mental", "physical"):
            items = resources.get(section, [])
            if not items:
                continue
            emoji, label = SECTION_META[section]
            section_title = QLabel(f"{emoji}  {label}")
            section_title.setStyleSheet(f"font-size:15px; font-weight:700; color:{C['text']};")
            layout.addWidget(section_title)
            for item in items:
                layout.addWidget(self._resource_card(item))

        layout.addStretch()
        scroll.setWidget(inner)
        outer.addWidget(scroll)

    def _resource_card(self, item):
        card = Card()
        name = QLabel(item["name"])
        name.setStyleSheet("font-weight:600;")
        card.layout_.addWidget(name)
        if item.get("contact"):
            contact = QLabel(item["contact"])
            contact.setStyleSheet(f"color:{C['primary']}; font-weight:700; font-size:15px;")
            card.layout_.addWidget(contact)
        if item.get("note"):
            note = QLabel(item["note"])
            note.setStyleSheet(f"color:{C['text_muted']}; font-size:11px;")
            card.layout_.addWidget(note)
        if item.get("url"):
            link_btn = QPushButton(f"Open {item['url']} ↗")
            link_btn.setObjectName("linkButton")
            link_btn.clicked.connect(lambda _c, url=item["url"]: QDesktopServices.openUrl(QUrl(url)))
            card.layout_.addWidget(link_btn)
        return card
