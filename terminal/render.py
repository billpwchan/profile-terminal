"""Render every panel into an output directory.

Each data source is isolated: when one feed fails, its panel is skipped and the previous render
(restored from the output branch) stays live. Nothing here ever needs an API key.
"""
import json
import sys
import traceback
from pathlib import Path
from zoneinfo import ZoneInfo

from . import cards, data, sample, theme

NOW = data.NOW


def ago(ts):
    days = (NOW - ts).days
    if days < 1:
        return "today"
    if days < 30:
        return f"{days}d ago"
    if days < 365:
        return f"{days // 30}mo ago"
    return f"{days // 365}y ago"


def streak(days):
    counts = [c for _, c in days]
    i = len(counts) - 1
    if counts and counts[i] == 0:
        i -= 1
    n = 0
    while i >= 0 and counts[i]:
        n, i = n + 1, i - 1
    return n


def _hm(s):
    h, m = s.split(":")
    return int(h) * 60 + int(m)


def session_states(cfg, now):
    out = []
    for s in cfg["markets"]["sessions"]:
        local = now.astimezone(ZoneInfo(s["tz"]))
        m = local.hour * 60 + local.minute
        state = "OPEN" if local.weekday() < 5 and _hm(s["open"]) <= m < _hm(s["close"]) else "CLOSED"
        if state == "OPEN" and s.get("lunch"):
            a, b = s["lunch"].split("-")
            if _hm(a) <= m < _hm(b):
                state = "LUNCH"
        out.append((s["name"], state))
    if any(t.get("crypto") for t in cfg["markets"]["tape"]):
        out.append(("CRYPTO", "24/7"))
    return out


def session_focus(cfg, states, tz):
    """Which tape symbols lead (and get highlighted), and how the LAB strip describes the moment."""
    tape = cfg["markets"]["tape"]
    live = [name for name, st in states if st in ("OPEN", "LUNCH")]
    if live:
        return {t["label"] for t in tape if t.get("session") in live}, f"{' + '.join(live)} SESSION LIVE"
    crypto = {t["label"] for t in tape if t.get("crypto")}
    weekend = NOW.astimezone(tz).weekday() >= 5
    return crypto, ("WEEKEND · CRYPTO TRADES 24/7" if weekend else "CASH MARKETS CLOSED · CRYPTO 24/7") if crypto else "MARKETS CLOSED"


def fmt_quote(item, v):
    if item.get("percent"):
        return f"{v:.2f}%"
    if item.get("decimals") is not None:
        return f"{v:,.{item['decimals']}f}"
    return f"{v:,.0f}" if v >= 10000 else f"{v:,.2f}"


class Renderer:
    def __init__(self, cfg, out, offline=False):
        self.cfg, self.out, self.offline = cfg, Path(out), offline
        self.tz = ZoneInfo(cfg["timezone"])
        self.tz_label = NOW.astimezone(self.tz).strftime("%Z") or cfg["timezone"]
        self.written = []

    def write(self, name, svg):
        (self.out / f"{name}.svg").write_text(svg)
        self.written.append(name)
        print(f"wrote {name}.svg ({len(svg) // 1024} KB)")

    @staticmethod
    def guarded(label, fn, *args):
        try:
            return fn(*args)
        except Exception:
            print(f"[{label}] failed, keeping the previous render", file=sys.stderr)
            traceback.print_exc()
            return None

    # ------------------------------------------------------------------ data
    def github(self):
        if self.cfg["demo"] or self.offline:
            user, repos, days, times, stars = sample.github(self.tz)
            return user, repos, days, times, lambda name: stars.get(name.split("/")[-1], [])
        data.USER = self.cfg["github_user"]
        user, repos = data.fetch_profile()
        days = data.fetch_calendar(user["createdAt"])
        times = self.guarded("commit times", data.fetch_commit_times, user["id"], repos, self.tz) or []
        return user, repos, days, times, lambda name: self.guarded(f"stars {name}", data.fetch_stars, name) or []

    def markets(self):
        tape = self.cfg["markets"]["tape"]
        if self.offline:
            return sample.market(tape)
        series = {}
        for item in tape:
            s = self.guarded(f"yahoo {item['symbol']}", data.fetch_chart, item["symbol"])
            if s and len(s) >= 2:
                series[item["label"]] = s
        return series

    def derivs(self):
        m = self.cfg["markets"]
        vol = {}
        for ccy in m["options"]:
            summ = sample.deribit(ccy) if self.offline else self.guarded(f"deribit {ccy}", data.fetch_deribit, ccy)
            if summ:
                vol[ccy] = cards.atm_term_structure(summ, NOW)
        hl = sample.hyperliquid(m["perps"]) if self.offline else (self.guarded("hyperliquid", data.fetch_hyperliquid) or {})
        return vol, {k: hl[k] for k in m["perps"] if k in hl}

    # ------------------------------------------------------------------ render
    def run(self):
        cfg = self.cfg
        self.out.mkdir(parents=True, exist_ok=True)
        theme.apply_theme(cfg["theme"], cfg.get("accent") or None)
        name = cfg["identity"]["name"]
        cards.TICKER = (name.split()[0] if name.split() else "YOU").upper()[:10]
        state = self.out / "state.json"
        if state.exists():
            theme.PREV.update(json.loads(state.read_text()))
        stamp = NOW.astimezone(self.tz).strftime(f"%d %b %H:%M {self.tz_label}").upper()
        tape_cfg = cfg["markets"]["tape"]
        crypto = {t["label"] for t in tape_cfg if t.get("crypto")}
        equity = tuple(t["label"] for t in tape_cfg if t.get("equity"))

        gh = self.guarded("github", self.github)
        series = self.markets()
        states = session_states(cfg, NOW)
        lead, lab_status = session_focus(cfg, states, self.tz)
        demo_note = "DEMO PROFILE · SAMPLE GITHUB DATA · " if cfg["demo"] else ""

        if gh:
            user, repos, days, times, stars_of = gh
            year = [c for _, c in days[-365:]]
            by_name = {r["name"].lower(): r for r in repos}
            tape = []
            for item in sorted(tape_cfg, key=lambda t: t["label"] not in lead):
                if item["label"] in series:
                    vals = list(series[item["label"]].values())
                    tape.append((item["label"], fmt_quote(item, vals[-1]), (vals[-1] / vals[-2] - 1) * 100, item["label"] in lead))
            stars_total = sum(r["stargazerCount"] for r in repos)
            tape += [(f"{cards.TICKER}:GH", f"{sum(year):,} 12M", None, False), ("STARS", f"{stars_total:,}", None, False),
                     ("FORKS", f"{sum(r['forkCount'] for r in repos):,}", None, False)]
            ident = cfg["identity"]
            hero = dict(name=ident["name"], role=ident["role"], rows=[tuple(r) for r in ident["rows"]][:5],
                        stamp=stamp, sessions=states, tape=tape, year=year,
                        total=sum(c for _, c in days), streak=streak(days), end=days[-1][0])
            if cfg["demo"]:
                # the showcase also renders the hero in every preset for the README's theme gallery
                for preset in theme.PRESETS:
                    theme.apply_theme(preset)
                    self.write(f"theme-{preset}", cards.hero(hero))
                theme.apply_theme(cfg["theme"], cfg.get("accent") or None)
            self.write("hero", cards.hero(hero))
            work = cfg["work"]["repos"][:4]
            for i, w in enumerate(work):
                r = by_name.get(w["repo"].split("/")[-1].lower())
                if not r:
                    print(f"[work] {w['repo']} not found among public repos", file=sys.stderr)
                    continue
                r = dict(r, _ago=f"UPDATED {ago(data.parse_ts(r['pushedAt'])).upper()}")
                stars = stars_of(w["repo"])
                copy = dict(tag=w.get("tag", ""), pitch=w.get("pitch", r.get("description") or ""), zh=w.get("sub", ""))
                self.write(f"work-{i}", cards.work_card(r, copy, stars, NOW, i % 2, dur=(19, 23, 31, 37)[i % 4]))
                if w["repo"] in cfg["work"].get("banners", []):
                    spec = dict(kicker=w.get("tag", ""), visual="stars", pitch=copy["pitch"], zh=copy["zh"], tags=[w.get("tag", "")])
                    self.write(f"banner-{r['name']}", cards.banner(r, spec, stars, NOW))
            if times:
                bands = [tuple(b) for b in cfg["flow"]["bands"]]
                self.write("activity", cards.activity(times, self.tz_label, bands))
            hidden = {h.lower() for h in cfg["flow"]["hide"]} | {w["repo"].split("/")[-1].lower() for w in work} | {cfg["github_user"].lower()}
            visible = sorted((r for r in repos if r["name"].lower() not in hidden and not r["isArchived"]),
                             key=lambda r: r["pushedAt"], reverse=True)[:cfg["flow"]["recent"]]
            if visible:
                self.write("recent", cards.recent(visible, lambda r: ago(data.parse_ts(r["pushedAt"]))))
            self.write("grid", cards.calendar_grid(days))
            links = cfg["links"][:5]
            for i, ln in enumerate(links):
                if ln.get("auto") == "github":
                    ln = dict(code="GH", title=f"{stars_total:,} stars", sub=f"{user['followers']['totalCount']:,} followers")
                self.write(f"key-{i}", cards.keycap(ln["code"], ln["title"], ln.get("sub", ""), i, len(links)))
            self.write("strip-work", cards.strip("WORK", demo_note + cfg["work"]["status"]))
            self.write("strip-flow", cards.strip("FLOW", f"{demo_note}HOW I SHIP · {sum(year):,} CONTRIBUTIONS IN 12M"))
        self.write("strip-lab", cards.strip("LAB", f"{lab_status} · YAHOO · DERIBIT · HYPERLIQUID"))

        risk = {t["label"]: series[t["label"]] for t in tape_cfg if t.get("risk") and t["label"] in series}
        if len(risk) >= 3:
            self.guarded("risk", lambda: self.write("risk", cards.risk_monitor(risk, crypto, stamp, equity)))
        vol, perps = self.derivs()
        if cfg["markets"]["options"] or cfg["markets"]["perps"]:
            self.guarded("derivatives", lambda: self.write("derivatives", cards.derivatives(vol, perps, stamp)))
        if len(risk) >= 3:
            def render_regime():
                rows, syms, M, _ = cards.risk_stats(risk, crypto)
                lead_ccy = cfg["markets"]["options"][0] if cfg["markets"]["options"] else None
                term = vol.get(lead_ccy, (None,))[0] if lead_ccy else None
                first = cfg["markets"]["perps"][0] if cfg["markets"]["perps"] else None
                funding = float(perps[first]["funding"]) * 24 * 365 * 100 if first in perps else None
                self.write("regime", cards.regime(rows, syms, M, crypto, term, funding, equity, lead_ccy or "", first or ""))
            self.guarded("regime", render_regime)

        state.write_text(json.dumps({**theme.PREV, **theme.CURR}, sort_keys=True, indent=0))
        (self.out / "manifest.json").write_text(json.dumps({"rendered": NOW.isoformat(), "panels": self.written}, indent=1))
        return self.written


def render(cfg, out, offline=False):
    return Renderer(cfg, out, offline).run()

