# Challenge master plan (PAPER ONLY)

The single source of truth for the paper trading challenge. If the conversation is compacted, start here. Never use any of this with live money.

## 1. Goal and dates

| Item | Value |
| --- | --- |
| Account | Alpaca **paper**, started 2026-10-06 with $100,000 |
| Target | **$500,000 (5x) minimum, no upper limit**. Keep pushing as high as possible; risk does not change when it is reached |
| Last stock session | Mon 2026-10-19 (US). Stocks and options close at 15:50 ET |
| Crypto | may trade until 04:30 ET on 2026-10-20 |
| Final close and report | 04:30 ET 2026-10-20 (16:30 SGT): close everything, write `trading/journal/challenge-summary.md` |
| User checks the result | 2026-10-20 18:00 SGT |

Be honest in every report: 5x in two weeks is very unlikely. Numbers always come from Alpaca (account, positions, fills), never estimated.

## 2. What the user asked for (all still in force)

* Be bold, take calculated risks, push hard to reach the goal. Trust is given to decide; "do whatever you need".
* Risk **up to 10% of the account on a setup**, only on proven, high quality setups. No random ("chapalang") trades.
* Keep testing other setups too, any style (day trading, swing, overnight, mean reversion, momentum, breakouts, gaps, volume, volatility, crypto, anything). Never stop looking for better strategies. Want a high win rate AND winners bigger than losers.
* Run 2 or 3 strategies side by side, compare, move money to the best. Judge a live strategy after 15 to 20 trades unless clearly broken.
* Backtests: at least 1 year of data, judged on a period they were not tuned on.
* No stupid risks: no trade without a stop, no doubling down on losers, no revenge trading, no betting the whole account on one trade, no opposite positions in the same symbol. Leverage limits apply to all strategies combined.
* Real broker stop order for every stock position; never hold a stock overnight through its earnings; keep cash free for weekend crypto if a crypto strategy works.
* $25,000 floor removed (user accepted the account may get restricted).
* Keep strategies simple, no over engineering. Research only what can improve results. Save tokens.
* Communication: one word "ok" replies on check ins; a **mini daily P&L report (2 lines) at 21:58 SGT**; one full final report at the end with exact entry and exit rules for each strategy so they can be traded by hand. Only message otherwise if something breaks or the user asks.
* Keep `trading/PLAYBOOK.md` of proven strategies (exact rules, indicators, win rate, average win vs loss, works without leverage or not) for later real money use.
* User preferences: no dashes in answers; deliverables as Markdown files.

## 3. Live strategies now (2026-10-08)

Defined in `scripts/strategies.py` (shared by the live runner and the backtester). Weights in `trading/state.json` → `weights`. All three trade only near the close, 15:50 to 15:58 ET, on 38 liquid symbols (`S.WIDE`).

| Strategy | Weight | Entry | Exit | Backtest (in sample / last 120 days) |
| --- | --- | --- | --- | --- |
| `rsi2d` | 0.4 | Daily RSI(2) < 10 and close > SMA200 | Close > SMA5, or 10 days; stop 3 ATR(14) | PF 1.60 (70% wins) / 2.90 (78%) |
| `ibs` | 0.35 | IBS < 0.1 and close > SMA200 | Close > previous day's high, or 5 days; stop 3 ATR(14) | PF 1.55 (64%) / 1.34 (56%) |
| `reversal` | 0.25 | Buy the 2 worst 1 day returns of the universe | Next regular open; 3% emergency stop | PF 1.14 / 1.10 (54%) |

Retired (weight 0, they only manage leftover positions): `trend`, `rsi2`, `orb`, `breakout`, `overnight`. Candidate not live: crypto daily trend above SMA50 (too few recent trades).

Universe excludes JPM, BAC, UNH, NFLX, PEP, KO, XOM, CVX (earnings may fall before 2026-10-20). Earnings dates: `trading/earnings.json`.

## 4. Sizing and limits (`scripts/challenge_run.py`)

| Rule | Value |
| --- | --- |
| Normal risk per trade | 4% of equity at equal weights, scaled by the strategy's weight × number of strategies (half outside regular hours) |
| **A+ setup** (`rsi2d` or `ibs` signal that also has RSI(2) < 5 and IBS < 0.15) | **10% of equity at risk**, up to 1x equity in one position, may use free capacity beyond its strategy's share. Backtest PF 2.16 in sample, 92% wins out of sample |
| One position cap | 1.0x equity intraday, 0.6x after 15:40 ET and outside regular hours (A+ up to 1.0x) |
| Gross exposure | 3.5x intraday; new entries after 15:40 ET stop at 1.8x; trim to 1.9x from 15:45 ET and outside regular hours |
| Positions | at most 6 per strategy, 12 total, one per symbol |
| Cooldown | 60 minutes before re-entering a symbol after any close |
| Crypto | cash only, long only, broker stop_limit |
| Reversal | each of its 2 picks gets half of the strategy's share |

## 5. Hard guards (never removed)

Paper only guard (refuses unless the paper endpoint, `ALPACA_PAPER` not false, `mode` = `paper_challenge`); a stop on every trade; real GTC broker stop for every stock position (`backup_stops`, placed last in each tick; closes cancel orders from a fresh Alpaca list); buy only options; unique `client_order_id` (`ch-<strategy>-<SYMBOL>-<stamp>-<n>`); one position per symbol; cooldown; combined leverage caps; no overnight hold into earnings; the 2026-10-20 04:30 ET end.

## 6. How it runs

* **Bot:** `python3 scripts/challenge_run.py --loop --max-minutes 110 >> trading/challenge.log 2>&1`, always started with the Bash tool's `run_in_background: true` and timeout 7200000. Never `nohup` or `setsid`: detached processes die when the container is suspended. The bot exits every 110 minutes; its exit notification wakes the session, which restarts it at once. After a container restart, `git fetch` / check status, then restart it. Ticks: 5 min regular session, 15 min pre, post, overnight, 30 min weekends. It pushes `trading/` about hourly.
* **Process check:** `pgrep -af "^python3 scripts/challenge_run.py --loop"` (anchored so it never matches its own shell).
* **Push:** `bash scripts/challenge_push.sh` (retries, merges `state.json` conflicts). GitHub 500 errors happen; just retry later.
* **Editing `trading/state.json`:** only while the bot is stopped (it rewrites the file every tick): stop the task, edit, test, restart.
* **Tests:** `bash scripts/challenge_test.sh` (11 dry run scenarios, no orders) must pass after every code change. One tick dry run: `python3 scripts/challenge_run.py --once --dry-run`.

## 7. Scheduled check ins and reports

* **Check ins:** self chaining `send_later` into this session with the message in `trading/RUNNER.md` → "Check in": every 60 minutes 08:00 to 17:00 ET on weekdays, every 240 minutes otherwise. Each one: confirm the bot runs (restart if not), push, schedule the next, reply "ok". Stop scheduling after the challenge ends or after the loop fails on 2 check ins in a row (log why).
* **Daily review:** the first check in after 16:00 ET on a weekday when `trading/journal/reviews.md` has no entry for today. Run `python3 scripts/strategy_backtest.py` (refreshes `trading/journal/strategy-scoreboard.md`), test at least one new batch of ideas (`scripts/strategy_search.py`, `scripts/strategy_ideas.py` or inline), adjust weights or promote a strategy only if it wins in sample and out of sample, fix real bugs only, update `trading/PLAYBOOK.md` when a strategy qualifies, recheck earnings dates within 7 days, run tests, restart, log in `reviews.md`, push.
* **Mini daily P&L report:** Routine "Daily P&L report" `trig_01Phf3qgZKsGRCrbriVpr7ju`, cron `CRON_TZ=Asia/Singapore 58 21 * * *`, fires into this session; reply 2 lines with Alpaca numbers; it disables itself after the challenge.

## 8. End of challenge (automatic in the bot)

15:50 ET 2026-10-19: close all stocks and options. Crypto only until 04:30 ET 2026-10-20, then cancel all orders, close everything, refresh the scoreboard, write `trading/journal/challenge-summary.md` (start and end equity, return, best and worst trades, max drawdown, leverage used, daily reviews and strategy changes, scoreboard with exact rules, a sane real money plan), set `challenge_active` false and exit. Then: push, stop check ins, make sure the summary has the exact entry and exit rules of every strategy, and send the user the final report.

## 9. Files

| Path | What |
| --- | --- |
| `trading/state.json` | mode, target, dates, weights, owners, mental stops, cooldowns, peak, drawdown, leverage samples |
| `trading/journal/YYYY-MM-DD.md` | every action of the bot |
| `trading/journal/reviews.md` | every review and strategy change with reasons and numbers |
| `trading/journal/strategy-scoreboard.md` | backtest and live results per strategy, exact rules |
| `trading/PLAYBOOK.md` | proven strategies for later real money use (none qualified yet) |
| `trading/RUNNER.md` | check in and daily review procedure |
| `trading/earnings.json` | earnings dates used by the no hold rule |
| `scripts/challenge_run.py` | the bot; `strategies.py` rules; `strategy_backtest.py` scoreboard; `strategy_search.py`, `strategy_ideas.py` research |

## 10. History in brief

* 2026-10-06: built the bot; first strategy (hourly trend) lost in backtests and live; multi strategy framework, backtester and scoreboard added; floor removed; goal raised to 5x by 2026-10-20; bugs fixed (overnight limit churn, partial fills counted as trades, loop sleeping past its exit, detached process dying, rate limits).
* 2026-10-07: wider search; IBS and reversal promoted; universe widened to 38 symbols; daily RSI(2) added; reversal capital split fixed.
* 2026-10-08: risk per trade raised to 4%; A+ setups get 10% risk and up to 1x equity. Equity before the open: $97,869.73 (−2.1% since start).
