#!/usr/bin/env python3
"""Wider strategy search: idea families that need their own trade logic (time of day, gaps,
cross-sectional ranking, daily patterns). Same rules as strategy_search.py: rank on in sample
only (at least 30 trades), report out of sample (the last 120 days) without using it to choose.
Per trade returns after costs (strategy_backtest.cost), unlevered.

  python3 scripts/strategy_ideas.py [family ...]
"""
import datetime
import itertools
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import strategies as S  # noqa: E402
import strategy_backtest as B  # noqa: E402

NOW = datetime.datetime.now(datetime.timezone.utc)
END = (NOW - datetime.timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
SPLIT = (NOW - datetime.timedelta(days=B.OOS_DAYS)).strftime("%Y-%m-%dT%H:%M:%SZ")
INTRADAY = S.ORB_UNIVERSE  # 5 minute history cached for these
ETF3 = ["QQQ", "SPY", "IWM"]


class _U:
    def __init__(self, tf, universe):
        self.timeframe, self.universe = tf, universe


def data(tf, universe, days):
    start = (NOW - datetime.timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return B.fetch(_U(tf, universe), start, END)


def days_of(bars):
    """Group 5 minute bars by ET date: {date: [(minute_of_day, bar), ...]}."""
    out = {}
    for b in bars:
        t = S.et_time(b)
        out.setdefault(t.date(), []).append((t.hour * 60 + t.minute, b))
    return out


def trade(sym, t, side, entry, exit_):
    sign = 1 if side == "long" else -1
    return {"symbol": sym, "t": t, "ret": sign * (exit_ - entry) / entry - 2 * B.cost(sym)}


def intraday_momentum(th, shorts):
    """Return from yesterday's close to 10:00 ET above th: buy at 15:30, sell at the 16:00 close."""
    def run(d):
        out = []
        for sym, bars in d.items():
            prev = None
            for day, rows in sorted(days_of(bars).items()):
                m = dict(rows)
                if prev and 595 in m and 930 in m and 955 in m:
                    r = m[595]["c"] / prev - 1  # 09:55 bar closes at 10:00
                    if r > th:
                        out.append(trade(sym, m[930]["t"], "long", m[925]["c"] if 925 in m else m[930]["o"], m[955]["c"]))
                    elif shorts and r < -th:
                        out.append(trade(sym, m[930]["t"], "short", m[925]["c"] if 925 in m else m[930]["o"], m[955]["c"]))
                regular = [b for mm, b in rows if 570 <= mm < 960]
                prev = regular[-1]["c"] if regular else prev
        return out
    return f"intraday momentum th{th:.2%} shorts{int(shorts)}", "5Min", INTRADAY, 400, run


def gap(g, mode):
    """Gap from yesterday's close to today's open of at least g. fade: trade back toward yesterday's close
    (target it, exit 15:55); go: trade with the gap, exit 15:55. Entry at the 09:35 close, stop at the day's
    extreme so far (first 5 minute bar)."""
    def run(d):
        out = []
        for sym, bars in d.items():
            prev = None
            for day, rows in sorted(days_of(bars).items()):
                reg = [(mm, b) for mm, b in rows if 570 <= mm < 960]
                if prev and len(reg) > 10 and reg[0][0] == 570:
                    gp = reg[0][1]["o"] / prev - 1
                    if abs(gp) >= g:
                        up = gp > 0
                        side = ("short" if up else "long") if mode == "fade" else ("long" if up else "short")
                        entry, first = reg[1][1]["c"], reg[0][1]
                        stop = first["h"] if side == "short" else first["l"]
                        target = prev if mode == "fade" else None
                        px = reg[-1][1]["c"]
                        for mm, b in reg[2:]:
                            if side == "long" and b["l"] <= stop or side == "short" and b["h"] >= stop:
                                px = stop
                                break
                            if target and (side == "long" and b["h"] >= target or side == "short" and b["l"] <= target):
                                px = target
                                break
                        if (side == "long" and stop < entry) or (side == "short" and stop > entry):
                            out.append(trade(sym, reg[1][1]["t"], side, entry, px))
                prev = reg[-1][1]["c"] if reg else prev
        return out
    return f"gap {mode} {g:.1%}", "5Min", INTRADAY, 400, run


def xs_reversal(k, hold):
    """Daily: at the close buy the k stocks with the worst 1 day return; sell at the next open or close."""
    def run(d):
        dates = sorted({b["t"][:10] for bars in d.values() for b in bars})
        by = {s: {b["t"][:10]: b for b in bars} for s, bars in d.items()}
        out = []
        for i in range(1, len(dates) - 1):
            rets = []
            for s in by:
                a, b = by[s].get(dates[i - 1]), by[s].get(dates[i])
                if a and b and by[s].get(dates[i + 1]):
                    rets.append((b["c"] / a["c"] - 1, s))
            for r, s in sorted(rets)[:k]:
                nxt = by[s][dates[i + 1]]
                out.append(trade(s, nxt["t"], "long", by[s][dates[i]]["c"], nxt["o"] if hold == "open" else nxt["c"]))
        return out
    return f"cross-section reversal k{k} to next {hold}", "1Day", S.STOCKS, 1100, run


def ibs(th, universe, label):
    """Daily: close in the bottom th of the day's range and above SMA200 -> buy at the close; sell at the first
    close above the previous day's high, or after 5 days."""
    def run(d):
        out = []
        for s, bars in d.items():
            c = [b["c"] for b in bars]
            i = 200
            while i < len(bars) - 1:
                b = bars[i]
                v = (b["c"] - b["l"]) / (b["h"] - b["l"]) if b["h"] > b["l"] else 0.5
                if v < th and b["c"] > sum(c[i - 199:i + 1]) / 200:
                    j = i + 1
                    while j < len(bars) - 1 and bars[j]["c"] <= bars[j - 1]["h"] and j - i < 5:
                        j += 1
                    out.append(trade(s, bars[i + 1]["t"], "long", b["c"], bars[j]["c"]))
                    i = j
                i += 1
        return out
    return f"ibs<{th} {label}", "1Day", universe, 1100, run


def nr7(universe, label):
    """Daily: today's range is the narrowest of 7 days -> next day buy if it trades above today's high
    (fill at the high, or the open if it gaps above), sell at that day's close."""
    def run(d):
        out = []
        for s, bars in d.items():
            for i in range(7, len(bars) - 1):
                rng = [b["h"] - b["l"] for b in bars[i - 6:i + 1]]
                if rng[-1] == min(rng) and bars[i + 1]["h"] > bars[i]["h"]:
                    entry = max(bars[i]["h"], bars[i + 1]["o"])
                    out.append(trade(s, bars[i + 1]["t"], "long", entry, bars[i + 1]["c"]))
        return out
    return f"nr7 breakout {label}", "1Day", universe, 1100, run


def crypto_trend(n):
    """Daily crypto: hold while the close is above SMA(n); one trade per holding period."""
    def run(d):
        out = []
        for s, bars in d.items():
            c, i = [b["c"] for b in bars], n
            while i < len(bars) - 1:
                if c[i] > sum(c[i - n + 1:i + 1]) / n:
                    j = i + 1
                    while j < len(bars) - 1 and c[j] > sum(c[j - n + 1:j + 1]) / n:
                        j += 1
                    out.append(trade(s, bars[i + 1]["t"], "long", c[i], c[j]))
                    i = j
                i += 1
        return out
    return f"crypto trend sma{n}", "1Day", S.CRYPTO, 1100, run


FAMILIES = {
    "momentum": [intraday_momentum(th, sh) for th, sh in itertools.product((0.0, 0.0025, 0.005), (False, True))],
    "gap": [gap(g, m) for g, m in itertools.product((0.005, 0.01, 0.02), ("fade", "go"))],
    "reversal": [xs_reversal(k, h) for k, h in itertools.product((1, 2, 3), ("open", "close"))],
    "ibs": [ibs(th, u, lab) for th, (u, lab) in itertools.product((0.1, 0.2, 0.3), ((ETF3, "etf"), (S.STOCKS, "stocks")))],
    "nr7": [nr7(u, lab) for u, lab in ((ETF3, "etf"), (S.STOCKS, "stocks"))],
    "crypto": [crypto_trend(n) for n in (10, 20, 50)],
}


def main():
    for fam in sys.argv[1:] or FAMILIES:
        results = []
        for name, tf, universe, days, run in FAMILIES[fam]:
            trades = run(data(tf, universe, days))
            ins = B.stats([t for t in trades if t["t"] < SPLIT])
            oos = B.stats([t for t in trades if t["t"] >= SPLIT])
            if ins["n"] >= 30:
                results.append((ins["pf"], name, ins, oos))
        results.sort(reverse=True)
        print(f"== {fam}")
        for pf, name, ins, oos in results[:4]:
            print(f"{name:38} IN n{ins['n']} win {ins['win']:.0%} avg {ins['avg_win']:+.2%}/{ins['avg_loss']:+.2%} "
                  f"pf {ins['pf']:.2f} | OUT n{oos['n']} win {oos.get('win', 0):.0%} "
                  f"avg {oos.get('avg_win', 0):+.2%}/{oos.get('avg_loss', 0):+.2%} pf {oos.get('pf', 0):.2f}", flush=True)


if __name__ == "__main__":
    main()
