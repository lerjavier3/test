# Challenge runner (PAPER ONLY)

The trading is done by one deterministic script, `scripts/challenge_run.py`, running as a background loop in the cloud container. The loop itself spends no Claude tokens. No fresh session Routines are used.

## Loop

Start it with the Bash tool's `run_in_background: true`, never `nohup` (see Check in step 2).

```bash
nohup python3 scripts/challenge_run.py --loop >> trading/challenge.log 2>&1 &
```

| Session (ET) | Checks every | Trades |
| --- | --- | --- |
| Regular 09:30 to 16:00 | 5 min | stocks long and short, crypto, QQQ calls or puts once a day after 09:35 |
| Pre 04:00 to 09:30, post 16:00 to 20:00, overnight 20:00 to 04:00 | 15 min | stock longs (limit, extended hours, half risk), crypto |
| Weekend | 30 min | crypto only |

It pushes `trading/` about hourly. The last stock session is 2026-10-19: at 15:50 ET it closes every stock and option position and only crypto trades after that. At 04:30 ET on 2026-10-20 (16:30 SGT) it closes everything, writes `trading/journal/challenge-summary.md` and exits 0, ready before the user checks at 06:00 ET (18:00 SGT). It exits 2 if the paper guard refuses, and 3 after 5 failed ticks in a row.

Test without placing orders: `python3 scripts/challenge_run.py --once --dry-run`.

## Check in

Scheduled with `send_later` into this session: every 60 minutes from 08:00 to 17:00 ET on weekdays, every 240 minutes otherwise. The container is reclaimed soon after the session goes idle, which kills the loop, so the check in is mainly what keeps it alive during market hours.

Each check in, a handful of tool calls:

1. `cd /home/user/test; pgrep -f "^python3 scripts/challenge_run.py --loop"; tail -3 trading/challenge.log`
2. If not running and `challenge_active` is true in `trading/state.json`: `git pull -q origin claude/mcp-trading-server-f75a0v`, then start it with the **Bash tool's `run_in_background: true`** (timeout 7200000): `python3 scripts/challenge_run.py --loop --max-minutes 115 >> trading/challenge.log 2>&1`. A detached `nohup`/`setsid` process dies when the container is suspended after the turn; a tracked background task keeps the container alive, and its exit (every 115 minutes) wakes this session to restart it.
3. `bash scripts/challenge_push.sh`
4. **Daily review**, only if it is a weekday, after 16:00 ET, and `trading/journal/reviews.md` has no entry for today (ET): do the review below.
5. Hard stop: if the loop failed to start or had crashed (exit 3 in the log) on this check in and the previous one, don't schedule another. Log why in `trading/journal/errors.md` and push.
6. If `challenge_active` is false: confirm `trading/journal/challenge-summary.md` exists, push, stop scheduling.
7. Otherwise schedule the next check in (same message), 60 or 240 minutes out as above. Reply with one word, "ok" (or "failed: <reason>"), except the daily review check in, which replies with the daily P&L report.

## Daily review (once a day, first check in after the US close)

The user wants a MINI daily P&L report (to save tokens), as the reply to the daily review check in, 2 lines max, Alpaca numbers only, e.g. `Equity $101,192 | day -$650 (-0.6%) | total +1.2% | 5x progress 0% | 7 positions | 3W 2L today` and one line for any strategy change. Other check ins reply "ok".

1. `python3 scripts/strategy_backtest.py` (backtests every strategy in `scripts/strategies.py` on 400 days, in sample vs the last 120 days out of sample, plus live results from Alpaca fills) refreshes `trading/journal/strategy-scoreboard.md`. Read it with today's `trading/journal/YYYY-MM-DD.md` and `tail -40 trading/challenge.log`.
2. Search for better strategies every day, even when one works: add simple variants or new ideas to `scripts/strategy_search.py` and run it. Rank on in sample only (at least 30 trades), then check out of sample. Want a high win rate AND average win bigger than average loss (profit factor above 1 in both periods). Research only what can improve results.
3. Promote a variant by adding it to `scripts/strategies.py` (simple rules, a `rules` text precise enough to trade by hand) and giving it a weight.
4. Allocation (`weights` in `trading/state.json`, 2 or 3 strategies live, weights sum to 1): judge a live strategy after 15 to 20 trades unless clearly broken, then move weight toward the best live and out of sample results. A strategy at weight 0 opens nothing new but still manages its open positions.
5. Never removed: paper only guard, a stop on every trade, one position per symbol (no doubling down, no opposite positions), the re-entry cooldown, no single trade risking the account, combined leverage caps, the 2026-10-20 04:30 ET end. No new trade right after a loss in the same symbol.
6. `bash scripts/challenge_test.sh` must pass. Edit `trading/state.json` only while the loop is stopped (it rewrites the file every tick): stop the background task, edit, test, restart it (Check in step 2).
7. Playbook: when a strategy passes all three checks in `trading/PLAYBOOK.md`, add it there with its exact rules and numbers; remove or mark it if it later fails.
8. Earnings: recheck the next report dates for the stocks in `trading/earnings.json` (one short search) if any date is within the next 7 days or unknown. The bot never holds a stock overnight into a report.
9. Crypto: if a crypto strategy is working live, set `crypto_reserve` in `trading/state.json` (share of equity, for example 0.2). On Fridays from 15:40 ET the bot sells its weakest stocks until that much real cash is free for weekend crypto trading. 0 means off.
10. Append to `trading/journal/reviews.md`: `## YYYY-MM-DD`, Alpaca equity, what happened, what was tested, the change (or "no change") and why.
11. Commit code and journal, then `bash scripts/challenge_push.sh`.
