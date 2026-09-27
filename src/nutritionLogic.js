/**
 * Turning the vision model's answer about a meal into clean, safe numbers, plus
 * a few small helpers for the Nutrition page. A JS port of the desktop app's
 * nutrition_logic.py, kept dependency-free so it's easy to reason about.
 *
 * Local vision models (llava etc.) are not reliable JSON writers: they wrap the
 * answer in code fences, use single quotes, put units in numbers ("450 kcal"),
 * leave trailing commas, or rename fields ("fiber"). parseAnalysis() copes with
 * all of that, and refuses to invent data when the answer has nothing usable in it.
 */

const NUTRIENT_ALIASES = {
  protein: ['protein', 'proteins'],
  carbs: ['carbs', 'carb', 'carbohydrates', 'carbohydrate'],
  fat: ['fat', 'fats', 'total fat'],
  fibre: ['fibre', 'fiber', 'dietary fibre', 'dietary fiber'],
};
const MAX_FOODS = 12;
const MAX_CALORIES = 6000; // a single meal above this is almost certainly a model error

/** A number from 450, 450.5, "450", or "about 450 kcal"; null if there isn't one. */
export function firstNumber(value) {
  if (typeof value === 'boolean') return null;
  if (typeof value === 'number') return value;
  if (typeof value === 'string') {
    const m = value.match(/-?\d+(?:[.,]\d+)?/);
    if (m) return parseFloat(m[0].replace(',', '.'));
  }
  return null;
}

/** Finds the JSON-ish object in the model's text and returns it as an object. Throws if there isn't one. */
export function extractJsonObject(raw) {
  const text = (raw || '').replace(/```(?:json)?/gi, '').trim();
  const start = text.indexOf('{');
  const end = text.lastIndexOf('}');
  if (start === -1 || end <= start) {
    throw new Error(`The model didn't return a meal analysis: ${(raw || '').slice(0, 100)}`);
  }
  let candidate = text.slice(start, end + 1);
  candidate = candidate.replace(/,\s*([}\]])/g, '$1'); // trailing commas
  try {
    const obj = JSON.parse(candidate);
    if (obj && typeof obj === 'object') return obj;
  } catch { /* fall through */ }
  // Tolerate single-quoted, JS-object-literal-ish JSON from some models.
  try {
    const obj = new Function(`"use strict"; return (${candidate});`)();
    if (obj && typeof obj === 'object') return obj;
  } catch { /* fall through */ }
  throw new Error("Couldn't read the model's answer as a meal analysis.");
}

function cleanText(value) {
  return typeof value === 'string' && value.trim() ? value.trim() : null;
}

function foodsFrom(value) {
  let list = value;
  if (typeof list === 'string') list = list.split(/,|;|\band\b/);
  if (!Array.isArray(list)) return [];
  return list.map(f => (f == null ? '' : String(f).trim())).filter(Boolean).slice(0, MAX_FOODS);
}

/**
 * Model text -> {foods, caloriesEstimate, nutrients, balanceScore, moodImpact, recommendation}.
 * Missing or unusable fields are null / empty rather than guessed. Throws if
 * nothing usable came back.
 */
export function parseAnalysis(raw) {
  const obj = extractJsonObject(raw);

  let calories = firstNumber(obj.calories_estimate ?? obj.calories);
  calories = calories != null && calories > 0 && calories <= MAX_CALORIES ? Math.round(calories) : null;

  const source = obj.nutrients && typeof obj.nutrients === 'object' ? obj.nutrients : obj;
  const lowered = {};
  for (const [k, v] of Object.entries(source)) lowered[String(k).toLowerCase()] = v;
  const nutrients = {};
  for (const [canonical, aliases] of Object.entries(NUTRIENT_ALIASES)) {
    for (const alias of aliases) {
      const grams = firstNumber(lowered[alias]);
      if (grams != null && grams >= 0) { nutrients[canonical] = Math.round(grams * 10) / 10; break; }
    }
  }

  let score = firstNumber(obj.balance_score);
  score = score != null ? Math.min(10, Math.max(1, Math.round(score))) : null;

  const result = {
    foods: foodsFrom(obj.foods),
    caloriesEstimate: calories,
    nutrients,
    balanceScore: score,
    moodImpact: cleanText(obj.mood_impact),
    recommendation: cleanText(obj.recommendation),
  };
  if (!(result.foods.length || calories != null || Object.keys(nutrients).length || score != null)) {
    throw new Error("The model's answer didn't contain any meal information — try a clearer photo.");
  }
  return result;
}

/** 'high' / 'mid' / 'low' — how well balanced a meal was (drives colours). */
export function balanceTone(score) {
  if (score == null) return 'mid';
  return score >= 7 ? 'high' : score >= 4 ? 'mid' : 'low';
}

export function balanceLabel(score) {
  if (score == null) return 'Not rated';
  return score >= 8 ? 'Great' : score >= 6 ? 'Good' : score >= 4 ? 'Fair' : 'Needs work';
}

/** The meals (localStorage records) logged on a calendar day (a Date). */
export function mealsOn(meals, day) {
  const key = day.toISOString().slice(0, 10);
  return meals.filter(m => new Date(m.timestamp).toISOString().slice(0, 10) === key);
}

/** {count, calories, avgBalance} for a list of meals (null when unknown). */
export function summariseMeals(meals) {
  const calories = meals.map(m => m.caloriesEstimate).filter(v => v != null);
  const scores = meals.map(m => m.balanceScore).filter(v => v != null);
  return {
    count: meals.length,
    calories: calories.length ? calories.reduce((a, b) => a + b, 0) : null,
    avgBalance: scores.length ? Math.round((scores.reduce((a, b) => a + b, 0) / scores.length) * 10) / 10 : null,
  };
}
