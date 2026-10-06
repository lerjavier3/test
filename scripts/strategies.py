"""Challenge strategies, shared by the live runner (challenge_run.py) and the backtester
(strategy_backtest.py) so both trade exactly the same rules.

Each strategy works on a list of bars ({"t","o","h","l","c"}) of its timeframe:
  prepare(bars)            -> indicator arrays
  entry(ind, bars, i)      -> ("long"|"short", stop_price, target_R or None) or None, on the close of bar i
  exit(ind, bars, i, pos)  -> reason string or None, on the close of bar i (stops and targets are separate)
pos = {"side", "entry_i", "entry", "stop"}. Keep every strategy simple; the RULES text is what the
final report gives the user for trading by hand.
"""
import datetime
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
STOCKS = ["QQQ", "SPY", "IWM", "NVDA", "TSLA", "AAPL", "MSFT", "AMZN", "META", "AMD", "GOOGL", "AVGO"]
CRYPTO = ["BTC/USD", "ETH/USD", "SOL/USD"]
ORB_UNIVERSE = ["QQQ", "SPY", "NVDA", "TSLA", "AMD"]


def ema(xs, n):
    k, out, e = 2 / (n + 1), [], None
    for x in xs:
        e = x if e is None else x * k + e * (1 - k)
        out.append(e)
    return out


def rsi(closes, n):
    out, up, dn = [50.0], 0.0, 0.0
    for i in range(1, len(closes)):
        ch = closes[i] - closes[i - 1]
        up = (up * (n - 1) + max(ch, 0)) / n
        dn = (dn * (n - 1) + max(-ch, 0)) / n
        out.append(100.0 if dn == 0 else 100 - 100 / (1 + up / dn))
    return out


def atr(bars, n=14):
    out, a = [], None
    for i, b in enumerate(bars):
        tr = b["h"] - b["l"] if i == 0 else max(b["h"] - b["l"], abs(b["h"] - bars[i - 1]["c"]),
                                                  abs(b["l"] - bars[i - 1]["c"]))
        a = tr if a is None else (a * (n - 1) + tr) / n
        out.append(a)
    return out


def et_time(bar):
    return datetime.datetime.fromisoformat(bar["t"].replace("Z", "+00:00")).astimezone(ET)


class Trend:
    name, timeframe, warmup = "trend", "1Hour", 60
    universe = STOCKS + CRYPTO
    indicators = "EMA20, EMA50, ATR14 (1 hour bars)"
    rules = ("1 hour bars. Long when close > EMA20 > EMA50; short (stocks only) when close < EMA20 < EMA50. "
             "Stop 1.5 x ATR14 from entry, take profit 4 x ATR14. Exit early when the opposite condition appears.")

    def prepare(self, bars):
        c = [b["c"] for b in bars]
        return {"e20": ema(c, 20), "e50": ema(c, 50), "atr": atr(bars)}

    def entry(self, ind, bars, i):
        c, e20, e50, a = bars[i]["c"], ind["e20"][i], ind["e50"][i], ind["atr"][i]
        if c > e20 > e50:
            return "long", c - 1.5 * a, 4 / 1.5
        if c < e20 < e50:
            return "short", c + 1.5 * a, 4 / 1.5
        return None

    def exit(self, ind, bars, i, pos):
        c, e20, e50 = bars[i]["c"], ind["e20"][i], ind["e50"][i]
        if pos["side"] == "long" and c < e20 < e50:
            return "trend flipped down"
        if pos["side"] == "short" and c > e20 > e50:
            return "trend flipped up"
        return None


class RSI2:
    name, timeframe, warmup = "rsi2", "1Hour", 200
    universe = STOCKS + CRYPTO
    indicators = "RSI2, EMA200, EMA5, ATR14 (1 hour bars)"
    rules = ("1 hour bars, long only. Buy when close > EMA200 and RSI(2) < 10. Stop 2 x ATR14 below entry. "
             "Sell when close > EMA5, or after 12 bars.")

    def prepare(self, bars):
        c = [b["c"] for b in bars]
        return {"e200": ema(c, 200), "e5": ema(c, 5), "rsi": rsi(c, 2), "atr": atr(bars)}

    def entry(self, ind, bars, i):
        if bars[i]["c"] > ind["e200"][i] and ind["rsi"][i] < 10:
            return "long", bars[i]["c"] - 2 * ind["atr"][i], None
        return None

    def exit(self, ind, bars, i, pos):
        if bars[i]["c"] > ind["e5"][i]:
            return "close above EMA5"
        if i - pos["entry_i"] >= 12:
            return "12 bar time stop"
        return None


class ORB:
    name, timeframe, warmup = "orb", "5Min", 3
    universe = ORB_UNIVERSE
    indicators = "30 minute opening range (5 minute bars)"
    rules = ("5 minute bars, regular session, long only. Opening range = high and low of 09:30 to 10:00 ET. From "
             "10:00 to 14:30 ET, the first 5 minute close above the range high is a buy, stop at the range low. "
             "One trade per symbol per day. Take profit at 2R. Close at 15:50 ET.")
    range_bars = 6

    def prepare(self, bars):
        hi, lo, day, rng = [], [], None, None
        for b in bars:
            t = et_time(b)
            if t.date() != day:
                day, rng = t.date(), [None, None, 0]
            if 0 <= t.hour * 60 + t.minute - 570 < 5 * self.range_bars:
                rng[0] = b["h"] if rng[0] is None else max(rng[0], b["h"])
                rng[1] = b["l"] if rng[1] is None else min(rng[1], b["l"])
                rng[2] += 1
            ok = rng[2] == self.range_bars
            hi.append(rng[0] if ok else None)
            lo.append(rng[1] if ok else None)
        return {"hi": hi, "lo": lo}

    def entry(self, ind, bars, i):
        t = et_time(bars[i])
        hm = t.hour * 60 + t.minute
        if ind["hi"][i] is None or not (570 + 5 * self.range_bars <= hm <= 14 * 60 + 30):
            return None
        if bars[i]["c"] > ind["hi"][i]:
            return "long", ind["lo"][i], 2.0
        return None

    def exit(self, ind, bars, i, pos):
        t = et_time(bars[i])
        return "15:50 ET close" if t.hour * 60 + t.minute >= 15 * 60 + 50 else None


class Breakout:
    name, timeframe, warmup = "breakout", "1Hour", 200
    universe = STOCKS
    indicators = "50 bar high, EMA200, EMA50, ATR14 (1 hour bars)"
    rules = ("1 hour bars, stocks and ETFs, long only. Buy when the close is above the highest high of the previous "
             "50 bars and above EMA200. Stop 3 x ATR14 below entry, no fixed target. Sell when a bar closes below "
             "EMA50.")

    def prepare(self, bars):
        c = [b["c"] for b in bars]
        return {"e200": ema(c, 200), "e50": ema(c, 50), "atr": atr(bars)}

    def entry(self, ind, bars, i):
        if i < 50:
            return None
        c = bars[i]["c"]
        if c > max(b["h"] for b in bars[i - 50:i]) and c > ind["e200"][i]:
            return "long", c - 3 * ind["atr"][i], None
        return None

    def exit(self, ind, bars, i, pos):
        return "close below EMA50" if bars[i]["c"] < ind["e50"][i] else None


class Overnight:
    """Live: entered 15:50 to 15:58 ET, sold at the next regular open. Backtest: close to next open."""
    name, timeframe, warmup = "overnight", "1Day", 20
    universe = STOCKS
    indicators = "SMA20 (daily bars)"
    rules = ("Daily. At about 15:55 ET buy the stocks and ETFs whose price is above their 20 day simple moving "
             "average (strongest first, as many as the slots allow). Sell at the next regular open (09:30 to "
             "09:35 ET). Emergency stop 3% below entry.")

    def prepare(self, bars):
        c = [b["c"] for b in bars]
        return {"sma": [sum(c[max(0, i - 19):i + 1]) / min(i + 1, 20) for i in range(len(c))]}

    def entry(self, ind, bars, i):
        c = bars[i]["c"]
        return ("long", c * 0.97, None) if c > ind["sma"][i] else None

    def exit(self, ind, bars, i, pos):
        return None  # time based, handled by the runner


ALL = {s.name: s for s in (Trend(), RSI2(), ORB(), Breakout(), Overnight())}

