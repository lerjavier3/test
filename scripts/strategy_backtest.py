#!/usr/bin/env python3
"""Backtest every strategy in strategies.py on 400 days of Alpaca bars and score the live trades,
then write trading/journal/strategy-scoreboard.md.

  python3 scripts/strategy_backtest.py            # all strategies
  python3 scripts/strategy_backtest.py rsi2 orb   # some of them

Fills: next bar open after the signal. Stops and targets are checked against each bar's high and low
(stop first when both are touched); gaps fill at the open. Costs per side: ETFs 2 bps, stocks 5 bps,
crypto 25 bps. The last 120 days are out of sample: parameters are never tuned on them, and a strategy
only gets more money if it is profitable there too. Live rows come from Alpaca fills, attributed by
the strategy name in each order's client_order_id. Returns are per trade, unlevered.
"""
import datetime
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import alpaca  # noqa: E402
import challenge as ch  # noqa: E402
import strategies as S  # noqa: E402

OOS_DAYS = 120
ETFS = {"QQQ", "SPY", "IWM"}
BOARD = os.path.join(ch.JOURNAL, "strategy-scoreboard.md")


def cost(sym):
    return 0.0025 if "/" in sym else 0.0002 if sym in ETFS else 0.0005


CACHE = os.path.join(ch.ROOT, ".bt_cache")


def fetch_symbol(sym, timeframe, start, end):
    """Bars for one symbol, cached on disk so each daily review only downloads what is new."""
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, f"{timeframe}_{sym.replace('/', '')}.json")
    bars = json.load(open(path)) if os.path.exists(path) else []
    bars = [b for b in bars if b["t"] >= start]
    since = bars[-1]["t"] if bars else start
    crypto = "/" in sym
    url = f"{ch.DATA}/v1beta3/crypto/us/bars" if crypto else f"{ch.DATA}/v2/stocks/bars"
    params = {"symbols": sym, "timeframe": timeframe, "start": since, "end": end, "limit": 10000}
    if not crypto:
        params.update(feed="sip", adjustment="all")
    new = []
    while True:
        s, d = alpaca.request("GET", url, params)
        if s == 429:
            time.sleep(5)
            continue
        if s != 200:
            raise RuntimeError(f"bars {sym}: http {s} {str(d)[:200]}")
        new += (d.get("bars") or {}).get(sym, [])
        if not d.get("next_page_token"):
            break
        params["page_token"] = d["next_page_token"]
    bars = [b for b in bars if b["t"] < since] + new
    json.dump(bars, open(path, "w"))
    return bars


def fetch(strategy, start, end):
    with ThreadPoolExecutor(4) as pool:  # Alpaca allows about 200 requests a minute
        futures = {s: pool.submit(fetch_symbol, s, strategy.timeframe, start, end) for s in strategy.universe}
    return {s: f.result() for s, f in futures.items()}


def simulate(strategy, sym, bars):
    ind, trades, pos, last_day = strategy.prepare(bars), [], None, None
    for i in range(strategy.warmup, len(bars) - 1):
        b = bars[i]
        if pos:
            px = reason = None
            if pos["side"] == "long" and b["l"] <= pos["stop"]:
                px, reason = min(b["o"], pos["stop"]), "stop"
            elif pos["side"] == "short" and b["h"] >= pos["stop"]:
                px, reason = max(b["o"], pos["stop"]), "stop"
            elif pos["target"] and pos["side"] == "long" and b["h"] >= pos["target"]:
                px, reason = max(b["o"], pos["target"]), "target"
            elif pos["target"] and pos["side"] == "short" and b["l"] <= pos["target"]:
                px, reason = min(b["o"], pos["target"]), "target"
            else:
                reason = strategy.exit(ind, bars, i, pos)
                px = b["c"] if reason else None
            if px is not None:
                sign = 1 if pos["side"] == "long" else -1
                trades.append({"symbol": sym, "t": pos["t"], "ret": sign * (px - pos["entry"]) / pos["entry"] - 2 * cost(sym)})
                pos = None
            continue
        sig = strategy.entry(ind, bars, i)
        if not sig or (sig[0] == "short" and "/" in sym):
            continue
        day = S.et_time(b).date()
        if strategy.name == "orb" and day == last_day:
            continue
        side, stop, r = sig
        entry = bars[i + 1]["o"]
        if (side == "long" and stop >= entry) or (side == "short" and stop <= entry):
            continue
        last_day = day
        pos = {"side": side, "entry": entry, "stop": stop, "entry_i": i + 1, "t": bars[i + 1]["t"],
               "target": entry + r * (entry - stop) if r else None}
    return trades


def overnight_trades(strategy, sym, bars):
    """Buy at the close when the entry rule fires, sell at the next open."""
    ind, out = strategy.prepare(bars), []
    for i in range(strategy.warmup, len(bars) - 1):
        if strategy.entry(ind, bars, i):
            out.append({"symbol": sym, "t": bars[i + 1]["t"], "ret": bars[i + 1]["o"] / bars[i]["c"] - 1 - 2 * cost(sym)})
    return out


def stats(trades):
    if not trades:
        return {"n": 0}
    wins = [t["ret"] for t in trades if t["ret"] > 0]
    losses = [t["ret"] for t in trades if t["ret"] <= 0]
    return {"n": len(trades), "win": len(wins) / len(trades),
            "avg_win": sum(wins) / len(wins) if wins else 0, "avg_loss": sum(losses) / len(losses) if losses else 0,
            "profit": sum(t["ret"] for t in trades),
            "pf": sum(wins) / -sum(losses) if losses and sum(losses) else float("inf")}


def live_trades(state):
    """Closed round trips from Alpaca fills, tagged with the strategy that opened them."""
    tags, token = {}, None
    after = state["start_date"] + "T00:00:00Z"
    while True:
        s, orders = alpaca.request("GET", f"{ch.API}/v2/orders", {"status": "all", "after": after, "limit": 500,
                                                                   "direction": "asc", "nested": "true"})
        if s != 200 or not orders:
            break
        for o in orders:
            parts = (o.get("client_order_id") or "").split("-")
            tag = parts[1] if len(parts) > 2 and parts[0] == "ch" and (parts[1] in S.ALL or parts[1] == "opt") \
                else ("trend" if parts[0] == "ch" else None)  # orders before the multi strategy change were trend
            tags[o["id"]] = tag
            for leg in o.get("legs") or []:
                tags[leg["id"]] = None
        if len(orders) < 500:
            break
        after = orders[-1]["submitted_at"]
    fills = []
    while True:
        s, page = alpaca.request("GET", f"{ch.API}/v2/account/activities/FILL", {
            "after": state["start_date"], "page_size": 100, "page_token": token, "direction": "asc"})
        if s != 200 or not page:
            break
        fills += page
        if len(page) < 100:
            break
        token = page[-1]["id"]
    book, trades = {}, []
    for f in fills:
        sym, qty, px = f["symbol"], float(f["qty"]), float(f["price"])
        mult = 100 if ch.is_option(sym) else 1
        signed = qty if f["side"] == "buy" else -qty
        lots = book.setdefault(sym, [])
        while signed and lots and (lots[0][0] > 0) != (signed > 0):
            lq, lp, tag = lots[0]
            m = min(abs(lq), abs(signed))
            sign = 1 if lq > 0 else -1
            trades.append({"strategy": tag or "trend", "symbol": sym, "ret": sign * (px - lp) / lp,
                           "pnl": sign * (px - lp) * m * mult})
            lq -= m * sign
            signed += m * sign
            if abs(lq) < 1e-12:
                lots.pop(0)
            else:
                lots[0] = (lq, lp, tag)
        if abs(signed) > 1e-12:
            lots.append((signed, px, tags.get(f.get("order_id"))))
    return trades


def row(name, period, st, extra=""):
    if not st["n"]:
        return f"| {name} | {period} | 0 | | | | | {extra} |"
    pf = "inf" if st["pf"] == float("inf") else f"{st['pf']:.2f}"
    return (f"| {name} | {period} | {st['n']} | {st['win']:.0%} | {st['avg_win']:+.2%} / {st['avg_loss']:+.2%} | "
            f"{st['profit']:+.1%} | {pf} | {extra} |")


def main():
    state = ch.paper_guard()
    names = sys.argv[1:] or list(S.ALL)
    now = datetime.datetime.now(datetime.timezone.utc)
    start = (now - datetime.timedelta(days=400)).strftime("%Y-%m-%dT%H:%M:%SZ")
    end = (now - datetime.timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%SZ")  # free SIP data needs a 15 min delay
    split = (now - datetime.timedelta(days=OOS_DAYS)).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = ["# Strategy scoreboard (PAPER challenge)", "",
             f"Updated {datetime.datetime.now(S.ET):%Y-%m-%d %H:%M} ET. Backtest: 400 days of Alpaca bars, "
             f"in sample before {split[:10]}, out of sample after (never tuned on). Per trade returns, unlevered, "
             "after costs. Live: Alpaca fills since the challenge started.", "",
             "| Strategy | Period | Trades | Win rate | Avg win / avg loss | Profit (sum of trade returns) | "
             "Profit factor | Indicators |", "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for n in names:
        strat = S.ALL[n]
        trades = []
        for sym, bars in fetch(strat, start, end).items():
            trades += overnight_trades(strat, sym, bars) if n == "overnight" else simulate(strat, sym, bars)
        ins = [t for t in trades if t["t"] < split]
        oos = [t for t in trades if t["t"] >= split]
        lines.append(row(n, "backtest in sample", stats(ins), strat.indicators))
        lines.append(row(n, "backtest out of sample", stats(oos), strat.indicators))
        print(n, "in", stats(ins), "out", stats(oos), flush=True)
    live = live_trades(state)
    for n in list(S.ALL) + ["opt"]:
        lt = [t for t in live if t["strategy"] == n]
        pnl = sum(t["pnl"] for t in lt)
        lines.append(row(n, "live", stats(lt), f"realized P&L ${pnl:,.0f}"))
    lines += ["", f"Allocation weights now: {state.get('weights')}", "",
              "## Rules", ""] + [f"* **{s.name}**: {s.rules}" for s in S.ALL.values()] + [
              "* **opt**: once a day between 09:35 and 11:00 ET, buy the QQQ call (first 5 minute bar up) or put "
              "(down), nearest expiry 1 to 4 days out, strike nearest the money. Exit at minus 50%, plus 100%, or "
              "15:45 ET the day before expiry.", ""]
    with open(BOARD, "w") as f:
        f.write("\n".join(lines))
    print(BOARD)


if __name__ == "__main__":
    main()
