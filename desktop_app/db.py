"""
SQLite persistence layer for Mind Fusion Desktop.

Everything lives in one local file, mind_fusion.db, created next to this
script the first time the app runs. There's no real password checking here
(this is a local single-computer wellbeing app, not a security demo) - an
"account" is just a row keyed by email, and signing in with an email that
already exists logs you back into that same account with its saved profile.
"""

import json
import sqlite3
import time
from pathlib import Path

DB_PATH = Path(__file__).parent / "mind_fusion.db"


class Database:
    def __init__(self, path=DB_PATH):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._create_tables()

    def _create_tables(self):
        cur = self.conn.cursor()
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                name    TEXT NOT NULL,
                email   TEXT NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS profiles (
                user_id     INTEGER PRIMARY KEY REFERENCES users(id),
                country     TEXT,
                language    TEXT,
                age_group   TEXT,
                conditions  TEXT DEFAULT '[]',
                habits      TEXT DEFAULT '[]',
                goals       TEXT DEFAULT '[]'
            );

            CREATE TABLE IF NOT EXISTS ai_config (
                user_id      INTEGER PRIMARY KEY REFERENCES users(id),
                provider     TEXT DEFAULT 'ollama',
                base_url     TEXT DEFAULT 'http://localhost:11434',
                chat_model   TEXT DEFAULT 'llama3.2',
                vision_model TEXT DEFAULT 'llava'
            );

            CREATE TABLE IF NOT EXISTS mood_history (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER REFERENCES users(id),
                mood       TEXT NOT NULL,
                timestamp  INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS journal_entries (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER REFERENCES users(id),
                prompt     TEXT,
                text       TEXT NOT NULL,
                mood       TEXT,
                timestamp  INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS affirm_favorites (
                user_id       INTEGER REFERENCES users(id),
                affirmation_id INTEGER,
                PRIMARY KEY (user_id, affirmation_id)
            );

            CREATE TABLE IF NOT EXISTS nutrition_history (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id          INTEGER REFERENCES users(id),
                foods            TEXT,
                calories_estimate INTEGER,
                balance_score    INTEGER,
                mood_impact      TEXT,
                timestamp        INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS chat_messages (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id   INTEGER REFERENCES users(id),
                role      TEXT NOT NULL,
                content   TEXT NOT NULL,
                mood      TEXT,
                timestamp INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS app_settings (
                key   TEXT PRIMARY KEY,
                value TEXT
            );

            CREATE TABLE IF NOT EXISTS habit_log (
                user_id  INTEGER REFERENCES users(id),
                habit_id TEXT NOT NULL,
                day      TEXT NOT NULL,          -- ISO date, e.g. 2026-09-21
                PRIMARY KEY (user_id, habit_id, day)
            );

            CREATE TABLE IF NOT EXISTS sleep_log (
                user_id INTEGER REFERENCES users(id),
                day     TEXT NOT NULL,           -- the date the sleep is logged on
                hours   REAL NOT NULL,
                quality INTEGER,                 -- 1 (poor) .. 5 (great)
                PRIMARY KEY (user_id, day)
            );

            CREATE TABLE IF NOT EXISTS exercise_sessions (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id       INTEGER REFERENCES users(id),
                exercise_id   TEXT NOT NULL,
                exercise_name TEXT NOT NULL,
                timestamp     INTEGER NOT NULL
            );

            -- Holds exactly one row: which user is currently signed in.
            -- Kept separate from `users`/`profiles` so signing out never
            -- deletes anyone's saved answers.
            CREATE TABLE IF NOT EXISTS session (
                id      INTEGER PRIMARY KEY CHECK (id = 1),
                user_id INTEGER REFERENCES users(id)
            );
        """)
        self.conn.commit()
        self._add_missing_columns("nutrition_history", {
            "protein": "REAL", "carbs": "REAL", "fat": "REAL", "fibre": "REAL", "recommendation": "TEXT",
        })
        self._add_missing_columns("exercise_sessions", {
            "duration_min": "INTEGER",   # minutes, when known (always set for manual entries)
            "source": "TEXT",            # 'manual' for ones typed in by hand; empty/NULL = a guided in-app session
        })

    def _add_missing_columns(self, table, columns):
        """Lightweight migration: databases made by an older version of the
        app don't have newer columns, so add any that are missing. Existing
        rows keep their data (the new columns are simply empty for them)."""
        existing = {row["name"] for row in self.conn.execute(f"PRAGMA table_info({table})")}
        for name, sql_type in columns.items():
            if name not in existing:
                self.conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {sql_type}")
        self.conn.commit()

    # -- Users / accounts ---------------------------------------------------

    def get_user_by_email(self, email):
        row = self.conn.execute(
            "SELECT * FROM users WHERE email = ?", (email.strip().lower(),)
        ).fetchone()
        return dict(row) if row else None

    def create_user(self, name, email):
        cur = self.conn.execute(
            "INSERT INTO users (name, email) VALUES (?, ?)",
            (name.strip(), email.strip().lower()),
        )
        self.conn.commit()
        user_id = cur.lastrowid
        # every user gets a default local-AI config right away
        self.conn.execute("INSERT INTO ai_config (user_id) VALUES (?)", (user_id,))
        self.conn.commit()
        return user_id

    # -- Profiles -------------------------------------------------------

    def get_profile(self, user_id):
        row = self.conn.execute(
            "SELECT * FROM profiles WHERE user_id = ?", (user_id,)
        ).fetchone()
        if not row:
            return None
        profile = dict(row)
        profile["conditions"] = json.loads(profile["conditions"])
        profile["habits"] = json.loads(profile["habits"])
        profile["goals"] = json.loads(profile["goals"])
        return profile

    def save_profile(self, user_id, country, language, age_group, conditions, habits, goals):
        self.conn.execute(
            """INSERT INTO profiles (user_id, country, language, age_group, conditions, habits, goals)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(user_id) DO UPDATE SET
                   country=excluded.country, language=excluded.language,
                   age_group=excluded.age_group, conditions=excluded.conditions,
                   habits=excluded.habits, goals=excluded.goals""",
            (user_id, country, language, age_group,
             json.dumps(conditions), json.dumps(habits), json.dumps(goals)),
        )
        self.conn.commit()

    # -- AI config --------------------------------------------------------

    def get_ai_config(self, user_id):
        row = self.conn.execute(
            "SELECT * FROM ai_config WHERE user_id = ?", (user_id,)
        ).fetchone()
        return dict(row) if row else None

    def save_ai_config(self, user_id, provider, base_url, chat_model, vision_model):
        self.conn.execute(
            """INSERT INTO ai_config (user_id, provider, base_url, chat_model, vision_model)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(user_id) DO UPDATE SET
                   provider=excluded.provider, base_url=excluded.base_url,
                   chat_model=excluded.chat_model, vision_model=excluded.vision_model""",
            (user_id, provider, base_url, chat_model, vision_model),
        )
        self.conn.commit()

    # -- Mood history -------------------------------------------------------

    def add_mood_entry(self, user_id, mood):
        self.conn.execute(
            "INSERT INTO mood_history (user_id, mood, timestamp) VALUES (?, ?, ?)",
            (user_id, mood, int(time.time() * 1000)),
        )
        self.conn.commit()

    def get_mood_history(self, user_id):
        rows = self.conn.execute(
            "SELECT mood, timestamp FROM mood_history WHERE user_id = ? ORDER BY timestamp ASC",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    # -- Journal --------------------------------------------------------

    def add_journal_entry(self, user_id, prompt, text, mood):
        self.conn.execute(
            "INSERT INTO journal_entries (user_id, prompt, text, mood, timestamp) VALUES (?, ?, ?, ?, ?)",
            (user_id, prompt, text, mood, int(time.time() * 1000)),
        )
        self.conn.commit()

    def get_journal_entries(self, user_id):
        rows = self.conn.execute(
            "SELECT * FROM journal_entries WHERE user_id = ? ORDER BY timestamp DESC",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def delete_journal_entry(self, entry_id):
        self.conn.execute("DELETE FROM journal_entries WHERE id = ?", (entry_id,))
        self.conn.commit()

    # -- Affirmation favorites -----------------------------------------------

    def get_favorite_ids(self, user_id):
        rows = self.conn.execute(
            "SELECT affirmation_id FROM affirm_favorites WHERE user_id = ?", (user_id,)
        ).fetchall()
        return [r["affirmation_id"] for r in rows]

    def toggle_favorite(self, user_id, affirmation_id):
        existing = self.conn.execute(
            "SELECT 1 FROM affirm_favorites WHERE user_id = ? AND affirmation_id = ?",
            (user_id, affirmation_id),
        ).fetchone()
        if existing:
            self.conn.execute(
                "DELETE FROM affirm_favorites WHERE user_id = ? AND affirmation_id = ?",
                (user_id, affirmation_id),
            )
        else:
            self.conn.execute(
                "INSERT INTO affirm_favorites (user_id, affirmation_id) VALUES (?, ?)",
                (user_id, affirmation_id),
            )
        self.conn.commit()

    # -- Nutrition history --------------------------------------------------

    def add_nutrition_entry(self, user_id, foods, calories_estimate, balance_score, mood_impact,
                            protein=None, carbs=None, fat=None, fibre=None, recommendation=None):
        cur = self.conn.execute(
            """INSERT INTO nutrition_history
               (user_id, foods, calories_estimate, balance_score, mood_impact,
                protein, carbs, fat, fibre, recommendation, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, foods, calories_estimate, balance_score, mood_impact,
             protein, carbs, fat, fibre, recommendation, int(time.time() * 1000)),
        )
        self.conn.commit()
        return cur.lastrowid

    def delete_nutrition_entry(self, entry_id):
        self.conn.execute("DELETE FROM nutrition_history WHERE id = ?", (entry_id,))
        self.conn.commit()

    def get_nutrition_history(self, user_id):
        rows = self.conn.execute(
            "SELECT * FROM nutrition_history WHERE user_id = ? ORDER BY timestamp DESC",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    # -- Exercise history -----------------------------------------------

    def add_exercise_session(self, user_id, exercise_id, exercise_name, timestamp_ms=None,
                             duration_min=None, source=None):
        """Logs an exercise. A finished guided session just passes the first three
        arguments; a manual entry also gives when it happened, how long, and
        source='manual'."""
        cur = self.conn.execute(
            """INSERT INTO exercise_sessions
               (user_id, exercise_id, exercise_name, timestamp, duration_min, source)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, exercise_id, exercise_name,
             timestamp_ms if timestamp_ms is not None else int(time.time() * 1000), duration_min, source),
        )
        self.conn.commit()
        return cur.lastrowid

    def delete_exercise_session(self, session_id):
        self.conn.execute("DELETE FROM exercise_sessions WHERE id = ?", (session_id,))
        self.conn.commit()

    def get_exercise_history(self, user_id):
        rows = self.conn.execute(
            "SELECT * FROM exercise_sessions WHERE user_id = ? ORDER BY timestamp DESC",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    # -- Chat history -----------------------------------------------------

    def add_chat_message(self, user_id, role, content, mood=None):
        self.conn.execute(
            "INSERT INTO chat_messages (user_id, role, content, mood, timestamp) VALUES (?, ?, ?, ?, ?)",
            (user_id, role, content, mood, int(time.time() * 1000)),
        )
        self.conn.commit()

    def get_chat_messages(self, user_id, limit=100):
        rows = self.conn.execute(
            "SELECT * FROM (SELECT * FROM chat_messages WHERE user_id = ? ORDER BY id DESC LIMIT ?) ORDER BY id ASC",
            (user_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def clear_chat_messages(self, user_id):
        self.conn.execute("DELETE FROM chat_messages WHERE user_id = ?", (user_id,))
        self.conn.commit()

    # -- App-wide settings (theme etc., not tied to one user) ---------------

    def get_setting(self, key, default=None):
        row = self.conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default

    def set_setting(self, key, value):
        self.conn.execute(
            "INSERT INTO app_settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value", (key, value))
        self.conn.commit()

    # -- Habits -------------------------------------------------------------

    def get_habits_done(self, user_id, day):
        rows = self.conn.execute(
            "SELECT habit_id FROM habit_log WHERE user_id = ? AND day = ?", (user_id, day.isoformat())).fetchall()
        return {r["habit_id"] for r in rows}

    def toggle_habit(self, user_id, habit_id, day):
        key = (user_id, habit_id, day.isoformat())
        exists = self.conn.execute(
            "SELECT 1 FROM habit_log WHERE user_id = ? AND habit_id = ? AND day = ?", key).fetchone()
        if exists:
            self.conn.execute("DELETE FROM habit_log WHERE user_id = ? AND habit_id = ? AND day = ?", key)
        else:
            self.conn.execute("INSERT INTO habit_log (user_id, habit_id, day) VALUES (?, ?, ?)", key)
        self.conn.commit()
        return not exists  # True if it is now checked

    def get_all_habit_days(self, user_id):
        """{habit_id: set of dates it was ticked} for every habit ever ticked."""
        from datetime import date
        result = {}
        for row in self.conn.execute("SELECT habit_id, day FROM habit_log WHERE user_id = ?", (user_id,)):
            result.setdefault(row["habit_id"], set()).add(date.fromisoformat(row["day"]))
        return result

    def get_habit_days(self, user_id, habit_id):
        """Set of dates (datetime.date) on which this habit was ticked."""
        from datetime import date
        rows = self.conn.execute(
            "SELECT day FROM habit_log WHERE user_id = ? AND habit_id = ?", (user_id, habit_id)).fetchall()
        return {date.fromisoformat(r["day"]) for r in rows}

    # -- Sleep ----------------------------------------------------------------

    def log_sleep(self, user_id, day, hours, quality):
        self.conn.execute(
            """INSERT INTO sleep_log (user_id, day, hours, quality) VALUES (?, ?, ?, ?)
               ON CONFLICT(user_id, day) DO UPDATE SET hours = excluded.hours, quality = excluded.quality""",
            (user_id, day.isoformat(), hours, quality))
        self.conn.commit()

    def get_sleep(self, user_id, day):
        row = self.conn.execute(
            "SELECT hours, quality FROM sleep_log WHERE user_id = ? AND day = ?", (user_id, day.isoformat())).fetchone()
        return dict(row) if row else None

    def get_sleep_history(self, user_id, limit=14):
        rows = self.conn.execute(
            "SELECT * FROM (SELECT day, hours, quality FROM sleep_log WHERE user_id = ? ORDER BY day DESC LIMIT ?) "
            "ORDER BY day ASC", (user_id, limit)).fetchall()
        return [dict(r) for r in rows]

    # -- Weekly summary -----------------------------------------------------------

    def get_week_summary(self, user_id, start_day):
        """Counts for the 7 days beginning at `start_day` (a date)."""
        from datetime import datetime, time as dtime, timedelta
        end_day = start_day + timedelta(days=7)
        start_ms = int(datetime.combine(start_day, dtime.min).timestamp() * 1000)
        end_ms = int(datetime.combine(end_day, dtime.min).timestamp() * 1000)

        def count(table):
            return self.conn.execute(
                f"SELECT COUNT(*) AS n FROM {table} WHERE user_id = ? AND timestamp >= ? AND timestamp < ?",
                (user_id, start_ms, end_ms)).fetchone()["n"]

        moods = [r["mood"] for r in self.conn.execute(
            "SELECT mood FROM mood_history WHERE user_id = ? AND timestamp >= ? AND timestamp < ?",
            (user_id, start_ms, end_ms)).fetchall()]
        habits = self.conn.execute(
            "SELECT COUNT(*) AS n FROM habit_log WHERE user_id = ? AND day >= ? AND day < ?",
            (user_id, start_day.isoformat(), end_day.isoformat())).fetchone()["n"]
        sleep = self.conn.execute(
            "SELECT AVG(hours) AS h FROM sleep_log WHERE user_id = ? AND day >= ? AND day < ?",
            (user_id, start_day.isoformat(), end_day.isoformat())).fetchone()["h"]
        return {
            "checkins": len(moods), "moods": moods,
            "journal": count("journal_entries"), "meals": count("nutrition_history"),
            "exercises": count("exercise_sessions"), "habits": habits, "sleep_avg": sleep,
        }

    # -- Activity summaries (used by the Today dashboard) --------------------

    def get_activity_days(self, user_id):
        """Set of local calendar dates (datetime.date) on which the user did
        anything - a mood check-in, journal entry, meal or exercise."""
        from datetime import datetime
        days = set()
        for table in ("mood_history", "journal_entries", "nutrition_history", "exercise_sessions"):
            rows = self.conn.execute(f"SELECT timestamp FROM {table} WHERE user_id = ?", (user_id,)).fetchall()
            for r in rows:
                days.add(datetime.fromtimestamp(r["timestamp"] / 1000).date())
        from datetime import date
        for table in ("habit_log", "sleep_log"):
            rows = self.conn.execute(f"SELECT day FROM {table} WHERE user_id = ?", (user_id,)).fetchall()
            days.update(date.fromisoformat(r["day"]) for r in rows)
        return days

    def count_rows(self, table, user_id):
        return self.conn.execute(f"SELECT COUNT(*) AS n FROM {table} WHERE user_id = ?", (user_id,)).fetchone()["n"]

    def export_all(self, user_id):
        """Everything stored for this user, as plain dicts, for JSON export."""
        user = self.conn.execute("SELECT id, name, email FROM users WHERE id = ?", (user_id,)).fetchone()
        return {
            "user": dict(user) if user else None,
            "profile": self.get_profile(user_id),
            "mood_history": self.get_mood_history(user_id),
            "journal_entries": self.get_journal_entries(user_id),
            "nutrition_history": self.get_nutrition_history(user_id),
            "exercise_sessions": self.get_exercise_history(user_id),
            "chat_messages": self.get_chat_messages(user_id, limit=100000),
            "favorite_affirmations": self.get_favorite_ids(user_id),
            "habit_log": [dict(r) for r in self.conn.execute(
                "SELECT habit_id, day FROM habit_log WHERE user_id = ? ORDER BY day", (user_id,)).fetchall()],
            "sleep_log": self.get_sleep_history(user_id, limit=100000),
        }

    # -- Session (who's currently signed in) --------------------------------

    def get_session_user_id(self):
        row = self.conn.execute("SELECT user_id FROM session WHERE id = 1").fetchone()
        return row["user_id"] if row else None

    def set_session_user_id(self, user_id):
        self.conn.execute(
            "INSERT INTO session (id, user_id) VALUES (1, ?) "
            "ON CONFLICT(id) DO UPDATE SET user_id = excluded.user_id",
            (user_id,),
        )
        self.conn.commit()

    def sign_out(self):
        """Clears only the session pointer. Profiles, mood history, and
        journal entries all stay in the database, tied to the user's account."""
        self.conn.execute("DELETE FROM session WHERE id = 1")
        self.conn.commit()
