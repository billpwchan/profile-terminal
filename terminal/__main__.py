"""profile-terminal command line.

  python -m terminal render  [--out dist] [--offline]   render every panel
  python -m terminal readme  [--write]                 print or write README.md from profile.yml
  python -m terminal snake   [--out dist]               frame dist/snake-raw.svg as a terminal panel
  python -m terminal check   [--out dist]               validate every rendered SVG
  python -m terminal preview [--out dist]               write dist/preview.html to see the page locally
  python -m terminal flag    <name>                     print a value for the workflow (snake, snake-outputs, profile-repo)
"""
import argparse
import html
from pathlib import Path

from . import cards, check, config, readme, render


def main():
    p = argparse.ArgumentParser(prog="python -m terminal", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("command", choices=["render", "readme", "snake", "check", "preview", "flag"])
    p.add_argument("name", nargs="?")
    p.add_argument("--out", default="dist")
    p.add_argument("--config", default="profile.yml")
    p.add_argument("--offline", action="store_true", help="sample data for every feed; no network")
    p.add_argument("--write", action="store_true")
    a = p.parse_args()
    cfg = config.load(a.config)
    out = Path(a.out)
    use_snake = bool(cfg["flow"]["snake"]) and not cfg["demo"]

    if a.command == "render":
        render.render(cfg, out, offline=a.offline)
    elif a.command == "check":
        check.check(out)
    elif a.command == "flag":
        from . import theme
        theme.apply_theme(cfg["theme"], cfg.get("accent") or None)
        dots = ",".join(["#161b22", theme.T["amber_dim"], theme.T["amber"] + "66", theme.T["amber"] + "aa", theme.T["amber"]])
        flags = {"snake": str(use_snake).lower(),
                 "snake-outputs": f"dist/snake-raw.svg?palette=github-dark&color_snake={theme.T['amber']}&color_dots={dots}",
                 "profile-repo": str(cfg["profile_repo"]).lower()}
        print(flags.get(a.name, ""))
    elif a.command == "snake":
        raw = out / "snake-raw.svg"
        if raw.exists():
            from . import theme
            theme.apply_theme(cfg["theme"], cfg.get("accent") or None)
            (out / "snake.svg").write_text(cards.snake_panel(raw.read_text()))
            raw.unlink()
            print("wrote snake.svg")
        else:
            print("no snake render this run; keeping the previous snake.svg")
    elif a.command == "readme":
        text = readme.build(cfg, use_snake)
        if a.write:
            Path("README.md").write_text(text)
            print("wrote README.md")
        else:
            print(text)
    elif a.command == "preview":
        body = readme.build(cfg, use_snake).replace(f"https://raw.githubusercontent.com/{cfg['repository']}/output/", "")
        (out / "preview.html").write_text(
            '<!doctype html><meta charset="utf-8"><title>profile-terminal preview</title>'
            '<style>body{background:#0d1117;margin:0;padding:32px}main{max-width:830px;margin:auto;line-height:0}'
            'p{margin:0}img{max-width:100%;vertical-align:top}</style><main>' + body + "</main>")
        print(f"open {html.escape(str(out / 'preview.html'))}")


if __name__ == "__main__":
    main()
