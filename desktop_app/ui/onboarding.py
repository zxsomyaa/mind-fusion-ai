"""
Welcome -> sign up / sign in -> 5-step profile wizard.

Because profiles are stored per-account in SQLite (see db.py), a returning
user who signs in with an email that already has a saved profile skips the
wizard completely - the onboarding questions are only ever asked once per
account, not once per session.

Layout: a branded panel on the left (hidden when the window is narrow) and
the form / wizard on the right.
"""

import re

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QGraphicsOpacityEffect, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QScrollArea, QSizePolicy, QStackedWidget, QVBoxLayout, QWidget,
)

from data import (
    AGE_GROUPS, COLORS as C, COUNTRIES, GOALS, HABITS, HEALTH_CONDITIONS, LANGUAGES,
)
from ui.flow_layout import FlowLayout
from ui.widgets import Chip

MAX_GOALS = 3
EMAIL_PATTERN = re.compile(r"^\S+@\S+\.\S+$")

# emoji, heading, sub-heading, short label shown under the step dot
STEPS = [
    ("🌍", "Where are you based?", "We use this to show the right support resources for your country.", "Location"),
    ("🎂", "How old are you?", "Different stages of life come with different needs.", "Age"),
    ("🩺", "Any health conditions?", "Select any that apply, or add your own. Skip if none.", "Health"),
    ("🌱", "Which habits do you already have?", "We'll turn these into a daily checklist for you.", "Habits"),
    ("🎯", "What would you like to work on?", f"Pick up to {MAX_GOALS} - we'll build around them.", "Goals"),
]
TOTAL_STEPS = len(STEPS)

AGE_CAPTIONS = {
    "18-24": "Early adulthood", "25-34": "Building your path", "35-44": "The busy years",
    "45-54": "Midlife", "55-64": "Looking ahead", "65+": "Golden years",
}


def _title(text, size=26):
    lbl = QLabel(text)
    lbl.setStyleSheet(f"font-size:{size}px; font-weight:700; color:{C['primary']};")
    return lbl


def _muted(text, size=13):
    lbl = QLabel(text)
    lbl.setWordWrap(True)
    lbl.setStyleSheet(f"color:{C['text_muted']}; font-size:{size}px;")
    return lbl


class StepIndicator(QWidget):
    """Numbered dots joined by a line: finished steps are filled with a tick,
    the current step is ringed, upcoming steps are grey."""

    def __init__(self, labels, parent=None):
        super().__init__(parent)
        self.labels = labels
        self.current = 0
        self.setFixedHeight(64)

    def set_current(self, index):
        self.current = index
        self.update()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        n = len(self.labels)
        margin, radius, cy = 34, 13, 18
        span = (self.width() - 2 * margin) / (n - 1)
        xs = [margin + i * span for i in range(n)]

        for i in range(n - 1):
            painter.setPen(QPen(QColor(C["primary"] if i < self.current else C["border"]), 3))
            painter.drawLine(int(xs[i] + radius + 2), cy, int(xs[i + 1] - radius - 2), cy)

        number_font = QFont(self.font()); number_font.setPointSize(11); number_font.setBold(True)
        label_font = QFont(self.font()); label_font.setPointSize(10)
        for i, x in enumerate(xs):
            done, current = i < self.current, i == self.current
            painter.setPen(QPen(QColor(C["primary"] if (done or current) else C["border"]), 2.5))
            painter.setBrush(QColor(C["primary"] if done else C["surface"]))
            painter.drawEllipse(int(x - radius), cy - radius, radius * 2, radius * 2)

            painter.setFont(number_font)
            painter.setPen(QColor(C["on_primary"] if done else (C["primary"] if current else C["text_muted"])))
            painter.drawText(int(x - radius), cy - radius, radius * 2, radius * 2, Qt.AlignCenter,
                             "✓" if done else str(i + 1))

            label_font.setBold(current)
            painter.setFont(label_font)
            painter.setPen(QColor(C["primary"] if current else C["text_muted"]))
            painter.drawText(int(x - 40), cy + radius + 6, 80, 18, Qt.AlignCenter, self.labels[i])


class OnboardingWidget(QWidget):
    login_completed = Signal(int)  # emits user_id once the profile is confirmed ready

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.pending_user_id = None
        self.step_index = 0

        # answers collected across the 5 profile-wizard steps
        self.profile = self._blank_profile()

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.hero = self._build_hero()
        # Ignored: the panel's own content must not set the window's minimum width,
        # otherwise the window can't be made narrow enough for the panel to hide
        self.hero.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Expanding)
        root.addWidget(self.hero, stretch=5)

        right = QVBoxLayout()
        right.setContentsMargins(40, 32, 40, 32)
        self.stack = QStackedWidget()
        right.addWidget(self.stack, alignment=Qt.AlignHCenter)
        root.addLayout(right, stretch=6)

        self.welcome_page = self._build_welcome()
        self.signup_page = self._build_signup()
        self.signin_page = self._build_signin()
        self.wizard_page = self._build_wizard()
        for page in (self.welcome_page, self.signup_page, self.signin_page, self.wizard_page):
            self.stack.addWidget(page)
        self.stack.setCurrentWidget(self.welcome_page)

    @staticmethod
    def _blank_profile():
        return {"country": None, "language": "en", "age_group": None,
                "conditions": [], "habits": [], "goals": []}

    def resizeEvent(self, event):
        super().resizeEvent(event)
        wide = self.width() >= 900
        self.hero.setVisible(wide)                  # on a narrow window the form gets all the room
        # one fixed form width on every page (otherwise each page picks its own and the
        # column jumps around between steps): as wide as allowed, up to 500px
        available = int(self.width() * 6 / 11) - 80 if wide else self.width() - 80
        self.stack.setFixedWidth(max(320, min(500, available)))

    def _show_page(self, page):
        self.stack.setCurrentWidget(page)
        self._fade_in(page)

    def _fade_in(self, widget):
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(240)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)

        def cleanup():
            try:
                widget.setGraphicsEffect(None)    # the effect is only needed while fading
            except RuntimeError:
                pass                              # the page was replaced before the fade finished
            anim.deleteLater()

        anim.finished.connect(cleanup)
        anim.start()

    # -- Brand panel -------------------------------------------------------

    def _build_hero(self):
        hero = QWidget()
        hero.setObjectName("hero")
        hero.setStyleSheet(
            "QWidget#hero { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, "
            f"stop:0 {C['primary']}, stop:1 {C['primary_light']}); }}"
        )
        layout = QVBoxLayout(hero)
        layout.setContentsMargins(56, 48, 56, 40)
        layout.setSpacing(0)
        ink = f"color:{C['on_primary']};"

        brand = QLabel("🌿  Mind Fusion")
        brand.setStyleSheet(f"{ink} font-size:20px; font-weight:700;")
        layout.addWidget(brand)
        layout.addStretch(2)

        headline = QLabel("Feel understood.\nFeel lighter.")
        headline.setStyleSheet(f"{ink} font-size:40px; font-weight:800;")
        layout.addWidget(headline)
        layout.addSpacing(14)
        sub = QLabel("A private, gentle companion for your mind and body - powered by AI that runs "
                     "entirely on your own computer.")
        sub.setWordWrap(True)
        sub.setStyleSheet(f"{ink} font-size:15px;")
        layout.addWidget(sub)
        layout.addSpacing(30)

        for emoji, text in (("💬", "Talk things through, any time of day"),
                            ("📓", "Journal, and track your mood, habits and sleep"),
                            ("🔒", "Everything stays on your device")):
            row = QHBoxLayout()
            row.setSpacing(14)
            badge = QLabel(emoji)
            badge.setFixedSize(38, 38)
            badge.setAlignment(Qt.AlignCenter)
            badge.setStyleSheet("background: rgba(255,255,255,0.22); border-radius:19px; font-size:17px;")
            row.addWidget(badge)
            label = QLabel(text)
            label.setStyleSheet(f"{ink} font-size:14px; font-weight:600;")
            row.addWidget(label, stretch=1)
            layout.addLayout(row)
            layout.addSpacing(10)

        layout.addStretch(3)
        note = QLabel("Supports your wellbeing · does not replace professional care")
        note.setStyleSheet(f"{ink} font-size:11px;")
        layout.addWidget(note)
        return hero

    # -- Welcome ---------------------------------------------------------------

    def _build_welcome(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.addStretch()

        badge = QLabel("🌿")
        badge.setFixedSize(68, 68)
        badge.setAlignment(Qt.AlignCenter)
        badge.setStyleSheet(f"background:{C['primary_pale']}; border-radius:34px; font-size:32px;")
        layout.addWidget(badge)
        layout.addSpacing(8)

        layout.addWidget(_title("Welcome to Mind Fusion", 30))
        layout.addWidget(_muted("Let's set things up in about a minute, so everything you see is "
                                "made for you.", 15))
        layout.addSpacing(18)

        get_started = QPushButton("Get started  →")
        get_started.setObjectName("bigBtn")
        get_started.setCursor(Qt.PointingHandCursor)
        get_started.clicked.connect(lambda: self._show_page(self.signup_page))
        layout.addWidget(get_started)

        have_account = QPushButton("I already have an account")
        have_account.setObjectName("bigBtnGhost")
        have_account.setCursor(Qt.PointingHandCursor)
        have_account.clicked.connect(lambda: self._show_page(self.signin_page))
        layout.addWidget(have_account)
        layout.addSpacing(18)

        chips = QWidget()
        chips.setObjectName("flowHost")
        flow = FlowLayout(chips, h_spacing=8, v_spacing=8)
        for text in ("🔒 Stays on your device", "🤖 Local AI", "🌙 Light & dark"):
            pill = QLabel(text)
            pill.setStyleSheet(
                f"background:{C['surface']}; border:1px solid {C['border']}; border-radius:12px; "
                f"padding:4px 12px; color:{C['text_muted']}; font-size:12px;"
            )
            flow.addWidget(pill)
        layout.addWidget(chips)
        layout.addStretch()
        return page

    # -- Form helpers -----------------------------------------------------------

    def _field(self, label, placeholder, password=False):
        """Label + input + (initially hidden) error line. Returns (widget, edit, error_label)."""
        box = QWidget()
        col = QVBoxLayout(box)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(5)
        lbl = QLabel(label)
        lbl.setStyleSheet("font-size:12px; font-weight:600;")
        col.addWidget(lbl)

        row = QHBoxLayout()
        row.setSpacing(8)
        edit = QLineEdit()
        edit.setPlaceholderText(placeholder)
        edit.setMinimumHeight(46)
        row.addWidget(edit, stretch=1)
        if password:
            edit.setEchoMode(QLineEdit.Password)
            toggle = QPushButton("Show")
            toggle.setObjectName("linkButton")
            toggle.setCursor(Qt.PointingHandCursor)
            toggle.setFixedWidth(46)

            def flip():
                hidden = edit.echoMode() == QLineEdit.Password
                edit.setEchoMode(QLineEdit.Normal if hidden else QLineEdit.Password)
                toggle.setText("Hide" if hidden else "Show")
            toggle.clicked.connect(flip)
            row.addWidget(toggle)
        col.addLayout(row)

        err = QLabel("")
        err.setStyleSheet("color:#E07A5F; font-size:11px;")
        err.setVisible(False)
        col.addWidget(err)
        return box, edit, err

    @staticmethod
    def _set_error(edit, err, message):
        edit.setProperty("error", bool(message))
        edit.style().unpolish(edit)
        edit.style().polish(edit)
        err.setText(message)
        err.setVisible(bool(message))

    def _switch_row(self, prompt, link_text, target_name):
        row = QHBoxLayout()
        row.addStretch()
        prompt_label = QLabel(prompt)
        prompt_label.setStyleSheet(f"color:{C['text_muted']}; font-size:13px;")
        row.addWidget(prompt_label)
        link = QPushButton(link_text)
        link.setObjectName("linkButton")
        link.setCursor(Qt.PointingHandCursor)
        link.clicked.connect(lambda: self._show_page(getattr(self, f"{target_name}_page")))
        row.addWidget(link)
        row.addStretch()
        return row

    # -- Sign up -------------------------------------------------------------------

    def _build_signup(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        layout.addStretch()
        layout.addWidget(self._back_placeholder("welcome"))
        layout.addWidget(_title("Create your account"))
        layout.addWidget(_muted("Just the basics - we'll personalise everything from here."))
        layout.addSpacing(6)

        box, self.su_name, self.su_name_err = self._field("Your name", "e.g. Priya")
        layout.addWidget(box)
        box, self.su_email, self.su_email_err = self._field("Email", "you@example.com")
        layout.addWidget(box)
        box, self.su_password, self.su_password_err = self._field("Password", "At least 6 characters", password=True)
        layout.addWidget(box)

        self.su_error = QLabel("")
        self.su_error.setWordWrap(True)
        self.su_error.setStyleSheet("color:#E07A5F; font-size:12px;")
        self.su_error.setVisible(False)
        layout.addWidget(self.su_error)

        create_btn = QPushButton("Create account  →")
        create_btn.setObjectName("bigBtn")
        create_btn.setCursor(Qt.PointingHandCursor)
        create_btn.clicked.connect(self._handle_signup)
        layout.addWidget(create_btn)
        for edit in (self.su_name, self.su_email, self.su_password):
            edit.returnPressed.connect(self._handle_signup)

        layout.addLayout(self._switch_row("Already have an account?", "Sign in", "signin"))
        layout.addStretch()
        return page

    def _back_placeholder(self, target_name):
        """Back link. The destination page is looked up by name when clicked,
        because the pages are built one after another and the target may not
        exist yet when the link is created."""
        back = QPushButton("←  Back")
        back.setObjectName("linkButton")
        back.setCursor(Qt.PointingHandCursor)
        back.setStyleSheet(f"color:{C['text_muted']}; background:none; border:none; text-align:left; padding:0;")
        back.clicked.connect(lambda: self._show_page(getattr(self, f"{target_name}_page")))
        return back

    def _handle_signup(self):
        name = self.su_name.text().strip()
        email = self.su_email.text().strip()
        password = self.su_password.text()

        self._set_error(self.su_name, self.su_name_err, "" if name else "Please tell us your name.")
        self._set_error(self.su_email, self.su_email_err,
                        "" if EMAIL_PATTERN.match(email) else "Enter a valid email address.")
        self._set_error(self.su_password, self.su_password_err,
                        "" if len(password) >= 6 else "Use at least 6 characters.")
        self.su_error.setVisible(False)
        if not name or not EMAIL_PATTERN.match(email) or len(password) < 6:
            return

        if self.db.get_user_by_email(email):
            self.su_error.setText("An account with that email already exists - try signing in instead.")
            self.su_error.setVisible(True)
            return

        user_id = self.db.create_user(name, email)
        self._enter_wizard(user_id)

    # -- Sign in -------------------------------------------------------------------

    def _build_signin(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        layout.addStretch()
        layout.addWidget(self._back_placeholder("welcome"))
        layout.addWidget(_title("Welcome back"))
        layout.addWidget(_muted("Sign in to pick up where you left off."))
        layout.addSpacing(6)

        box, self.si_email, self.si_email_err = self._field("Email", "you@example.com")
        layout.addWidget(box)
        box, self.si_password, self.si_password_err = self._field("Password", "Your password", password=True)
        layout.addWidget(box)

        self.si_error = QLabel("")
        self.si_error.setWordWrap(True)
        self.si_error.setStyleSheet("color:#E07A5F; font-size:12px;")
        self.si_error.setVisible(False)
        layout.addWidget(self.si_error)

        self.si_create_link = QPushButton("Create an account with this email")
        self.si_create_link.setObjectName("linkButton")
        self.si_create_link.setCursor(Qt.PointingHandCursor)
        self.si_create_link.setVisible(False)
        self.si_create_link.clicked.connect(self._create_from_signin)
        layout.addWidget(self.si_create_link, alignment=Qt.AlignLeft)

        signin_btn = QPushButton("Sign in  →")
        signin_btn.setObjectName("bigBtn")
        signin_btn.setCursor(Qt.PointingHandCursor)
        signin_btn.clicked.connect(self._handle_signin)
        layout.addWidget(signin_btn)
        for edit in (self.si_email, self.si_password):
            edit.returnPressed.connect(self._handle_signin)

        layout.addLayout(self._switch_row("New here?", "Create an account", "signup"))
        layout.addStretch()
        return page

    def _handle_signin(self):
        email = self.si_email.text().strip()
        password = self.si_password.text()

        self._set_error(self.si_email, self.si_email_err,
                        "" if EMAIL_PATTERN.match(email) else "Enter the email you signed up with.")
        self._set_error(self.si_password, self.si_password_err, "" if password else "Please enter your password.")
        self.si_error.setVisible(False)
        self.si_create_link.setVisible(False)
        if not EMAIL_PATTERN.match(email) or not password:
            return

        existing = self.db.get_user_by_email(email)
        if not existing:
            self.si_error.setText("We couldn't find an account with that email. "
                                  "Check the spelling, or create a new account.")
            self.si_error.setVisible(True)
            self.si_create_link.setVisible(True)
            return

        # returning user - jump straight past the wizard if their profile is saved
        if self.db.get_profile(existing["id"]):
            self.db.set_session_user_id(existing["id"])
            self.login_completed.emit(existing["id"])
        else:
            self._enter_wizard(existing["id"])   # signed up earlier but never finished the questions

    def _create_from_signin(self):
        self.su_email.setText(self.si_email.text().strip())
        self._show_page(self.signup_page)
        self.su_name.setFocus()

    # -- Profile wizard ---------------------------------------------------------------

    def _enter_wizard(self, user_id):
        self.pending_user_id = user_id
        self.step_index = 0
        self.profile = self._blank_profile()
        self._render_step()
        self._show_page(self.wizard_page)

    def _build_wizard(self):
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(10)

        self.indicator = StepIndicator([s[3] for s in STEPS])
        outer.addWidget(self.indicator)

        head = QHBoxLayout()
        self.step_emoji = QLabel("")
        self.step_emoji.setStyleSheet("font-size:30px;")
        head.addWidget(self.step_emoji, alignment=Qt.AlignTop)
        titles = QVBoxLayout()
        titles.setSpacing(2)
        self.step_title = _title("", 22)
        self.step_sub = _muted("")
        titles.addWidget(self.step_title)
        titles.addWidget(self.step_sub)
        head.addLayout(titles, stretch=1)
        outer.addLayout(head)

        self.step_scroll = QScrollArea()
        self.step_scroll.setWidgetResizable(True)
        self.step_scroll.setMinimumHeight(280)
        outer.addWidget(self.step_scroll, stretch=1)

        self.step_hint = QLabel("")
        self.step_hint.setStyleSheet(f"color:{C['text_muted']}; font-size:12px;")
        self.step_hint.setAlignment(Qt.AlignCenter)
        outer.addWidget(self.step_hint)

        nav = QHBoxLayout()
        self.back_btn = QPushButton("←  Back")
        self.back_btn.setObjectName("bigBtnGhost")
        self.back_btn.setCursor(Qt.PointingHandCursor)
        self.back_btn.clicked.connect(self._wizard_back)
        self.next_btn = QPushButton("Continue  →")
        self.next_btn.setObjectName("bigBtn")
        self.next_btn.setCursor(Qt.PointingHandCursor)
        self.next_btn.clicked.connect(self._wizard_next)
        nav.addWidget(self.back_btn)
        nav.addWidget(self.next_btn, stretch=1)
        outer.addLayout(nav)
        return page

    def _render_step(self):
        emoji, title, sub, _label = STEPS[self.step_index]
        self.indicator.set_current(self.step_index)
        self.step_emoji.setText(emoji)
        self.step_title.setText(title)
        self.step_sub.setText(sub)
        self.next_btn.setText("Begin my journey  →" if self.step_index == TOTAL_STEPS - 1 else "Continue  →")

        builders = [self._step_location, self._step_age, self._step_conditions,
                    self._step_habits, self._step_goals]
        content = builders[self.step_index]()
        self.step_scroll.setWidget(content)
        self._fade_in(content)
        self._update_nav()

    def _can_proceed(self):
        if self.step_index == 0:
            return bool(self.profile["country"])
        if self.step_index == 1:
            return bool(self.profile["age_group"])
        return True

    def _update_nav(self):
        ok = self._can_proceed()
        self.next_btn.setEnabled(ok)
        hints = {0: "Pick your country to continue", 1: "Choose an age group to continue"}
        self.step_hint.setText("" if ok else hints.get(self.step_index, ""))

    # -- step contents -------------------------------------------------------------------

    @staticmethod
    def _chip_host():
        host = QWidget()
        host.setObjectName("flowHost")
        return host, FlowLayout(host, h_spacing=8, v_spacing=8)

    def _counter(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color:{C['primary']}; font-size:12px; font-weight:600;")
        return lbl

    def _step_location(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 4, 8, 4)
        layout.setSpacing(12)

        self.country_search = QLineEdit()
        self.country_search.setPlaceholderText("🔍  Search countries…")
        self.country_search.setMinimumHeight(44)
        self.country_search.textChanged.connect(self._render_country_chips)
        layout.addWidget(self.country_search)

        self._country_host, self._country_flow = self._chip_host()
        layout.addWidget(self._country_host)
        self._render_country_chips()

        layout.addWidget(_muted("Preferred language"))
        host, flow = self._chip_host()
        self._language_chips = []
        for lang in LANGUAGES:
            chip = Chip(lang["name"])
            chip.setChecked(lang["code"] == self.profile["language"])
            chip.clicked.connect(lambda _c, code=lang["code"], me=chip: self._pick_language(code, me))
            self._language_chips.append(chip)
            flow.addWidget(chip)
        layout.addWidget(host)
        layout.addStretch()
        return page

    def _render_country_chips(self):
        """Rebuilds the country chips to match the search box (rebuilding is
        simpler and safer than hiding chips inside a flow layout)."""
        query = self.country_search.text().strip().lower() if hasattr(self, "country_search") else ""
        flow = self._country_flow
        while flow.count():
            item = flow.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        matches = [c for c in COUNTRIES if query in c["name"].lower()]
        for country in matches:
            chip = Chip(f"{country['flag']}  {country['name']}")
            chip.setChecked(country["code"] == self.profile["country"])
            chip.clicked.connect(lambda _c, code=country["code"], me=chip: self._pick_country(code, me))
            flow.addWidget(chip)
        if not matches:
            flow.addWidget(_muted("No country matches that search."))

    def _pick_country(self, code, clicked_chip):
        self.profile["country"] = code
        for i in range(self._country_flow.count()):
            chip = self._country_flow.itemAt(i).widget()
            if isinstance(chip, Chip):
                chip.setChecked(chip is clicked_chip)
        clicked_chip.setChecked(True)
        self._update_nav()

    def _pick_language(self, code, clicked_chip):
        self.profile["language"] = code
        for chip in self._language_chips:
            chip.setChecked(chip is clicked_chip)
        clicked_chip.setChecked(True)

    def _step_age(self):
        page = QWidget()
        grid = QGridLayout(page)
        grid.setContentsMargins(0, 4, 8, 4)
        grid.setSpacing(12)
        self._age_buttons = {}
        for i, ag in enumerate(AGE_GROUPS):
            btn = QPushButton(f"{ag['label']}\n{AGE_CAPTIONS.get(ag['id'], '')}")
            btn.setObjectName("choiceCard")
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setChecked(ag["id"] == self.profile["age_group"])
            btn.clicked.connect(lambda _c, id_=ag["id"]: self._pick_age(id_))
            self._age_buttons[ag["id"]] = btn
            grid.addWidget(btn, i // 2, i % 2)
        grid.setRowStretch(len(AGE_GROUPS) // 2 + 1, 1)
        return page

    def _pick_age(self, age_id):
        self.profile["age_group"] = age_id
        for key, btn in self._age_buttons.items():
            btn.setChecked(key == age_id)
        self._update_nav()

    def _step_conditions(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 4, 8, 4)
        layout.setSpacing(12)

        host, self._conditions_flow = self._chip_host()
        known = {h["id"] for h in HEALTH_CONDITIONS}
        for hc in HEALTH_CONDITIONS:
            chip = Chip(f"{hc['emoji']}  {hc['label']}")
            chip.setChecked(hc["id"] in self.profile["conditions"])
            chip.clicked.connect(lambda _c, id_=hc["id"]: self._toggle("conditions", id_))
            self._conditions_flow.addWidget(chip)
        for custom in [c for c in self.profile["conditions"] if c not in known]:
            self._add_custom_chip(custom)
        layout.addWidget(host)

        row = QHBoxLayout()
        self.custom_condition_input = QLineEdit()
        self.custom_condition_input.setPlaceholderText("Add a condition that isn't listed…")
        self.custom_condition_input.setMinimumHeight(44)
        self.custom_condition_input.returnPressed.connect(self._add_custom_condition)
        add_btn = QPushButton("Add")
        add_btn.setObjectName("ghost")
        add_btn.clicked.connect(self._add_custom_condition)
        row.addWidget(self.custom_condition_input, stretch=1)
        row.addWidget(add_btn)
        layout.addLayout(row)
        layout.addWidget(_muted("No conditions? That's perfectly fine - just continue."))
        layout.addStretch()
        return page

    def _add_custom_chip(self, text):
        chip = Chip(text)
        chip.setChecked(True)
        chip.clicked.connect(lambda _c, t=text, me=chip: self._remove_custom(t, me))
        self._conditions_flow.addWidget(chip)

    def _add_custom_condition(self):
        text = self.custom_condition_input.text().strip()
        if not text or text in self.profile["conditions"]:
            return
        self.profile["conditions"].append(text)
        self._add_custom_chip(text)
        self.custom_condition_input.clear()

    def _remove_custom(self, text, chip):
        if text in self.profile["conditions"]:
            self.profile["conditions"].remove(text)
        self._conditions_flow.removeWidget(chip)
        chip.deleteLater()

    def _step_habits(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 4, 8, 4)
        layout.setSpacing(12)
        host, flow = self._chip_host()
        for h in HABITS:
            chip = Chip(f"{h['emoji']}  {h['label']}")
            chip.setChecked(h["id"] in self.profile["habits"])
            chip.clicked.connect(lambda _c, id_=h["id"]: self._toggle("habits", id_))
            flow.addWidget(chip)
        layout.addWidget(host)
        layout.addWidget(_muted("Each one becomes a daily checkbox on your Today page, with its own streak."))
        layout.addStretch()
        return page

    def _step_goals(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 4, 8, 4)
        layout.setSpacing(12)
        host, flow = self._chip_host()
        self._goal_chips = {}
        for g in GOALS:
            chip = Chip(f"{g['emoji']}  {g['label']}")
            chip.setChecked(g["id"] in self.profile["goals"])
            chip.clicked.connect(lambda _c, id_=g["id"]: self._toggle_goal(id_))
            self._goal_chips[g["id"]] = chip
            flow.addWidget(chip)
        layout.addWidget(host)
        self.goal_counter = self._counter("")
        layout.addWidget(self.goal_counter)
        layout.addStretch()
        self._refresh_goal_chips()
        return page

    def _toggle(self, key, value):
        items = self.profile[key]
        if value in items:
            items.remove(value)
        else:
            items.append(value)

    def _toggle_goal(self, goal_id):
        goals = self.profile["goals"]
        if goal_id in goals:
            goals.remove(goal_id)
        elif len(goals) < MAX_GOALS:
            goals.append(goal_id)
        self._refresh_goal_chips()

    def _refresh_goal_chips(self):
        """Ticks match the chosen goals; once three are chosen the rest are
        greyed out until one is un-ticked."""
        goals = self.profile["goals"]
        for gid, chip in self._goal_chips.items():
            chip.setChecked(gid in goals)
            chip.setEnabled(gid in goals or len(goals) < MAX_GOALS)
        self.goal_counter.setText(
            f"{len(goals)} of {MAX_GOALS} chosen" + (" - untick one to change" if len(goals) == MAX_GOALS else "")
        )

    # -- wizard navigation ------------------------------------------------------------------

    def _wizard_back(self):
        if self.step_index > 0:
            self.step_index -= 1
            self._render_step()
        else:
            self._show_page(self.welcome_page)

    def _wizard_next(self):
        if not self._can_proceed():
            return
        if self.step_index < TOTAL_STEPS - 1:
            self.step_index += 1
            self._render_step()
            return
        self.db.save_profile(
            self.pending_user_id,
            self.profile["country"], self.profile["language"], self.profile["age_group"],
            self.profile["conditions"], self.profile["habits"], self.profile["goals"],
        )
        self.db.set_session_user_id(self.pending_user_id)
        self.login_completed.emit(self.pending_user_id)

    def reset_to_welcome(self):
        """Called after sign-out so a fresh session starts at the welcome screen."""
        for edit, err in ((self.si_email, self.si_email_err), (self.si_password, self.si_password_err),
                          (self.su_name, self.su_name_err), (self.su_email, self.su_email_err),
                          (self.su_password, self.su_password_err)):
            edit.clear()
            self._set_error(edit, err, "")
        for label in (self.si_error, self.su_error):
            label.setVisible(False)
        self.si_create_link.setVisible(False)
        self._show_page(self.welcome_page)
