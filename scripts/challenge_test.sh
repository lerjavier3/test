#!/usr/bin/env bash
# Dry run challenge_run.py through every session and the final days. Places no orders.
# Exits non-zero if any scenario crashes. Run after every strategy change.
cd "$(dirname "$0")/.."
fail=0
run() {
  out=$(python3 scripts/challenge_scenario.py "$@" 2>&1)
  if [ $? -ne 0 ] || grep -q Traceback <<<"$out"; then echo "FAIL $*"; echo "$out" | tail -8; fail=1
  else echo "ok   $* ($(grep -c DRY <<<"$out") orders)"; fi
}
run regular 10:30
run regular 15:50 --pos
run overnight 23:00
run overnight 02:00 --pos
run pre 07:00 --pos
run closed 12:00
run regular 15:52 2026-10-12 --pos
run overnight 22:00 2026-10-12
run pre 04:31 2026-10-13 --pos
python3 scripts/challenge_run.py --once --dry-run >/dev/null 2>&1 || { echo "FAIL live dry run"; fail=1; }
exit $fail
