"""Load profile.yml, fill defaults, and resolve the demo switch."""
import os
from pathlib import Path

import yaml

DEFAULTS = {
    "github_user": "",
    "demo": "auto",
    "theme": "amber",
    "accent": "",
    "timezone": "UTC",
    "identity": {"name": "YOUR NAME", "role": "ENGINEER", "rows": []},
    "links": [{"code": "GH", "auto": "github"}],
    "work": {"status": "SELECTED PROJECTS", "repos": [], "banners": []},
    "markets": {"tape": [], "sessions": [], "options": [], "perps": []},
    "flow": {"bands": [], "snake": True, "recent": 5, "hide": []},
}


def _merge(base, over):
    out = dict(base)
    for k, v in (over or {}).items():
        out[k] = _merge(base[k], v) if isinstance(v, dict) and isinstance(base.get(k), dict) else v
    return out


def load(path="profile.yml"):
    raw = yaml.safe_load(Path(path).read_text()) if Path(path).exists() else {}
    cfg = _merge(DEFAULTS, raw)
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    owner = os.environ.get("GITHUB_REPOSITORY_OWNER", repo.split("/")[0] if repo else "")
    cfg["github_user"] = cfg["github_user"] or owner
    demo = cfg["demo"]
    if demo == "auto":
        # the showcase repo keeps its template name; a real profile repo is named after its owner
        demo = not repo or repo.split("/")[-1] == "profile-terminal"
    cfg["demo"] = bool(demo)
    cfg["repository"] = repo or f"{cfg['github_user'] or 'you'}/{cfg['github_user'] or 'you'}"
    cfg["profile_repo"] = bool(repo) and repo.split("/")[-1].lower() == owner.lower()
    return cfg
