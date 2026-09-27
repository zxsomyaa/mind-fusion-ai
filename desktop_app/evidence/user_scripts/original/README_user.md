
# Collecting evidence for the test cases

Two files do the work. Put both in the folder where your application's Python
modules live, so they can import them, and run them from there.

    test_components.py     the unit suite for the three components
    evidence_run.py        everything else, one command per kind of proof

Each command writes a text file into `./evidence/`. Send me those files and I
will lay them out as listings in the appendix, with the test-case table
pointing at each one the way the status column already points at figures.

---

## Before the first run

Open each file and edit the CONFIG block at the top. You are telling the
scripts where your own code lives:

    MOOD_MAPPER   = "mood:detect_mood"        # module : function
    FUSION_ENGINE = "fusion:fuse"
    RECOMMENDER   = "recommend:get_recommendations"
    DB_PATH       = ""                        # leave blank and it will search
    CHAT_MODEL    = "llama3"                  # exactly as `ollama list` prints it

If a component's real signature differs from what the tests assume, change the
test rather than the component — the tests exist to describe your code, not to
impose a shape on it. Tell me what you changed and I will match the report to it.

---

## Run these, in this order

**1. The unit suite.** This is the strongest single artefact you can produce,
and Section 5.2 already claims it exists.

    pip install pytest
    pytest -v test_components.py | tee evidence/pytest.txt

Twenty-six tests: the eight moods, the empty and neutral paths, the divisor
floor, tie determinism, the fusion engine either side of the 0.12 margin, the
live disagreement from Figure 9, and the recommender's three-item contract,
contraindication filter and de-duplication.

One test is marked `xfail` — negation. It is *expected* to fail, because
TC-E01 is a known defect. If it ever passes, pytest says XPASS and you have
fixed something without noticing.

**2. Latency.** The biggest gap in the report. Objective 5 currently reads "met
on the web prototype; not yet established for the desktop build", and Table 10
has a row saying "not yet measured". One command closes both.

    python3 evidence_run.py bench

Ignore the first run if it is far slower than the rest — that is the model
loading into memory. Report the warm figure and say so.

**3. The mood matrix.** Twelve inputs, expected against detected, in one table.

    python3 evidence_run.py moods

Two rows will say MISMATCH: the negation case and the Hindi one. Leave them.
They are TC-E01 and TC-E02, both already recorded as failures, and a table that
shows its own failures is worth more than one that does not.

**4. The database.** Proof that onboarding and the journal really persist.

    python3 evidence_run.py db          # then quit the app, reopen it, run again

Read the output before sending it and delete anything personal. Use the test
profile, not your own.

**5. Models and versions.** Confirms Table 5, which currently rests on my
assumptions about which checkpoints you pulled.

    python3 evidence_run.py models

**6. Filesystem.** Run it once, do a voice check-in, run it again. The second
run lists what appeared in between; TC-I08 passes if no audio file did.

    python3 evidence_run.py privacy
    # do a voice check-in in the app
    python3 evidence_run.py privacy

**7. The nutrition analyser, twice on one photograph.** Needs Ollama running.

    python3 evidence_run.py meal ~/Desktop/tacos.jpg
    python3 evidence_run.py meal ~/Desktop/tacos.jpg --nofood ~/Desktop/desk.jpg

The second form also sends an image with no food in it. If llava invents a
meal, that is TC-F22, already recorded as a failure — this is what makes it
demonstrable rather than asserted.

Or run everything except the meal analysis in one go:

    python3 evidence_run.py all

---

## Still needs a screenshot

Four things are only visible in the interface, so they need a capture rather
than a log:

- the crisis alert firing, with the helpline panel
- the fallback reply with Ollama stopped, and the sidebar showing it is down
- the Journal screen with an entry and the search box
- a guided exercise mid-timer

---

## One rule

Anything you did not run stays Blocked in the table. The report's credibility
comes from the failures it admits — TC-E01, TC-E02, TC-E03, TC-E12, TC-F21,
