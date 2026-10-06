#!/usr/bin/env python3
"""Search simple strategy variants on the cached backtest data (run strategy_backtest.py first).

Each family gets a small grid of parameters. Variants are ranked on the IN SAMPLE period only
(profit factor, at least 30 trades); the best few are then shown with their out of sample result,
which was never used for choosing. Promote a variant into strategies.py only if it is profitable
out of sample too.

  python3 scripts/strategy_search.py [family ...]
"""
import datetime
import itertools
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import strategies as S  # noqa: E402
import strategy_backtest as B  # noqa: E402


class Breakout:
    """Close above the highest high of the last n bars while above EMA(trend): long. Mirror for shorts."""
    timeframe, universe = "1Hour", S.STOCKS + S.CRYPTO

    def __init__(self, n, k, r, exit_ema, shorts):
        self.n, self.k, self.r, self.exit_ema, self.shorts = n, k, r, exit_ema, shorts
        self.name, self.warmup = f"breakout n{n} k{k} r{r} exit{exit_ema} shorts{int(shorts)}", max(n, 200)

    def prepare(self, bars):
        c = [b["c"] for b in bars]
        return {"trend": S.ema(c, 200), "ex": S.ema(c, self.exit_ema), "atr": S.atr(bars)}

    def entry(self, ind, bars, i):
        c, a = bars[i]["c"], ind["atr"][i]
        hi = max(b["h"] for b in bars[i - self.n:i])
        lo = min(b["l"] for b in bars[i - self.n:i])
        if c > hi and c > ind["trend"][i]:
            return "long", c - self.k * a, self.r
        if self.shorts and c < lo and c < ind["trend"][i]:
            return "short", c + self.k * a, self.r
        return None

    def exit(self, ind, bars, i, pos):
        c = bars[i]["c"]
        if pos["side"] == "long" and c < ind["ex"][i]:
            return "below exit EMA"
        if pos["side"] == "short" and c > ind["ex"][i]:
            return "above exit EMA"
        return None


class Pullback:
    """Long only: above EMA200, RSI(2) below a threshold. Exit above EMA5 or after max_bars."""
    timeframe, universe = "1Hour", S.STOCKS + S.CRYPTO

    def __init__(self, th, k, max_bars):
        self.th, self.k, self.max_bars = th, k, max_bars
        self.name, self.warmup = f"pullback rsi<{th} k{k} max{max_bars}", 200

    def prepare(self, bars):
        c = [b["c"] for b in bars]
        return {"e200": S.ema(c, 200), "e5": S.ema(c, 5), "rsi": S.rsi(c, 2), "atr": S.atr(bars)}

    def entry(self, ind, bars, i):
        if bars[i]["c"] > ind["e200"][i] and ind["rsi"][i] < self.th:
            return "long", bars[i]["c"] - self.k * ind["atr"][i], None
        return None

    def exit(self, ind, bars, i, pos):
        if bars[i]["c"] > ind["e5"][i]:
            return "above EMA5"
        return "time stop" if i - pos["entry_i"] >= self.max_bars else None


class OpeningRange:
    """ORB with a variable range length and target; r=None holds to 15:50 ET."""
    timeframe, universe = "5Min", S.ORB_UNIVERSE

    def __init__(self, bars_in_range, r, shorts):
        self.nr, self.r, self.shorts = bars_in_range, r, shorts
        self.name, self.warmup = f"orb {5 * bars_in_range}min r{r} shorts{int(shorts)}", 3

    def prepare(self, bars):
        hi, lo, day, rng = [], [], None, None
        for b in bars:
            t = S.et_time(b)
            if t.date() != day:
                day, rng = t.date(), [None, None, 0]
            m = t.hour * 60 + t.minute - 570
            if 0 <= m < 5 * self.nr:
                rng[0] = b["h"] if rng[0] is None else max(rng[0], b["h"])
                rng[1] = b["l"] if rng[1] is None else min(rng[1], b["l"])
                rng[2] += 1
            ok = rng[2] == self.nr
            hi.append(rng[0] if ok else None)
            lo.append(rng[1] if ok else None)
        return {"hi": hi, "lo": lo}

    def entry(self, ind, bars, i):
        t = S.et_time(bars[i])
        hm = t.hour * 60 + t.minute
        if ind["hi"][i] is None or not (570 + 5 * self.nr <= hm <= 14 * 60 + 30):
            return None
        c = bars[i]["c"]
        if c > ind["hi"][i]:
            return "long", ind["lo"][i], self.r
        if self.shorts and c < ind["lo"][i]:
            return "short", ind["hi"][i], self.r
        return None

    def exit(self, ind, bars, i, pos):
        t = S.et_time(bars[i])
        return "15:50 ET" if t.hour * 60 + t.minute >= 15 * 60 + 50 else None


class IBS:
    """Daily bars, long only: close in the bottom of the day's range (IBS < th) above SMA200 -> buy next open;
    sell at the next open after a close above the prior day's high, or after max_days."""
    timeframe = "1Day"

    def __init__(self, th, max_days, universe, label):
        self.th, self.max_days, self.universe = th, max_days, universe
        self.name, self.warmup = f"ibs<{th} max{max_days} {label}", 200

    def prepare(self, bars):
        c = [b["c"] for b in bars]
        sma = [sum(c[max(0, i - 199):i + 1]) / min(i + 1, 200) for i in range(len(c))]
        return {"sma": sma, "atr": S.atr(bars)}

    def entry(self, ind, bars, i):
        b = bars[i]
        ibs = (b["c"] - b["l"]) / (b["h"] - b["l"]) if b["h"] > b["l"] else 0.5
        if ibs < self.th and b["c"] > ind["sma"][i]:
            return "long", b["c"] - 3 * ind["atr"][i], None
        return None

    def exit(self, ind, bars, i, pos):
        if bars[i]["c"] > bars[i - 1]["h"]:
            return "close above prior high"
        return "time" if i - pos["entry_i"] >= self.max_days else None


class Overnight:
    """Buy at the close, sell at the next open (daily bars), only while the close is above SMA(n)."""
    timeframe = "1Day"

    def __init__(self, n, universe, label):
        self.n, self.universe, self.name = n, universe, f"overnight sma{n} {label}"


def overnight_trades(v, data):
    trades = []
    for sym, bars in data.items():
        c = [b["c"] for b in bars]
        for i in range(v.n, len(bars) - 1):
            if c[i] > sum(c[i - v.n + 1:i + 1]) / v.n:
                trades.append({"symbol": sym, "t": bars[i + 1]["t"],
                               "ret": bars[i + 1]["o"] / c[i] - 1 - 2 * B.cost(sym)})
    return trades


ETF3 = ["QQQ", "SPY", "IWM"]
FAMILIES = {
    "ibs": [IBS(th, md, u, lab) for th, md, (u, lab) in
            itertools.product((0.15, 0.25), (3, 5), ((ETF3, "etf"), (S.STOCKS, "stocks")))],
    "overnight": [Overnight(n, u, lab) for n, (u, lab) in
                  itertools.product((1, 20, 50), ((ETF3, "etf"), (S.STOCKS, "stocks")))],
    "breakout_stocks": [Breakout(n, k, r, e, False) for n, k, r, e in
                        itertools.product((20, 50), (2, 3), (None, 3), (20, 50))],
    "breakout": [Breakout(n, k, r, e, sh) for n, k, r, e, sh in
                 itertools.product((20, 50), (2, 3), (None, 3), (20, 50), (False, True))],
    "pullback": [Pullback(th, k, mb) for th, k, mb in itertools.product((5, 10), (3, 6), (12, 36))],
    "orb": [OpeningRange(nr, r, sh) for nr, r, sh in itertools.product((1, 3, 6), (1.0, 2.0, None), (False, True))],
}


def main():
    now = datetime.datetime.now(datetime.timezone.utc)
    start = (now - datetime.timedelta(days=400)).strftime("%Y-%m-%dT%H:%M:%SZ")
    end = (now - datetime.timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    split = (now - datetime.timedelta(days=B.OOS_DAYS)).strftime("%Y-%m-%dT%H:%M:%SZ")
    for fam in sys.argv[1:] or FAMILIES:
        variants = FAMILIES[fam]
        results = []
        for v in variants:
            if fam == "breakout_stocks":
                v.universe = S.STOCKS
            data = B.fetch(v, start, end)
            trades = overnight_trades(v, data) if fam == "overnight" else \
                [t for sym, bars in data.items() for t in B.simulate(v, sym, bars)]
            ins = B.stats([t for t in trades if t["t"] < split])
            oos = B.stats([t for t in trades if t["t"] >= split])
            if ins["n"] >= 30:
                results.append((ins["pf"], v.name, ins, oos))
        results.sort(reverse=True)
        print(f"== {fam}: best by in sample profit factor (out of sample shown, not used to choose)")
        for pf, name, ins, oos in results[:5]:
            print(f"{name:40} IN n{ins['n']} win {ins['win']:.0%} avg {ins['avg_win']:+.2%}/{ins['avg_loss']:+.2%} "
                  f"pf {ins['pf']:.2f} | OUT n{oos['n']} win {oos.get('win', 0):.0%} pf {oos.get('pf', 0):.2f} "
                  f"profit {oos.get('profit', 0):+.1%}")


if __name__ == "__main__":
    main()
