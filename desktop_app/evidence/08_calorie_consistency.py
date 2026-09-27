"""
Evidence 8 - do the calorie total and the macronutrients the analyser reports agree with each other? (TC-F21)

Regenerate:  python evidence/08_calorie_consistency.py > evidence/output/08_calorie_consistency.txt

Reads the parsed analyses already recorded in evidence/output/03_*.txt and 03b_*.txt (values exactly as the
app parsed and would display/save them) and checks energy arithmetic: kcal ~ 4*protein + 4*carbs + 9*fat
(the standard Atwater factors). NOTE: what TC-F21 asserts is not visible to me; this is my reading of
"calorie totals" - that the reported total is not reconciled with the components. If your case means
something else (e.g. daily totals summed across meals) this file does not evidence it.
"""
import json
import re
from pathlib import Path

OUT = Path(__file__).resolve().parent / "output"
print("kcal reported vs kcal implied by the reported macros (4 kcal/g protein & carbs, 9 kcal/g fat)")
print(f"{'file':<38}{'run':<5}{'reported':>9}{'implied':>9}{'diff':>8}  {'protein/carbs/fat g':<20}")
for f in sorted(OUT.glob("03*_meal_analyser*.txt")):
    text = f.read_text()
    for m in re.finditer(r"---- run (\d+): .*?\nraw model response.*?\nparsed by the app:\n((?:    [^\n]*\n)+)", text, re.S):
        block = "\n".join(line[4:] for line in m.group(2).splitlines())
        try:
            d = json.loads(block)
        except ValueError:
            continue
        n = d["nutrients"]
        p, c, fat = n.get("protein") or 0, n.get("carbs") or 0, n.get("fat") or 0
        implied = 4 * p + 4 * c + 9 * fat
        print(f"{f.name:<38}{m.group(1):<5}{d['calories_estimate']:>9}{implied:>9.0f}{d['calories_estimate'] - implied:>+8.0f}  {p:g}/{c:g}/{fat:g}")
print("\nThe app displays calories_estimate as given (nutrition_logic.parse_analysis only clamps ranges); "
      "it does not compare it with the macros.")
