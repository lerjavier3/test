# Challenge Routines (PAPER ONLY)

Three Routines, each firing a **fresh session** in the same cloud environment (it holds the Alpaca paper keys). Times in ET. All three are disabled by the final run on 2026-10-13 (see the skill's **End of challenge**). Their ids go into `trading/state.json` → `routines`.

| Name | Cron | Runs |
| --- | --- | --- |
| Challenge hourly | `0 * * * *` (hourly; the server anchors the minute to creation time) | 24/7 until 2026-10-13 16:00 ET |
| Challenge open 09:36 ET | `CRON_TZ=America/New_York 36 9 * * 1-5` | weekdays |
| Challenge close 15:50 ET | `CRON_TZ=America/New_York 50 15 * * 1-5` | weekdays; the 2026-10-13 run is the final run |

## Prompt (same for all three, `<RUN>` is `hourly`, `open` or `close`)

```markdown
PAPER ONLY trading challenge run (<RUN>). Keep this run short: about 6 tool calls, no research.

1. git fetch origin claude/mcp-trading-server-f75a0v && git checkout -B claude/mcp-trading-server-f75a0v origin/claude/mcp-trading-server-f75a0v
2. Read .claude/skills/challenge-trader/SKILL.md and follow "Each run" exactly, as a <RUN> run.
3. Journal with: python3 scripts/challenge.py journal --run <RUN> --note "..."
4. Push with: bash scripts/challenge_push.sh  (pushes only to claude/mcp-trading-server-f75a0v; never open a pull request)
5. If preflight shows the challenge is over, or this is the 15:50 ET run on 2026-10-13, do "End of challenge" from the skill, including disabling every Routine listed in trading/state.json "routines" with update_trigger enabled=false.
If anything is refused by scripts/challenge.py (not paper, floor, duplicate id), do not work around it: journal it and push.
```
