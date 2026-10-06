#!/usr/bin/env python3
"""Paper challenge engine: guards, signals, guarded orders, journal and summary.

PAPER ONLY. Every command refuses to run unless the endpoint is the Alpaca paper
API and trading/state.json says "mode": "paper_challenge". Never use these rules
with live money.

  python3 scripts/challenge.py preflight            # guards, state update, session
  python3 scripts/challenge.py signals              # trend signals for the universe
  python3 scripts/challenge.py order QQQ buy 50 --limit 480.1 --stop 474 --id ch-QQQ-20261006-1
  python3 scripts/challenge.py journal --run hourly --note "what happened"
  python3 scripts/challenge.py summary              # numbers for trading/journal/challenge-summary.md
  python3 scripts/challenge.py clear-stop QQQ        # forget a mental stop after closing
"""
import argparse
import datetime
import json
import os
import sys
import time
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import alpaca  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(ROOT, "trading", "state.json")
JOURNAL = os.path.join(ROOT, "trading", "journal")
ET = ZoneInfo("America/New_York")
API = alpaca.PAPER_URL
DATA = alpaca.DATA_URL

STOCKS = ["QQQ", "SPY", "IWM", "NVDA", "TSLA", "AAPL", "MSFT", "AMZN", "META", "AMD", "GOOGL", "AVGO"]
CRYPTO = ["BTC/USD", "ETH/USD", "SOL/USD"]
OPTION_UNDERLYINGS = ["QQQ", "SPY"]


def die(msg, code=2):
    print(json.dumps({"refused": msg}))
    sys.exit(code)


def paper_guard():
    """The one rule that is never bent: paper endpoint and challenge mode only."""
    if os.environ.get("ALPACA_PAPER", "true").strip().lower() == "false":
        die("ALPACA_PAPER=false. The challenge mode only runs on paper.")
    if alpaca.base_url(False) != alpaca.PAPER_URL:
        die("Endpoint is not paper-api.alpaca.markets.")
    state = load_state()
    if state.get("mode") != "paper_challenge":
        die("trading/state.json mode is not paper_challenge.")
    return state


def load_state():
    with open(STATE) as f:
        return json.load(f)


def save_state(state):
    with open(STATE, "w") as f:
        json.dump(state, f, indent=2)
        f.write("\n")


def get(path, params=None, base=API):
    s, d = alpaca.request("GET", f"{base}{path}", params)
    if s != 200:
        if s == 429:
            log_error("rate limited by Alpaca on " + path)
        die(f"GET {path} failed: http {s} {d}", 1)
    return d


def log_error(msg):
    day_dir = os.path.join(JOURNAL, datetime.datetime.now(ET).date().isoformat())
    os.makedirs(day_dir, exist_ok=True)
    with open(os.path.join(day_dir, "errors.md"), "a") as f:
        f.write(f"\n* ERROR {datetime.datetime.now(ET):%H:%M} ET: {msg}\n")


def session_now(clock):
    """regular, pre, post, overnight or closed (stocks). Crypto trades in all of them."""
    now = datetime.datetime.now(ET)
    if clock.get("is_open"):
        return "regular"
    wd, t = now.weekday(), now.hour * 60 + now.minute
    # Alpaca overnight runs Sunday 20:00 to Friday 04:00 ET; pre 04:00 to 09:30; post 16:00 to 20:00.
    if wd == 5 or (wd == 6 and t < 20 * 60) or (wd == 4 and t >= 20 * 60):
        return "closed"
    if 4 * 60 <= t < 9 * 60 + 30:
        return "pre"
    if 16 * 60 <= t < 20 * 60:
        return "post"
    return "overnight"


def cmd_preflight(args):
    state = paper_guard()
    acct = get("/v2/account")
    positions = get("/v2/positions")
    clock = get("/v2/clock")
    equity = float(acct["equity"])
    now = datetime.datetime.now(ET)
    end = datetime.datetime.fromisoformat(state["end_after_et"]).replace(tzinfo=ET)

    state["peak_equity"] = max(state.get("peak_equity", equity), equity)
    state["trough_equity"] = min(state.get("trough_equity", equity), equity)
    dd = 1 - equity / state["peak_equity"]
    state["max_drawdown_pct"] = round(max(state.get("max_drawdown_pct", 0), dd * 100), 2)
    state["last_equity"] = equity
    last = state.get("last_run_et")
    if last and now - datetime.datetime.fromisoformat(last) > datetime.timedelta(minutes=80):
        # A gap means scheduled runs did not happen: usage limits, rate limits or a failed session.
        state.setdefault("rate_limit_failures", []).append(
            f"no completed run between {last} and {now.isoformat(timespec='minutes')}")
    state["last_run_et"] = now.isoformat(timespec="minutes")

    reasons = []
    if equity < state["equity_floor"]:
        reasons.append(f"equity {equity:.0f} below floor {state['equity_floor']}")
    if now >= end:
        reasons.append("challenge window is over")
        state["challenge_active"] = False
    if not state.get("challenge_active", True):
        reasons.append("challenge_active is false")
    if acct.get("trading_blocked") or acct.get("account_blocked"):
        reasons.append("account blocked")
    save_state(state)

    long_mv = sum(float(p["market_value"]) for p in positions if float(p["market_value"]) > 0)
    short_mv = -sum(float(p["market_value"]) for p in positions if float(p["market_value"]) < 0)
    report = {
        "endpoint": "paper",
        "time_et": now.strftime("%Y-%m-%d %H:%M %a"),
        "session": session_now(clock),
        "equity": equity, "cash": float(acct["cash"]), "buying_power": float(acct["buying_power"]),
        "regt_buying_power": float(acct.get("regt_buying_power") or 0),
        "options_buying_power": float(acct.get("options_buying_power") or 0),
        "non_marginable_buying_power": float(acct.get("non_marginable_buying_power") or 0),
        "gross_leverage": round((long_mv + short_mv) / equity, 2) if equity > 0 else None,
        "peak": state["peak_equity"], "drawdown_pct": round(dd * 100, 2),
        "max_drawdown_pct": state["max_drawdown_pct"],
        "progress_to_target": round((equity - state["starting_equity"]) /
                                    (state["target_equity"] - state["starting_equity"]), 3),
        "can_open_new": not reasons, "blocked_because": reasons,
        "is_final_run": now >= end,
        "positions": [{k: p[k] for k in ("symbol", "asset_class", "side", "qty", "avg_entry_price",
                                         "current_price", "unrealized_pl", "unrealized_plpc")} for p in positions],
        "open_orders": [{k: o.get(k) for k in ("client_order_id", "symbol", "side", "type", "qty",
                                               "stop_price", "limit_price", "status")}
                        for o in get("/v2/orders", {"status": "open", "limit": 100})],
    }
    print(json.dumps(report, indent=1))


def ema(xs, n):
    k, e = 2 / (n + 1), xs[0]
    for x in xs[1:]:
        e = x * k + e * (1 - k)
    return e


def atr(bars, n=14):
    trs = [max(b["h"] - b["l"], abs(b["h"] - a["c"]), abs(b["l"] - a["c"])) for a, b in zip(bars, bars[1:])]
    return sum(trs[-n:]) / min(n, len(trs))


def signal_for(sym, bars):
    if len(bars) < 55:
        return {"symbol": sym, "signal": "no_data", "bars": len(bars)}
    closes = [b["c"] for b in bars]
    last, fast, slow, a = closes[-1], ema(closes[-60:], 20), ema(closes[-60:], 50), atr(bars)
    hi20, lo20 = max(b["h"] for b in bars[-21:-1]), min(b["l"] for b in bars[-21:-1])
    sig = "flat"
    if last > fast > slow:
        sig = "long_breakout" if last > hi20 else "long"
    elif last < fast < slow:
        sig = "short_breakdown" if last < lo20 else "short"
    return {"symbol": sym, "last": round(last, 4), "ema20": round(fast, 4), "ema50": round(slow, 4),
            "atr14_1h": round(a, 4), "signal": sig,
            "long_stop": round(last - 1.5 * a, 4), "short_stop": round(last + 1.5 * a, 4)}


def all_bars(path, params):
    """Multi-symbol bar requests come back in pages; merge them."""
    bars, params = {}, dict(params, limit=10000)
    while True:
        d = get(path, params, base=DATA)
        for sym, rows in (d.get("bars") or {}).items():
            bars.setdefault(sym, []).extend(rows)
        if not d.get("next_page_token"):
            return bars
        params["page_token"] = d["next_page_token"]


def cmd_signals(args):
    paper_guard()
    start = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=21)).strftime("%Y-%m-%dT%H:%M:%SZ")
    stocks = all_bars("/v2/stocks/bars", {"symbols": ",".join(STOCKS), "timeframe": "1Hour", "start": start,
                                          "feed": "iex", "adjustment": "all"})
    crypto = all_bars("/v1beta3/crypto/us/bars", {"symbols": ",".join(CRYPTO), "timeframe": "1Hour", "start": start})
    out = [signal_for(sym, stocks.get(sym, [])) for sym in STOCKS]
    out += [signal_for(sym, crypto.get(sym, [])) for sym in CRYPTO]
    print(json.dumps(out, indent=1))


def is_option(sym):
    return len(sym) > 15 and sym[-9] in "CP" and sym[-8:].isdigit()


def cmd_order(args):
    state = paper_guard()
    sym = args.symbol.upper()
    positions = {p["symbol"].replace("/", ""): p for p in get("/v2/positions")}
    held = positions.get(sym.replace("/", ""))
    held_qty = float(held["qty"]) if held else 0.0
    closing = (args.side == "sell" and held_qty > 0) or (args.side == "buy" and held_qty < 0)

    if closing and args.qty > abs(held_qty) + 1e-9:
        die(f"close qty {args.qty} exceeds held {held_qty}; would flip the position.")
    if not closing:
        acct = get("/v2/account")
        if float(acct["equity"]) < state["equity_floor"]:
            die("equity below the $25,000 floor: no new trades.")
        if not state.get("challenge_active", True):
            die("challenge is over: closing trades only.")
        if is_option(sym) and args.side == "sell":
            die("options: buying calls or puts only. No selling to open.")
        if "/" in sym and args.side == "sell":
            die("crypto cannot be shorted on Alpaca.")
        if not (args.stop or args.stop_limit or args.mental_stop):
            die("every new position needs --stop, --stop-limit or --mental-stop (logged).")
    if not args.id:
        die("--id (client_order_id) is required.")
    s, _ = alpaca.request("GET", f"{API}/v2/orders:by_client_order_id", {"client_order_id": args.id})
    if s == 200:
        die(f"client_order_id {args.id} already used: not sending a duplicate.")

    body = {"symbol": sym, "side": args.side, "qty": str(args.qty), "client_order_id": args.id,
            "type": "limit" if args.limit else "market",
            "time_in_force": args.tif or ("gtc" if "/" in sym else "day")}
    if args.limit:
        body["limit_price"] = alpaca.fmt_price(args.limit)
    if args.extended:
        if not args.limit:
            die("extended and overnight sessions need a limit price.")
        body["extended_hours"] = True
        body["time_in_force"] = "day"
    if args.stop and not closing and not args.extended and "/" not in sym and not is_option(sym):
        body["order_class"] = "bracket" if args.tp else "oto"
        body["stop_loss"] = {"stop_price": alpaca.fmt_price(args.stop)}
        if args.tp:
            body["take_profit"] = {"limit_price": alpaca.fmt_price(args.tp)}
    elif args.stop_limit is not None and closing:
        body["type"] = "stop_limit"
        body["stop_price"] = alpaca.fmt_price(args.stop_limit)
    s, d = alpaca.request("POST", f"{API}/v2/orders", body=body)
    if s >= 400 or s == 0:
        log_error(f"order {args.id} rejected: http {s} {d}")
        die(f"order rejected: http {s} {d}", 1)

    # Confirm the fill: poll up to args.wait seconds, then report whatever the status is.
    status = d
    for _ in range(max(1, args.wait // 2)):
        if status.get("status") in ("filled", "canceled", "rejected", "expired"):
            break
        time.sleep(2)
        _, status = alpaca.request("GET", f"{API}/v2/orders/{d['id']}")
    result = {k: status.get(k) for k in ("client_order_id", "symbol", "side", "qty", "type", "order_class",
                                         "status", "filled_qty", "filled_avg_price", "limit_price", "stop_price")}
    result["mental_stop"] = args.mental_stop
    if args.mental_stop and not closing:
        state.setdefault("mental_stops", {})[sym] = {"stop": args.mental_stop, "side": args.side, "id": args.id}
        save_state(state)
    print(json.dumps(result, indent=1))


def cmd_journal(args):
    state = paper_guard()
    os.makedirs(JOURNAL, exist_ok=True)
    now = datetime.datetime.now(ET)
    day_dir = os.path.join(JOURNAL, now.date().isoformat())
    os.makedirs(day_dir, exist_ok=True)
    # One file per run, so overlapping runs never conflict when they push.
    path = os.path.join(day_dir, f"{now:%H%M}-{args.run}.md")
    new = not os.path.exists(path)
    eq = state.get("last_equity", 0)
    prog = (eq - state["starting_equity"]) / (state["target_equity"] - state["starting_equity"])
    with open(path, "a") as f:
        if new:
            f.write(f"# {now:%Y-%m-%d %H:%M} ET, {args.run} run (PAPER challenge)\n")
        f.write("\n"
                f"* Equity {eq:,.2f} | peak {state['peak_equity']:,.2f} | max drawdown "
                f"{state['max_drawdown_pct']}% | progress to 3x {prog:.1%}\n")
        for line in args.note:
            f.write(f"* {line}\n")
    print(path)


def realized_trades(fills):
    """FIFO match fills per symbol into closed round trips."""
    book, trades = {}, []
    for f in sorted(fills, key=lambda x: x["transaction_time"]):
        sym, qty, px = f["symbol"], float(f["qty"]), float(f["price"])
        mult = 100 if is_option(sym) else 1
        signed = qty if f["side"] == "buy" else -qty
        lots = book.setdefault(sym, [])
        while signed and lots and (lots[0][0] > 0) != (signed > 0):
            lq, lp, lt = lots[0]
            m = min(abs(lq), abs(signed))
            pnl = (px - lp) * m * mult * (1 if lq > 0 else -1)
            trades.append({"symbol": sym, "side": "long" if lq > 0 else "short", "qty": m,
                           "entry": lp, "exit": px, "pnl": round(pnl, 2), "opened": lt,
                           "closed": f["transaction_time"]})
            lq = lq - m if lq > 0 else lq + m
            signed = signed - m if signed > 0 else signed + m
            if abs(lq) < 1e-12:
                lots.pop(0)
            else:
                lots[0] = (lq, lp, lt)
        if abs(signed) > 1e-12:
            lots.append((signed, px, f["transaction_time"]))
    return trades


def cmd_summary(args):
    state = paper_guard()
    hist = get("/v2/account/portfolio/history", {"period": "1W", "timeframe": "1H", "extended_hours": "true"})
    eq = [e for e in hist.get("equity", []) if e]
    peak, mdd = 0, 0
    for e in eq:
        peak = max(peak, e)
        mdd = max(mdd, 1 - e / peak)
    mdd = max(mdd * 100, state.get("max_drawdown_pct", 0))
    fills, token = [], None
    while True:
        s, page = alpaca.request("GET", f"{API}/v2/account/activities/FILL",
                                 {"after": state["start_date"], "page_size": 100, "page_token": token,
                                  "direction": "asc"})
        if s != 200 or not page:
            break
        fills += page
        if len(page) < 100:
            break
        token = page[-1]["id"]
    trades = realized_trades(fills)
    end_eq = float(get("/v2/account")["equity"])
    trades.sort(key=lambda t: t["pnl"])
    wins = [t for t in trades if t["pnl"] > 0]
    data = {"start_equity": state["starting_equity"], "end_equity": end_eq,
            "return_pct": round((end_eq / state["starting_equity"] - 1) * 100, 2),
            "target_equity": state["target_equity"], "max_drawdown_pct": round(mdd, 2),
            "peak_equity": state["peak_equity"], "trough_equity": state["trough_equity"],
            "fills": len(fills), "round_trips": len(trades),
            "win_rate": round(len(wins) / len(trades), 3) if trades else None,
            "best_trades": trades[::-1][:3], "worst_trades": trades[:3]}
    print(json.dumps(data, indent=1))


def cmd_merge_state(args):
    """Merge two copies of state.json after a push race (used by challenge_push.sh)."""
    mine, theirs = (json.load(open(x)) for x in (args.mine, args.theirs))
    merged = dict(theirs)
    merged["peak_equity"] = max(mine["peak_equity"], theirs["peak_equity"])
    merged["trough_equity"] = min(mine["trough_equity"], theirs["trough_equity"])
    merged["max_drawdown_pct"] = max(mine["max_drawdown_pct"], theirs["max_drawdown_pct"])
    merged["challenge_active"] = mine.get("challenge_active", True) and theirs.get("challenge_active", True)
    if (mine.get("last_run_et") or "") > (theirs.get("last_run_et") or ""):
        merged["last_run_et"], merged["last_equity"] = mine["last_run_et"], mine["last_equity"]
    for key in ("mental_stops", "routines"):
        merged[key] = {**theirs.get(key, {}), **mine.get(key, {})}
    merged["rate_limit_failures"] = list(dict.fromkeys(
        theirs.get("rate_limit_failures", []) + mine.get("rate_limit_failures", [])))
    print(json.dumps(merged, indent=2))


def cmd_clear_stop(args):
    state = paper_guard()
    state.get("mental_stops", {}).pop(args.symbol.upper(), None)
    save_state(state)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("preflight").set_defaults(fn=cmd_preflight)
    sub.add_parser("signals").set_defaults(fn=cmd_signals)
    o = sub.add_parser("order")
    o.add_argument("symbol", help="stock, crypto like BTC/USD, or OCC option symbol")
    o.add_argument("side", choices=["buy", "sell"]); o.add_argument("qty", type=float)
    o.add_argument("--limit", type=float); o.add_argument("--stop", type=float, help="attached broker stop (regular hours stocks)")
    o.add_argument("--tp", type=float); o.add_argument("--stop-limit", type=float, help="stop trigger for a closing stop_limit order")
    o.add_argument("--mental-stop", type=float, help="stop checked by every run (crypto, options, extended hours)")
    o.add_argument("--extended", action="store_true"); o.add_argument("--tif", choices=["day", "gtc", "ioc"])
    o.add_argument("--id", help="client_order_id: ch-<SYMBOL>-<YYYYMMDDHHMM>-<n>")
    o.add_argument("--wait", type=int, default=20, help="seconds to wait for a fill")
    o.set_defaults(fn=cmd_order)
    j = sub.add_parser("journal"); j.add_argument("--run", default="hourly")
    j.add_argument("--note", action="append", default=[]); j.set_defaults(fn=cmd_journal)
    sub.add_parser("summary").set_defaults(fn=cmd_summary)
    m = sub.add_parser("merge-state"); m.add_argument("mine"); m.add_argument("theirs"); m.set_defaults(fn=cmd_merge_state)
    cs = sub.add_parser("clear-stop"); cs.add_argument("symbol"); cs.set_defaults(fn=cmd_clear_stop)
    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
