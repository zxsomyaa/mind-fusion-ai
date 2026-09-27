"""The signed-in app shell: a left sidebar (navigation, connection status,
settings / theme / export / sign out) and a stack of pages on the right."""

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QButtonGroup, QFileDialog, QHBoxLayout, QLabel, QMessageBox, QPushButton, QStackedWidget,
    QVBoxLayout, QWidget,
)

import json
from datetime import date

from ai_client import check_connection
from data import COLORS as C
from ui.settings_dialog import AISettingsDialog
from ui.tabs.affirm_tab import AffirmTab
from ui.tabs.chat_tab import ChatTab
from ui.tabs.exercises_tab import ExercisesTab
from ui.tabs.health_tab import HealthTab
from ui.tabs.home_tab import HomeTab
from ui.tabs.insights_tab import InsightsTab
from ui.tabs.journal_tab import JournalTab
from ui.tabs.nutrition_tab import NutritionTab
from ui.tabs.support_tab import SupportTab
from workers import FnWorker

CONNECTION_CHECK_INTERVAL_MS = 30_000


class Pages(QStackedWidget):
    """A QStackedWidget that remembers a label per page, so it can stand in
    for the old QTabWidget (addTab / tabText / currentChanged all still work)
    while the actual navigation is drawn by the sidebar."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._labels = []

    def addTab(self, widget, label):
        self._labels.append(label)
        return self.addWidget(widget)

    def tabText(self, index):
        return self._labels[index]


class MainAppWidget(QWidget):
    signed_out = Signal()
    theme_changed = Signal(str)  # "light" or "dark"

    def __init__(self, db, user, profile, parent=None, start_index=0):
        super().__init__(parent)
        self.db = db
        self.user = user
        self.profile = profile
        self.connected = None
        self._connection_worker = None
        self._closing = False
        self.theme = db.get_setting("theme", "light")

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.tabs = Pages()
        self.home_tab = HomeTab(db, user["id"], user["name"], profile, self._go_to_tab)
        self.chat_tab = ChatTab(db, user["id"], {**profile, "name": user["name"]}, self.get_ai_config,
                                on_open_support=lambda: self.tabs.setCurrentWidget(self.support_tab))
        self.health_tab = HealthTab(profile)
        self.nutrition_tab = NutritionTab(db, user["id"], self.get_ai_config)
        self.journal_tab = JournalTab(db, user["id"], on_go_to_chat=self._go_to_chat_with_text)
        self.insights_tab = InsightsTab(db, user["id"], profile)
        self.exercises_tab = ExercisesTab(db, user["id"])
        self.affirm_tab = AffirmTab(db, user["id"])
        self.support_tab = SupportTab(profile)

        pages = [
            (self.home_tab, "🏠", "Today"), (self.chat_tab, "💬", "Chat"), (self.health_tab, "🌿", "Health"),
            (self.nutrition_tab, "🥗", "Nutrition"), (self.journal_tab, "📓", "Journal"),
            (self.insights_tab, "✨", "Insights"), (self.exercises_tab, "🧘", "Exercises"),
            (self.affirm_tab, "💕", "Affirm"), (self.support_tab, "🤝", "Support"),
        ]
        for widget, emoji, label in pages:
            self.tabs.addTab(widget, f"{emoji} {label}")

        root.addWidget(self._build_sidebar(pages))

        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(0)
        right.addWidget(self.tabs, stretch=1)
        footer = QLabel("Mind Fusion supports your wellbeing but does not replace professional medical or mental health care.")
        footer.setStyleSheet(f"color:{C['text_muted']}; font-size:10px; padding:8px; font-style:italic;")
        footer.setAlignment(Qt.AlignCenter)
        right.addWidget(footer)
        root.addLayout(right, stretch=1)

        self.tabs.currentChanged.connect(self._on_tab_changed)
        self.tabs.currentChanged.connect(self._sync_nav)
        self.tabs.setCurrentIndex(start_index)
        self._sync_nav(start_index)

        self._check_connection()
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._check_connection)
        self._poll_timer.start(CONNECTION_CHECK_INTERVAL_MS)

    def _build_sidebar(self, pages):
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(232)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 20, 16, 16)
        layout.setSpacing(4)

        logo = QLabel("🌿  Mind Fusion")
        logo.setStyleSheet(f"font-size:19px; font-weight:700; color:{C['primary']};")
        layout.addWidget(logo)
        tagline = QLabel("your wellbeing companion")
        tagline.setStyleSheet(f"color:{C['text_muted']}; font-size:11px; padding-bottom:14px;")
        layout.addWidget(tagline)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        self.nav_buttons = []
        for i, (_widget, emoji, label) in enumerate(pages):
            btn = QPushButton(f"{emoji}   {label}")
            btn.setObjectName("navBtn")
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _c, idx=i: self.tabs.setCurrentIndex(idx))
            self.nav_group.addButton(btn)
            self.nav_buttons.append(btn)
            layout.addWidget(btn)

        layout.addStretch()

        self.status_dot = QLabel("● Checking…")
        self.status_dot.setStyleSheet("color:#D4A017; font-size:12px;")
        layout.addWidget(self.status_dot)

        user_row = QHBoxLayout()
        avatar = QLabel((self.user["name"] or "?")[:1].upper())
        avatar.setFixedSize(34, 34)
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setStyleSheet(
            f"background:{C['primary_pale']}; color:{C['primary']}; border-radius:17px; font-weight:700;"
        )
        user_row.addWidget(avatar)
        name = QLabel(self.user["name"])
        name.setStyleSheet("font-weight:600;")
        user_row.addWidget(name, stretch=1)
        layout.addLayout(user_row)

        tools = QHBoxLayout()
        tools.setSpacing(8)
        for text, tip, handler in (
            ("⚙", "Local AI settings", self._open_settings),
            ("☀️" if self.theme == "dark" else "🌙", "Switch light / dark theme", self._toggle_theme),
            ("⬇", "Export all your data as JSON", self._export_data),
        ):
            btn = QPushButton(text)
            btn.setObjectName("iconBtn")
            btn.setToolTip(tip)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(handler)
            tools.addWidget(btn)
        tools.addStretch()
        layout.addLayout(tools)

        sign_out_btn = QPushButton("Sign out")
        sign_out_btn.setObjectName("ghost")
        sign_out_btn.clicked.connect(self._sign_out)
        layout.addWidget(sign_out_btn)
        return sidebar

    def _sync_nav(self, index):
        if 0 <= index < len(self.nav_buttons):
            self.nav_buttons[index].setChecked(True)

    def _toggle_theme(self):
        self.theme_changed.emit("light" if self.theme == "dark" else "dark")

    def get_ai_config(self):
        row = self.db.get_ai_config(self.user["id"])
        return {
            "provider": row["provider"], "base_url": row["base_url"],
            "chat_model": row["chat_model"], "vision_model": row["vision_model"],
        }

    def _check_connection(self):
        config = self.get_ai_config()
        self._connection_worker = FnWorker(lambda: check_connection(config))
        # bound methods (not lambdas): Qt drops these automatically if this
        # window is destroyed while a check is still in flight
        self._connection_worker.finished_ok.connect(self._on_connection_ok)
        self._connection_worker.failed.connect(self._on_connection_failed)
        self._connection_worker.start()

    def _on_connection_ok(self, _models):
        self._set_connected(True)

    def _on_connection_failed(self, _error):
        self._set_connected(False)

    def shutdown(self):
        """Called before this window is replaced (theme switch) or closed, so
        late results from background work don't touch deleted widgets."""
        self._closing = True
        self._poll_timer.stop()

    def _set_connected(self, connected):
        if self._closing:
            return
        self.connected = connected
        if connected:
            self.status_dot.setText("● Local AI connected")
            self.status_dot.setStyleSheet(f"color:{C['sage']}; font-size:12px;")
        else:
            self.status_dot.setText("● Local AI not connected")
            self.status_dot.setStyleSheet("color:#E07A5F; font-size:12px;")
        self.chat_tab.set_connected(connected)
        self.nutrition_tab.set_connected(connected)

    def _open_settings(self):
        current = self.get_ai_config()
        dialog = AISettingsDialog(current, self)
        if dialog.exec():
            cfg = dialog.result_config
            self.db.save_ai_config(self.user["id"], cfg["provider"], cfg["base_url"], cfg["chat_model"], cfg["vision_model"])
            self._check_connection()

    def _sign_out(self):
        self.db.sign_out()
        self.shutdown()
        self.signed_out.emit()

    def _go_to_chat_with_text(self, text):
        self.tabs.setCurrentWidget(self.chat_tab)
        self.chat_tab.input_box.setPlainText(text)

    def _go_to_tab(self, key):
        target = {
            "chat": self.chat_tab, "journal": self.journal_tab,
            "exercises": self.exercises_tab, "nutrition": self.nutrition_tab,
        }.get(key)
        if target is not None:
            self.tabs.setCurrentWidget(target)

    def _export_data(self):
        default_name = f"mind_fusion_export_{date.today().isoformat()}.json"
        path, _ = QFileDialog.getSaveFileName(self, "Export your data", default_name, "JSON (*.json)")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.db.export_all(self.user["id"]), f, indent=2, ensure_ascii=False)
        except OSError as exc:
            QMessageBox.warning(self, "Export failed", f"Couldn't write the file:\n{exc}")
            return
        QMessageBox.information(self, "Export complete", f"Your data was saved to:\n{path}")

    def _on_tab_changed(self, index):
        widget = self.tabs.widget(index)
        if widget is self.insights_tab:
            self.insights_tab.refresh()
        elif widget is self.home_tab:
            self.home_tab.refresh()
        elif widget is self.nutrition_tab:
            self.nutrition_tab.refresh()
        elif widget is self.exercises_tab:
            self.exercises_tab.refresh_recent()
