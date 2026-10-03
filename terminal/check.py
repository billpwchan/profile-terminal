"""Fail fast when a rendered panel is not well-formed XML: on GitHub that shows up as a broken image."""
import xml.etree.ElementTree as ET
from pathlib import Path


def check(out):
    out = Path(out)
    files = sorted(out.glob("*.svg"))
    bad = []
    for f in files:
        try:
            ET.parse(f)
        except ET.ParseError as e:
            bad.append(f"{f.name}: {e}")
    if bad:
        raise SystemExit("malformed SVG:\n" + "\n".join(bad))
    print(f"{len(files)} SVGs well-formed")
    return len(files)
