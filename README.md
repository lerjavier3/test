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
| `trading/` | Also holds the runtime state file and daily journal |

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
