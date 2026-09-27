#!/bin/sh
# Evidence 4 - database queries: onboarding fields (six), journal entry, and persistence across a restart.
# Regenerate:  sh evidence/04_database_evidence.sh
# Uses a scratch database (evidence/output/evidence.db), never your real mind_fusion.db.
cd "$(dirname "$0")/.." || exit 1
DB=evidence/output/evidence.db
OUT=evidence/output/04_database_evidence.txt
rm -f "$DB"
q() { sqlite3 -header -column "$DB" "$1"; }
filt() { grep -v "propagateSizeHints\|^objc\[\|qt.qpa.fonts"; }
{
echo "# Database evidence - $(date '+%Y-%m-%d %H:%M:%S')"
echo "# scratch database: $DB   (sqlite3 $(sqlite3 --version | cut -d' ' -f1))"
echo
echo "############ STEP 1: process A drives the real onboarding wizard and Journal tab"
echo "\$ python evidence/04_database_driver.py --phase write --db $DB"
python evidence/04_database_driver.py --phase write --db "$DB" 2>&1 | filt
echo
echo "############ STEP 2: query the database directly with the sqlite3 command-line tool"
echo
echo "\$ sqlite3 -header -column $DB \"SELECT * FROM users;\""
q "SELECT * FROM users;"
echo
echo "\$ sqlite3 -header -column $DB \"SELECT * FROM profiles;\"     -- the six onboarding answers"
q "SELECT * FROM profiles;"
echo
echo "  (table: profiles; columns: country, language, age_group, conditions, habits, goals = six fields;"
echo "   list fields are stored as JSON text)"
echo "\$ sqlite3 $DB \"SELECT COUNT(*) FROM pragma_table_info('profiles') WHERE name NOT IN ('user_id');\""
sqlite3 "$DB" "SELECT COUNT(*) FROM pragma_table_info('profiles') WHERE name NOT IN ('user_id');"
echo
echo "\$ sqlite3 -header -column $DB \"SELECT id, user_id, prompt, text, mood, datetime(timestamp/1000,'unixepoch','localtime') AS saved_at FROM journal_entries;\""
q "SELECT id, user_id, prompt, text, mood, datetime(timestamp/1000,'unixepoch','localtime') AS saved_at FROM journal_entries;"
echo
echo "\$ sqlite3 -header -column $DB \"SELECT * FROM session;\"      -- who is signed in"
q "SELECT * FROM session;"
echo
echo "\$ sqlite3 -header -column $DB \"SELECT id, mood, datetime(timestamp/1000,'unixepoch','localtime') FROM mood_history;\"   -- journal entry also logged a mood"
q "SELECT id, mood, datetime(timestamp/1000,'unixepoch','localtime') AS at FROM mood_history;"
sqlite3 "$DB" ".dump profiles journal_entries users session mood_history" > evidence/output/.before.sql
echo
echo "############ STEP 3: RESTART - a brand-new operating-system process opens the same file"
echo "\$ python evidence/04_database_driver.py --phase restart --db $DB"
python evidence/04_database_driver.py --phase restart --db "$DB" 2>&1 | filt
echo
echo "############ STEP 4: the same queries after the restart, and a diff of the whole saved data"
echo "\$ sqlite3 -header -column $DB \"SELECT * FROM profiles;\""
q "SELECT * FROM profiles;"
echo
echo "\$ sqlite3 -header -column $DB \"SELECT id, prompt, text, mood FROM journal_entries;\""
q "SELECT id, prompt, text, mood FROM journal_entries;"
sqlite3 "$DB" ".dump profiles journal_entries users session mood_history" > evidence/output/.after.sql
echo
echo "\$ diff <(dump before restart) <(dump after restart)"
if diff evidence/output/.before.sql evidence/output/.after.sql > /dev/null; then
  echo "(no differences - every saved row is byte-for-byte identical after the restart)"
else
  diff evidence/output/.before.sql evidence/output/.after.sql
fi
rm -f evidence/output/.before.sql evidence/output/.after.sql
} > "$OUT" 2>&1
cat "$OUT"
