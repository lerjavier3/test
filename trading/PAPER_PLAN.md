# Paper Trading Plan

What runs first, in what order, and what has to be true before anything moves to real money. The evidence behind each strategy is in `research/RESEARCH.md`.

## Phase 0: access check (before the first trade)

Run `python3 scripts/alpaca.py check` and record the result in `trading/journal/`.

| Check | Needed for | If it fails |
| --- | --- | --- |
| `account_http` is 200 and the endpoint is `paper-api` | everything | Stop. Network policy or keys are wrong. |
| `trading_blocked` and `account_blocked` are false | everything | Stop and tell the user. |
| `daily_bars_ok` | swing sleeves | Stop. No swing signals without daily bars. |
| `minute_history_ok` | ORB backtest, day sleeve | Day sleeve stays off until fixed. |
| `shorting_enabled` | short ORB setups | Day sleeve trades longs only. |
| `pattern_day_trader`, `daytrade_count` | day sleeve | Under $25,000 with PDT still enforced by Alpaca: at most 3 day trades in 5 days, so the day sleeve trades QQQ only and skips once the count reaches 3. |
| `crypto_data_http` is 200 | later crypto sleeve | Ignore for now. |

Required network hosts: `paper-api.alpaca.markets`, `data.alpaca.markets` (and `api.alpaca.markets` only if live trading is ever approved).

## Phase 1: research that needs Alpaca data (first session)

1. Pull QQQ and SPY 1 minute bars from 2016 to now and backtest ORB with 1 to 2 bps spread and slippage per side. Also backtest Plan B (noise area) from `.claude/skills/day-trader/SKILL.md`.
2. Rerun the momentum rotation on the exact live universe with Alpaca daily bars through today.
3. Write the results into `research/results/` and update `research/RESEARCH.md` section 7.

## Phase 2: paper week 1 (all three sleeves, paper money only)

| Order | Strategy | Sleeve | When it trades |
| --- | --- | --- | --- |
| 1 | **Momentum rotation**, top 5 of liquid large caps and sector ETFs, only while SPY is above its 200 day average | Swing core, 60% | Initial entry on the first 15:45 ET run, then month end only |
| 2 | **RSI(2) pullback** on SPY, QQQ, IWM, DIA | Swing filler, 20% | Any day RSI(2) drops below 10 in an uptrend, so possibly no trades in week 1 |
| 3 | **5 minute Opening Range Breakout** on QQQ and SPY | Day, 20% | Every market day at 09:36 ET, flat by 15:50 ET |

Week 1 is about **plumbing**, not profit. Pass criteria:

* Every scheduled run fired within 5 minutes of its time, or logged why it skipped.
* Every entry had a stop on the broker side.
* Zero risk rule violations, zero duplicate orders, zero positions the bot can't explain.
* The day sleeve was flat at every close.
* A journal entry exists for every run, plus the Friday weekly summary.

## Phase 3: paper weeks 2 to 8

Keep running unchanged. At the end, compare each sleeve to its backtest:

* Momentum: holding the expected names, stops working.
* RSI(2): win rate roughly 60% to 75% over enough trades (too few trades in 8 weeks to judge return).
* ORB: average R per trade after costs. If the Phase 1 backtest was negative **and** paper is negative, move its 20% to the swing sleeves or switch to Plan B (user approval needed).

## Phase 4: real money (only with written approval)

Only after Phase 3 passes and the user says so in writing:

1. Set `"mode": "live"` in `trading/state.json` and `ALPACA_PAPER=false` in the environment.
2. Start with the swing sleeves only. The day sleeve stays on paper until it has a positive edge after costs.
3. Same risk rules. The 15% drawdown halt applies to real money exactly as on paper.

## Not in the plan yet

* **Crypto (BTC, ETH):** trend filter only (hold while above the 200 day average), after testing on Alpaca crypto bars with real fees.
* **Options, leverage, leveraged or inverse ETFs, penny stocks:** excluded by the risk manager.
