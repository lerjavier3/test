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

## Check in (about every 4 hours, via send_later into the session that started the loop)

```markdown
Challenge check in. Keep it to a few tool calls, don't read docs.
1. pgrep -f "challenge_run.py --loop" ; tail -5 trading/challenge.log
2. If not running and trading/state.json challenge_active is true: restart it with
   nohup python3 scripts/challenge_run.py --loop >> trading/challenge.log 2>&1 &
   then confirm with pgrep after a few seconds.
3. bash scripts/challenge_push.sh
4. If the loop failed to start or had crashed (exit 3 in the log) on this check in and the previous one,
   do not schedule another check in; log why in trading/journal/errors.md and push.
5. If challenge_active is false (after 2026-10-13 04:30 ET): confirm challenge-summary.md exists, push, stop scheduling.
6. Otherwise schedule the next check in about 4 hours out.
```

The container is reclaimed when the session is idle for a while, which kills the loop. Trading pauses until the next check in restarts it, and the preflight records the gap in `rate_limit_failures`.
