#!/usr/bin/env python3
"""
Mind Fusion AI — evidence collector.

Produces machine-generated proof for the test cases in Appendix B, one text
file per command, written to ./evidence/.  Every file carries a header with
the date, machine and Python version so a marker can see it was really run.

    python3 evidence_run.py moods              # TC-F07, E01, E02, E03, E06
    python3 evidence_run.py meal photo.jpg     # TC-F19, E12  (runs llava twice)
    python3 evidence_run.py meal photo.jpg --nofood empty.jpg   # adds TC-F22
    python3 evidence_run.py db                 # TC-F01, F11, I07
    python3 evidence_run.py privacy            # TC-I08  (run before and after)
    python3 evidence_run.py models             # confirms Table 5
    python3 evidence_run.py bench              # the desktop latency figure
    python3 evidence_run.py all                # everything except meal

Nothing here touches your application's data. The db command reads only.

--------------------------------------------------------------------------
BEFORE THE FIRST RUN: edit the CONFIG block. If you do not know a value,
leave it — the script searches for the database and reports what it finds.
--------------------------------------------------------------------------
"""
import argparse
import base64
import datetime
import difflib
import glob
import importlib
import json
import os
import platform
import re
import shutil
import sqlite3
import statistics
import subprocess
import sys
import tempfile
import time

# ====================== CONFIG — edit these ===============================

MOOD_MAPPER = "mood:detect_mood"          # "module:function"
DB_PATH = ""                              # leave "" to search for it
OLLAMA = "http://localhost:11434"
CHAT_MODEL = "llama3"                     # as it appears in `ollama list`
VISION_MODEL = "llava"
BENCH_RUNS = 5                            # generation is slow; 5 is enough

# ==========================================================================

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "evidence")


# ----------------------------------------------------------------- plumbing

class Tee:
    """Write to the console and to the evidence file at the same time."""

    def __init__(self, name):
        os.makedirs(OUT_DIR, exist_ok=True)
        self.path = os.path.join(OUT_DIR, name + ".txt")
        self.fh = open(self.path, "w", encoding="utf-8")

    def __call__(self, line=""):
        print(line)
        self.fh.write(line + "\n")

    def close(self):
        self.fh.close()
        print("\n  written to %s" % self.path)


def header(out, title, cases):
    out("=" * 78)
    out(title)
    out("Test cases: %s" % cases)
    out("Run:        %s" % datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    out("Machine:    %s %s, Python %s" % (platform.system(), platform.machine(),
                                          platform.python_version()))
    out("=" * 78)
    out()


def load(spec):
    module_name, _, attr = spec.partition(":")
    sys.path.insert(0, os.getcwd())
    module = importlib.import_module(module_name)
    return getattr(module, attr)


def run(cmd):
    """Run a shell command and return its output, or the error."""
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
        return (r.stdout + r.stderr).strip() or "(no output)"
    except Exception as exc:                                    # pragma: no cover
        return "command failed: %s" % exc


# -------------------------------------------------------------------- moods

# expected mood -> phrase.  The last four are the edge cases the report
# discusses; two of them are expected to fail and that is the point.
MOOD_CASES = [
    ("TC-F07", "happy",    "I feel really happy today"),
    ("TC-F07", "calm",     "I feel calm and settled"),
    ("TC-F07", "sad",      "I feel sad and low"),
    ("TC-F07", "anxious",  "I feel anxious about tomorrow"),
    ("TC-F07", "stressed", "work has been stressful all week"),
    ("TC-F07", "grateful", "I feel grateful for today"),
    ("TC-F07", "tired",    "I feel tired and worn out"),
    ("TC-F07", "hopeful",  "I feel hopeful about things"),
    ("TC-E01", "not stressed", "I am not stressed at all"),
    ("TC-E02", "anxious",  "मुझे बहुत चिंता हो रही है"),
    ("TC-E03", "stable",   "I'm completely overwhelmed and totally drained"),
    ("TC-E06", "calm",     "I went to the shop and bought bread and milk"),
]


def cmd_moods(args):
    out = Tee("moods")
    header(out, "Mood mapper: expected against actual",
           "TC-F07, TC-E01, TC-E02, TC-E03, TC-E06")
    try:
        detect_mood = load(MOOD_MAPPER)
    except Exception as exc:
        out("could not import %s: %s" % (MOOD_MAPPER, exc))
        out("Edit MOOD_MAPPER in the CONFIG block at the top of this file.")
        return out.close()

    out("%-8s  %-14s  %-44s  %-10s  %5s  %s"
        % ("case", "expected", "input", "detected", "conf", ""))
    out("-" * 108)
    agree = 0
    for case, expected, phrase in MOOD_CASES:
        result = detect_mood(phrase)
        mood, conf = result["mood"], result["confidence"]
        if expected == "not stressed":
            ok = mood != "stressed"
        elif expected == "stable":
            ok = mood == detect_mood(phrase)["mood"]        # determinism only
        else:
            ok = mood == expected
        agree += ok
        out("%-8s  %-14s  %-44s  %-10s  %5.2f  %s"
            % (case, expected, phrase[:44], mood, conf, "ok" if ok else "MISMATCH"))
    out("-" * 108)
    out("%d of %d as expected" % (agree, len(MOOD_CASES)))
    out()
    out("TC-E03 is recorded as stable/unstable rather than correct/incorrect,")
    out("because the case asks whether repeated runs agree, not which mood wins.")
    out.close()


# --------------------------------------------------------------------- meal

MEAL_PROMPT = ("Analyse this meal photo. Reply with JSON only, with the keys "
               "foods, calories, protein_g, carbs_g, fat_g, fibre_g, mood_note, "
               "suggestion, balance_score.")


def _llava(photo, out):
    try:
        import requests
    except ImportError:
        out("the requests package is not installed: pip install requests")
        return None
    with open(photo, "rb") as fh:
        b64 = base64.b64encode(fh.read()).decode()
    started = time.time()
    try:
        r = requests.post(OLLAMA + "/api/chat", timeout=300, json={
            "model": VISION_MODEL, "stream": False,
            "messages": [{"role": "user", "content": MEAL_PROMPT, "images": [b64]}]})
        body = r.json().get("message", {}).get("content", "")
    except Exception as exc:
        out("call failed: %s" % exc)
        return None
    out("  %.1f s, %d characters" % (time.time() - started, len(body)))
    return body


def _numbers(text):
    return re.findall(r"\d+(?:\.\d+)?", text or "")


def cmd_meal(args):
    out = Tee("meal")
    header(out, "Nutrition analyser: the same photograph analysed twice",
           "TC-F19, TC-E12" + (", TC-F22" if args.nofood else ""))
    out("Photograph: %s" % args.photo)
    out("Model:      %s via %s" % (VISION_MODEL, OLLAMA))
    out()

    runs = []
    for n in (1, 2):
        out("--- run %d " % n + "-" * 60)
        body = _llava(args.photo, out)
        if body is None:
            return out.close()
        out(body)
        out()
        runs.append(body)

    out("--- what changed between the two runs " + "-" * 38)
    a, b = _numbers(runs[0]), _numbers(runs[1])
    out("numbers in run 1: %s" % ", ".join(a))
    out("numbers in run 2: %s" % ", ".join(b))
    out("identical: %s" % ("yes" if a == b else "NO — TC-E12 fails"))
    out()
    for line in difflib.unified_diff(runs[0].splitlines(), runs[1].splitlines(),
                                     "run 1", "run 2", lineterm="", n=1):
        out(line)

    if args.nofood:
        out()
        out("--- an image containing no food (TC-F22) " + "-" * 36)
        body = _llava(args.nofood, out)
        if body:
            out(body)
            out()
            out("TC-F22 fails if the model has invented a meal above.")
    out.close()


# ----------------------------------------------------------------------- db

DB_CANDIDATES = ["*.db", "*.sqlite", "*.sqlite3",
                 os.path.expanduser("~/Library/Application Support/*/*.db"),
                 os.path.expanduser("~/.mindfusion/*.db"),
                 os.path.expanduser("~/**/mind*fusion*.db")]
INTERESTING = ("profile", "user", "journal", "mood", "checkin", "check_in",
               "meal", "sleep", "habit", "chat", "exercise")


def find_db(out):
    if DB_PATH and os.path.exists(DB_PATH):
        return DB_PATH
    for pattern in DB_CANDIDATES:
        for path in glob.glob(pattern, recursive=True):
            try:
                with sqlite3.connect("file:%s?mode=ro" % path, uri=True) as c:
                    c.execute("select name from sqlite_master limit 1")
                out("found database: %s" % path)
                return path
            except Exception:
                continue
    out("no database found. Set DB_PATH in the CONFIG block.")
    return None


def cmd_db(args):
    out = Tee("database")
    header(out, "SQLite: what the application actually stored",
           "TC-F01, TC-F11, TC-I07")
    out("NOTE: read this file before pasting it into the report and remove")
    out("anything personal. Use the test profile, not your own.")
    out()
    path = args.path or find_db(out)
    if not path:
        return out.close()
    out("File:  %s" % path)
    out("Size:  %.1f KB" % (os.path.getsize(path) / 1024))
    out()
    con = sqlite3.connect("file:%s?mode=ro" % path, uri=True)
    con.row_factory = sqlite3.Row
    tables = [r[0] for r in con.execute(
        "select name from sqlite_master where type='table' order by name")]
    out("Tables: %s" % ", ".join(tables))
    out()
    for table in tables:
        if not any(k in table.lower() for k in INTERESTING):
            continue
        out("--- %s " % table + "-" * (70 - len(table)))
        schema = con.execute("select sql from sqlite_master where name=?",
                             (table,)).fetchone()[0]
        out(schema)
        count = con.execute("select count(*) from '%s'" % table).fetchone()[0]
        out("rows: %d" % count)
        if count:
            row = con.execute("select * from '%s' order by rowid desc limit 1"
                              % table).fetchone()
            out("most recent row:")
            for key in row.keys():
                value = str(row[key])
                out("    %-18s %s" % (key, value[:90] + ("…" if len(value) > 90 else "")))
        out()
    out("TC-F01 passes if the profile row holds all six onboarding fields.")
    out("TC-F11 and TC-I07 pass if the journal row survived a restart —")
    out("quit the application, reopen it, and run this command again.")
    out.close()


# ------------------------------------------------------------------ privacy

AUDIO = (".wav", ".mp3", ".m4a", ".flac", ".ogg", ".webm", ".aiff", ".caf")
IMAGE_TMP = (".png", ".jpg", ".jpeg", ".bmp")
SNAPSHOT = os.path.join(OUT_DIR, ".privacy_snapshot.json")


def scan_dirs():
    dirs = [tempfile.gettempdir(), os.getcwd(),
            os.path.expanduser("~/Library/Caches"), "/var/folders"]
    found = {}
    for d in dirs:
        if not os.path.isdir(d):
            continue
        for root, _, files in os.walk(d):
            if root.count(os.sep) > d.count(os.sep) + 3:
                continue
            for f in files:
                if f.lower().endswith(AUDIO + IMAGE_TMP):
                    p = os.path.join(root, f)
                    try:
                        found[p] = os.path.getsize(p)
                    except OSError:
                        pass
        if len(found) > 4000:
            break
    return found


def cmd_privacy(args):
    out = Tee("privacy")
    header(out, "Filesystem: is anything written during a check-in?", "TC-I08")
    now = scan_dirs()
    out("Scanned the temporary directories for audio and image files.")
    out("Files matching: %d" % len(now))
    out()
    if os.path.exists(SNAPSHOT):
        before = json.load(open(SNAPSHOT))
        added = sorted(set(now) - set(before))
        out("--- compared with the snapshot taken at %s ---"
            % before.get("_taken", "an earlier run"))
        out("new files since then: %d" % len([a for a in added if a != "_taken"]))
        for path in added:
            if path == "_taken":
                continue
            out("    %8d B  %s" % (now[path], path))
        out()
        out("TC-I08 passes if no audio file appears above after a voice check-in.")
    else:
        out("No earlier snapshot, so this run is the baseline.")
        out("Now do a voice check-in in the application, then run this again.")
    payload = dict(now)
    payload["_taken"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    json.dump(payload, open(SNAPSHOT, "w"))
    out()
    out("--- listening sockets held by the application (TC-I03) ---")
    out(run("lsof -nP -iTCP -sTCP:ESTABLISHED 2>/dev/null | head -25"))
    out()
    out("With the network off, nothing here should point outside this machine")
    out("except the loopback connection to Ollama on port 11434.")
    out.close()


# ------------------------------------------------------------------- models

def cmd_models(args):
    out = Tee("models")
    header(out, "Installed models and versions", "confirms Table 5")
    for cmd in ("ollama --version", "ollama list", "ollama ps",
                "python3 -c \"import cv2, onnxruntime, faster_whisper, PySide6;"
                " print('opencv', cv2.__version__);"
                " print('onnxruntime', onnxruntime.__version__);"
                " print('PySide6', PySide6.__version__)\""):
        out("$ " + cmd.split("-c")[0].strip())
        out(run(cmd))
        out()
    out.close()


# -------------------------------------------------------------------- bench

BENCH_PROMPT = ("You are a wellbeing companion. The user is feeling stressed and "
                "has declared hypertension. Reply in four to six sentences.")


def cmd_bench(args):
    out = Tee("latency")
    header(out, "End-to-end latency on the desktop build", "TC-I01, Objective 5")
    out("This times the stages that run outside the interface: mood detection")
    out("and generation through the local Ollama server. It does not include")
    out("Qt's rendering, so treat it as a lower bound on the full path.")
    out()

    try:
        detect_mood = load(MOOD_MAPPER)
        samples = []
        for _ in range(200):
            t = time.perf_counter()
            detect_mood("work has been relentless this week")
            samples.append((time.perf_counter() - t) * 1000)
        out("mood mapper, 200 runs:  mean %.3f ms, max %.3f ms"
            % (statistics.mean(samples), max(samples)))
    except Exception as exc:
        out("mood mapper not timed: %s" % exc)
    out()

    try:
        import requests
    except ImportError:
        out("the requests package is not installed: pip install requests")
        return out.close()

    out("generation, %s via %s, %d runs:" % (CHAT_MODEL, OLLAMA, BENCH_RUNS))
    times = []
    for n in range(1, BENCH_RUNS + 1):
        started = time.perf_counter()
        try:
            r = requests.post(OLLAMA + "/api/chat", timeout=300, json={
                "model": CHAT_MODEL, "stream": False,
                "messages": [{"role": "user", "content": BENCH_PROMPT}]})
            body = r.json().get("message", {}).get("content", "")
        except Exception as exc:
            out("  run %d failed: %s" % (n, exc))
            continue
        elapsed = time.perf_counter() - started
        times.append(elapsed)
        out("  run %d: %6.2f s   (%d characters returned)" % (n, elapsed, len(body)))
    if times:
        out()
        out("  mean   %.2f s" % statistics.mean(times))
        out("  median %.2f s" % statistics.median(times))
        out("  worst  %.2f s" % max(times))
        out()
        budget = 5.0
        out("  budget %.1f s: %s" % (budget,
            "met" if max(times) <= budget else "EXCEEDED on the slowest run"))
        out()
        out("  first run includes loading the model into memory; if it is far")
        out("  slower than the rest, report the warm figure and say so.")
    out.close()


# --------------------------------------------------------------------- main

def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("moods")
    m = sub.add_parser("meal"); m.add_argument("photo"); m.add_argument("--nofood")
    d = sub.add_parser("db"); d.add_argument("path", nargs="?")
    sub.add_parser("privacy")
    sub.add_parser("models")
    sub.add_parser("bench")
    sub.add_parser("all")
    args = p.parse_args()

    if args.cmd == "all":
        for fn in (cmd_moods, cmd_db, cmd_privacy, cmd_models, cmd_bench):
            try:
                fn(argparse.Namespace(path=None))
            except Exception as exc:
                print("%s failed: %s" % (fn.__name__, exc))
            print()
        return
    {"moods": cmd_moods, "meal": cmd_meal, "db": cmd_db, "privacy": cmd_privacy,
     "models": cmd_models, "bench": cmd_bench}[args.cmd](args)


if __name__ == "__main__":
    main()
