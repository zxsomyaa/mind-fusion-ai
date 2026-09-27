"""
Automated tests for Mind Fusion Desktop.

Run from the desktop_app folder:   python -m unittest discover -s tests -v

Safe to run any time: every test uses a temporary database (never
mind_fusion.db), the Qt UI runs "offscreen" (no window appears), and the local
AI server and camera are replaced with stand-ins, so nothing is downloaded and
no real camera or model is touched.
"""

import os
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import cv2  # noqa: E402
import numpy as np  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

import data  # noqa: E402
import face_analysis as fa  # noqa: E402
import styles  # noqa: E402
from db import Database  # noqa: E402
from image_utils import ImageLoadError, load_image_any  # noqa: E402
import insights_logic as il  # noqa: E402
import nutrition_logic as nl  # noqa: E402

_app = QApplication.instance() or QApplication([])

SAMPLE_FACE_URL = "https://raw.githubusercontent.com/opencv/opencv/4.x/samples/data/lena.jpg"
SAMPLE_FACE = Path(__file__).parent / "sample_face.jpg"


def _sample_face():
    """A real portrait for face-detection tests; downloaded once, or None if offline."""
    if not SAMPLE_FACE.exists():
        try:
            urllib.request.urlretrieve(SAMPLE_FACE_URL, SAMPLE_FACE)
        except OSError:
            return None
    return cv2.imread(str(SAMPLE_FACE))


class MoodDetectionTests(unittest.TestCase):
    def test_english(self):
        self.assertEqual(data.detect_mood("I feel anxious and worried")["mood"], "anxious")
        self.assertEqual(data.detect_mood("I'm feeling really down today.")["mood"], "sad")
        self.assertEqual(data.detect_mood("thank you so much")["mood"], "grateful")

    def test_hinglish_and_hindi(self):
        self.assertEqual(data.detect_mood("mujhe dar lagta hain")["mood"], "anxious")   # the reported bug
        self.assertEqual(data.detect_mood("मुझे डर लग रहा है")["mood"], "anxious")
        self.assertEqual(data.detect_mood("main bahut udaas hoon")["mood"], "sad")
        self.assertEqual(data.detect_mood("aaj main bahut khush hoon!")["mood"], "happy")

    def test_whole_word_matching(self):
        self.assertEqual(data.detect_mood("It is dark outside")["mood"], "calm")      # 'dark' is not 'dar'
        self.assertEqual(data.detect_mood("please help me")["mood"], "calm")          # 'please' is not 'ease'

    def test_crisis_detection_incl_hindi(self):
        for text in ("I want to die", "SELF-HARM thoughts", "mujhe marna chahta hoon", "मैं आत्महत्या के बारे में सोच रहा हूँ"):
            self.assertTrue(data.detect_crisis(text), text)
        self.assertFalse(data.detect_crisis("mujhe dar lagta hai"))


class LanguageTests(unittest.TestCase):
    def test_choices_include_match_english_hindi_hinglish_and_the_signup_languages(self):
        codes = [l["code"] for l in data.CHAT_LANGUAGES]
        self.assertEqual(codes[:4], ["auto", "en", "hi", "hinglish"])
        self.assertEqual(len(codes), len(set(codes)))                           # no duplicates
        for l in data.LANGUAGES:
            self.assertIn(l["code"], codes)

    def test_defaults_follow_the_signup_language(self):
        self.assertEqual(data.default_chat_language("en"), "auto")
        self.assertEqual(data.default_chat_language(None), "auto")
        self.assertEqual(data.default_chat_language("hi"), "hi")
        self.assertEqual(data.default_chat_language("klingon"), "auto")          # unknown -> safe default

    def test_each_choice_gives_a_distinct_instruction(self):
        instructions = {c: data.language_instruction(c) for c in (l["code"] for l in data.CHAT_LANGUAGES)}
        self.assertTrue(all(instructions.values()))
        self.assertEqual(len(set(instructions.values())), len(instructions))
        self.assertIn("Roman", instructions["hinglish"])
        self.assertIn("Never use Devanagari", instructions["hinglish"])
        self.assertIn("Spanish", instructions["es"])
        self.assertEqual(data.language_instruction("nope"), "")

    def test_speech_to_text_gets_a_hint_only_for_real_languages(self):
        self.assertEqual([data.whisper_language(c) for c in ("auto", "hinglish", "hi", "es", "en")],
                         [None, None, "hi", "es", "en"])

    def test_language_reminder_is_empty_only_for_auto(self):
        # 'auto' means "whatever the user writes" - there is nothing to remind the
        # model to switch to, so it alone gets no reminder message.
        self.assertEqual(data.language_reminder("auto"), "")
        self.assertEqual(data.language_reminder(None), "")
        self.assertEqual(data.language_reminder("nope"), "")
        for code in (c["code"] for c in data.CHAT_LANGUAGES if c["code"] != "auto"):
            self.assertTrue(data.language_reminder(code), code)
        self.assertIn("Spanish", data.language_reminder("es"))
        self.assertIn("Hinglish", data.language_reminder("hinglish"))


class ImageLoaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        d = Path(cls.tmp.name)
        img = np.zeros((300, 400, 3), dtype="uint8")
        img[:] = (40, 120, 200)
        for name in ("a.png", "b.jpg", "c.webp", "d.bmp"):
            cv2.imwrite(str(d / name), img)
        cls.dir = d

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_common_formats_load(self):
        for name in ("a.png", "b.jpg", "c.webp", "d.bmp"):
            image = load_image_any(self.dir / name)
            self.assertEqual((image.width(), image.height()), (400, 300), name)

    @unittest.skipUnless(sys.platform == "darwin", "uses macOS sips to make a HEIC file")
    def test_heic_even_when_named_jpg(self):
        heic = self.dir / "e.heic"
        subprocess.run(["sips", "-s", "format", "heic", str(self.dir / "a.png"), "--out", str(heic)],
                       capture_output=True, check=True)
        disguised = self.dir / "photo.jpg"
        disguised.write_bytes(heic.read_bytes())
        self.assertFalse(load_image_any(heic).isNull())
        self.assertFalse(load_image_any(disguised).isNull())

    def test_failures_explain_themselves(self):
        fake = self.dir / "fake.jpg"
        fake.write_text("not an image")
        with self.assertRaisesRegex(ImageLoadError, "Couldn't read this image"):
            load_image_any(fake)
        empty = self.dir / "empty.jpg"
        empty.touch()
        with self.assertRaisesRegex(ImageLoadError, "empty"):
            load_image_any(empty)
        with self.assertRaisesRegex(ImageLoadError, "no longer exists"):
            load_image_any(self.dir / "missing.jpg")

    @unittest.skipIf(os.geteuid() == 0, "root ignores file permissions")
    def test_blocked_file_reports_permission_problem(self):
        blocked = self.dir / "blocked.png"
        blocked.write_bytes((self.dir / "a.png").read_bytes())
        blocked.chmod(0)
        try:
            with self.assertRaisesRegex(ImageLoadError, "blocking access"):
                load_image_any(blocked)
        finally:
            blocked.chmod(0o644)


class FakeCapture:
    """Stands in for cv2.VideoCapture: replays a fixed list of frames."""

    def __init__(self, frames):
        self.frames, self.i, self.released = frames, 0, False

    def isOpened(self):
        return self.frames is not None

    def read(self):
        if not self.frames:
            return False, None
        frame = self.frames[self.i % len(self.frames)]
        self.i += 1
        time.sleep(0.005)   # a real camera isn't infinitely fast
        return True, frame.copy()

    def release(self):
        self.released = True


def wait_until(condition, timeout=20.0):
    """Runs the Qt event loop until condition() is true (or the timeout passes)."""
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        _app.processEvents()
        if condition():
            return True
        time.sleep(0.01)
    return False


class CameraTests(unittest.TestCase):
    """The camera is replaced by FakeCapture objects; the models are real."""

    black = np.zeros((480, 640, 3), dtype="uint8")
    ceiling = np.full((480, 640, 3), 170, dtype="uint8") + \
        np.random.default_rng(0).integers(0, 12, (480, 640, 3)).astype("uint8")

    @classmethod
    def setUpClass(cls):
        if not fa.FACE_MODEL_PATH.exists() or not fa.EMOTION_MODEL_PATH.exists():
            fa.ensure_models_downloaded()
        cls.face = _sample_face()

    def setUp(self):
        self.opened = []   # every FakeCapture created, so tests can check it was released
        self.cameras = {}
        self._patches = [
            mock.patch.object(fa.cv2, "VideoCapture", self._make_capture),
            mock.patch.object(fa, "WARMUP_FRAMES", 2),
        ]
        for p in self._patches:
            p.start()

    def tearDown(self):
        for p in self._patches:
            p.stop()

    def _make_capture(self, index):
        cap = FakeCapture(self.cameras.get(index))
        self.opened.append(cap)
        return cap

    def _run_worker(self):
        worker = fa.CameraWorker()
        log = {"frames": [], "camera": [], "status": [], "result": None, "capture_failed": None, "failed": None}
        worker.frame_ready.connect(lambda img, face: log["frames"].append((img, face)))
        worker.camera_changed.connect(lambda i: log["camera"].append(i))
        worker.status.connect(lambda m: log["status"].append(m))
        worker.result.connect(lambda r: log.update(result=r))
        worker.capture_failed.connect(lambda m: log.update(capture_failed=m))
        worker.failed.connect(lambda m: log.update(failed=m))
        worker.start()
        self.addCleanup(lambda: (worker.stop(), worker.wait(5000)))
        return worker, log

    # -- pure helpers ---------------------------------------------------------

    def test_blank_frames_and_faceless_frames(self):
        self.assertTrue(fa._looks_blank(self.black))
        self.assertFalse(fa._looks_blank(self.ceiling))
        self.assertIsNone(fa.detect_face_box(self.ceiling))

    def test_summarise_averages_frames(self):
        happy = np.array([0.1, 0.8, 0.0, 0.0, 0.0, 0.0, 0.1, 0.0])
        neutral = np.array([0.7, 0.2, 0.0, 0.0, 0.0, 0.0, 0.1, 0.0])
        label, confidence, mood = fa.summarise_emotions([happy, happy, neutral])
        self.assertEqual((label, mood), ("happiness", "happy"))      # 2 of 3 frames outvote the odd one
        self.assertAlmostEqual(confidence, (0.8 + 0.8 + 0.2) / 3)

    def test_camera_selection_skips_blank_cameras(self):
        self.cameras = {0: [self.black], 1: [self.ceiling], 2: [self.ceiling]}
        cap, index, reason = fa.open_first_working_camera(0)
        self.assertEqual((index, reason), (1, "ok"))
        self.assertTrue(self.opened[0].released)        # the blank one was closed again
        self.cameras = {0: [self.black], 1: None, 2: None}
        self.assertEqual(fa.open_first_working_camera(0), (None, None, "blank"))
        self.cameras = {}
        self.assertEqual(fa.open_first_working_camera(0), (None, None, "none"))

    @unittest.skipIf(_sample_face() is None, "no sample face image (offline)")
    def test_detector_finds_faces_a_strict_threshold_would_miss(self):
        small = cv2.resize(self.face, None, fx=0.35, fy=0.35)
        dark = (self.face * 0.25).astype("uint8")
        detector = fa.FaceDetector()
        for name, img in (("clear", self.face), ("small", small), ("dark", dark)):
            self.assertIsNotNone(detector.detect(img), name)
        first = detector._detector
        detector.detect(self.face)
        self.assertIs(detector._detector, first)   # model kept loaded between frames

    # -- the live worker -----------------------------------------------------------

    @unittest.skipIf(_sample_face() is None, "no sample face image (offline)")
    def test_live_preview_then_capture(self):
        self.cameras = {0: [self.face]}
        worker, log = self._run_worker()
        self.assertTrue(wait_until(lambda: any(face for _img, face in log["frames"])), "no live frame with a face")
        self.assertTrue(wait_until(lambda: len(log["frames"]) >= 6), "expected a stream of frames, not one picture")
        self.assertFalse(log["frames"][-1][0].isNull())
        self.assertEqual(log["camera"], [0])

        worker.request_capture()
        self.assertTrue(wait_until(lambda: log["result"] is not None), "no result")
        result = log["result"]
        self.assertIn(result["mood"], data.MOODS)
        self.assertEqual(result["frames"], fa.CAPTURE_SAMPLES)
        self.assertFalse(result["preview"].isNull())

        worker.stop()
        self.assertTrue(worker.wait(5000))
        self.assertTrue(self.opened[0].released)                       # camera really switched off

    def test_capture_without_a_face_reports_it(self):
        self.cameras = {0: [self.ceiling]}
        worker, log = self._run_worker()
        self.assertTrue(wait_until(lambda: len(log["frames"]) > 2))
        worker.request_capture()
        self.assertTrue(wait_until(lambda: log["capture_failed"] is not None, timeout=fa.CAPTURE_TIMEOUT_S + 10))
        self.assertIn("couldn't see a face", log["capture_failed"].lower())
        self.assertIsNone(log["result"])
        self.assertFalse(any(face for _img, face in log["frames"]))     # never claimed to see one

    @unittest.skipIf(_sample_face() is None, "no sample face image (offline)")
    def test_starts_on_the_first_camera_that_delivers_a_picture(self):
        self.cameras = {0: [self.black], 1: [self.face]}                # camera 0 = paused iPhone
        worker, log = self._run_worker()
        self.assertTrue(wait_until(lambda: len(log["frames"]) > 2))
        self.assertEqual(log["camera"], [1])

    @unittest.skipIf(_sample_face() is None, "no sample face image (offline)")
    def test_switch_camera(self):
        self.cameras = {0: [self.face], 1: [self.ceiling]}
        worker, log = self._run_worker()
        self.assertTrue(wait_until(lambda: len(log["frames"]) > 2))
        worker.switch_camera()
        self.assertTrue(wait_until(lambda: log["camera"] == [0, 1]), f"camera events: {log['camera']}")
        self.assertTrue(self.opened[0].released)

    def test_no_camera_reports_failure(self):
        self.cameras = {}
        worker, log = self._run_worker()
        self.assertTrue(wait_until(lambda: log["failed"] is not None))
        self.assertIn("Could not access a webcam", log["failed"])

    def test_all_blank_mentions_continuity_camera(self):
        self.cameras = {0: [self.black], 1: [self.black], 2: [self.black]}
        worker, log = self._run_worker()
        self.assertTrue(wait_until(lambda: log["failed"] is not None))
        self.assertIn("Continuity", log["failed"])

    # -- the window -------------------------------------------------------------------

    @unittest.skipIf(_sample_face() is None, "no sample face image (offline)")
    def test_dialog_shows_live_picture_and_logs_a_mood(self):
        from ui.camera_dialog import CameraDialog
        self.cameras = {0: [self.face]}
        dialog = CameraDialog()
        chosen = []
        dialog.mood_selected.connect(chosen.append)
        dialog.show()
        self.addCleanup(dialog.reject)

        self.assertTrue(wait_until(lambda: dialog.view.pixmap() is not None and not dialog.view.pixmap().isNull()),
                        "no live picture in the window")
        self.assertTrue(wait_until(lambda: dialog.analyse_btn.isEnabled()))
        self.assertTrue(wait_until(lambda: "Face found" in dialog.status.text()))

        dialog.analyse_btn.click()
        self.assertTrue(wait_until(lambda: not dialog.result_label.isHidden()), "no result shown")
        self.assertFalse(dialog.log_btn.isHidden())
        dialog.log_btn.click()
        self.assertEqual(len(chosen), 1)
        self.assertIn(chosen[0]["mood"], data.MOODS)
        self.assertIsNone(dialog._worker)                                # worker stopped
        self.assertTrue(self.opened[0].released)                         # camera off

    def test_closing_the_window_switches_the_camera_off(self):
        from ui.camera_dialog import CameraDialog
        self.cameras = {0: [self.ceiling]}
        dialog = CameraDialog()
        dialog.show()
        self.assertTrue(wait_until(lambda: dialog.analyse_btn.isEnabled()))
        dialog.reject()
        self.assertTrue(self.opened[0].released)

    def test_dialog_explains_when_no_camera(self):
        from ui.camera_dialog import CameraDialog
        self.cameras = {}
        dialog = CameraDialog()
        dialog.show()
        self.addCleanup(dialog.reject)
        self.assertTrue(wait_until(lambda: "Could not access a webcam" in dialog.status.text()))
        self.assertFalse(dialog.analyse_btn.isEnabled())


class NutritionLogicTests(unittest.TestCase):
    """The vision model's answers are messy - the parser must cope, and must not invent data."""

    CLEAN = ('{"foods":["dal","rice"],"calories_estimate":520,"nutrients":{"protein":22,"carbs":80,'
             '"fat":12,"fibre":9},"mood_impact":"steady energy","recommendation":"add greens","balance_score":8}')

    def test_clean_answer(self):
        r = nl.parse_analysis(self.CLEAN)
        self.assertEqual(r["foods"], ["dal", "rice"])
        self.assertEqual((r["calories_estimate"], r["balance_score"]), (520, 8))
        self.assertEqual(r["nutrients"], {"protein": 22.0, "carbs": 80.0, "fat": 12.0, "fibre": 9.0})
        self.assertEqual((r["mood_impact"], r["recommendation"]), ("steady energy", "add greens"))

    def test_code_fences_and_chatter_around_the_json(self):
        r = nl.parse_analysis("Sure! Here is the analysis:\n```json\n" + self.CLEAN + "\n```\nHope that helps.")
        self.assertEqual(r["calories_estimate"], 520)

    def test_single_quotes_trailing_commas_and_units(self):
        raw = "{'foods': 'dal, rice and salad', 'calories': '450 kcal', 'nutrients': {'Protein': '22 g', 'Carbohydrates': 55, 'Fiber': 6,}, 'balance_score': '7/10',}"
        r = nl.parse_analysis(raw)
        self.assertEqual(r["foods"], ["dal", "rice", "salad"])
        self.assertEqual(r["calories_estimate"], 450)
        self.assertEqual(r["nutrients"], {"protein": 22.0, "carbs": 55.0, "fibre": 6.0})
        self.assertEqual(r["balance_score"], 7)

    def test_flat_nutrient_fields(self):
        r = nl.parse_analysis('{"foods":["toast"],"protein":8,"fat":"3g","carbs":30}')
        self.assertEqual(r["nutrients"], {"protein": 8.0, "carbs": 30.0, "fat": 3.0})

    def test_nonsense_values_are_clamped_or_dropped(self):
        r = nl.parse_analysis('{"foods":["x"],"calories_estimate":999999,"balance_score":12,"nutrients":{"protein":-5}}')
        self.assertIsNone(r["calories_estimate"])          # an implausible number is dropped, not trusted
        self.assertEqual(r["balance_score"], 10)             # clamped into 1-10
        self.assertEqual(r["nutrients"], {})                 # negative grams rejected
        self.assertEqual(nl.parse_analysis('{"foods":["x"],"balance_score":0}')["balance_score"], 1)

    def test_refuses_to_invent_data(self):
        for raw in ("I can't tell what this is.", "", "{}", '{"foods": [], "mood_impact": "hm"}', "{not json at all}"):
            with self.assertRaises(ValueError, msg=raw):
                nl.parse_analysis(raw)

    def test_labels_and_summaries(self):
        self.assertEqual([nl.balance_tone(s) for s in (None, 2, 5, 9)], ["mid", "low", "mid", "high"])
        self.assertEqual([nl.balance_label(s) for s in (3, 5, 7, 9, None)], ["Needs work", "Fair", "Good", "Great", "Not rated"])
        now = int(time.time() * 1000)
        meals = [{"calories_estimate": 500, "balance_score": 8, "timestamp": now},
                 {"calories_estimate": 700, "balance_score": 4, "timestamp": now},
                 {"calories_estimate": None, "balance_score": None, "timestamp": now - 3 * 86400000}]
        today_meals = nl.meals_on(meals, date.today())
        self.assertEqual(len(today_meals), 2)
        self.assertEqual(nl.summarise_meals(today_meals), {"count": 2, "calories": 1200, "avg_balance": 6.0})
        self.assertEqual(nl.summarise_meals([]), {"count": 0, "calories": None, "avg_balance": None})


def _ts(day, hour=12):
    return int(datetime_of(day, hour).timestamp() * 1000)


def datetime_of(day, hour=12):
    from datetime import datetime
    return datetime(day.year, day.month, day.day, hour)


class InsightsLogicTests(unittest.TestCase):
    today = date(2026, 9, 26)

    def _data(self, moods=(), sleep=(), habit_days=None, meals=(), exercises=(), journal=()):
        return {
            "moods": [{"mood": m, "timestamp": _ts(d)} for d, m in moods],
            "sleep": [{"day": d.isoformat(), "hours": h, "quality": 3} for d, h in sleep],
            "habit_days": habit_days or {},
            "meals": [{"calories_estimate": c, "balance_score": b, "timestamp": _ts(d)} for d, c, b in meals],
            "exercises": [{"exercise_name": "Box Breathing", "timestamp": _ts(d)} for d in exercises],
            "journal": [{"text": "x", "timestamp": _ts(d)} for d in journal],
        }

    def days_ago(self, n):
        return self.today - timedelta(days=n)

    def test_windows(self):
        self.assertEqual(il.window(7, self.today), (self.days_ago(6), self.today))
        self.assertEqual(il.window(7, self.today, back=1), (self.days_ago(13), self.days_ago(7)))
        self.assertEqual(il.window(None, self.today), (None, self.today))

    def test_slicing_by_window(self):
        data = self._data(moods=[(self.days_ago(1), "happy"), (self.days_ago(10), "sad")],
                          sleep=[(self.days_ago(1), 7), (self.days_ago(10), 5)],
                          habit_days={"exercise": {self.days_ago(2), self.days_ago(20)}})
        sliced = il.slice_data(data, *il.window(7, self.today))
        self.assertEqual([m["mood"] for m in sliced["moods"]], ["happy"])
        self.assertEqual(len(sliced["sleep"]), 1)
        self.assertEqual(sliced["habit_days"], {"exercise": {self.days_ago(2)}})

    def test_positive_share(self):
        self.assertEqual(il.positive_share(["happy", "calm", "sad", "stressed"]), 50)
        self.assertIsNone(il.positive_share([]))

    def test_kpi_cards_compare_with_previous_period(self):
        moods = [(self.days_ago(i), "happy") for i in range(3)] + [(self.days_ago(i), "sad") for i in (8, 9, 10, 11)]
        cards = {c["key"]: c for c in il.kpi_cards(self._data(moods=moods), 7, self.today)}
        self.assertEqual(cards["checkins"]["value"], "3")
        self.assertEqual((cards["checkins"]["delta"], cards["checkins"]["sign"]), ("-1", -1))   # 3 vs 4
        self.assertEqual(cards["positive"]["value"], "100%")
        self.assertEqual(cards["positive"]["delta"], "+100 pts")
        self.assertEqual(cards["sleep"]["value"], "-")                                            # nothing logged
        self.assertIsNone(cards["sleep"]["delta"])

    def test_kpi_cards_all_time_has_no_comparison(self):
        cards = il.kpi_cards(self._data(moods=[(self.days_ago(1), "happy")]), None, self.today)
        self.assertTrue(all(c["delta"] is None for c in cards))

    def test_weekday_positive_share(self):
        # 2026-09-26 is a Saturday (weekday index 5); two Saturdays (one good, one heavy), one Monday (good)
        sat, mon = self.today, self.today - timedelta(days=5)
        moods = [{"mood": "happy", "timestamp": _ts(sat)}, {"mood": "sad", "timestamp": _ts(sat - timedelta(days=7))},
                 {"mood": "calm", "timestamp": _ts(mon)}]
        shares = il.weekday_positive_share(moods)
        self.assertEqual(shares[0], (100, 1))          # Monday
        self.assertEqual(shares[5], (50, 2))           # Saturday
        self.assertEqual(shares[2], (None, 0))         # Wednesday: nothing logged

    def test_checkin_streaks(self):
        d = self.days_ago
        moods = [{"mood": "happy", "timestamp": _ts(x)} for x in (d(0), d(1), d(2), d(10), d(11), d(12), d(13), d(14))]
        self.assertEqual(il.checkin_streaks(moods, self.today), {"current": 3, "longest": 5, "days": 8})
        # not checked in yet today: yesterday's run is still alive
        self.assertEqual(il.checkin_streaks(moods[1:3], self.today)["current"], 2)
        # a gap of a whole day breaks it
        self.assertEqual(il.checkin_streaks([{"mood": "happy", "timestamp": _ts(d(3))}], self.today)["current"], 0)
        self.assertEqual(il.checkin_streaks([], self.today), {"current": 0, "longest": 0, "days": 0})

    def test_calendar_grid_shape_and_values(self):
        grid = il.calendar_grid([{"mood": "happy", "timestamp": _ts(self.today)},
                                 {"mood": "sad", "timestamp": _ts(self.days_ago(1))}], self.today, weeks=4)
        self.assertEqual((len(grid), {len(c) for c in grid}), (4, {7}))
        last = grid[-1]                                   # 2026-09-26 is a Saturday -> index 5
        self.assertEqual(last[5]["date"], self.today)
        self.assertEqual(last[5]["score"], 1)
        self.assertEqual(last[4]["score"], -1)
        self.assertIsNone(last[6])                        # Sunday is in the future
        self.assertIsNone(last[3]["score"])               # no check-in that day

    def test_sleep_finding_needs_enough_data_and_a_clear_gap(self):
        good = [(self.days_ago(i), "happy") for i in range(1, 4)]
        bad = [(self.days_ago(i), "sad") for i in range(4, 7)]
        sleep = [(self.days_ago(i), 8) for i in range(1, 4)] + [(self.days_ago(i), 5) for i in range(4, 7)]
        found = il.find_insights(self._data(moods=good + bad, sleep=sleep), self.today)
        self.assertTrue(any("slept 7+ hours" in f[2] and "100%" in f[2] and "0%" in f[2] for f in found))
        # too little data -> nothing claimed
        few = il.find_insights(self._data(moods=good[:2], sleep=sleep[:2]), self.today)
        self.assertFalse(any("slept" in f[2] for f in few))
        # no real difference -> nothing claimed
        same = il.find_insights(self._data(moods=[(self.days_ago(i), "happy") for i in range(1, 7)],
                                           sleep=[(self.days_ago(i), 8 if i % 2 else 5) for i in range(1, 7)]), self.today)
        self.assertFalse(any("slept" in f[2] for f in same))

    def test_movement_finding(self):
        active = [self.days_ago(i) for i in (1, 2, 3)]
        moods = [(d, "happy") for d in active] + [(self.days_ago(i), "sad") for i in (4, 5, 6)]
        found = il.find_insights(self._data(moods=moods, exercises=active), self.today)
        self.assertTrue(any("exercise session" in f[2] for f in found))

    def test_meal_trend_and_consistency_findings(self):
        meals = [(self.days_ago(1), 500, 9), (self.days_ago(2), 500, 8), (self.days_ago(8), 500, 4), (self.days_ago(9), 500, 5)]
        moods = [(self.days_ago(i), "calm") for i in range(0, 5)]
        found = il.find_insights(self._data(moods=moods, meals=meals), self.today)
        texts = " | ".join(f[2] for f in found)
        self.assertIn("more balanced this week", texts)
        self.assertIn("checked in on 5 of the last 14 days", texts)

    def test_findings_are_capped_and_heavy_mood_note_comes_first(self):
        moods = [(self.days_ago(i), "stressed") for i in range(6)]
        found = il.find_insights(self._data(moods=moods), self.today)
        self.assertEqual(found[0][1], "warn")
        self.assertLessEqual(len(found), 4)

    def test_no_data_no_findings(self):
        self.assertEqual(il.find_insights(self._data(), self.today), [])


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.tmp.name) / "t.db")
        self.uid = self.db.create_user("A", "a@b.co")

    def tearDown(self):
        self.db.conn.close()
        self.tmp.cleanup()

    def test_habits_toggle_and_streak_data(self):
        t = date.today()
        self.assertTrue(self.db.toggle_habit(self.uid, "exercise", t))
        self.assertFalse(self.db.toggle_habit(self.uid, "exercise", t))
        self.db.toggle_habit(self.uid, "exercise", t)
        self.db.toggle_habit(self.uid, "exercise", t - timedelta(1))
        self.assertEqual(self.db.get_habit_days(self.uid, "exercise"), {t, t - timedelta(1)})

    def test_manual_exercise_entries(self):
        self.db.add_exercise_session(self.uid, "box_breathing", "Box Breathing")          # guided: 3 arguments, as before
        when = int((time.time() - 3 * 86400) * 1000)
        sid = self.db.add_exercise_session(self.uid, "manual", "Evening walk", timestamp_ms=when,
                                           duration_min=45, source="manual")
        rows = {r["exercise_name"]: r for r in self.db.get_exercise_history(self.uid)}
        self.assertEqual((rows["Evening walk"]["timestamp"], rows["Evening walk"]["duration_min"],
                          rows["Evening walk"]["source"]), (when, 45, "manual"))
        self.assertEqual((rows["Box Breathing"]["duration_min"], rows["Box Breathing"]["source"]), (None, None))
        self.db.delete_exercise_session(sid)
        self.assertEqual([r["exercise_name"] for r in self.db.get_exercise_history(self.uid)], ["Box Breathing"])

    def test_old_database_is_migrated_without_losing_rows(self):
        import sqlite3
        old = Path(self.tmp.name) / "old.db"
        conn = sqlite3.connect(old)      # a database as an older version of the app made it
        conn.executescript("""
            CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE);
            CREATE TABLE exercise_sessions (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, exercise_id TEXT NOT NULL,
                exercise_name TEXT NOT NULL, timestamp INTEGER NOT NULL);
            CREATE TABLE nutrition_history (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, foods TEXT,
                calories_estimate INTEGER, balance_score INTEGER, mood_impact TEXT, timestamp INTEGER NOT NULL);
            INSERT INTO users (name, email) VALUES ('Old', 'old@example.com');
            INSERT INTO exercise_sessions (user_id, exercise_id, exercise_name, timestamp) VALUES (1, 'x', 'Old session', 1);
            INSERT INTO nutrition_history (user_id, foods, calories_estimate, balance_score, timestamp) VALUES (1, 'old meal', 400, 6, 1);
        """)
        conn.commit()
        conn.close()
        migrated = Database(old)
        try:
            self.assertEqual(migrated.get_exercise_history(1)[0]["exercise_name"], "Old session")
            self.assertIsNone(migrated.get_exercise_history(1)[0]["duration_min"])
            self.assertEqual(migrated.get_nutrition_history(1)[0]["foods"], "old meal")
            self.assertIsNone(migrated.get_nutrition_history(1)[0]["protein"])
            Database(old).conn.close()     # opening again is harmless
        finally:
            migrated.conn.close()

    def test_sleep_upsert(self):
        t = date.today()
        self.db.log_sleep(self.uid, t, 7.5, 4)
        self.db.log_sleep(self.uid, t, 6.0, 2)
        self.assertEqual(self.db.get_sleep(self.uid, t), {"hours": 6.0, "quality": 2})
        self.assertEqual(len(self.db.get_sleep_history(self.uid)), 1)

    def test_week_summary_and_activity_days(self):
        t = date.today()
        self.db.add_mood_entry(self.uid, "happy")
        self.db.toggle_habit(self.uid, "hydration", t)
        self.db.log_sleep(self.uid, t, 6.0, 3)
        week = self.db.get_week_summary(self.uid, t - timedelta(6))
        self.assertEqual((week["checkins"], week["habits"], week["sleep_avg"]), (1, 1, 6.0))
        self.assertEqual(self.db.get_week_summary(self.uid, t - timedelta(13))["checkins"], 0)
        self.assertIn(t, self.db.get_activity_days(self.uid))

    def test_settings_chat_and_export(self):
        self.db.set_setting("theme", "dark")
        self.assertEqual(self.db.get_setting("theme"), "dark")
        self.db.add_chat_message(self.uid, "user", "hi", "calm")
        self.assertEqual(len(self.db.get_chat_messages(self.uid)), 1)
        exported = self.db.export_all(self.uid)
        for key in ("user", "profile", "mood_history", "journal_entries", "chat_messages", "habit_log", "sleep_log"):
            self.assertIn(key, exported)


class OnboardingTests(unittest.TestCase):
    """The welcome / sign-up / sign-in screens and the 5-step profile wizard."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.tmp.name) / "t.db")
        data.apply_theme("light")
        _app.setStyleSheet(styles.build_stylesheet())
        from ui.onboarding import OnboardingWidget
        self.ob = OnboardingWidget(self.db)
        self.ob.resize(1240, 800)
        self.ob.show()
        self.logged_in = []
        self.ob.login_completed.connect(self.logged_in.append)

    def tearDown(self):
        self.ob.close()
        _app.processEvents()
        self.db.conn.close()
        self.tmp.cleanup()

    def _sign_up(self, name="Priya", email="priya@example.com", password="secret123"):
        self.ob.su_name.setText(name)
        self.ob.su_email.setText(email)
        self.ob.su_password.setText(password)
        self.ob._handle_signup()

    def test_signup_validation_shows_inline_errors_and_creates_nothing(self):
        self.ob._handle_signup()
        for err in (self.ob.su_name_err, self.ob.su_email_err, self.ob.su_password_err):
            self.assertFalse(err.isHidden())
        self._sign_up(email="not-an-email", password="123")
        self.assertIn("valid email", self.ob.su_email_err.text())
        self.assertIn("6 characters", self.ob.su_password_err.text())
        self.assertIsNone(self.db.get_user_by_email("not-an-email"))
        self.assertIs(self.ob.stack.currentWidget(), self.ob.welcome_page)   # never left the first page

    def test_duplicate_email_is_refused(self):
        self.db.create_user("Existing", "priya@example.com")
        self._sign_up()
        self.assertFalse(self.ob.su_error.isHidden())
        self.assertIn("already exists", self.ob.su_error.text())

    def test_wizard_gates_and_completes(self):
        self._sign_up()
        self.assertIs(self.ob.stack.currentWidget(), self.ob.wizard_page)
        # step 1 needs a country
        self.assertFalse(self.ob.next_btn.isEnabled())
        self.ob._wizard_next()
        self.assertEqual(self.ob.step_index, 0)
        self.ob._pick_country("IN", self.ob._country_flow.itemAt(4).widget())
        self.assertTrue(self.ob.next_btn.isEnabled())
        self.ob._wizard_next()
        # step 2 needs an age group
        self.assertFalse(self.ob.next_btn.isEnabled())
        self.ob._pick_age("25-34")
        self.ob._wizard_next()
        # step 3: a listed condition plus a custom one, then remove the custom one again
        self.ob._toggle("conditions", "anxiety")
        self.ob.custom_condition_input.setText("Migraine aura")
        self.ob._add_custom_condition()
        self.assertIn("Migraine aura", self.ob.profile["conditions"])
        chip = self.ob._conditions_flow.itemAt(self.ob._conditions_flow.count() - 1).widget()
        chip.click()
        self.assertNotIn("Migraine aura", self.ob.profile["conditions"])
        self.ob.custom_condition_input.setText("Asthma attacks")
        self.ob._add_custom_condition()
        self.ob._wizard_next()
        # step 4 habits
        self.ob._toggle("habits", "exercise")
        self.ob._wizard_next()
        # step 5: at most three goals
        for goal in ("reduce_stress", "better_sleep", "boost_mood", "mindfulness"):
            self.ob._toggle_goal(goal)
        self.assertEqual(len(self.ob.profile["goals"]), 3)
        self.assertNotIn("mindfulness", self.ob.profile["goals"])
        disabled = [g for g, c in self.ob._goal_chips.items() if not c.isEnabled()]
        self.assertEqual(len(disabled), 5)                      # the other 5 are greyed out
        self.ob._toggle_goal("boost_mood")                       # un-tick one -> the rest unlock
        self.assertTrue(all(c.isEnabled() for c in self.ob._goal_chips.values()))
        self.ob._toggle_goal("boost_mood")
        self.ob._wizard_next()                                   # finish

        uid = self.db.get_user_by_email("priya@example.com")["id"]
        self.assertEqual(self.logged_in, [uid])
        profile = self.db.get_profile(uid)
        self.assertEqual((profile["country"], profile["age_group"]), ("IN", "25-34"))
        self.assertEqual(profile["conditions"], ["anxiety", "Asthma attacks"])
        self.assertEqual(profile["habits"], ["exercise"])
        self.assertEqual(profile["goals"], ["reduce_stress", "better_sleep", "boost_mood"])
        self.assertEqual(self.db.get_session_user_id(), uid)

    def test_back_button_keeps_answers(self):
        self._sign_up()
        self.ob._pick_country("IN", self.ob._country_flow.itemAt(4).widget())
        self.ob._wizard_next()
        self.ob._pick_age("35-44")
        self.ob._wizard_back()
        self.assertEqual(self.ob.step_index, 0)
        checked = [self.ob._country_flow.itemAt(i).widget().isChecked() for i in range(self.ob._country_flow.count())]
        self.assertEqual(sum(checked), 1)
        self.assertEqual(self.ob.profile["age_group"], "35-44")

    def test_country_search_filters(self):
        self._sign_up()
        self.ob.country_search.setText("ind")
        self.assertEqual(self.ob._country_flow.count(), 1)
        self.ob.country_search.setText("zzz")
        self.assertEqual(self.ob._country_flow.count(), 1)      # the "no country matches" note
        self.assertNotIsInstance(self.ob._country_flow.itemAt(0).widget(), type(self.ob._language_chips[0]))
        self.ob.country_search.setText("")
        self.assertEqual(self.ob._country_flow.count(), len(data.COUNTRIES))

    def test_returning_user_skips_the_wizard(self):
        uid = self.db.create_user("Priya", "priya@example.com")
        self.db.save_profile(uid, "IN", "en", "25-34", [], [], ["reduce_stress"])
        self.ob._show_page(self.ob.signin_page)
        self.ob.si_email.setText("PRIYA@example.com")            # case-insensitive
        self.ob.si_password.setText("anything")
        self.ob._handle_signin()
        self.assertEqual(self.logged_in, [uid])
        self.assertIs(self.ob.stack.currentWidget(), self.ob.signin_page)   # no wizard shown

    def test_unfinished_signup_resumes_the_wizard(self):
        self.db.create_user("Priya", "priya@example.com")        # signed up, never answered the questions
        self.ob.si_email.setText("priya@example.com")
        self.ob.si_password.setText("x")
        self.ob._handle_signin()
        self.assertEqual(self.logged_in, [])
        self.assertIs(self.ob.stack.currentWidget(), self.ob.wizard_page)

    def test_unknown_email_offers_to_create_account_instead_of_making_one(self):
        self.ob.si_email.setText("nobody@example.com")
        self.ob.si_password.setText("secret1")
        self.ob._handle_signin()
        self.assertFalse(self.ob.si_error.isHidden())
        self.assertFalse(self.ob.si_create_link.isHidden())
        self.assertIsNone(self.db.get_user_by_email("nobody@example.com"))   # nothing was created silently
        self.ob.si_create_link.click()
        self.assertIs(self.ob.stack.currentWidget(), self.ob.signup_page)
        self.assertEqual(self.ob.su_email.text(), "nobody@example.com")

    def test_reset_clears_forms(self):
        self._sign_up(email="bad", password="1")
        self.ob.reset_to_welcome()
        self.assertEqual((self.ob.su_name.text(), self.ob.su_email.text()), ("", ""))
        self.assertTrue(self.ob.su_email_err.isHidden())
        self.assertIs(self.ob.stack.currentWidget(), self.ob.welcome_page)

    def test_responsive_layout(self):
        self.ob.resize(1240, 800)
        self.assertFalse(self.ob.hero.isHidden())
        self.assertTrue(320 <= self.ob.stack.width() <= 500)
        self.ob.resize(700, 800)
        self.assertTrue(self.ob.hero.isHidden())                 # narrow window: form only
        self.assertTrue(320 <= self.ob.stack.width() <= 500)

    def test_dark_theme_builds(self):
        from ui.onboarding import OnboardingWidget
        data.apply_theme("dark")
        try:
            _app.setStyleSheet(styles.build_stylesheet())
            dark = OnboardingWidget(self.db)
            dark.resize(1240, 800)
            dark.show()
            self.assertIn(data.DARK_COLORS["primary"], dark.hero.styleSheet())
            dark.close()
        finally:
            data.apply_theme("light")


class NutritionTabTests(unittest.TestCase):
    """The Nutrition page, with the vision model replaced by canned answers."""

    ANSWER = ("Here you go:\n```json\n{'foods': ['dal', 'rice'], 'calories': '520 kcal', 'nutrients': "
              "{'Protein': '22 g', 'Carbohydrates': 80, 'Fat': 12, 'Fiber': 9}, 'mood_impact': 'steady energy', "
              "'recommendation': 'add greens', 'balance_score': '8/10',}\n```")

    def setUp(self):
        from ui.tabs.nutrition_tab import NutritionTab
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.tmp.name) / "t.db")
        self.uid = self.db.create_user("T", "t@example.com")
        data.apply_theme("light")
        _app.setStyleSheet(styles.build_stylesheet())
        self.tab = NutritionTab(self.db, self.uid, lambda: {"provider": "ollama", "base_url": "x",
                                                              "chat_model": "m", "vision_model": "llava"})
        self.tab.resize(1000, 900)
        self.tab.show()
        self.photo = Path(self.tmp.name) / "meal.png"
        cv2.imwrite(str(self.photo), np.full((300, 400, 3), 120, dtype="uint8"))

    def tearDown(self):
        self.tab.close()
        self.db.conn.close()
        self.tmp.cleanup()

    def _analyse_with(self, answer=None, error=None):
        self.tab._load_path(str(self.photo))
        patcher = mock.patch("ui.tabs.nutrition_tab.vision_ai", side_effect=error) if error else \
            mock.patch("ui.tabs.nutrition_tab.vision_ai", return_value=answer)
        with patcher:
            self.tab._analyse()
            self.tab._worker.wait(10000)
            for _ in range(20):
                _app.processEvents()

    def _stat_values(self):
        from ui.widgets import StatCard
        return [c.value_label.text() for c in self.tab.findChildren(StatCard)]

    def test_starts_empty_with_analyse_disabled(self):
        self.assertFalse(self.tab.analyse_btn.isEnabled())
        self.assertEqual(self.tab.results.currentIndex(), 0)
        self.assertEqual(self._stat_values(), ["-", "0", "-"])

    def test_messy_model_answer_is_saved_shown_and_counted(self):
        self._analyse_with(self.ANSWER)
        meals = self.db.get_nutrition_history(self.uid)
        self.assertEqual(len(meals), 1)
        m = meals[0]
        self.assertEqual((m["foods"], m["calories_estimate"], m["balance_score"]), ("dal, rice", 520, 8))
        self.assertEqual((m["protein"], m["carbs"], m["fat"], m["fibre"]), (22.0, 80.0, 12.0, 9.0))
        self.assertEqual((m["mood_impact"], m["recommendation"]), ("steady energy", "add greens"))
        self.assertEqual(self.tab.results.currentIndex(), 2)                       # results page shown
        self.assertEqual(self._stat_values(), ["520", "1", "8.0/10"])              # today's totals updated
        self.assertEqual(self.tab.error_label.text(), "")
        self.assertTrue(self.tab.analyse_btn.isEnabled() and self.tab.pick_btn.isEnabled())

    def test_unusable_answer_saves_nothing_and_says_so(self):
        self._analyse_with("Sorry, I can't tell what this is.")
        self.assertEqual(self.db.get_nutrition_history(self.uid), [])
        self.assertIn("didn't return a meal analysis", self.tab.error_label.text())
        self.assertEqual(self.tab.results.currentIndex(), 0)
        self.assertTrue(self.tab.analyse_btn.isEnabled())                          # can try again

    def test_model_unreachable_gives_a_helpful_message(self):
        self._analyse_with(error=RuntimeError("Connection refused"))
        self.assertIn("Couldn't reach the vision model", self.tab.error_label.text())
        self.assertEqual(self.db.get_nutrition_history(self.uid), [])

    def test_partial_answer_still_works(self):
        self._analyse_with('{"foods": ["toast"], "balance_score": 6}')             # no calories, no macros
        m = self.db.get_nutrition_history(self.uid)[0]
        self.assertEqual((m["foods"], m["calories_estimate"], m["protein"]), ("toast", None, None))
        self.assertEqual(self.tab.results.currentIndex(), 2)

    def test_delete_a_meal(self):
        from PySide6.QtWidgets import QPushButton
        self.db.add_nutrition_entry(self.uid, "pizza", 800, 4, "heavy")
        self.tab.refresh()
        delete = [b for b in self.tab.findChildren(QPushButton) if b.toolTip().startswith("Remove this meal")]
        self.assertEqual(len(delete), 1)
        delete[0].click()
        self.assertEqual(self.db.get_nutrition_history(self.uid), [])
        self.assertEqual(self._stat_values(), ["-", "0", "-"])

    def test_dropping_a_photo_loads_it(self):
        self.tab.drop.file_dropped.emit(str(self.photo))
        self.assertTrue(self.tab.analyse_btn.isEnabled())
        self.assertIsNotNone(self.tab.image_base64)
        self.tab.drop.file_dropped.emit(str(Path(self.tmp.name) / "missing.png"))   # a bad drop explains itself
        self.assertFalse(self.tab.analyse_btn.isEnabled())
        self.assertIn("no longer exists", self.tab.error_label.text())


class InsightsTabTests(unittest.TestCase):
    def setUp(self):
        from ui.tabs.insights_tab import InsightsTab
        self.InsightsTab = InsightsTab
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.tmp.name) / "t.db")
        self.uid = self.db.create_user("T", "t@example.com")
        data.apply_theme("light")
        _app.setStyleSheet(styles.build_stylesheet())

    def tearDown(self):
        self.db.conn.close()
        self.tmp.cleanup()

    def _seed(self):
        now = time.time()
        for days_ago, mood in ((1, "happy"), (2, "calm"), (3, "stressed"), (4, "happy"), (40, "sad"), (41, "sad")):
            self.db.conn.execute("INSERT INTO mood_history (user_id, mood, timestamp) VALUES (?,?,?)",
                                 (self.uid, mood, int((now - days_ago * 86400) * 1000)))
        self.db.conn.commit()
        self.db.log_sleep(self.uid, date.today() - timedelta(1), 7.5, 4)
        self.db.toggle_habit(self.uid, "exercise", date.today())
        self.db.add_nutrition_entry(self.uid, "dal", 500, 8, "ok", protein=20, carbs=60, fat=10, fibre=5)

    def _tab(self):
        tab = self.InsightsTab(self.db, self.uid, {"habits": ["exercise", "hydration"]})
        tab.resize(1000, 900)
        tab.show()
        return tab

    def _texts(self, tab):
        from PySide6.QtWidgets import QLabel
        return " | ".join(l.text() for l in tab.findChildren(QLabel))

    def _kpis(self, tab):
        from ui.widgets import StatCard
        return [c.value_label.text() for c in tab.findChildren(StatCard)]

    def test_empty_state(self):
        tab = self._tab()
        self.assertIn("Your insights will appear here", self._texts(tab))
        self.assertEqual(self._kpis(tab), [])
        tab.close()

    def test_full_page_with_data(self):
        self._seed()
        tab = self._tab()
        text = self._texts(tab)
        for section in ("What we noticed", "Mood mix", "Mood trend", "Mood calendar", "Best days of the week", "Sleep",
                        "Habit consistency", "Nutrition", "Calories per day", "Macros", "Exercises", "Journal"):
            self.assertIn(section, text, section)
        self.assertEqual(len(self._kpis(tab)), 4)
        tab.close()

    def test_range_pills_change_the_numbers(self):
        self._seed()
        tab = self._tab()
        self.assertEqual(tab.range_days, 30)
        self.assertEqual(self._kpis(tab)[0], "4")                # 4 check-ins in the last 30 days
        tab.range_buttons[None].click()                          # all time -> includes the two 40-day-old ones
        self.assertEqual(tab.range_days, None)
        self.assertEqual(self._kpis(tab)[0], "6")
        self.assertTrue(tab.range_buttons[None].isChecked())
        tab.range_buttons[7].click()
        self.assertEqual((tab.range_days, self._kpis(tab)[0]), (7, "4"))
        tab.close()

    def test_refresh_after_new_data(self):
        self._seed()
        tab = self._tab()
        self.db.add_mood_entry(self.uid, "happy")
        tab.refresh()
        self.assertEqual(self._kpis(tab)[0], "5")
        tab.close()

    def _sections(self, tab):
        from ui.widgets import CollapsibleSection
        return {s.title_label.text(): s for s in tab.findChildren(CollapsibleSection)}

    def test_calories_macros_and_weekday_are_dropdowns_closed_by_default(self):
        self._seed()
        tab = self._tab()
        sections = self._sections(tab)
        self.assertEqual(set(sections), {"Best days of the week", "Sleep", "Calories per day", "Macros"})
        for name, section in sections.items():
            self.assertFalse(section.is_open(), name)
            self.assertTrue(section.body.isHidden(), name)                       # content hidden...
            self.assertFalse(section.summary_label.isHidden(), name)             # ...but a one-line summary shows
        self.assertIn("Average 500 kcal", sections["Calories per day"].summary_label.text())
        self.assertIn("20 g protein", sections["Macros"].summary_label.text())
        tab.close()

    def test_sleep_lives_inside_the_calendar_card_as_a_dropdown(self):
        from PySide6.QtWidgets import QLabel
        self._seed()
        tab = self._tab()
        sleep = self._sections(tab)["Sleep"]
        self.assertFalse(sleep.is_open())
        self.assertIn("Average 7.5 h", sleep.summary_label.text())               # summary while closed
        text = self._texts(tab)
        self.assertLess(text.index("Mood calendar"), text.index("Best days of the week"))
        self.assertLess(text.index("Best days of the week"), text.index("Sleep"))
        # 'Sleep' appears once - as the dropdown's title - not as a separate top-level card
        self.assertEqual(sum(1 for l in tab.findChildren(QLabel) if l.text() == "Sleep"), 1)
        # and it sits in the same card as the calendar
        calendar_card = sleep.parentWidget()
        while calendar_card is not None and "Mood calendar" not in " ".join(
                l.text() for l in calendar_card.findChildren(QLabel)[:3]):
            calendar_card = calendar_card.parentWidget()
        self.assertIsNotNone(calendar_card)
        tab.close()

    def test_habit_consistency_is_compact(self):
        from PySide6.QtWidgets import QProgressBar
        self._seed()
        tab = self._tab()
        text = self._texts(tab)
        self.assertIn("Habit consistency", text)
        self.assertNotIn("Share of days each habit was ticked", text)            # the old long subtitle is gone
        slim = [b for b in tab.findChildren(QProgressBar) if b.maximumHeight() == 6]
        self.assertEqual(len(slim), 2)                                            # one slim bar per habit (exercise, hydration)
        self.assertIn("1/30", text)                                               # short "ticked/days" value
        tab.close()

    def test_dropdown_opens_closes_and_remembers(self):
        self._seed()
        tab = self._tab()
        calories = self._sections(tab)["Calories per day"]
        calories.header.clicked.emit()
        self.assertTrue(calories.is_open())
        self.assertFalse(calories.body.isHidden())
        self.assertTrue(calories.summary_label.isHidden())                       # summary hides while open
        self.assertEqual(self.db.get_setting("insights_open"), "calories")
        tab.set_range(7)                                                          # a refresh keeps it open
        self.assertTrue(self._sections(tab)["Calories per day"].is_open())
        tab.close()
        again = self._tab()                                                       # ...and so does reopening the page
        self.assertTrue(self._sections(again)["Calories per day"].is_open())
        self.assertFalse(self._sections(again)["Macros"].is_open())
        self._sections(again)["Calories per day"].header.clicked.emit()
        self.assertEqual(self.db.get_setting("insights_open"), "")
        again.close()

    def test_weekday_dropdown_sits_under_the_calendar_with_streaks(self):
        self._seed()
        tab = self._tab()
        text = self._texts(tab)
        self.assertLess(text.index("Mood calendar"), text.index("Best days of the week"))
        self.assertLess(text.index("Best days of the week"), text.index("Sleep"))
        self.assertIn("day streak", text)
        self.assertIn("longest streak", text)
        tab.close()

    def _add_with(self, tab, result):
        class StubDialog:
            def __init__(self, parent=None):
                self.result = result

            def exec(self):
                return 1 if result else 0

        with mock.patch("ui.exercise_dialog.AddExerciseDialog", StubDialog):
            tab.add_exercise_btn.click()

    def test_add_exercise_manually(self):
        from datetime import datetime
        self._seed()
        tab = self._tab()
        self.assertIn("0 sessions", self._texts(tab))
        when = datetime.now() - timedelta(days=2)
        self._add_with(tab, {"name": "Evening walk", "when": when, "minutes": 45})
        row = self.db.get_exercise_history(self.uid)[0]
        self.assertEqual((row["exercise_name"], row["duration_min"], row["source"]), ("Evening walk", 45, "manual"))
        self.assertEqual(datetime.fromtimestamp(row["timestamp"] / 1000).date(), when.date())   # backdated correctly
        text = self._texts(tab)
        self.assertIn("1 session  ·  45 min logged", text)
        self.assertIn("Evening walk", text)
        self.assertIn("added by you", text)
        self._add_with(tab, None)                                                # cancelled -> nothing new
        self.assertEqual(len(self.db.get_exercise_history(self.uid)), 1)
        tab.close()

    def test_delete_an_exercise_entry(self):
        from PySide6.QtWidgets import QPushButton
        self._seed()
        self.db.add_exercise_session(self.uid, "manual", "Yoga", duration_min=30, source="manual")
        tab = self._tab()
        buttons = [b for b in tab.findChildren(QPushButton) if b.toolTip() == "Remove this entry"]
        self.assertEqual(len(buttons), 1)
        buttons[0].click()
        self.assertEqual(self.db.get_exercise_history(self.uid), [])
        self.assertIn("0 sessions", self._texts(tab))
        tab.close()

    def test_manual_exercise_counts_towards_findings(self):
        self._seed()
        # three good-mood days with a manual walk, three heavy days without -> the movement finding appears
        for i in (1, 2, 3):
            self.db.add_exercise_session(self.uid, "manual", "Walk", timestamp_ms=int((time.time() - i * 86400) * 1000),
                                         duration_min=30, source="manual")
        for i in (11, 12, 13):
            self.db.conn.execute("INSERT INTO mood_history (user_id, mood, timestamp) VALUES (?,?,?)",
                                 (self.uid, "sad", int((time.time() - i * 86400) * 1000)))
        self.db.conn.commit()
        tab = self._tab()
        self.assertIn("exercise session", self._texts(tab))
        tab.close()

    def test_dark_theme_renders(self):
        self._seed()
        data.apply_theme("dark")
        try:
            _app.setStyleSheet(styles.build_stylesheet())
            tab = self._tab()
            self.assertFalse(tab.grab().isNull())
            tab.close()
        finally:
            data.apply_theme("light")


class AddExerciseDialogTests(unittest.TestCase):
    def setUp(self):
        from ui.exercise_dialog import AddExerciseDialog
        data.apply_theme("light")
        _app.setStyleSheet(styles.build_stylesheet())
        self.dialog = AddExerciseDialog()
        self.dialog.show()

    def tearDown(self):
        self.dialog.close()

    def test_needs_an_activity_name(self):
        self.assertEqual(self.dialog.activity.currentText(), "")                  # starts empty
        self.dialog.save_btn.click()
        self.assertIsNone(self.dialog.result)
        self.assertFalse(self.dialog.error.isHidden())

    def test_offers_common_and_guided_activities_and_accepts_custom_text(self):
        items = [self.dialog.activity.itemText(i) for i in range(self.dialog.activity.count())]
        self.assertIn("Walking", items)
        self.assertIn("Box Breathing", items)                                     # the app's own exercises too
        self.dialog.activity.setEditText("  Salsa class ")
        self.dialog.minutes.setValue(75)
        self.dialog.save_btn.click()
        self.assertEqual((self.dialog.result["name"], self.dialog.result["minutes"]), ("Salsa class", 75))

    def test_cannot_pick_a_future_time(self):
        from datetime import datetime
        self.dialog.activity.setEditText("Run")
        self.dialog.when.setDateTime(self.dialog.when.dateTime().addDays(5))
        self.dialog.save_btn.click()
        self.assertLessEqual(self.dialog.result["when"], datetime.now())


class ChartTests(unittest.TestCase):
    """Every chart must paint without error whatever it is given - empty, tiny or large."""

    def test_nice_max(self):
        from ui.charts import nice_max
        self.assertEqual([nice_max(v) for v in (0, 0.7, 37, 830, 1900)], [1, 0.8, 40, 1000, 2000])

    def test_all_charts_paint_in_both_themes(self):
        from ui.charts import BarChart, DonutChart, LineChart, MoodCalendar, RingGauge
        for theme in ("light", "dark"):
            data.apply_theme(theme)
            try:
                bar = BarChart()
                for bars in ([], [{"label": "a", "value": 0}], [{"label": str(i), "value": i * 3.3, "tooltip": "t"} for i in range(40)]):
                    bar.set_data(bars, band=(7, 9))
                    bar.resize(400, 200)
                    self.assertFalse(bar.grab().isNull())
                line = LineChart()
                for n in (0, 1, 2, 30):
                    line.set_points([{"x": i, "y": (-1) ** i, "label": str(i), "tooltip": ""} for i in range(n)])
                    line.resize(400, 200)
                    self.assertFalse(line.grab().isNull())
                donut = DonutChart()
                for segs in ([], [("a", 0, "#fff")], [("a", 1, "#E07A5F")], [("a", 3, "#E07A5F"), ("b", 1, "#52B788")]):
                    donut.set_segments(segs, "x", "y")
                    donut.resize(400, 170)
                    self.assertFalse(donut.grab().isNull())
                ring = RingGauge()
                for f in (0, 0.5, 1, 7, -3):
                    ring.set_value(f, "8/10", "Great")
                    self.assertFalse(ring.grab().isNull())
                cal = MoodCalendar()
                cal.set_grid([])
                cal.set_grid(il.calendar_grid([], date(2026, 9, 26), 12))
                self.assertFalse(cal.grab().isNull())
            finally:
                data.apply_theme("light")

    def test_bar_hit_testing(self):
        from ui.charts import BarChart
        bar = BarChart()
        bar.resize(450, 200)
        bar.set_data([{"label": str(i), "value": i + 1} for i in range(4)])
        plot = bar._plot()
        slot = plot.width() / 4
        self.assertEqual([bar._bar_at(plot.left() + slot * (i + 0.5)) for i in range(4)], [0, 1, 2, 3])
        self.assertIsNone(bar._bar_at(plot.left() - 5))


class AppTests(unittest.TestCase):
    """Drives the real windows, offscreen, against a temporary database."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.tmp.name) / "t.db")
        self.uid = self.db.create_user("Tester", "t@example.com")
        self.db.save_profile(self.uid, "IN", "en", "25-34", [], ["exercise", "hydration"], ["reduce_stress"])
        self.db.set_session_user_id(self.uid)
        data.apply_theme("light")
        _app.setStyleSheet(styles.build_stylesheet())

        # no real AI server: connection check fails fast, chat replies are a stub
        self.patches = [
            mock.patch("ui.main_window.check_connection", side_effect=ConnectionError("test")),
            mock.patch("ui.tabs.chat_tab.chat_ai", return_value="stub reply"),
        ]
        for p in self.patches:
            p.start()

        import main
        self.win = main.AppWindow(self.db)
        self.mw = self.win.main_widget

    def tearDown(self):
        for p in self.patches:
            p.stop()
        mw = self.win.main_widget
        mw._poll_timer.stop()
        if mw._connection_worker:
            mw._connection_worker.wait(3000)
        self.db.conn.close()
        self.tmp.cleanup()
        data.apply_theme("light")

    def _wait(self, worker):
        if worker:
            worker.wait(10000)
        _app.processEvents()
        for _ in range(5):
            _app.processEvents()

    def test_boots_signed_in_with_nine_pages(self):
        self.assertIsNotNone(self.mw)
        self.assertEqual(self.mw.tabs.count(), 9)
        self.assertEqual(len(self.mw.nav_buttons), 9)
        self.mw.nav_buttons[4].click()
        self.assertIs(self.mw.tabs.currentWidget(), self.mw.journal_tab)

    def test_hinglish_chat_message_is_recorded_as_anxious(self):
        chat = self.mw.chat_tab
        chat._send_text("mujhe dar lagta hain")
        self._wait(chat._worker)
        self.assertEqual(self.db.get_mood_history(self.uid)[-1]["mood"], "anxious")
        roles = [m["role"] for m in self.db.get_chat_messages(self.uid)]
        self.assertEqual(roles, ["user", "assistant"])

    def test_crisis_message_shows_local_helplines(self):
        chat = self.mw.chat_tab
        chat._send_text("I just want to die")
        self._wait(chat._worker)
        self.assertFalse(chat.crisis_banner.isHidden())
        self.assertTrue("iCall" in chat.crisis_text.text() or "Vandrevala" in chat.crisis_text.text())

    def test_nutrition_photo_picker_loads_or_explains(self):
        nutrition = self.mw.nutrition_tab
        d = Path(self.tmp.name)
        good, bad = d / "meal.png", d / "broken.jpg"
        cv2.imwrite(str(good), np.full((200, 300, 3), 90, dtype="uint8"))
        bad.write_text("not an image")

        with mock.patch("ui.tabs.nutrition_tab.QFileDialog.getOpenFileName", return_value=(str(good), "")):
            nutrition._pick_image()
        self.assertTrue(nutrition.analyse_btn.isEnabled())
        self.assertIsNotNone(nutrition.image_base64)
        self.assertEqual(nutrition.error_label.text(), "")

        with mock.patch("ui.tabs.nutrition_tab.QFileDialog.getOpenFileName", return_value=(str(bad), "")):
            nutrition._pick_image()
        self.assertFalse(nutrition.analyse_btn.isEnabled())
        self.assertIn("Couldn't read this image", nutrition.error_label.text())

    def test_camera_button_opens_dialog_and_logged_mood_reaches_chat(self):
        result = {"mood": "anxious", "fer_label": "fear", "confidence": 0.8, "frames": 5, "preview": None}

        class StubDialog:
            def __init__(self, parent=None):
                self.mood_selected = mock.Mock()
                self.opened = False

            def exec(self):
                self.opened = True

        dialogs = []

        def make(parent=None):
            d = StubDialog(parent)
            dialogs.append(d)
            return d

        chat = self.mw.chat_tab
        with mock.patch("ui.tabs.chat_tab.CameraDialog", make):
            chat.camera_btn.click()
        self.assertTrue(dialogs and dialogs[0].opened)                  # button opens the live window
        dialogs[0].mood_selected.connect.assert_called_once_with(chat._on_face_mood)
        chat._on_face_mood(result)                                       # what the window emits on "Log this mood"
        self.assertEqual(self.db.get_mood_history(self.uid)[-1]["mood"], "anxious")
        self.assertIn("Anxious", chat.mood_badge.text())

    def test_exercises_page_can_log_and_remove_your_own_exercise(self):
        from datetime import datetime
        from PySide6.QtWidgets import QLabel, QPushButton
        page = self.mw.exercises_tab
        self.assertIn("Nothing yet", " ".join(l.text() for l in page.findChildren(QLabel)))

        class StubDialog:
            def __init__(self, parent=None):
                self.result = {"name": "Evening walk", "when": datetime.now() - timedelta(days=1), "minutes": 45}

            def exec(self):
                return 1

        with mock.patch("ui.exercise_dialog.AddExerciseDialog", StubDialog):
            page.add_exercise_btn.click()
        row = self.db.get_exercise_history(self.uid)[0]
        self.assertEqual((row["exercise_name"], row["duration_min"], row["source"]), ("Evening walk", 45, "manual"))
        self.assertIn("Logged Evening walk", page.logged_label.text())
        self.assertFalse(page.logged_label.isHidden())
        labels = " ".join(l.text() for l in page.findChildren(QLabel))
        self.assertIn("Evening walk", labels)
        self.assertIn("added by you", labels)
        [b for b in page.findChildren(QPushButton) if b.toolTip() == "Remove this entry"][0].click()
        self.assertEqual(self.db.get_exercise_history(self.uid), [])
        self.assertIn("Nothing yet", " ".join(l.text() for l in page.findChildren(QLabel)))

    def test_exercises_page_shows_entries_added_elsewhere_when_opened(self):
        from PySide6.QtWidgets import QLabel
        self.db.add_exercise_session(self.uid, "manual", "Yoga class", duration_min=60, source="manual")
        self.mw.tabs.setCurrentWidget(self.mw.exercises_tab)
        self.assertIn("Yoga class", " ".join(l.text() for l in self.mw.exercises_tab.findChildren(QLabel)))

    def _send_and_capture_prompt(self, text="hello"):
        prompts = []
        chat = self.mw.chat_tab
        with mock.patch("ui.tabs.chat_tab.chat_ai", side_effect=lambda cfg, msgs, prompt: prompts.append(prompt) or "ok"):
            chat._send_text(text)
            self._wait(chat._worker)
        return prompts[-1]

    def test_reply_language_can_be_changed_and_reaches_the_model(self):
        chat = self.mw.chat_tab
        self.assertEqual(chat.language, "auto")                                   # English profile -> match what I write
        self.assertEqual(chat.language_combo.currentData(), "auto")
        self.assertIn("same language the person writes in", self._send_and_capture_prompt())

        chat.language_combo.setCurrentIndex(chat.language_combo.findData("hinglish"))
        self.assertEqual(chat.language, "hinglish")
        self.assertIn("Never use Devanagari", self._send_and_capture_prompt("mujhe dar lagta hai"))

        chat.language_combo.setCurrentIndex(chat.language_combo.findData("es"))
        self.assertIn("Respond entirely in Spanish", self._send_and_capture_prompt("hi again"))
        self.assertIn("Replies will now be in", chat.assist_status.text())

    def test_reply_language_is_remembered_per_user(self):
        chat = self.mw.chat_tab
        chat.language_combo.setCurrentIndex(chat.language_combo.findData("hi"))
        self.assertEqual(self.db.get_setting(f"chat_language_{self.uid}"), "hi")
        from ui.main_window import MainAppWidget
        rebuilt = MainAppWidget(self.db, self.mw.user, self.mw.profile)           # e.g. after a restart or theme switch
        try:
            self.assertEqual(rebuilt.chat_tab.language, "hi")
            self.assertEqual(rebuilt.chat_tab.language_combo.currentData(), "hi")
        finally:
            rebuilt.shutdown()
            if rebuilt._connection_worker:
                rebuilt._connection_worker.wait(3000)
        other = self.db.create_user("Other", "other@example.com")
        self.assertIsNone(self.db.get_setting(f"chat_language_{other}"))          # another user is unaffected

    def test_signup_language_is_the_starting_reply_language(self):
        from ui.tabs.chat_tab import ChatTab
        hindi_profile = {**self.mw.profile, "language": "hi", "name": "T"}
        chat = ChatTab(self.db, self.db.create_user("Hindi", "hindi@example.com"), hindi_profile, lambda: {})
        self.assertEqual((chat.language, chat.language_combo.currentData()), ("hi", "hi"))

    def test_habits_and_sleep_on_today_tab(self):
        home = self.mw.home_tab
        box, _streak = home._habit_boxes["exercise"]
        box.setChecked(True)
        self.assertEqual(self.db.get_habits_done(self.uid, date.today()), {"exercise"})
        home.sleep_hours.setValue(6.5)
        home.sleep_quality.button(3).setChecked(True)
        home._save_sleep()
        self.assertEqual(self.db.get_sleep(self.uid, date.today()), {"hours": 6.5, "quality": 3})

    def test_theme_toggle_persists_and_keeps_page(self):
        self.mw.tabs.setCurrentIndex(5)
        old = self.win.main_widget
        self.mw._toggle_theme()
        self._wait(None)
        self.assertEqual(self.db.get_setting("theme"), "dark")
        self.assertEqual(data.COLORS["bg"], "#1B1714")
        self.assertIsNot(self.win.main_widget, old)
        self.assertEqual(self.win.main_widget.tabs.currentIndex(), 5)
        self.win.main_widget._toggle_theme()
        self.assertEqual(self.db.get_setting("theme"), "light")

    def test_sign_out_keeps_the_account(self):
        self.mw._sign_out()
        self.assertIs(self.win.stack.currentWidget(), self.win.onboarding)
        self.assertIsNone(self.db.get_session_user_id())
        self.assertIsNotNone(self.db.get_profile(self.uid))  # profile survives sign-out


if __name__ == "__main__":
    unittest.main(verbosity=2)
