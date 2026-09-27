"""
Turning the vision model's answer about a meal into clean, safe numbers, plus
a few small helpers for the Nutrition page. No Qt in here, so it is easy to test.

Local vision models (llava etc.) are not reliable JSON writers: they wrap the
answer in code fences, use single quotes, put units in numbers ("450 kcal"),
leave trailing commas, rename fields ("fiber"), or give a score of 12/10.
parse_analysis() copes with all of that, and refuses to invent data when the
answer has nothing usable in it.
"""

import ast
import json
import re
from datetime import datetime

NUTRIENT_ALIASES = {
    "protein": ("protein", "proteins"),
    "carbs":   ("carbs", "carb", "carbohydrates", "carbohydrate"),
    "fat":     ("fat", "fats", "total fat"),
    "fibre":   ("fibre", "fiber", "dietary fibre", "dietary fiber"),
}
MAX_FOODS = 12
MAX_CALORIES = 6000   # a single meal above this is almost certainly a model error


def first_number(value):
    """A number from 450, 450.5, "450", or "about 450 kcal"; None if there isn't one."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        match = re.search(r"-?\d+(?:[.,]\d+)?", value)
        if match:
            return float(match.group().replace(",", "."))
    return None


def extract_json_object(raw):
    """Finds the JSON-ish object in the model's text and returns it as a dict.
    Raises ValueError if there isn't one."""
    text = re.sub(r"```(?:json)?", "", raw or "").strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError(f"The model didn't return a meal analysis: {(raw or '')[:100]!r}")
    candidate = text[start:end + 1]
    candidate = re.sub(r",\s*([}\]])", r"\1", candidate)   # trailing commas
    for parser in (json.loads, ast.literal_eval):           # literal_eval handles 'single quotes'
        try:
            obj = parser(candidate)
        except (ValueError, SyntaxError):
            continue
        if isinstance(obj, dict):
            return obj
    raise ValueError("Couldn't read the model's answer as a meal analysis.")


def _clean_text(value):
    return value.strip() if isinstance(value, str) and value.strip() else None


def _foods(value):
    if isinstance(value, str):
        value = re.split(r",|;|\band\b", value)
    if not isinstance(value, (list, tuple)):
        return []
    foods = [str(f).strip() for f in value if f is not None and str(f).strip()]
    return foods[:MAX_FOODS]


def parse_analysis(raw):
    """Model text -> {"foods", "calories_estimate", "nutrients", "balance_score",
    "mood_impact", "recommendation"}. Missing or unusable fields are None / empty
    rather than guessed. Raises ValueError if nothing usable came back."""
    obj = extract_json_object(raw)

    calories = first_number(obj.get("calories_estimate", obj.get("calories")))
    calories = int(round(calories)) if calories is not None and 0 < calories <= MAX_CALORIES else None

    source = obj.get("nutrients") if isinstance(obj.get("nutrients"), dict) else obj
    lowered = {str(k).lower(): v for k, v in source.items()}
    nutrients = {}
    for canonical, aliases in NUTRIENT_ALIASES.items():
        for alias in aliases:
            grams = first_number(lowered.get(alias))
            if grams is not None and grams >= 0:
                nutrients[canonical] = round(grams, 1)
                break

    score = first_number(obj.get("balance_score"))
    score = min(10, max(1, int(round(score)))) if score is not None else None

    result = {
        "foods": _foods(obj.get("foods")),
        "calories_estimate": calories,
        "nutrients": nutrients,
        "balance_score": score,
        "mood_impact": _clean_text(obj.get("mood_impact")),
        "recommendation": _clean_text(obj.get("recommendation")),
    }
    if not (result["foods"] or calories is not None or nutrients or score is not None):
        raise ValueError("The model's answer didn't contain any meal information - try a clearer photo.")
    return result


def balance_tone(score):
    """'high' / 'mid' / 'low' - how well balanced a meal was (drives colours)."""
    if score is None:
        return "mid"
    return "high" if score >= 7 else "mid" if score >= 4 else "low"


def balance_label(score):
    if score is None:
        return "Not rated"
    return "Great" if score >= 8 else "Good" if score >= 6 else "Fair" if score >= 4 else "Needs work"


def meals_on(meals, day):
    """The meals (rows from the nutrition_history table) logged on a calendar day."""
    return [m for m in meals if datetime.fromtimestamp(m["timestamp"] / 1000).date() == day]


def summarise_meals(meals):
    """{"count", "calories", "avg_balance"} for a list of meals (None when unknown)."""
    calories = [m["calories_estimate"] for m in meals if m.get("calories_estimate") is not None]
    scores = [m["balance_score"] for m in meals if m.get("balance_score") is not None]
    return {
        "count": len(meals),
        "calories": sum(calories) if calories else None,
        "avg_balance": round(sum(scores) / len(scores), 1) if scores else None,
    }
