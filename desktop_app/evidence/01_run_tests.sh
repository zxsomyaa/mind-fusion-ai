#!/bin/sh
# Evidence 1 - the automated test suite, verbose, with timings.
# Regenerate:  sh evidence/01_run_tests.sh
cd "$(dirname "$0")/.." || exit 1
OUT=evidence/output/01_pytest_output.txt
{
  echo "# Mind Fusion Desktop - automated test run"
  echo "# command : python -m pytest -v --durations=8 tests/"
  echo "# date    : $(date '+%Y-%m-%d %H:%M:%S %Z')"
  echo "# machine : $(sysctl -n machdep.cpu.brand_string), $(sysctl -n hw.memsize | awk '{printf "%.0f GB", $1/1073741824}') RAM, macOS $(sw_vers -productVersion)"
  echo "# python  : $(python --version 2>&1)"
  echo
  QT_QPA_PLATFORM=offscreen python -m pytest -v --durations=8 -p no:cacheprovider tests/ 2>&1 \
    | grep -v "propagateSizeHints\|^objc\[\|qt.qpa.fonts"
} > "$OUT"
tail -25 "$OUT"
