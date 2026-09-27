"""
Driver for evidence 4. Run by evidence/04_database_evidence.sh - not meant to be run alone.

  --phase write    : drives the REAL onboarding wizard and journal code against a scratch database
  --phase restart  : a NEW process opens the same file and starts the real AppWindow, to show
                     the saved account, profile and journal come back without re-entering anything
"""
import argparse
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtWidgets import QApplication   # noqa: E402
from db import Database                       # noqa: E402

parser = argparse.ArgumentParser()
parser.add_argument("--phase", required=True, choices=["write", "restart"])
parser.add_argument("--db", required=True)
args = parser.parse_args()
app = QApplication([])

if args.phase == "write":
    from ui.onboarding import OnboardingWidget
    from ui.tabs.journal_tab import JournalTab

    db = Database(args.db)
    ob = OnboardingWidget(db)
    ob.resize(1240, 800)
    ob.show()
    done = []
    ob.login_completed.connect(done.append)

    # --- sign up (screen 1) ---
    ob.su_name.setText("Evidence User")
    ob.su_email.setText("evidence@example.com")
    ob.su_password.setText("secret123")
    ob._handle_signup()

    # --- the five profile steps, using the real widgets' own handlers ---
    chip = lambda flow, text: next(flow.itemAt(i).widget() for i in range(flow.count()) if text in flow.itemAt(i).widget().text())
    ob._pick_country("IN", chip(ob._country_flow, "India"))
    ob._pick_language("hi", next(c for c in ob._language_chips if "हिंदी" in c.text()))
    ob._wizard_next()
    ob._pick_age("25-34")
    ob._wizard_next()
    ob._toggle("conditions", "anxiety")
    ob.custom_condition_input.setText("Migraine aura")
    ob._add_custom_condition()
    ob._wizard_next()
    ob._toggle("habits", "exercise")
    ob._toggle("habits", "meditation")
    ob._wizard_next()
    ob._toggle_goal("reduce_stress")
    ob._toggle_goal("better_sleep")
    ob._wizard_next()                      # last step -> saves the profile and signs in
    print(f"onboarding finished; login_completed emitted for user id {done}")

    # --- a journal entry, via the real Journal tab ---
    journal = JournalTab(db, done[0])
    journal.text_box.setPlainText("Today was stressful at work, but a long walk in the evening helped me feel calmer.")
    journal._save_entry()
    print("journal entry saved via JournalTab._save_entry()")
    db.conn.close()

else:
    from main import AppWindow
    from ui.tabs.journal_tab import JournalTab

    db = Database(args.db)
    print(f"process {os.getpid()} opened {Path(args.db).name}")
    print(f"session table says signed-in user id: {db.get_session_user_id()}")
    win = AppWindow(db)                    # exactly what main.py builds at start-up
    main = win.main_widget
    print(f"start-up went straight to the main app (no sign-in / onboarding screen): {main is not None}")
    if main is not None:
        print(f"  signed-in user : {main.user['name']} <{main.user['email']}>")
        print(f"  profile loaded : country={main.profile['country']} language={main.profile['language']} "
              f"age={main.profile['age_group']} conditions={main.profile['conditions']} "
              f"habits={main.profile['habits']} goals={main.profile['goals']}")
        journal = main.journal_tab
        print(f"  journal tab lists {journal.entries_layout.count() - 1} saved entr{'y' if journal.entries_layout.count() - 1 == 1 else 'ies'} without being asked to reload")
        main.shutdown()
        if main._connection_worker:
            main._connection_worker.wait(4000)
    db.conn.close()
