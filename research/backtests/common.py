"""Shared helpers for the research backtests: data loading, indicators and metrics."""
from pathlib import Path

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def load_close_panel(path):
    """Wide CSV (date index, one column of daily closes per ticker)."""
    return pd.read_csv(path, index_col=0, parse_dates=True).sort_index()


def load_ohlcv(data_dir, ticker):
    df = pd.read_csv(Path(data_dir) / "ohlcv" / f"{ticker.lower()}.csv", parse_dates=["date"])
    return df.set_index("date").sort_index()


def rsi(close, n):
    """Wilder RSI. Works on a Series or a DataFrame of closes."""
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    rs = gain / loss.replace(0, np.nan)
    out = 100 - 100 / (1 + rs)
    return out.where(loss != 0, 100.0)


def metrics(daily_ret, exposure=None):
    """Summary stats for a series of daily strategy returns (already net of costs)."""
    r = daily_ret.dropna()
    if r.empty:
        return {}
    eq = (1 + r).cumprod()
    years = len(r) / TRADING_DAYS
    cagr = eq.iloc[-1] ** (1 / years) - 1 if eq.iloc[-1] > 0 else -1.0
    dd = eq / eq.cummax() - 1
    vol = r.std() * np.sqrt(TRADING_DAYS)
    sharpe = r.mean() / r.std() * np.sqrt(TRADING_DAYS) if r.std() > 0 else np.nan
    out = {
        "start": r.index[0].date().isoformat(),
        "end": r.index[-1].date().isoformat(),
        "CAGR %": round(cagr * 100, 2),
        "MaxDD %": round(dd.min() * 100, 2),
        "Sharpe": round(sharpe, 2),
        "Vol %": round(vol * 100, 2),
        "Total %": round((eq.iloc[-1] - 1) * 100, 1),
    }
    if exposure is not None:
        out["Exposure %"] = round(float(exposure.reindex(r.index).fillna(0).mean()) * 100, 1)
    return out


def trade_stats(trade_returns):
    t = pd.Series(trade_returns, dtype=float)
    if t.empty:
        return {"Trades": 0}
    wins, losses = t[t > 0], t[t <= 0]
    pf = wins.sum() / -losses.sum() if losses.sum() < 0 else np.inf
    return {
        "Trades": int(len(t)),
        "Win %": round((t > 0).mean() * 100, 1),
        "Avg trade %": round(t.mean() * 100, 3),
        "Avg win %": round(wins.mean() * 100, 2) if len(wins) else 0.0,
        "Avg loss %": round(losses.mean() * 100, 2) if len(losses) else 0.0,
        "Profit factor": round(pf, 2),
    }


def to_markdown(rows, title=None):
    df = pd.DataFrame(rows)
    lines = [f"### {title}", ""] if title else []
    cols = list(df.columns)
    lines.append("| " + " | ".join(cols) + " |")
    lines.append("| " + " | ".join("---" for _ in cols) + " |")
    for _, row in df.iterrows():
        lines.append("| " + " | ".join("" if pd.isna(v) else str(v) for v in row.values) + " |")
    lines.append("")
    return "\n".join(lines)
