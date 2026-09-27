"""
Evidence 2 - results log for the mood mappers: expected vs actual.

Regenerate:  python evidence/02_mood_mapper.py > evidence/output/02_mood_mapper_results.txt

The EXPECTED columns are written out here by hand from the design (what each
input is *meant* to map to), independent of the code under test, so a PASS
means the mapper still behaves as designed - it isn't comparing the code with itself.
"""
import os
import sys
from datetime import datetime
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import data                                    # noqa: E402
from face_analysis import FER_LABELS, FER_TO_APP_MOOD   # noqa: E402

passed = failed = 0


def row(*cells, widths):
    print("  ".join(str(c).ljust(w) for c, w in zip(cells, widths)))


def check(ok):
    global passed, failed
    passed += bool(ok)
    failed += not ok
    return "PASS" if ok else "FAIL"


print("Mind Fusion Desktop - mood mapper results log")
print(f"date: {datetime.now():%Y-%m-%d %H:%M:%S}")
print("command: python evidence/02_mood_mapper.py")
print()

# ---------------------------------------------------------------- A: camera -> mood
print("A. Facial-expression category (FER+ model, 8 classes) -> app mood")
print("   code under test: face_analysis.FER_TO_APP_MOOD")
EXPECTED_FER = {                       # from the design: how each expression should be treated
    "neutral": "calm", "happiness": "happy", "surprise": "hopeful", "sadness": "sad",
    "anger": "stressed", "disgust": "stressed", "fear": "anxious", "contempt": "stressed",
}
w = (12, 10, 10, 6)
row("FER label", "expected", "actual", "result", widths=w)
row("-" * 12, "-" * 10, "-" * 10, "-" * 6, widths=w)
for label in FER_LABELS:
    actual = FER_TO_APP_MOOD.get(label)
    row(label, EXPECTED_FER[label], actual, check(actual == EXPECTED_FER[label]), widths=w)
covered = check(set(FER_LABELS) == set(EXPECTED_FER) and all(l in FER_TO_APP_MOOD for l in FER_LABELS))
print(f"   all 8 model classes have a mapping ........ {covered}")
valid = check(all(m in data.MOODS for m in FER_TO_APP_MOOD.values()))
print(f"   every output is a real app mood ............ {valid}")
reachable = set(FER_TO_APP_MOOD.values())
print(f"   app moods reachable from the camera: {sorted(reachable)}")
print(f"   NOT reachable from the camera (text/journal only): {sorted(set(data.MOODS) - reachable)}")
print()

# ---------------------------------------------------------------- B: text -> mood
print("B. Text check-in -> mood (keyword detector), one sentence per mood")
print("   code under test: data.detect_mood")
CASES = [   # (text, expected mood)
    ("I'm so happy today, everything went great", "happy"),
    ("I feel calm and peaceful this evening", "calm"),
    ("I'm feeling really down and lonely", "sad"),
    ("I'm anxious and worried about tomorrow", "anxious"),
    ("I'm overwhelmed, the deadline pressure is too much", "stressed"),
    ("I'm so grateful and thankful for my friends", "grateful"),
    ("I'm exhausted and completely drained", "tired"),
    ("I'm hopeful that things are getting better", "hopeful"),
    # Hindi / Hinglish (Hindi typed in English letters, and in Devanagari)
    ("mujhe dar lagta hain", "anxious"),
    ("main bahut udaas hoon", "sad"),
    ("aaj main bahut khush hoon", "happy"),
    ("मुझे डर लग रहा है", "anxious"),
    # whole-word matching: words that merely CONTAIN a keyword must not trigger it
    ("It is dark outside", "calm"),
    ("please help me", "calm"),
    # nothing recognisable -> the documented default
    ("", "calm"),
]
w = (52, 10, 10, 6, 6)
row("input", "expected", "actual", "conf.", "result", widths=w)
row("-" * 52, "-" * 10, "-" * 10, "-" * 6, "-" * 6, widths=w)
for text, expected in CASES:
    result = data.detect_mood(text)
    shown = (text[:49] + "...") if len(text) > 52 else (text or "(empty)")
    row(shown, expected, result["mood"], f"{result['confidence']:.2f}", check(result["mood"] == expected), widths=w)
print()

# ---------------------------------------------------------------- C: crisis detector
print("C. Crisis-language detector (should be over-cautious: a false alarm is cheap)")
print("   code under test: data.detect_crisis")
CRISIS = [
    ("I want to die", True), ("I'm thinking about suicide", True), ("I keep wanting to hurt myself", True),
    ("mujhe marna chahta hoon", True), ("मैं आत्महत्या के बारे में सोच रहा हूँ", True),
    ("I'm so tired today", False), ("mujhe dar lagta hai", False), ("Work is killing me with deadlines", False),
]
w = (52, 10, 10, 6)
row("input", "expected", "actual", "result", widths=w)
row("-" * 52, "-" * 10, "-" * 10, "-" * 6, widths=w)
for text, expected in CRISIS:
    actual = data.detect_crisis(text)
    row(text, "alert" if expected else "no alert", "alert" if actual else "no alert", check(actual == expected), widths=w)
print()

# ---------------------------------------------------------------- summary
print(f"RESULT: {passed} passed, {failed} failed, out of {passed + failed} checks")
print()

# ---------------------------------------------------------------- known limitations
print("D. Known limitations - shown on purpose, NOT counted as pass/fail above")
print("   The detector matches keywords; it does not understand grammar or tone.")
LIMITS = [
    ("I am not happy at all", "negation: 'happy' is found, 'not' is ignored"),
    ("Oh great, another deadline", "sarcasm: taken literally"),
    ("Ich bin sehr traurig", "a language with no keywords: falls back to 'calm'"),
]
w = (34, 10, 60)
row("input", "detected", "why", widths=w)
row("-" * 34, "-" * 10, "-" * 60, widths=w)
for text, why in LIMITS:
    row(text, data.detect_mood(text)["mood"], why, widths=w)

sys.exit(1 if failed else 0)
