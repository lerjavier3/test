#!/usr/bin/env python3
"""Minimal Alpaca REST client for the trading skills (standard library only).

Used when the Alpaca MCP server is not connected. Reads ALPACA_API_KEY,
ALPACA_SECRET_KEY and ALPACA_PAPER from the environment. Paper trading is the
default; live trading needs ALPACA_PAPER=false AND --live on the command line.

Examples:
  python3 scripts/alpaca.py check
  python3 scripts/alpaca.py account
  python3 scripts/alpaca.py bars SPY --timeframe 1Day --limit 260
  python3 scripts/alpaca.py order QQQ buy 10 --limit 480.10 --stop 476.50 --tp 520 --id day-QQQ-20261007-1
  python3 scripts/alpaca.py cancel-all
"""
import argparse
import datetime
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

PAPER_URL = "https://paper-api.alpaca.markets"
LIVE_URL = "https://api.alpaca.markets"
DATA_URL = "https://data.alpaca.markets"


def base_url(live_flag):
    paper_env = os.environ.get("ALPACA_PAPER", "true").strip().lower() != "false"
    if live_flag and paper_env:
        sys.exit("Refusing --live: ALPACA_PAPER is not set to false.")
    if not live_flag and not paper_env:
        sys.exit("ALPACA_PAPER=false but --live was not passed. Refusing to guess.")
    return LIVE_URL if live_flag else PAPER_URL


def request(method, url, params=None, body=None):
    key = os.environ.get("ALPACA_API_KEY")
    secret = os.environ.get("ALPACA_SECRET_KEY")
    if not key or not secret:
        sys.exit("ALPACA_API_KEY and ALPACA_SECRET_KEY must be set.")
    if params:
        url += "?" + urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("APCA-API-KEY-ID", key)
    req.add_header("APCA-API-SECRET-KEY", secret)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
            return resp.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        return e.code, {"error": e.read().decode(errors="replace")}
    except urllib.error.URLError as e:
        return 0, {"error": str(e.reason)}


def out(status, payload):
    print(json.dumps({"http": status, "data": payload}, indent=2, default=str))
    if status == 0 or status >= 400:
        sys.exit(1)


def cmd_check(args):
    """Report what the bot can and cannot do with these keys."""
    api = base_url(args.live)
    report = {"endpoint": api}
    s, acct = request("GET", f"{api}/v2/account")
    report["account_http"] = s
    if s == 200:
        report["account"] = {k: acct.get(k) for k in (
            "status", "currency", "equity", "cash", "buying_power", "multiplier",
            "shorting_enabled", "pattern_day_trader", "daytrade_count",
            "trading_blocked", "account_blocked", "crypto_status")}
    else:
        report["account_error"] = acct
    s, cfg = request("GET", f"{api}/v2/account/configurations")
    report["config_http"] = s
    if s == 200:
        report["config"] = cfg
    s, clock = request("GET", f"{api}/v2/clock")
    report["clock"] = clock if s == 200 else {"http": s, "error": clock}
    # Without a start date Alpaca only returns today's bars, which is empty before the open.
    start = (datetime.date.today() - datetime.timedelta(days=14)).isoformat()
    s, bars = request("GET", f"{DATA_URL}/v2/stocks/SPY/bars",
                      {"timeframe": "1Day", "start": start, "limit": 5, "feed": args.feed, "adjustment": "all"})
    report["daily_bars_http"] = s
    report["daily_bars_ok"] = s == 200 and bool((bars or {}).get("bars"))
    # Long minute history comes from the SIP feed (free when older than 15 minutes).
    s, mins = request("GET", f"{DATA_URL}/v2/stocks/QQQ/bars",
                      {"timeframe": "1Min", "start": "2018-01-02T14:30:00Z",
                       "end": "2018-01-02T14:40:00Z", "feed": "sip"})
    report["minute_history_http"] = s
    report["minute_history_ok"] = s == 200 and bool((mins or {}).get("bars"))
    s, crypto = request("GET", f"{DATA_URL}/v1beta3/crypto/us/latest/trades", {"symbols": "BTC/USD"})
    report["crypto_data_http"] = s
    ok = report["account_http"] == 200 and report["daily_bars_ok"]
    report["ready_to_trade"] = ok
    print(json.dumps(report, indent=2, default=str))
    sys.exit(0 if ok else 1)


def cmd_simple(path):
    def run(args):
        out(*request("GET", f"{base_url(args.live)}/v2/{path}"))
    return run


def cmd_orders(args):
    out(*request("GET", f"{base_url(args.live)}/v2/orders", {"status": args.status, "limit": 100}))


def cmd_bars(args):
    out(*request("GET", f"{DATA_URL}/v2/stocks/{args.symbol}/bars", {
        "timeframe": args.timeframe, "start": args.start, "end": args.end,
        "limit": args.limit, "feed": args.feed, "adjustment": "all"}))


def cmd_quote(args):
    out(*request("GET", f"{DATA_URL}/v2/stocks/{args.symbol}/quotes/latest", {"feed": args.feed}))


def cmd_order(args):
    body = {
        "symbol": args.symbol, "side": args.side, "qty": str(args.qty),
        "type": "limit" if args.limit else "market",
        "time_in_force": args.tif,
    }
    if args.limit:
        body["limit_price"] = f"{args.limit:.2f}"
    if args.id:
        body["client_order_id"] = args.id
    if args.stop and args.tp:
        body["order_class"] = "bracket"
        body["stop_loss"] = {"stop_price": f"{args.stop:.2f}"}
        body["take_profit"] = {"limit_price": f"{args.tp:.2f}"}
    elif args.stop:
        body["order_class"] = "oto"
        body["stop_loss"] = {"stop_price": f"{args.stop:.2f}"}
    elif args.stop_only:
        body["type"] = "stop"
        body["stop_price"] = f"{args.stop_only:.2f}"
        body.pop("limit_price", None)
    out(*request("POST", f"{base_url(args.live)}/v2/orders", body=body))


def cmd_cancel(args):
    out(*request("DELETE", f"{base_url(args.live)}/v2/orders/{args.order_id}"))


def cmd_cancel_all(args):
    out(*request("DELETE", f"{base_url(args.live)}/v2/orders"))


def cmd_close(args):
    out(*request("DELETE", f"{base_url(args.live)}/v2/positions/{args.symbol}"))


def cmd_calendar(args):
    out(*request("GET", f"{base_url(args.live)}/v2/calendar", {"start": args.start, "end": args.end}))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--live", action="store_true", help="use the live endpoint (also needs ALPACA_PAPER=false)")
    p.add_argument("--feed", default="iex", help="market data feed: iex (free) or sip (paid)")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("check").set_defaults(fn=cmd_check)
    for name, path in (("account", "account"), ("clock", "clock"), ("positions", "positions"),
                       ("config", "account/configurations")):
        sub.add_parser(name).set_defaults(fn=cmd_simple(path))

    o = sub.add_parser("orders"); o.add_argument("--status", default="open"); o.set_defaults(fn=cmd_orders)

    b = sub.add_parser("bars")
    b.add_argument("symbol"); b.add_argument("--timeframe", default="1Day")
    b.add_argument("--start"); b.add_argument("--end"); b.add_argument("--limit", type=int, default=1000)
    b.set_defaults(fn=cmd_bars)

    q = sub.add_parser("quote"); q.add_argument("symbol"); q.set_defaults(fn=cmd_quote)

    od = sub.add_parser("order")
    od.add_argument("symbol"); od.add_argument("side", choices=["buy", "sell"]); od.add_argument("qty", type=float)
    od.add_argument("--limit", type=float, help="limit price (omit for market)")
    od.add_argument("--stop", type=float, help="attached stop loss (bracket or OTO)")
    od.add_argument("--tp", type=float, help="attached take profit (makes it a bracket)")
    od.add_argument("--stop-only", type=float, help="standalone stop order at this price")
    od.add_argument("--tif", default="day", choices=["day", "gtc"])
    od.add_argument("--id", help="client_order_id, <sleeve>-<ticker>-<YYYYMMDD>-<n>")
    od.set_defaults(fn=cmd_order)

    c = sub.add_parser("cancel"); c.add_argument("order_id"); c.set_defaults(fn=cmd_cancel)
    sub.add_parser("cancel-all").set_defaults(fn=cmd_cancel_all)
    cl = sub.add_parser("close"); cl.add_argument("symbol"); cl.set_defaults(fn=cmd_close)
    ca = sub.add_parser("calendar"); ca.add_argument("--start"); ca.add_argument("--end"); ca.set_defaults(fn=cmd_calendar)

    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
