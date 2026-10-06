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

## 2026-10-06 (11:20 ET, user request: multiple strategies)

* Equity $101,703 (Alpaca).
* Built: shared strategy definitions (`scripts/strategies.py`), a backtester on 400 days of Alpaca bars with the last 120 days out of sample (`scripts/strategy_backtest.py`), a variant search (`scripts/strategy_search.py`) and `trading/journal/strategy-scoreboard.md`.
* Tested: the live hourly trend strategy loses after costs (profit factor 0.74 in sample, 0.82 out of sample, 27% win rate), RSI(2) pullbacks lose (0.60 / 0.58, average loss bigger than average win), 15 minute ORB about breakeven (0.90 / 0.96). Variant search: hourly breakouts on stocks only (50 bar high, 3 ATR stop, exit below EMA50) 1.15 / 0.97; overnight hold of stocks above their 20 day average 1.11 / 1.03; 30 minute ORB longs 1.00 / 0.88; daily IBS had too few trades in 400 days to judge.
* Change: live weights breakout 0.4, overnight 0.4, orb (30 minute, long only) 0.2. Trend and rsi2 get weight 0: no new trades, their open positions are still managed by their exit rules. No strategy is clearly profitable out of sample yet, so the search continues every day.
