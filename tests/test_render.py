"""Offline end-to-end render: every panel, every theme, no network."""
import xml.etree.ElementTree as ET

import pytest

from terminal import config, readme, render, theme


@pytest.fixture
def cfg(monkeypatch):
    monkeypatch.setenv("GITHUB_REPOSITORY", "octo/profile-terminal")
    monkeypatch.setenv("GITHUB_REPOSITORY_OWNER", "octo")
    return config.load("profile.yml")


def test_demo_resolves_for_showcase_repo(cfg):
    assert cfg["demo"] is True
    assert cfg["github_user"] == "octo"


def test_profile_repo_turns_demo_off(monkeypatch):
    monkeypatch.setenv("GITHUB_REPOSITORY", "octo/octo")
    monkeypatch.setenv("GITHUB_REPOSITORY_OWNER", "octo")
    c = config.load("profile.yml")
    assert c["demo"] is False and c["profile_repo"] is True


@pytest.mark.parametrize("preset", list(theme.PRESETS))
def test_offline_render_is_well_formed(cfg, tmp_path, preset):
    cfg["theme"] = preset
    written = render.render(cfg, tmp_path, offline=True)
    for name in ("hero", "risk", "regime", "derivatives", "activity", "grid", "recent", "strip-lab", "key-0", "work-0"):
        assert name in written
    for f in tmp_path.glob("*.svg"):
        ET.parse(f)
        assert "<script" not in f.read_text()
    assert (tmp_path / "state.json").exists()


def test_readme_references_every_tile(cfg):
    text = readme.build(cfg, use_snake=False)
    for name in ("hero", "key-0", "work-3", "regime", "risk", "derivatives", "activity", "grid", "recent"):
        assert f"/output/{name}.svg" in text
