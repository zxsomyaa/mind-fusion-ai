
"""
Mind Fusion AI — unit tests for the three components written for this project.

These are the tests Section 5.2 of the report describes: exhaustive over the
mood mapper's interesting cases, careful on the fusion engine's margin, and
minimal on the recommendation mapper's contract.

Run:      pytest -v test_components.py
Capture:  pytest -v test_components.py > evidence/pytest.txt 2>&1

--------------------------------------------------------------------------
BEFORE THE FIRST RUN: edit the CONFIG block below so the imports match your
own module and function names. Nothing else needs changing.
--------------------------------------------------------------------------
"""
import importlib
import pytest

# ====================== CONFIG — edit these ===============================

# Where each component lives, as "module:function".
# e.g. "mind_fusion.mood:detect_mood" or "app.core.mood:detect_mood"
MOOD_MAPPER = "mood:detect_mood"
FUSION_ENGINE = "fusion:fuse"
RECOMMENDER = "recommend:get_recommendations"

# One unambiguous phrase per mood, in YOUR lexicon's vocabulary.
# If a test fails here it is a real gap in the lexicon, not a broken test —
# leave the failure in and report it.
PHRASES = {
    "happy":    "I feel really happy today",
    "calm":     "I feel calm and settled",
    "sad":      "I feel sad and low",
    "anxious":  "I feel anxious about tomorrow",
    "stressed": "work has been stressful all week",
    "grateful": "I feel grateful for today",
    "tired":    "I feel tired and worn out",
    "hopeful":  "I feel hopeful about things",
}

# The recommendation mapper's call signature, if it differs from
# get_recommendations(mood, conditions, recent).  Set to None to skip.
RECOMMENDER_CALL = lambda fn, mood, conditions, recent: fn(mood, conditions, recent)

# A condition and a suggestion that must never be offered with it.
CONTRAINDICATION = ("hypertension", "high-intensity")

# ==========================================================================


def _load(spec):
    """Import 'module:function'.  Skips the test cleanly if it is not there."""
    module_name, _, attr = spec.partition(":")
    try:
        module = importlib.import_module(module_name)
    except ImportError as exc:                       # pragma: no cover
        pytest.skip(f"cannot import {module_name!r}: {exc}. Edit CONFIG in this file.")
    if not hasattr(module, attr):                    # pragma: no cover
        pytest.skip(f"{module_name!r} has no {attr!r}. Edit CONFIG in this file.")
    return getattr(module, attr)


@pytest.fixture(scope="module")
def detect_mood():
    return _load(MOOD_MAPPER)


@pytest.fixture(scope="module")
def fuse():
    return _load(FUSION_ENGINE)


@pytest.fixture(scope="module")
def recommend():
    return _load(RECOMMENDER)


# ---------------------------------------------------------------- mood mapper

@pytest.mark.parametrize("expected,phrase", sorted(PHRASES.items()))
def test_each_of_the_eight_moods_is_detected(detect_mood, expected, phrase):
    """TC-F07. Every state in the vocabulary is reachable from plain language."""
    assert detect_mood(phrase)["mood"] == expected


def test_empty_input_returns_calm_at_low_confidence(detect_mood):
    """The empty path returns a default instead of raising."""
    result = detect_mood("")
    assert result["mood"] == "calm"
    assert result["confidence"] == pytest.approx(0.30, abs=0.01)


def test_text_with_no_emotional_vocabulary_returns_the_default(detect_mood):
    """TC-E06. Nothing in the lexicon matches, so nothing is asserted."""
    result = detect_mood("I went to the shop and bought bread and milk")
    assert result["mood"] == "calm"
    assert result["confidence"] <= 0.31


def test_divisor_floor_stops_one_match_reporting_full_confidence(detect_mood):
    """A single incidental hit must not come back at 1.0."""
    result = detect_mood("happy")
    assert result["confidence"] <= 0.34


def test_confidence_is_always_bounded(detect_mood):
    for phrase in list(PHRASES.values()) + ["", "happy happy happy sad sad"]:
        confidence = detect_mood(phrase)["confidence"]
        assert 0.0 <= confidence <= 1.0, phrase


def test_tie_resolution_is_deterministic(detect_mood):
    """Ties fall to dictionary order; the point is that they never vary."""
    tied = "I feel happy and sad at the same time"
    assert detect_mood(tied)["mood"] == detect_mood(tied)["mood"]


@pytest.mark.xfail(reason="documented limitation: substring matching has no "
                          "representation of negation (TC-E01)", strict=False)
def test_negation_is_not_handled(detect_mood):
    assert detect_mood("I am not stressed at all")["mood"] != "stressed"


# -------------------------------------------------------------- fusion engine

def test_single_channel_renormalises_to_its_own_weight(fuse):
    """A typed check-in with no audio or face uses the same function."""
    result = fuse({"text": ("sad", 0.8)})
    assert result["mood"] == "sad"
    assert result["confidence"] == pytest.approx(0.8, abs=0.01)


def test_two_channels_renormalise_over_the_channels_present(fuse):
    result = fuse({"text": ("sad", 0.9), "face": ("sad", 0.9)})
    assert result["mood"] == "sad"
    assert result["confidence"] == pytest.approx(0.9, abs=0.01)


def test_agreeing_channels_are_not_ambiguous(fuse):
    result = fuse({"text": ("anxious", 0.9), "speech": ("anxious", 0.8)})
    assert result["mood"] == "anxious"
    assert result["ambiguous"] is False


def test_disagreement_above_the_margin_resolves(fuse):
    """Gap of 0.121, just above the 0.12 margin: the winner is asserted."""
    result = fuse({"text": ("sad", 1.0), "speech": ("happy", 0.758)})
    assert result["mood"] == "sad"
    assert result["ambiguous"] is False


def test_disagreement_below_the_margin_sets_the_flag(fuse):
    """Gap of 0.119, just below the margin: ask rather than guess."""
    result = fuse({"text": ("sad", 1.0), "speech": ("happy", 0.762)})
    assert result["ambiguous"] is True


def test_the_live_disagreement_from_figure_9_is_flagged(fuse):
    """TC-E13. Text says sad, the camera says happy at 99%."""
    result = fuse({"text": ("sad", 0.5), "face": ("happy", 0.99)})
    assert result["ambiguous"] is True


def test_fused_confidence_is_bounded(fuse):
    result = fuse({"text": ("sad", 1.0), "speech": ("sad", 1.0), "face": ("sad", 1.0)})
    assert 0.0 <= result["confidence"] <= 1.0


def test_empty_channel_set_does_not_raise(fuse):
    fuse({})


# ------------------------------------------------------- recommendation mapper

def test_exactly_three_suggestions_are_returned(recommend):
    """FR7. The count is part of the contract."""
    suggestions = RECOMMENDER_CALL(recommend, "stressed", [], [])
    assert len(suggestions) == 3


def test_contraindicated_suggestions_are_removed(recommend):
    """FR19. A declared condition filters the pool before the user sees it."""
    condition, banned = CONTRAINDICATION
    suggestions = RECOMMENDER_CALL(recommend, "stressed", [condition], [])
    assert not any(banned.lower() in str(s).lower() for s in suggestions)


def test_recent_suggestions_are_not_repeated(recommend):
    first = RECOMMENDER_CALL(recommend, "sad", [], [])
    second = RECOMMENDER_CALL(recommend, "sad", [], list(first))
    assert not set(map(str, first)) & set(map(str, second))


def test_the_same_input_gives_the_same_output(recommend):
    """Determinism is what makes a suggestion auditable."""
    a = RECOMMENDER_CALL(recommend, "anxious", ["hypertension"], [])
    b = RECOMMENDER_CALL(recommend, "anxious", ["hypertension"], [])
    assert list(map(str, a)) == list(map(str, b))

