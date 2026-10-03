"""Build the profile README from profile.yml: one block of zero-gap tiles served from the output branch."""
import html


def _img(base, name, alt, width="100%"):
    return f'<img src="{base}{name}.svg" alt="{html.escape(alt, quote=True)}" width="{width}">'


def _a(href, inner):
    return f'<a href="{html.escape(href, quote=True)}">{inner}</a>'


def build(cfg, use_snake):
    base = f"https://raw.githubusercontent.com/{cfg['repository']}/output/"
    user = cfg["github_user"]
    ident = cfg["identity"]
    hero_alt = f"{ident['name']}, {ident['role']}. " + "; ".join(f"{c}: {v}" for c, v in ident["rows"])
    home = next((ln["url"] for ln in cfg["links"] if ln.get("url", "").startswith("http")), f"https://github.com/{user}")
    lines = [_a(home, _img(base, "hero", hero_alt))]
    links = cfg["links"][:5]
    width = f"{100 / len(links):g}%" if links else "20%"
    keys = []
    for i, ln in enumerate(links):
        url = f"https://github.com/{user}?tab=followers" if ln.get("auto") == "github" else ln.get("url", "#")
        alt = "GitHub stars and followers" if ln.get("auto") == "github" else f"{ln['title']}: {ln.get('sub', '')}"
        keys.append(_a(url, _img(base, f"key-{i}", alt, width)))
    lines.append("".join(keys))
    work = cfg["work"]["repos"][:4]
    if work:
        lines.append(_a(f"https://github.com/{user}?tab=repositories&sort=stargazers", _img(base, "strip-work", "Section 2: selected work")))
        tiles = []
        for i, w in enumerate(work):
            repo = w["repo"] if "/" in w["repo"] else f"{user}/{w['repo']}"
            tiles.append(_a(f"https://github.com/{repo}", _img(base, f"work-{i}", f"{w['repo']}: {w.get('pitch', '')}", "50%")))
        for i in range(0, len(tiles), 2):
            lines.append("".join(tiles[i:i + 2]))
    m = cfg["markets"]
    if m["tape"] or m["options"] or m["perps"]:
        lines.append(_img(base, "strip-lab", "Section 3: lab"))
        lines.append(_img(base, "regime", "Regime monitor: rule-based market state signals"))
        lines.append(_img(base, "risk", "Cross-asset realized volatility, drawdown and correlation"))
        if m["options"] or m["perps"]:
            lines.append(_img(base, "derivatives", "Options ATM implied vol term structure and perpetual funding"))
    lines.append(_img(base, "strip-flow", "Section 4: flow"))
    lines.append(_img(base, "activity", "Commit volume profile by hour and weekday"))
    lines.append(_img(base, "snake" if use_snake else "grid", "Contribution grid"))
    lines.append(_a(f"https://github.com/{user}?tab=repositories&sort=updated", _img(base, "recent", "Recently pushed repositories")))
    return '<p align="center">\n' + "\n".join(lines) + "\n</p>\n"
