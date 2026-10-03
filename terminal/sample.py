"""Deterministic sample data in the exact shapes the live fetchers return.

Used by demo mode (GitHub panels for a fictional persona) and by `--offline` renders and tests
(every feed, so the whole terminal renders without network access).
"""
import datetime as dt
import math
import random

NOW = dt.datetime.now(dt.timezone.utc)

REPOS = [
    # name, description, language, colour, stars, forks, days since push
    ("tickstore", "Columnar tick store with nanosecond replay", "Rust", "#dea584", 1284, 96, 2),
    ("fillsim", "Queue-position aware fill simulator for limit orders", "Python", "#3572A5", 417, 38, 5),
    ("alphalab", "Reproducible factor research with walk-forward validation", "Python", "#3572A5", 263, 29, 11),
    ("bookviz", "Order book heatmaps in your terminal", "Rust", "#dea584", 932, 51, 1),
    ("kalman-playground", "Kalman filters for pairs and spreads, explained", "Python", "#3572A5", 88, 12, 23),
    ("latency-lab", "Measuring tick-to-trade latency on commodity hardware", "C++", "#f34b7d", 141, 9, 34),
    ("dotfiles", "Terminal, editor and tmux setup", "Shell", "#89e051", 37, 4, 3),
]


def _rng(seed):
    return random.Random(seed)


def github(tz):
    r = _rng(7)
    user = {"id": "DEMO", "createdAt": "2019-03-04T09:00:00Z", "followers": {"totalCount": 1873}}
    repos = [{"name": n, "description": d, "url": f"https://github.com/example/{n}", "stargazerCount": s,
              "forkCount": f, "pushedAt": (NOW - dt.timedelta(days=p, hours=r.randint(0, 20))).isoformat().replace("+00:00", "Z"),
              "isArchived": False, "primaryLanguage": {"name": lang, "color": col}}
             for n, d, lang, col, s, f, p in REPOS]
    start = dt.date(2019, 3, 4)
    days, d = [], start
    while d <= NOW.date():
        base = 6 + 4 * math.sin(d.toordinal() / 41) + (3 if d.weekday() < 5 else -3)
        burst = 18 if r.random() < .04 else 0
        days.append((d.isoformat(), max(0, int(r.gauss(base, 3)) + burst) if r.random() > .07 else 0))
        d += dt.timedelta(days=1)
    # a plausible day: a morning ramp, an afternoon block, and a late-evening open-source shift
    weights = [3, 2, 1, 1, 1, 1, 2, 4, 7, 9, 10, 9, 6, 8, 10, 11, 9, 7, 5, 6, 8, 10, 9, 6]
    hours = [h for h, w in enumerate(weights) for _ in range(w)]
    times = []
    for _ in range(760):
        h = r.choice(hours)
        when = NOW - dt.timedelta(days=r.randint(0, 420))
        times.append(when.astimezone(tz).replace(hour=h, minute=r.randint(0, 59)))
    stars = {}
    for n, _, _, _, s, _, p in REPOS:
        first = NOW - dt.timedelta(days=r.randint(500, 2100))
        stars[n] = sorted(first + (NOW - first) * (r.random() ** 1.7) for _ in range(s))
    return user, repos, days, times, stars


def market(tape):
    """Six months of daily closes per tape label: crypto shares one factor, equities another,
    so correlations and drawdowns look like a real cross-asset book. Crypto trades every day."""
    r = _rng(11)
    start = {"BTC": 84000, "ETH": 2650, "SOL": 118, "SPX": 7680, "NDX": 30300, "FTSE": 9300, "GOLD": 4150,
             "US10Y": 4.1, "GBPUSD": 1.27, "HSI": 24500}
    out = {}
    d, days = NOW.date() - dt.timedelta(days=182), []
    while d <= NOW.date():
        days.append(d)
        d += dt.timedelta(days=1)
    crypto_f = [r.gauss(0, .024) for _ in days]
    equity_f = [r.gauss(0, .008) for _ in days]
    for item in tape:
        label, crypto = item["label"], item.get("crypto")
        price = start.get(label, 100 * (1 + r.random()))
        beta = 1.35 if label == "SOL" else 1.1 if label == "ETH" else 1.0
        series = {}
        for k, day in enumerate(days):
            if not crypto and day.weekday() >= 5:
                continue
            if crypto:
                ret = beta * crypto_f[k] + .25 * equity_f[k] + r.gauss(0, .009)
            elif item.get("equity"):
                ret = equity_f[k] * (1.25 if label == "NDX" else 1) + r.gauss(0, .003)
            else:
                ret = .4 * equity_f[k] + r.gauss(0, .006)
            price *= math.exp(ret)
            series[day] = price
        out[label] = series
    return out


def deribit(currency):
    r = _rng(sum(map(ord, currency)))
    und, base = (84000, 34) if currency == "BTC" else (2650, 46)
    res = []
    for k, dte in enumerate([1.2, 3, 10, 24, 52, 87, 178, 269, 360]):
        exp = (NOW + dt.timedelta(days=dte)).strftime("%d%b%y").upper().lstrip("0")
        atm = base + 7 * math.log1p(dte) / math.log1p(360) + r.uniform(-1, 1)
        step = und * .05
        for j in range(-3, 4):
            strike = round((und + j * step) / (1000 if currency == "BTC" else 50)) * (1000 if currency == "BTC" else 50)
            for kind in "CP":
                res.append({"instrument_name": f"{currency}-{exp}-{strike}-{kind}", "mark_iv": round(atm + abs(j) * 1.4, 2),
                            "underlying_price": und, "open_interest": r.uniform(20, 900)})
    return res


def hyperliquid(names):
    r = _rng(5)
    px = {"BTC": 84000, "ETH": 2650, "SOL": 118, "HYPE": 41, "XRP": 2.6}
    return {n: {"funding": f"{r.uniform(-.00001, .00002):.8f}", "markPx": str(px.get(n, 10)),
                "openInterest": str(r.uniform(2e8, 3e9) / px.get(n, 10))} for n in names}
