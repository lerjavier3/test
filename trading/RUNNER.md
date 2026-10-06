# Challenge runner (PAPER ONLY)

The trading is done by one deterministic script, `scripts/challenge_run.py`, running as a background loop in the cloud container. The loop itself spends no Claude tokens. No fresh session Routines are used.

## Loop

```bash
nohup python3 scripts/challenge_run.py --loop >> trading/challenge.log 2>&1 &
```

| Session (ET) | Checks every | Trades |
| --- | --- | --- |
| Regular 09:30 to 16:00 | 5 min | stocks long and short, crypto, QQQ calls or puts once a day after 09:35 |
| Pre 04:00 to 09:30, post 16:00 to 20:00, overnight 20:00 to 04:00 | 15 min | stock longs (limit, extended hours, half risk), crypto |
| Weekend | 30 min | crypto only |

It pushes `trading/` about hourly. The last stock session is 2026-10-12: at 15:50 ET it closes every stock and option position and only crypto trades after that. At 04:30 ET on 2026-10-13 (16:30 SGT) it closes everything, writes `trading/journal/challenge-summary.md` and exits 0, ready before the user checks at 06:00 ET (18:00 SGT). It exits 2 if the paper guard refuses, and 3 after 5 failed ticks in a row.

Test without placing orders: `python3 scripts/challenge_run.py --once --dry-run`.

## Check in

Scheduled with `send_later` into this session: every 60 minutes from 08:00 to 17:00 ET on weekdays, every 240 minutes otherwise. The container is reclaimed soon after the session goes idle, which kills the loop, so the check in is mainly what keeps it alive during market hours.

Each check in, a handful of tool calls:

1. `cd /home/user/test; pgrep -f "^python3 scripts/challenge_run.py --loop"; tail -3 trading/challenge.log`
2. If not running and `challenge_active` is true in `trading/state.json`: `git pull -q origin claude/mcp-trading-server-f75a0v`, then `(setsid nohup python3 scripts/challenge_run.py --loop >> trading/challenge.log 2>&1 < /dev/null &)` and confirm with `pgrep`.
3. `bash scripts/challenge_push.sh`
4. **Daily review**, only if it is a weekday, after 16:00 ET, and `trading/journal/reviews.md` has no entry for today (ET): do the review below.
5. Hard stop: if the loop failed to start or had crashed (exit 3 in the log) on this check in and the previous one, don't schedule another. Log why in `trading/journal/errors.md` and push.
6. If `challenge_active` is false: confirm `trading/journal/challenge-summary.md` exists, push, stop scheduling.
7. Otherwise schedule the next check in (same message), 60 or 240 minutes out as above. Reply in 2 lines at most.

## Daily review (once a day, first check in after the US close)

1. Read today's `trading/journal/YYYY-MM-DD.md`, `tail -40 trading/challenge.log` and `python3 scripts/challenge.py summary`.
2. Judge what worked and what didn't: trades, stops hit, signals that never fired, errors, gaps. A short web search is fine if it helps, for example scheduled market events for the next session.
3. Keep changes minimal: fix what is actually broken, no new features. Every number written to the journal or reviews comes from Alpaca (account, positions, fills), never estimated.
   Then, if a change is likely to improve the odds of reaching $300,000 or more by the deadline, edit `scripts/challenge_run.py`. Allowed: anything within the same paper challenge. Never removed: the paper only guard, a stop on every position, the $25,000 floor, buy only options, unique order ids, the 1.9x overnight cap and the 2026-10-13 04:30 ET end.
4. `bash scripts/challenge_test.sh` must pass. If it fails and can't be fixed quickly, revert the change.
5. Restart the loop: `pkill -f "^python3 scripts/challenge_run.py --loop"`, then start it as in step 2.
6. Append to `trading/journal/reviews.md`: `## YYYY-MM-DD`, equity and day P&L, what happened, the change made (or "no change") and why. The final summary includes this file.
7. Commit the code and journal, then `bash scripts/challenge_push.sh`.
