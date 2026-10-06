# Daily reviews and strategy changes (PAPER challenge)

## 2026-10-06 (08:30 ET, user request)

* Equity $99,990 (Alpaca), holding SPY 77 and AVGO 164 from the 08:26 ET breakout entries.
* Change: entries now also take trend signals (close and EMA20 on the same side of EMA50), not only 20 bar breakouts. Breakouts still go first, then the strongest trends, up to 6 positions.
* Why: the user asked for the account to hold positions and be used actively; breakout only entries left it in cash most of the time.
* Unchanged: stops, $25,000 floor, paper guard, leverage caps.

## 2026-10-06 (10:10 ET, user request)

* Change: the $25,000 equity floor is removed (`equity_floor` set to 0 in `trading/state.json`). The user accepted that Alpaca may restrict the account if equity drops low.
* Unchanged: paper only guard, a stop on every position, buy only options, unique order ids, 1.9x overnight cap, end at 04:30 ET on 2026-10-13.

## 2026-10-06 (10:20 ET, user request)

* Change: goal raised to 5x minimum ($500,000, no upper limit). Deadline moved to 2026-10-20 18:00 SGT. Last stock session 2026-10-19 (stocks and options close at 15:50 ET); crypto runs until 04:30 ET on 2026-10-20 (16:30 SGT), then everything is closed and the final report written.
* Updated: `trading/state.json` (target_equity, target_date, stocks_end_et, end_after_et), summary labels and history window in the scripts, tests, RUNNER.md, skill and README.
