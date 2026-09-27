"""
Evidence 3 - the meal analyser run on ONE photo several times (default 2), raw
responses printed side by side, to document that the local vision model is not
deterministic.

Regenerate:  python evidence/03_meal_analyser_twice.py [--runs N] > evidence/output/03_meal_analyser_twice.txt

It uses the app's own code: NutritionTab._load_path (load + resize + JPEG + base64),
ai_client.vision_ai (the request), NUTRITION_PROMPT, and nutrition_logic.parse_analysis.
"""
import argparse
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import textwrap
import time
import urllib.request
from datetime import datetime
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtWidgets import QApplication            # noqa: E402
from ai_client import vision_ai                         # noqa: E402
from db import Database                                # noqa: E402
from nutrition_logic import parse_analysis              # noqa: E402
from ui.tabs.nutrition_tab import NUTRITION_PROMPT, NutritionTab, MAX_DIMENSION   # noqa: E402

parser = argparse.ArgumentParser()
parser.add_argument("--runs", type=int, default=2)
parser.add_argument("--photo", default=None, help="another photo under evidence/assets/ (e.g. nofood_photo.jpg); its <name>_source.json must sit beside it")
args = parser.parse_args()

PHOTO = ROOT / "evidence" / "assets" / (args.photo or "meal_photo.jpg")
SOURCE = json.loads(PHOTO.with_name(PHOTO.stem + "_source.json").read_text())

# the model the app is actually configured to use (read-only look at the real settings)
try:
    ro = sqlite3.connect(f"file:{ROOT / 'mind_fusion.db'}?mode=ro", uri=True)
    provider, base_url, _chat, vision_model = ro.execute("SELECT provider, base_url, chat_model, vision_model FROM ai_config LIMIT 1").fetchone()
except Exception:
    provider, base_url, vision_model = "ollama", "http://localhost:11434", "llava"
config = {"provider": provider, "base_url": base_url, "chat_model": "unused", "vision_model": vision_model}


def http_json(path, body=None):
    req = urllib.request.Request(base_url + path, data=json.dumps(body).encode() if body else None,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())


print("Mind Fusion Desktop - meal analyser, one photo, repeated")
print(f"date    : {datetime.now():%Y-%m-%d %H:%M:%S}")
print(f"command : python evidence/03_meal_analyser_twice.py --runs {args.runs}" + (f" --photo {args.photo}" if args.photo else ""))
print(f"machine : {subprocess.run(['sysctl','-n','machdep.cpu.brand_string'],capture_output=True,text=True).stdout.strip()}, "
      f"{int(subprocess.run(['sysctl','-n','hw.memsize'],capture_output=True,text=True).stdout)//2**30} GB RAM")
print(f"ollama  : {http_json('/api/version')['version']}   model: {vision_model}")
try:
    shown = http_json("/api/show", {"model": vision_model})
    params = (shown.get("parameters") or "").strip().replace("\n", "; ") or "(none set in the model file - Ollama defaults apply)"
    print(f"model-file sampling parameters: {params}")
except Exception as exc:                                          # noqa: BLE001
    print(f"model-file sampling parameters: (could not read: {exc})")
print(f"photo   : {SOURCE['title']}  ({SOURCE['license']}, Wikimedia Commons)  {SOURCE['descriptionurl']}")
print()

app = QApplication([])
tmp = tempfile.TemporaryDirectory()
db = Database(Path(tmp.name) / "scratch.db")
uid = db.create_user("Evidence", "evidence@example.com")
tab = NutritionTab(db, uid, lambda: config)
tab._load_path(str(PHOTO))                                        # the app's real loading + resizing code
assert tab.image_base64, "photo failed to load"
print(f"prepared exactly as the app does: longest side <= {MAX_DIMENSION}px, JPEG q85, base64 length {len(tab.image_base64):,} chars")
print("prompt sent (verbatim):")
print(textwrap.indent(NUTRITION_PROMPT, "    | "))
print()

runs = []
for i in range(1, args.runs + 1):
    started = time.perf_counter()
    try:
        raw = vision_ai(config, tab.image_base64, NUTRITION_PROMPT)
        elapsed = time.perf_counter() - started
        try:
            parsed, error = parse_analysis(raw), None
        except ValueError as exc:
            parsed, error = None, str(exc)
    except Exception as exc:                                       # noqa: BLE001
        raw, elapsed, parsed, error = "", time.perf_counter() - started, None, f"request failed: {exc}"
    runs.append({"raw": raw, "parsed": parsed, "error": error, "seconds": elapsed})
    print(f"---- run {i}: {elapsed:.1f} s ----")
    print("raw model response (verbatim):")
    print(textwrap.indent(raw.strip() or "(empty)", "    | "))
    print("parsed by the app:" if parsed else f"NOT parsed: {error}")
    if parsed:
        print(textwrap.indent(json.dumps(parsed, indent=2, ensure_ascii=False), "    "))
    print()

# ---------------------------------------------------------------- side by side
ok_runs = [r for r in runs if r["parsed"]]
print("=" * 100)
print(f"SIDE BY SIDE (parsed fields), runs 1 and 2" + (f" of {len(runs)}" if len(runs) > 2 else ""))
print("=" * 100)
W = 38
if len(ok_runs) >= 2:
    a, b = ok_runs[0]["parsed"], ok_runs[1]["parsed"]
    fields = [("foods", ", ".join(a["foods"]), ", ".join(b["foods"])),
              ("calories_estimate", a["calories_estimate"], b["calories_estimate"]),
              ("balance_score", a["balance_score"], b["balance_score"])]
    for key in ("protein", "carbs", "fat", "fibre"):
        fields.append((f"nutrients.{key}", a["nutrients"].get(key), b["nutrients"].get(key)))
    fields += [("mood_impact", a["mood_impact"], b["mood_impact"]), ("recommendation", a["recommendation"], b["recommendation"])]
    print(f"{'field'.ljust(20)}{'run 1'.ljust(W)}{'run 2'.ljust(W)}same?")
    print("-" * 100)
    differing = 0
    for name, x, y in fields:
        same = x == y
        differing += not same
        lx, ly = textwrap.wrap(str(x), W - 2) or ["-"], textwrap.wrap(str(y), W - 2) or ["-"]
        for n in range(max(len(lx), len(ly))):
            print(f"{(name if n == 0 else '').ljust(20)}{(lx[n] if n < len(lx) else '').ljust(W)}{(ly[n] if n < len(ly) else '').ljust(W)}{('yes' if same else 'NO') if n == 0 else ''}")
    print("-" * 100)
    identical_text = ok_runs[0]["raw"].strip() == ok_runs[1]["raw"].strip()
    print(f"raw response text identical between run 1 and run 2 : {'YES' if identical_text else 'NO'}")
    print(f"parsed fields that differ                            : {differing} of {len(fields)}")
    print(f"response times                                       : " + ", ".join(f"{r['seconds']:.1f} s" for r in runs))
else:
    print("fewer than two runs produced a parseable answer - see the raw responses above.")
    print("(this is itself a finding: the app shows the user a message instead of guessing.)")

if len(runs) > 2:
    print()
    print("All runs, key numbers:")
    for i, r in enumerate(runs, 1):
        p = r["parsed"]
        print(f"  run {i}: " + (f"kcal={p['calories_estimate']}, balance={p['balance_score']}, foods={p['foods']}" if p else f"unparsed ({r['error']})"))
