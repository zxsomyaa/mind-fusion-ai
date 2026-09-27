"""Nutrition tab - drop in a meal photo, send it to the local vision model
(llava via Ollama by default), and see the breakdown as calories, a balance
score, macros and tips - plus today's totals and your recent meals.

If the configured vision model isn't pulled yet, this tab downloads it
automatically in the background the first time it's needed - no manual
`ollama pull` step and no separate download button to click.
"""

import base64
from datetime import date, datetime

from PySide6.QtCore import QBuffer, QIODevice, Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFileDialog, QFrame, QHBoxLayout, QLabel, QProgressBar, QPushButton, QScrollArea,
    QStackedWidget, QVBoxLayout, QWidget,
)

from ai_client import check_connection, vision_ai
from data import COLORS as C
from image_utils import IMAGE_FILE_FILTER, ImageLoadError, load_image_any
from nutrition_logic import (
    balance_label, balance_tone, meals_on, parse_analysis, summarise_meals,
)
from ui.charts import DonutChart, RingGauge
from ui.flow_layout import FlowLayout
from ui.widgets import Card, StatCard, pill, score_badge, tone_colour
from workers import FnWorker, PullWorker

NUTRITION_PROMPT = (
    'Look at this meal photo and respond with ONLY a raw JSON object - no markdown, '
    "no code fences, no explanation. Use exactly this structure:\n"
    '{"foods":["item1"],"calories_estimate":450,"nutrients":{"protein":22,"carbs":55,"fat":14,"fibre":6},'
    '"mood_impact":"one sentence about energy/mood","recommendation":"one practical suggestion","balance_score":7}\n'
    "Estimate realistically. balance_score is 1-10."
)

MAX_DIMENSION = 768          # keeps the base64 payload small enough for local models
DAY_CALORIES = 2000          # reference for "share of a day" - a rough, common figure
MACRO_COLOURS = {"protein": "#E07A5F", "carbs": "#D4A017", "fat": "#748CAB", "fibre": "#52B788"}
MACRO_NAMES = {"protein": "Protein", "carbs": "Carbs", "fat": "Fat", "fibre": "Fibre"}


def _heading(text):
    label = QLabel(text)
    label.setStyleSheet("font-size:15px; font-weight:700;")
    return label


def _muted(text, size=12):
    label = QLabel(text)
    label.setWordWrap(True)
    label.setStyleSheet(f"color:{C['text_muted']}; font-size:{size}px;")
    return label


class DropZone(QFrame):
    """A dashed area you can drop a photo onto or click to browse. Shows the
    chosen photo once there is one."""

    clicked = Signal()
    file_dropped = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("dropZone")
        self.setAcceptDrops(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(250)
        self._style(dragging=False)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        self.picture = QLabel()
        self.picture.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.picture)
        self.clear()

    def _style(self, dragging):
        border = C["primary"] if dragging else C["border"]
        background = C["primary_pale"] if dragging else C["surface"]
        self.setStyleSheet(
            f"QFrame#dropZone {{ background:{background}; border:2px dashed {border}; border-radius:16px; }}"
        )

    def clear(self):
        self.picture.setPixmap(QPixmap())
        self.picture.setText(
            f"<div style='text-align:center;'><span style='font-size:38px;'>🍽️</span><br>"
            f"<b style='font-size:15px;'>Drop a meal photo here</b><br>"
            f"<span style='color:{C['text_muted']};'>or click to choose one</span></div>"
        )

    def show_pixmap(self, pixmap):
        self.picture.setText("")
        self.picture.setPixmap(pixmap.scaled(self.width() - 24, self.height() - 24,
                                             Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() and any(u.isLocalFile() for u in event.mimeData().urls()):
            event.acceptProposedAction()
            self._style(dragging=True)

    def dragLeaveEvent(self, _event):
        self._style(dragging=False)

    def dropEvent(self, event):
        self._style(dragging=False)
        for url in event.mimeData().urls():
            if url.isLocalFile():
                self.file_dropped.emit(url.toLocalFile())
                break


class MealRow(Card):
    """One logged meal: balance badge, what it was, when, macros, and a delete button."""

    def __init__(self, meal, on_delete, parent=None):
        super().__init__(parent)
        self.layout_.setContentsMargins(14, 12, 14, 12)
        row = QHBoxLayout()
        row.setSpacing(14)

        score = meal.get("balance_score")
        row.addWidget(score_badge(str(score) if score is not None else "?", balance_tone(score)))

        info = QVBoxLayout()
        info.setSpacing(2)
        title = QLabel(meal.get("foods") or "Meal")
        title.setWordWrap(True)
        title.setStyleSheet("font-size:14px; font-weight:700;")
        info.addWidget(title)
        when = datetime.fromtimestamp(meal["timestamp"] / 1000).strftime("%a %d %b, %H:%M")
        bits = [when]
        if meal.get("calories_estimate") is not None:
            bits.append(f"{meal['calories_estimate']} kcal")
        macros = [f"{letter} {meal[key]:g}g" for letter, key in (("P", "protein"), ("C", "carbs"), ("F", "fat"))
                  if meal.get(key) is not None]
        if macros:
            bits.append(" · ".join(macros))
        info.addWidget(_muted("  ·  ".join(bits)))
        if meal.get("mood_impact"):
            note = _muted(meal["mood_impact"])
            note.setStyleSheet(f"color:{C['text_muted']}; font-size:12px; font-style:italic;")
            info.addWidget(note)
        row.addLayout(info, stretch=1)

        delete = QPushButton("×")
        delete.setObjectName("iconBtn")
        delete.setToolTip("Remove this meal from your log")
        delete.setCursor(Qt.PointingHandCursor)
        delete.clicked.connect(lambda: on_delete(meal["id"]))
        row.addWidget(delete, alignment=Qt.AlignTop)
        self.layout_.addLayout(row)


class NutritionTab(QWidget):
    def __init__(self, db, user_id, get_ai_config, parent=None):
        super().__init__(parent)
        self.db = db
        self.user_id = user_id
        self.get_ai_config = get_ai_config
        self.image_base64 = None
        self.connected = None
        self._worker = None
        self._pull_worker = None
        self._model_check_worker = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        outer.addWidget(scroll)
        page = QWidget()
        scroll.setWidget(page)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 22, 28, 28)
        layout.setSpacing(16)

        title = QLabel("Meal analysis")
        title.setStyleSheet(f"font-size:24px; font-weight:800; color:{C['primary']};")
        layout.addWidget(title)
        layout.addWidget(_muted("Snap or drop a photo of your meal for an instant nutrition estimate and a "
                                "note on how it might affect your energy. Analysed on your computer.", 13))

        self.status_banner = QLabel("")
        self.status_banner.setWordWrap(True)
        self.status_banner.setVisible(False)
        layout.addWidget(self.status_banner)

        self.today_row = QHBoxLayout()
        self.today_row.setSpacing(14)
        layout.addLayout(self.today_row)

        # -- upload (left) and results (right) ---------------------------------------
        columns = QHBoxLayout()
        columns.setSpacing(18)
        layout.addLayout(columns)

        upload = Card()
        upload.layout_.setSpacing(12)
        upload.layout_.addWidget(_heading("Your meal"))
        self.drop = DropZone()
        self.drop.clicked.connect(self._pick_image)
        self.drop.file_dropped.connect(self._load_path)
        upload.layout_.addWidget(self.drop)

        buttons = QHBoxLayout()
        self.pick_btn = QPushButton("Choose photo…")
        self.pick_btn.setObjectName("ghost")
        self.pick_btn.clicked.connect(self._pick_image)
        self.analyse_btn = QPushButton("Analyse meal  →")
        self.analyse_btn.clicked.connect(self._analyse)
        self.analyse_btn.setEnabled(False)
        buttons.addWidget(self.pick_btn)
        buttons.addWidget(self.analyse_btn, stretch=1)
        upload.layout_.addLayout(buttons)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color:#E07A5F; font-size:12px;")
        self.error_label.setWordWrap(True)
        upload.layout_.addWidget(self.error_label)
        upload.layout_.addWidget(_muted("PNG, JPEG, HEIC, WebP and more. The photo is resized on your computer "
                                        "and never leaves it.", 11))
        columns.addWidget(upload, stretch=4, alignment=Qt.AlignTop)   # only as tall as its content

        self.results = QStackedWidget()
        self.results.addWidget(self._build_placeholder())     # 0: nothing yet
        self.results.addWidget(self._build_analysing())       # 1: working
        self.result_page = QWidget()                            # 2: the analysis
        self.result_layout = QVBoxLayout(self.result_page)
        self.result_layout.setContentsMargins(0, 0, 0, 0)
        self.result_layout.setSpacing(14)
        self.results.addWidget(self.result_page)
        columns.addWidget(self.results, stretch=6)

        # -- recent meals ----------------------------------------------------------------
        layout.addSpacing(6)
        layout.addWidget(_heading("Recent meals"))
        self.meals_layout = QVBoxLayout()
        self.meals_layout.setSpacing(10)
        layout.addLayout(self.meals_layout)
        layout.addStretch()

        self.refresh()

    # -- panels -----------------------------------------------------------------------------

    def _build_placeholder(self):
        card = Card()
        card.layout_.setAlignment(Qt.AlignCenter)
        icon = QLabel("🥗")
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet("font-size:44px;")
        card.layout_.addWidget(icon)
        head = QLabel("Your analysis will appear here")
        head.setAlignment(Qt.AlignCenter)
        head.setStyleSheet("font-size:16px; font-weight:700;")
        card.layout_.addWidget(head)
        hint = _muted("You'll see estimated calories, how balanced the meal is, its macros, and a "
                      "suggestion - and it's saved to your meal log.", 12)
        hint.setAlignment(Qt.AlignCenter)
        card.layout_.addWidget(hint)
        return card

    def _build_analysing(self):
        card = Card()
        card.layout_.setAlignment(Qt.AlignCenter)
        icon = QLabel("🔍")
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet("font-size:40px;")
        card.layout_.addWidget(icon)
        head = QLabel("Analysing your meal…")
        head.setAlignment(Qt.AlignCenter)
        head.setStyleSheet("font-size:16px; font-weight:700;")
        card.layout_.addWidget(head)
        bar = QProgressBar()
        bar.setRange(0, 0)                       # endless "busy" animation
        bar.setTextVisible(False)
        bar.setFixedHeight(8)
        card.layout_.addWidget(bar)
        hint = _muted("A local model does this on your own computer, so it can take up to a minute.", 12)
        hint.setAlignment(Qt.AlignCenter)
        card.layout_.addWidget(hint)
        return card

    # -- connection / model (unchanged behaviour) --------------------------------------------

    def set_connected(self, connected):
        self.connected = connected
        if connected:
            self._check_vision_model()
        elif connected is False:
            self.status_banner.setVisible(True)
            self.status_banner.setText("Not connected to your local AI server. Check settings.")
            self.status_banner.setStyleSheet(
                f"background:{C['sage_pale']}; color:{C['sage']}; border-radius:8px; padding:8px 12px;"
            )

    def _check_vision_model(self):
        config = self.get_ai_config()
        if config["provider"] != "ollama":
            self.status_banner.setVisible(False)
            return

        def check():
            models = check_connection(config)
            base = config["vision_model"].split(":")[0]
            return any(m.split(":")[0] == base for m in models)

        worker = FnWorker(check)
        worker.finished_ok.connect(lambda ready: None if ready else self._start_auto_pull(config))
        worker.start()
        self._model_check_worker = worker  # keep a reference so it isn't garbage collected

    def _start_auto_pull(self, config):
        self.status_banner.setVisible(True)
        self.status_banner.setStyleSheet(
            "background:#FDF6E3; color:#8A6D1D; border-radius:8px; padding:8px 12px;"
        )
        self.status_banner.setText("Getting things ready… this only happens once.")

        self._pull_worker = PullWorker(config, config["vision_model"])
        self._pull_worker.progress.connect(self._on_pull_progress)
        self._pull_worker.finished_ok.connect(self._on_pull_done)
        self._pull_worker.failed.connect(self._on_pull_failed)
        self._pull_worker.start()

    def _on_pull_progress(self, status):
        completed, total = status.get("completed"), status.get("total")
        if completed and total:
            self.status_banner.setText(f"Getting things ready ({round(completed / total * 100)}%)…")

    def _on_pull_done(self):
        self.status_banner.setVisible(False)

    def _on_pull_failed(self, message):
        self.status_banner.setText(f"Couldn't prepare the vision model: {message}")

    # -- choosing a photo ------------------------------------------------------------------------

    def _pick_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choose a meal photo", "", IMAGE_FILE_FILTER)
        if path:
            self._load_path(path)

    def _load_path(self, path):
        try:
            image = load_image_any(path)
        except ImageLoadError as exc:
            self.image_base64 = None
            self.drop.clear()
            self.analyse_btn.setEnabled(False)
            self.error_label.setText(str(exc))
            return

        scaled = image.scaled(MAX_DIMENSION, MAX_DIMENSION, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.drop.show_pixmap(QPixmap.fromImage(scaled))

        buffer = QBuffer()
        buffer.open(QIODevice.WriteOnly)
        scaled.save(buffer, "JPEG", 85)
        self.image_base64 = base64.b64encode(buffer.data().data()).decode("ascii")

        self.analyse_btn.setEnabled(True)
        self.error_label.setText("")
        self.results.setCurrentIndex(0)

    # -- analysing ---------------------------------------------------------------------------------

    def _analyse(self):
        if not self.image_base64:
            return
        self.analyse_btn.setEnabled(False)
        self.pick_btn.setEnabled(False)
        self.error_label.setText("")
        self.results.setCurrentIndex(1)

        config = self.get_ai_config()
        image = self.image_base64
        self._worker = FnWorker(lambda: vision_ai(config, image, NUTRITION_PROMPT))
        self._worker.finished_ok.connect(self._on_result)
        self._worker.failed.connect(self._on_error)
        self._worker.start()

    def _finish_analysis(self):
        self.analyse_btn.setEnabled(bool(self.image_base64))
        self.pick_btn.setEnabled(True)

    def _on_result(self, raw):
        self._finish_analysis()
        try:
            analysis = parse_analysis(raw)
        except ValueError as exc:
            self.results.setCurrentIndex(0)
            self.error_label.setText(str(exc))
            return

        nutrients = analysis["nutrients"]
        self.db.add_nutrition_entry(
            self.user_id, ", ".join(analysis["foods"]), analysis["calories_estimate"], analysis["balance_score"],
            analysis["mood_impact"], protein=nutrients.get("protein"), carbs=nutrients.get("carbs"),
            fat=nutrients.get("fat"), fibre=nutrients.get("fibre"), recommendation=analysis["recommendation"],
        )
        self._render_result(analysis)
        self.results.setCurrentIndex(2)
        self.refresh()

    def _on_error(self, message):
        self._finish_analysis()
        self.results.setCurrentIndex(0)
        if "Connection" in message or "connect" in message.lower():
            self.error_label.setText("Couldn't reach the vision model - is Ollama running? Check settings.")
        else:
            self.error_label.setText(f"Analysis failed: {message}")

    # -- showing an analysis ----------------------------------------------------------------------

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                widget = item.widget()
                widget.setParent(None)      # leave the page immediately; deleteLater alone keeps it attached
                widget.deleteLater()        # until Qt next processes events
            elif item.layout():
                self._clear_layout(item.layout())

    def _render_result(self, analysis):
        self._clear_layout(self.result_layout)

        top = QHBoxLayout()
        top.setSpacing(14)
        top.addWidget(self._calories_card(analysis["calories_estimate"]), stretch=1)
        top.addWidget(self._balance_card(analysis["balance_score"]), stretch=1)
        self.result_layout.addLayout(top)

        if analysis["nutrients"]:
            self.result_layout.addWidget(self._macros_card(analysis["nutrients"]))
        if analysis["foods"]:
            self.result_layout.addWidget(self._foods_card(analysis["foods"]))

        notes = QHBoxLayout()
        notes.setSpacing(14)
        if analysis["mood_impact"]:
            notes.addWidget(self._note_card("⚡", "Energy & mood", analysis["mood_impact"]), stretch=1)
        if analysis["recommendation"]:
            notes.addWidget(self._note_card("💡", "Try this next", analysis["recommendation"]), stretch=1)
        if notes.count():
            self.result_layout.addLayout(notes)

        saved = QLabel("✓ Saved to your meal log")
        saved.setStyleSheet(f"color:{C['sage']}; font-size:12px; font-weight:600;")
        self.result_layout.addWidget(saved)

    def _calories_card(self, calories):
        card = Card()
        card.layout_.addWidget(_heading("Estimated calories"))
        if calories is None:
            card.layout_.addWidget(_muted("The model didn't give a calorie estimate for this photo."))
            return card
        value = QLabel(f"{calories} <span style='font-size:14px; font-weight:600; color:{C['text_muted']};'>kcal</span>")
        value.setStyleSheet("font-size:34px; font-weight:800;")
        card.layout_.addWidget(value)
        share = min(100, round(calories / DAY_CALORIES * 100))
        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(share)
        bar.setTextVisible(False)
        bar.setFixedHeight(8)
        bar.setStyleSheet(
            f"QProgressBar {{ height:8px; border-radius:4px; background:{C['border']}; }}"
            f"QProgressBar::chunk {{ border-radius:4px; background:{C['primary']}; }}"
        )
        card.layout_.addWidget(bar)
        card.layout_.addWidget(_muted(f"about {round(calories / DAY_CALORIES * 100)}% of a {DAY_CALORIES:,} kcal day"))
        return card

    def _balance_card(self, score):
        card = Card()
        card.layout_.addWidget(_heading("Meal balance"))
        gauge = RingGauge(size=112, thickness=11)
        tone = balance_tone(score)
        gauge.set_value((score or 0) / 10, f"{score}/10" if score is not None else "-",
                        balance_label(score), tone_colour(tone))
        card.layout_.addWidget(gauge, alignment=Qt.AlignCenter)
        return card

    def _macros_card(self, nutrients):
        card = Card()
        card.layout_.addWidget(_heading("Macros (by weight)"))
        donut = DonutChart()
        segments = [(MACRO_NAMES[k], nutrients[k], MACRO_COLOURS[k]) for k in MACRO_NAMES if k in nutrients]
        total = sum(v for _l, v, _c in segments)
        donut.set_segments(segments, f"{total:g} g", "total", unit=" g")
        card.layout_.addWidget(donut)
        return card

    def _foods_card(self, foods):
        card = Card()
        card.layout_.addWidget(_heading("What I can see"))
        host = QWidget()
        host.setObjectName("flowHost")
        flow = FlowLayout(host, h_spacing=8, v_spacing=8)
        for food in foods:
            flow.addWidget(pill(food))
        card.layout_.addWidget(host)
        return card

    def _note_card(self, emoji, title, text):
        card = Card()
        card.layout_.addWidget(_heading(f"{emoji}  {title}"))
        body = QLabel(text)
        body.setWordWrap(True)
        body.setStyleSheet("font-size:13px;")
        card.layout_.addWidget(body)
        return card

    # -- today + history ------------------------------------------------------------------------------

    def refresh(self):
        """Reloads today's totals and the recent-meals list from the database."""
        meals = self.db.get_nutrition_history(self.user_id)
        today = summarise_meals(meals_on(meals, date.today()))

        self._clear_layout(self.today_row)
        self.today_row.addWidget(StatCard("Calories today", f"{today['calories']:,}" if today["calories"] is not None else "-"))
        self.today_row.addWidget(StatCard("Meals logged today", str(today["count"])))
        self.today_row.addWidget(StatCard("Avg balance today",
                                          f"{today['avg_balance']}/10" if today["avg_balance"] is not None else "-"))

        self._clear_layout(self.meals_layout)
        if not meals:
            empty = _muted("No meals yet - analyse your first one above and it will show up here.", 13)
            self.meals_layout.addWidget(empty)
            return
        for meal in meals[:8]:
            self.meals_layout.addWidget(MealRow(meal, self._delete_meal))

    def _delete_meal(self, meal_id):
        self.db.delete_nutrition_entry(meal_id)
        self.refresh()
