"""
Mind Fusion Desktop - entry point.

Run with:  python main.py   (from inside the desktop_app folder, with the
venv activated). See README.md for setup instructions.
"""

import sys

from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget

from data import apply_theme
from db import Database
from styles import APP_STYLESHEET, build_stylesheet
from ui.main_window import MainAppWidget
from ui.onboarding import OnboardingWidget


class AppWindow(QMainWindow):
    def __init__(self, db=None):
        super().__init__()
        self.setWindowTitle("Mind Fusion")
        self.resize(1240, 800)

        self.db = db or Database()

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.onboarding = OnboardingWidget(self.db)
        self.onboarding.login_completed.connect(self._on_login)
        self.stack.addWidget(self.onboarding)

        self.main_widget = None

        # If someone was already signed in last time the app was closed,
        # skip straight past onboarding.
        session_user_id = self.db.get_session_user_id()
        if session_user_id:
            user = self._get_user(session_user_id)
            profile = self.db.get_profile(session_user_id) if user else None
            if user and profile:
                self._show_main(user, profile)

    def _get_user(self, user_id):
        row = self.db.conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None

    def _on_login(self, user_id):
        user = self._get_user(user_id)
        profile = self.db.get_profile(user_id)
        self._show_main(user, profile)

    def _show_main(self, user, profile, start_index=0):
        if self.main_widget:
            self.main_widget.shutdown()
            self.stack.removeWidget(self.main_widget)
            self.main_widget.deleteLater()

        self.main_widget = MainAppWidget(self.db, user, profile, start_index=start_index)
        self.main_widget.signed_out.connect(self._on_sign_out)
        self.main_widget.theme_changed.connect(self._on_theme_changed)
        self.stack.addWidget(self.main_widget)
        self.stack.setCurrentWidget(self.main_widget)

    def _on_theme_changed(self, theme):
        """Save the choice, restyle the whole app, and rebuild the screens so
        every widget picks up the new palette (staying on the same page)."""
        self.db.set_setting("theme", theme)
        apply_theme(theme)
        QApplication.instance().setStyleSheet(build_stylesheet())

        old = self.main_widget
        user, profile, index = old.user, old.profile, old.tabs.currentIndex()
        self._show_main(user, profile, start_index=index)

        self.stack.removeWidget(self.onboarding)
        self.onboarding.deleteLater()
        self.onboarding = OnboardingWidget(self.db)
        self.onboarding.login_completed.connect(self._on_login)
        self.stack.addWidget(self.onboarding)
        self.stack.setCurrentWidget(self.main_widget)

    def _on_sign_out(self):
        self.onboarding.reset_to_welcome()
        self.stack.setCurrentWidget(self.onboarding)


def main():
    app = QApplication(sys.argv)
    db = Database()
    apply_theme(db.get_setting("theme", "light"))
    app.setStyleSheet(build_stylesheet())
    window = AppWindow(db)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
