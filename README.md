# Claude Trading Bot (Alpaca)

Research and playbooks for an automated trading routine run by Claude Code on a schedule.

## Layout

| Path | What it is |
| --- | --- |
| `research/RESEARCH.md` | Strategy research, backtest results and the plan |
| `research/results/` | Full backtest tables |
| `research/backtests/` | Backtest code (`swing.py`, `day.py`) |
| `scripts/get_data.sh` | Downloads the free datasets used by the backtests |
| `.claude/skills/risk-manager/` | Hard risk rules, loaded before every trade |
| `.claude/skills/swing-trader/` | Daily swing routine (momentum rotation plus RSI(2) pullbacks) |
| `.claude/skills/day-trader/` | Intraday Opening Range Breakout routine (experimental) |
| `scripts/alpaca.py` | Standard library Alpaca client (paper by default), used when the Alpaca MCP isn't connected |
| `trading/PAPER_PLAN.md` | Which strategies run first, paper test phases and the bar for real money |
| `.claude/skills/challenge-trader/` | **PAPER ONLY** one week aggressive challenge (margin, shorts, crypto, long options, 24/7) |
| `scripts/challenge_run.py` | Deterministic challenge runner: one tick or a self running loop (`--loop`, `--dry-run`) |
| `scripts/challenge.py`, `scripts/challenge_push.sh` | Challenge helpers (paper guard, $25,000 floor, signals, guarded manual orders, summary) and conflict safe push |
| `trading/RUNNER.md` | How the challenge loop runs, the check ins and the daily strategy review |
| `scripts/challenge_test.sh` | Dry run tests of the runner across every session (no orders) |
| `trading/` | Also holds the runtime state file and the journal |

## Rerun the backtests

```bash
bash scripts/get_data.sh data_cache
cd research/backtests
python3 swing.py ../../data_cache ../results/swing_results.md
python3 day.py ../../data_cache ../results/day_results.md
```

## Setup checklist

1. Alpaca paper account and API keys, stored as environment secrets `ALPACA_API_KEY`, `ALPACA_SECRET_KEY` and `ALPACA_PAPER=true`
2. Cloud environment network access allows `api.alpaca.markets`, `paper-api.alpaca.markets` and `data.alpaca.markets`. Verify with `python3 scripts/alpaca.py check`
3. Alpaca MCP server connected (optional: `scripts/alpaca.py` covers everything the skills need)
4. Budget, target amount and target date written into `trading/state.json`
5. Scheduled runs: 09:36 ET (day entry), 15:45 ET (swing), 15:50 ET (day exit), on market days

## Paper challenge mode (never with live money)

`trading/state.json` currently has `"mode": "paper_challenge"`: a one week aggressive paper experiment the user asked for ($100,000 to a $300,000 target by 2026-10-13, with margin, shorts, crypto and long calls or puts, around the clock). Its rules are in `.claude/skills/challenge-trader/` and run as a background loop of `scripts/challenge_run.py` (see `trading/RUNNER.md`). The $300,000 target is a minimum, not a cap: the loop keeps trading the same way after reaching it.

* **The challenge rules must never be used with live money.** `scripts/challenge.py` refuses to run on anything but the paper endpoint.
* Reaching 3x in a week is extremely unlikely; the most likely outcome is a large loss. It is a stress test of the plumbing and an illustration of what leverage does, not a plan.
* The conservative `risk-manager`, `swing-trader` and `day-trader` rules are unchanged and remain the only rules for any real money use. They don't run while the challenge mode is active. After the challenge, reset `trading/state.json` to the `"mode": "paper"` structure in the risk manager skill before using them.
