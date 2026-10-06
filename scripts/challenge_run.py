#!/usr/bin/env python3
"""Deterministic PAPER ONLY challenge runner: one tick, or a loop that trades by itself.

  python3 scripts/challenge_run.py --once --dry-run   # decide, print, place nothing
  python3 scripts/challenge_run.py --once             # one real tick on paper
  nohup python3 scripts/challenge_run.py --loop >> trading/challenge.log 2>&1 &

Each tick: paper guard, account snapshot, manage open positions (stops, signal
flips, option exits, leverage trim), new entries if allowed, journal, state.
The loop sleeps 5 min in the regular session, 15 min in pre, post and overnight,
30 min on weekends (crypto only), pushes trading/ about hourly, liquidates at
15:50 ET on the final day, writes the summary and exits. Never use with live money.
Exit codes: 0 done, 2 refused (not paper, wrong mode), 3 too many errors in a row.
"""
import argparse
import datetime
import json
import math
import os
import subprocess
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import alpaca  # noqa: E402
import challenge as ch  # noqa: E402

API, DATA, ET = ch.API, ch.DATA, ch.ET
RISK = 0.04                 # equity risked per trade (entry to stop)
GROSS_REGULAR = 3.5         # max gross exposure / equity in the regular session
GROSS_OVERNIGHT = 1.9       # held through the close and outside regular hours
MAX_POSITIONS = 6
POS_CAP_REGULAR = 1.0       # max value of one stock position / equity, regular session
POS_CAP_OVERNIGHT = 0.6     # same, after 15:40 ET and outside regular hours
OPTION_BUDGET = 0.08        # premium per options trade, share of equity
MAX_ERRORS = 5              # consecutive failed ticks before the loop exits


class Tick:
    def __init__(self, dry):
        self.dry, self.notes, self.n = dry, [], 0
        self.state = ch.paper_guard()
        self.now = datetime.datetime.now(ET)
        self.stamp = self.now.strftime("%Y%m%d%H%M")

    # ---------- broker helpers ----------
    def oid(self, sym):
        self.n += 1
        return f"ch-{sym.replace('/', '')}-{self.stamp}-{self.n}"

    def submit(self, body, why):
        body["client_order_id"] = self.oid(body["symbol"])
        line = f"{body['side']} {body['qty']} {body['symbol']} {body['type']}" + \
               (f" @{body['limit_price']}" if "limit_price" in body else "") + \
               (f" stop {body['stop_loss']['stop_price']}" if "stop_loss" in body else "") + \
               (f" trigger {body['stop_price']}" if "stop_price" in body else "") + f" ({why})"
        if self.dry:
            self.notes.append("DRY " + line)
            return {"status": "filled", "filled_qty": body["qty"], "filled_avg_price": body.get("limit_price")}
        s, d = alpaca.request("POST", f"{API}/v2/orders", body=body)
        if s >= 400 or s == 0:
            self.notes.append(f"REJECTED {line}: {str(d)[:160]}")
            return None
        for _ in range(10):  # confirm the fill, up to 20 s
            if d.get("status") in ("filled", "canceled", "rejected", "expired"):
                break
            time.sleep(2)
            _, d = alpaca.request("GET", f"{API}/v2/orders/{d['id']}")
        # Unfilled limit entries and closes are canceled (a bracket's legs go with it); the next tick
        # tries again with a fresh price. Market and stop_limit orders are left working.
        if body["type"] == "limit" and float(d.get("filled_qty") or 0) == 0:
            alpaca.request("DELETE", f"{API}/v2/orders/{d['id']}")
            self.notes.append(f"UNFILLED, canceled: {line}")
            return None
        self.notes.append(f"{d.get('status')} {d.get('filled_qty')} @ {d.get('filled_avg_price')}: {line} [{body['client_order_id']}]")
        return d

    def cancel_symbol_orders(self, sym):
        for o in self.orders:
            if o["symbol"].replace("/", "") == sym.replace("/", ""):
                if not self.dry:
                    alpaca.request("DELETE", f"{API}/v2/orders/{o['id']}")
        self.orders = [o for o in self.orders if o["symbol"].replace("/", "") != sym.replace("/", "")]

    def close(self, p, why):
        sym, qty = p["symbol"], abs(float(p["qty"]))
        side = "sell" if float(p["qty"]) > 0 else "buy"
        crypto = p["asset_class"] == "crypto"
        if not crypto and p["asset_class"] != "us_option" and self.session not in ("regular",) and side == "buy":
            self.notes.append(f"cannot cover short {sym} outside regular hours, waiting ({why})")
            return
        self.cancel_symbol_orders(sym)
        if not self.dry:
            time.sleep(1)
        body = {"symbol": crypto_pair(sym) if crypto else sym, "side": side,
                "qty": str(qty if crypto else int(qty) if qty == int(qty) else qty)}
        if self.session == "regular" or crypto:
            body.update(type="market", time_in_force="gtc" if crypto else "day")
        else:
            if p["asset_class"] == "us_option":
                self.notes.append(f"options closed outside regular hours, waiting ({why})")
                return
            px = float(p["current_price"]) * (0.997 if side == "sell" else 1.003)
            body.update(type="limit", limit_price=alpaca.fmt_price(px), time_in_force="day", extended_hours=True)
        if self.submit(body, "close: " + why):
            self.state.get("mental_stops", {}).pop(sym, None)
            self.closed.add(sym)

    # ---------- market data ----------
    def ref_price(self, sym):
        if "/" in sym:
            q = ch.get("/v1beta3/crypto/us/latest/quotes", {"symbols": sym}, base=DATA)["quotes"][sym]
            return (q["ap"] + q["bp"]) / 2
        if self.session == "overnight":
            q = ch.get("/v2/stocks/quotes/latest", {"symbols": sym, "feed": "overnight"}, base=DATA)["quotes"].get(sym)
            return (q["ap"] + q["bp"]) / 2 if q and q["ap"] and q["bp"] else None
        t = ch.get("/v2/stocks/trades/latest", {"symbols": sym, "feed": "iex"}, base=DATA)["trades"].get(sym)
        return t["p"] if t else None

    # ---------- the tick ----------
    def run(self):
        st = self.state
        acct = ch.get("/v2/account")
        self.positions = ch.get("/v2/positions")
        self.orders = ch.get("/v2/orders", {"status": "open", "limit": 200})
        clock = ch.get("/v2/clock")
        self.session = ch.session_now(clock)
        self.closed, self.stocks_done = set(), False
        eq = self.equity = float(acct["equity"])
        st["peak_equity"] = max(st["peak_equity"], eq)
        st["trough_equity"] = min(st["trough_equity"], eq)
        st["max_drawdown_pct"] = round(max(st["max_drawdown_pct"], (1 - eq / st["peak_equity"]) * 100), 2)
        st["last_equity"], st["last_run_et"] = eq, self.now.isoformat(timespec="minutes")
        gross = sum(abs(float(p["market_value"])) for p in self.positions)
        lev = gross / eq if eq > 0 else 0
        st["max_gross_leverage"] = round(max(st.get("max_gross_leverage", 0), lev), 2)
        st.setdefault("leverage_samples", []).append(round(lev, 2))
        st["leverage_samples"] = st["leverage_samples"][-2000:]

        end = datetime.datetime.fromisoformat(st["end_after_et"]).replace(tzinfo=ET)
        if self.now >= end or not st.get("challenge_active", True):
            return self.finish()
        stocks_end = datetime.datetime.fromisoformat(st["stocks_end_et"]).replace(tzinfo=ET)
        self.stocks_done = self.now >= stocks_end  # after the last stock session only crypto trades

        self.signals = {s["symbol"]: s for s in signals()}
        if self.stocks_done:
            for p in self.positions:
                if p["asset_class"] != "crypto":
                    self.close(p, "last stock session is over")
        self.manage(acct)
        can_open = eq >= st["equity_floor"] and not acct.get("trading_blocked")
        if not can_open:
            self.notes.append(f"no new trades: equity {eq:,.0f} vs floor {st['equity_floor']:,}")
        else:
            self.enter(acct)
        return 0

    def manage(self, acct):
        hm = self.now.hour * 60 + self.now.minute
        stops = self.state.setdefault("mental_stops", {})
        for p in list(self.positions):
            sym, px, qty = p["symbol"], float(p["current_price"]), float(p["qty"])
            if sym in self.closed:
                continue
            if p["asset_class"] == "us_option":
                entry = float(p["avg_entry_price"])
                exp = datetime.date(2000 + int(sym[-15:-13]), int(sym[-13:-11]), int(sym[-11:-9]))
                if px <= entry * 0.5:
                    self.close(p, "option -50%")
                elif px >= entry * 2:
                    self.close(p, "option +100%")
                elif self.session == "regular" and (exp - self.now.date()).days <= 1 and hm >= 15 * 60 + 45:
                    self.close(p, "option expires next day")
                continue
            ms = stops.get(sym)
            if ms and ((qty > 0 and px <= ms["stop"]) or (qty < 0 and px >= ms["stop"])):
                self.close(p, f"stop {ms['stop']} hit at {px}")
                continue
            sig = self.signals.get(ch_symbol(p)) or {}
            s = sig.get("signal", "")
            if (qty > 0 and s.startswith("short")) or (qty < 0 and s.startswith("long")):
                self.close(p, f"signal flipped to {s}")
        # Leverage trim: before the close and whenever outside the regular session.
        if self.session != "regular" or hm >= 15 * 60 + 45:
            live = [p for p in self.positions if p["symbol"] not in self.closed and p["asset_class"] == "us_equity"]
            gross = sum(abs(float(p["market_value"])) for p in live)
            for p in sorted(live, key=lambda p: float(p["unrealized_plpc"])):
                if gross <= GROSS_OVERNIGHT * self.equity:
                    break
                self.close(p, f"trim gross to {GROSS_OVERNIGHT}x")
                gross -= abs(float(p["market_value"]))

    def enter(self, acct):
        held = {ch_symbol(p) for p in self.positions if p["symbol"] not in self.closed}
        working = {o["symbol"] for o in self.orders}
        n_open = len(held)
        gross = sum(abs(float(p["market_value"])) for p in self.positions if p["symbol"] not in self.closed)
        hm = self.now.hour * 60 + self.now.minute
        day = self.session == "regular" and hm < 15 * 60 + 40  # late entries must fit the overnight limit
        cap = (GROSS_REGULAR if day else GROSS_OVERNIGHT) * self.equity
        pos_cap = (POS_CAP_REGULAR if day else POS_CAP_OVERNIGHT) * self.equity
        bp = float(acct["buying_power"]) if self.session == "regular" else float(acct.get("regt_buying_power") or 0)
        cash_crypto = float(acct.get("non_marginable_buying_power") or 0)
        risk = RISK * self.equity * (1 if self.session == "regular" else 0.5)

        if self.session == "regular" and self.now.weekday() < 5 and not self.stocks_done:
            self.options_open(acct)

        # Stay invested: breakouts first, then any symbol in a clear trend (close and EMA20 on the same
        # side of EMA50), strongest trend first, until MAX_POSITIONS are held.
        tradable = ("long_breakout", "short_breakdown", "long", "short")
        ranked = sorted((s for s in self.signals.values() if s.get("signal") in tradable and s.get("atr14_1h")),
                        key=lambda s: (s["signal"] in ("long", "short"), -abs(s["last"] - s["ema50"]) / s["atr14_1h"]))
        for s in ranked:
            sym, sig = s["symbol"], s.get("signal")
            if n_open >= MAX_POSITIONS:
                continue
            if sym in held or sym in working or sym.replace("/", "") in working:
                continue
            crypto = "/" in sym
            if not crypto and (self.session == "closed" or self.stocks_done):
                continue
            if sig.startswith("short") and (crypto or not day):  # shorts can't be covered overnight
                continue
            px = self.ref_price(sym)
            if not px:
                continue
            long = sig.startswith("long")
            stop = px - 1.5 * s["atr14_1h"] if long else px + 1.5 * s["atr14_1h"]
            per_unit = abs(px - stop)
            if crypto:
                qty = min(risk / per_unit, 0.95 * cash_crypto / px)
                qty = math.floor(qty * 1e4) / 1e4
                if qty * px < 10:
                    continue
                body = {"symbol": sym, "side": "buy", "qty": str(qty), "type": "limit",
                        "limit_price": alpaca.fmt_price(px * 1.002), "time_in_force": "gtc"}
                d = self.submit(body, f"{sig} {sym}, stop {stop:.2f}")
                if d and float(d.get("filled_qty") or 0) > 0:
                    cash_crypto -= qty * px
                    n_open += 1
                    self.crypto_stop(sym, stop)
                continue
            room = min(cap - gross, 0.95 * bp)
            qty = int(min(risk / per_unit, room / px, pos_cap / px))
            if qty < 1:
                continue
            lim = px * (1.002 if long else 0.998)
            body = {"symbol": sym, "side": "buy" if long else "sell", "qty": str(qty), "type": "limit",
                    "limit_price": alpaca.fmt_price(lim)}
            if self.session == "regular":
                tp = px + 4 * s["atr14_1h"] if long else px - 4 * s["atr14_1h"]
                body.update(time_in_force="gtc", order_class="bracket",
                            stop_loss={"stop_price": alpaca.fmt_price(stop)},
                            take_profit={"limit_price": alpaca.fmt_price(tp)})
            else:
                body.update(time_in_force="day", extended_hours=True)
            d = self.submit(body, f"{sig}, {self.session}")
            if d and float(d.get("filled_qty") or 0) > 0:
                # Broker stops don't trigger outside regular hours, so every run also checks this one.
                self.state.setdefault("mental_stops", {})[sym] = {"stop": round(stop, 2), "side": body["side"]}
                gross += qty * px
                bp -= qty * px / (4 if self.session == "regular" else 2)
                n_open += 1

    def crypto_stop(self, sym, stop):
        if self.dry:
            return self.notes.append(f"DRY stop_limit sell {sym} trigger {stop:.2f}")
        time.sleep(2)
        pos = [p for p in ch.get("/v2/positions") if p["symbol"] == sym.replace("/", "")]
        if not pos:
            return
        self.submit({"symbol": sym, "side": "sell", "qty": pos[0]["qty_available"], "type": "stop_limit",
                     "stop_price": alpaca.fmt_price(stop), "limit_price": alpaca.fmt_price(stop * 0.99),
                     "time_in_force": "gtc"}, "crypto stop")

    def options_open(self, acct):
        """Once a day after 09:35 ET: buy a QQQ call or put in the direction of the first 5 minute bar."""
        today = self.now.date().isoformat()
        hm = self.now.hour * 60 + self.now.minute
        if self.state.get("last_options_day") == today or not (9 * 60 + 35 <= hm <= 11 * 60):
            return
        if any(p["asset_class"] == "us_option" for p in self.positions):
            return
        self.state["last_options_day"] = today
        start = self.now.replace(hour=9, minute=30, second=0, microsecond=0).astimezone(datetime.timezone.utc)
        bars = ch.get("/v2/stocks/QQQ/bars", {"timeframe": "5Min", "start": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                              "limit": 1, "feed": "iex"}, base=DATA).get("bars") or []
        if not bars or bars[0]["c"] == bars[0]["o"]:
            return self.notes.append("options: no opening bar direction")
        kind = "call" if bars[0]["c"] > bars[0]["o"] else "put"
        under = self.ref_price("QQQ")
        snaps = ch.get(f"/v1beta1/options/snapshots/QQQ", {
            "feed": "indicative", "type": kind,
            "expiration_date_gte": (self.now.date() + datetime.timedelta(days=1)).isoformat(),
            "expiration_date_lte": (self.now.date() + datetime.timedelta(days=4)).isoformat(),
            "strike_price_gte": round(under * 0.99), "strike_price_lte": round(under * 1.01), "limit": 200},
            base=DATA).get("snapshots") or {}
        best = None
        for occ, sn in snaps.items():
            q = sn.get("latestQuote") or {}
            if not q.get("ap") or not q.get("bp"):
                continue
            key = (occ[-15:-9], abs(int(occ[-8:]) / 1000 - under))  # nearest expiry, then nearest strike
            if best is None or key < best[0]:
                best = (key, occ, q["ap"])
        if not best:
            return self.notes.append("options: no quotes")
        occ, ask = best[1], best[2]
        budget = min(OPTION_BUDGET * self.equity, float(acct.get("options_buying_power") or 0))
        qty = int(budget // (ask * 100))
        if qty < 1:
            return
        self.submit({"symbol": occ, "side": "buy", "qty": str(qty), "type": "limit",
                     "limit_price": f"{ask:.2f}", "time_in_force": "day"},
                    f"opening bar {kind}, exit -50%/+100%")

    def finish(self):
        st = self.state
        self.notes.append("FINAL: canceling orders and closing everything")
        if not self.dry:
            alpaca.request("DELETE", f"{API}/v2/orders")
            time.sleep(2)
        self.orders = []
        for p in self.positions:  # crypto at market; any stock left uses an extended hours limit
            self.close(p, "challenge over")
        if not self.dry:
            time.sleep(10)
            st["challenge_active"] = False
            write_summary(st)
        return 0

    def journal(self):
        day = self.now.date().isoformat()
        path = os.path.join(ch.JOURNAL, f"{day}.md")
        os.makedirs(ch.JOURNAL, exist_ok=True)
        st = self.state
        prog = (self.equity - st["starting_equity"]) / (st["target_equity"] - st["starting_equity"])
        head = (f"{self.now:%H:%M} ET {self.session}: equity {self.equity:,.0f}, peak {st['peak_equity']:,.0f}, "
                f"max dd {st['max_drawdown_pct']}%, lev {st['leverage_samples'][-1]}x, progress {prog:.0%}, "
                f"positions {len(self.positions) - len(self.closed)}")
        if self.notes or self.now.minute < 10 or self.dry:
            if not self.dry:
                new = not os.path.exists(path)
                with open(path, "a") as f:
                    if new:
                        f.write(f"# Challenge journal {day} (PAPER)\n\n")
                    f.write(f"* {head}\n" + "".join(f"  * {n}\n" for n in self.notes))
        return [head] + self.notes


def crypto_pair(sym):
    return sym if "/" in sym else sym[:-3] + "/USD"


def ch_symbol(p):
    return crypto_pair(p["symbol"]) if p["asset_class"] == "crypto" else p["symbol"]


def signals():
    start = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=21)).strftime("%Y-%m-%dT%H:%M:%SZ")
    stocks = ch.all_bars("/v2/stocks/bars", {"symbols": ",".join(ch.STOCKS), "timeframe": "1Hour",
                                             "start": start, "feed": "iex", "adjustment": "all"})
    crypto = ch.all_bars("/v1beta3/crypto/us/bars", {"symbols": ",".join(ch.CRYPTO), "timeframe": "1Hour", "start": start})
    return [ch.signal_for(s, stocks.get(s, [])) for s in ch.STOCKS] + \
           [ch.signal_for(s, crypto.get(s, [])) for s in ch.CRYPTO]


def write_summary(st):
    hist = ch.get("/v2/account/portfolio/history", {"period": "1M", "timeframe": "1H", "extended_hours": "true"})
    peak, mdd = 0, 0
    for e in [e for e in hist.get("equity", []) if e]:
        peak = max(peak, e)
        mdd = max(mdd, 1 - e / peak)
    mdd = max(mdd * 100, st["max_drawdown_pct"])
    fills, token = [], None
    while True:
        s, page = alpaca.request("GET", f"{API}/v2/account/activities/FILL", {
            "after": st["start_date"], "page_size": 100, "page_token": token, "direction": "asc"})
        if s != 200 or not page:
            break
        fills += page
        if len(page) < 100:
            break
        token = page[-1]["id"]
    trades = sorted(ch.realized_trades(fills), key=lambda t: t["pnl"])
    end = float(ch.get("/v2/account")["equity"])
    ret = end / st["starting_equity"] - 1
    levs = [x for x in st.get("leverage_samples", []) if x > 0] or [0]
    avg_lev = sum(levs) / len(levs)
    wins = [t for t in trades if t["pnl"] > 0]
    row = lambda t: f"| {t['symbol']} | {t['side']} | {t['qty']:g} | {t['entry']:g} | {t['exit']:g} | {t['pnl']:,.2f} |"
    md = [f"# Challenge summary (PAPER, {st['start_date']} to {st['target_date']})", "",
          "| | |", "| --- | --- |",
          f"| Start equity | ${st['starting_equity']:,.2f} |", f"| End equity | ${end:,.2f} |",
          f"| Return | {ret:.1%} |", f"| Target (5x minimum) | ${st['target_equity']:,.0f}, "
          f"{'reached' if end >= st['target_equity'] else 'not reached'} |",
          f"| Peak / trough equity | ${st['peak_equity']:,.0f} / ${st['trough_equity']:,.0f} |",
          f"| Max drawdown | {mdd:.1f}% |", f"| Round trips | {len(trades)}, win rate "
          f"{(len(wins) / len(trades) if trades else 0):.0%} |",
          f"| Missed run gaps | {len(st.get('rate_limit_failures', []))} |", "",
          "## Best trades", "", "| Symbol | Side | Qty | Entry | Exit | P&L |", "| --- | --- | --- | --- | --- | --- |",
          *[row(t) for t in trades[::-1][:3]], "", "## Worst trades", "",
          "| Symbol | Side | Qty | Entry | Exit | P&L |", "| --- | --- | --- | --- | --- | --- |",
          *[row(t) for t in trades[:3]], "",
          "## How leverage affected the result", "",
          f"Gross exposure (sum of Alpaca position values / equity, sampled every tick) averaged {avg_lev:.2f}x "
          f"while positions were open and peaked at {st.get('max_gross_leverage', 0)}x. Gains and losses scale with "
          "exposure, so the return and drawdown above were taken at that leverage. Costs and slippage scale with "
          "leverage too, so a strategy with no edge loses faster when levered.", "",
          "## A sane real money plan instead", "",
          "* Follow `trading/PAPER_PLAN.md`: momentum rotation plus RSI(2) pullbacks on liquid large caps and ETFs, "
          "no leverage, 1% risk per trade, a 15% drawdown halt.",
          "* Expect about 10% to 15% a year with 15% to 25% drawdowns along the way (`research/RESEARCH.md`), "
          "not 5x in two weeks.",
          "* Paper trade it for 8 weeks first and only move to real money with written approval.", ""]
    reviews = os.path.join(ch.JOURNAL, "reviews.md")
    if os.path.exists(reviews):  # every daily review and strategy change, in order
        md += ["## Daily reviews and strategy changes", "", open(reviews).read().split("\n", 1)[-1].strip(), ""]
    with open(os.path.join(ch.JOURNAL, "challenge-summary.md"), "w") as f:
        f.write("\n".join(md))


def push():
    r = subprocess.run(["bash", os.path.join(ch.ROOT, "scripts", "challenge_push.sh")],
                       capture_output=True, text=True, timeout=180)
    return r.returncode == 0


def tick(dry):
    t = Tick(dry)
    try:
        code = t.run()
    finally:
        if not dry and hasattr(t, "equity"):
            ch.save_state(t.state)
    lines = t.journal() if hasattr(t, "equity") else t.notes
    return code, t, lines


def sleep_for(session):
    return {"regular": 300, "pre": 900, "post": 900, "overnight": 900}.get(session, 1800)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--loop", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--max-minutes", type=float, help="exit 0 after this long (the background task limit is 2 h)")
    a = ap.parse_args()
    if not a.loop:
        code, t, lines = tick(a.dry_run)
        print("\n".join(lines[:10]))
        sys.exit(code)
    errors, last_push, started = 0, 0.0, time.time()
    while True:
        if a.max_minutes and time.time() - started > a.max_minutes * 60:
            push()
            print("max minutes reached, exiting for restart", flush=True)
            sys.exit(0)
        session = "closed"
        try:
            code, t, lines = tick(a.dry_run)
            session = t.session
            errors = 0
            print(f"[{t.now:%m-%d %H:%M}] " + " | ".join(lines), flush=True)
            if not t.state.get("challenge_active", True):
                push()
                print("challenge over, summary written, exiting", flush=True)
                sys.exit(0)
        except SystemExit as e:
            if e.code == 2:
                raise  # paper guard refused: never retry
            errors += 1
            print(f"[{datetime.datetime.now(ET):%m-%d %H:%M}] tick failed ({errors} in a row): exit {e.code}", flush=True)
        except Exception:
            errors += 1
            print(f"[{datetime.datetime.now(ET):%m-%d %H:%M}] tick error ({errors} in a row):\n"
                  + traceback.format_exc(limit=3), flush=True)
        if errors >= MAX_ERRORS:
            ch.log_error(f"challenge_run loop stopped after {errors} failed ticks in a row")
            push()
            sys.exit(3)
        if not a.dry_run and time.time() - last_push > 3300:
            last_push = time.time() if push() else last_push
        time.sleep(sleep_for(session))


if __name__ == "__main__":
    main()
