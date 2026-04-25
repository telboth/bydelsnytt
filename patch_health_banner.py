"""Diskret helsebanner: en-linjet melding med lenke til health.html.

Erstatter den eksisterende boksen-med-liste med en kompakt en-linje-melding:
    Kildehelse: 2 kilder leverer ikke akkurat naa. Mer info →
- Lenker til health.html
- Mindre visuell vekt (font 12px, mer subtil farge)
- Senker terskelen til 3+ dager uten saker (var 7) saa det fanges tidligere
"""
from __future__ import annotations
from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parent
BUILD_PY = ROOT / "build.py"

# 1) CSS: redusere visuell vekt og legge til a-styling
OLD_CSS = (
    ".health-banner {\n"
    "  background: #fff4e5;\n"
    "  border: 1px solid #f5c27a;\n"
    "  color: #663c00;\n"
    "  padding: 10px 14px;\n"
    "  border-radius: 8px;\n"
    "  margin-bottom: 16px;\n"
    "  font-size: 13px;\n"
    "}\n"
    ".health-banner strong { color: #8a4a00; }\n"
    ".health-banner ul { margin: 6px 0 0 0; padding-left: 20px; }\n"
    ".health-banner li { margin: 2px 0; }\n"
)
NEW_CSS = (
    ".health-banner {\n"
    "  background: #fff8ec;\n"
    "  border: 1px solid #f0d9a8;\n"
    "  color: #7a5a1a;\n"
    "  padding: 6px 12px;\n"
    "  border-radius: 6px;\n"
    "  margin-bottom: 14px;\n"
    "  font-size: 12px;\n"
    "  display: flex; align-items: center; gap: 8px;\n"
    "  flex-wrap: wrap;\n"
    "}\n"
    ".health-banner strong { color: #8a4a00; font-weight: 600; }\n"
    ".health-banner a {\n"
    "  color: #1862a8; text-decoration: none; font-weight: 500;\n"
    "  margin-left: auto;\n"
    "}\n"
    ".health-banner a:hover { text-decoration: underline; }\n"
)

# 2) Render-funksjonen: bytte til en-linjet format med lenke
OLD_RENDER = (
    "    stale = _health.stale_sources(data)\n"
    "    if not stale:\n"
    "        return \"\"\n"
    "    lis = []\n"
    "    for s in stale:\n"
    "        last = s.get(\"last_success_iso\") or \"aldri\"\n"
    "        if last != \"aldri\":\n"
    "            last = last[:10]\n"
    "        lis.append(\n"
    "            f\"<li><strong>{esc(s['name'])}</strong> \"\n"
    "            f\"(siste suksess: {esc(last)})</li>\"\n"
    "        )\n"
    "    return (\n"
    "        '<div class=\"health-banner\">'\n"
    "        '<strong>Kildehelse:</strong> '\n"
    "        f'{len(stale)} kilde{\"\" if len(stale)==1 else \"r\"} har ikke levert saker '\n"
    "        'paa en uke. Sjekk om feedene fremdeles fungerer:'\n"
    "        f'<ul>{\"\".join(lis)}</ul>'\n"
    "        '</div>'\n"
    "    )\n"
)
NEW_RENDER = (
    "    # Senk terskelen til 3 dager for at problemer skal fanges tidligere.\n"
    "    stale = _health.stale_sources(data, stale_days=3)\n"
    "    if not stale:\n"
    "        return \"\"\n"
    "    n = len(stale)\n"
    "    names = \", \".join(esc(s['name']) for s in stale[:3])\n"
    "    if n > 3:\n"
    "        names += f\" + {n - 3} til\"\n"
    "    return (\n"
    "        '<div class=\"health-banner\" role=\"status\">'\n"
    "        '<strong>Kildehelse:</strong> '\n"
    "        f'{n} kilde{\"\" if n == 1 else \"r\"} leverer ikke akkurat n&aring; '\n"
    "        f'<span style=\"color:#a07a3a;\">({names})</span>'\n"
    "        '<a href=\"health.html\">Mer info &rarr;</a>'\n"
    "        '</div>'\n"
    "    )\n"
)


def patch() -> None:
    src = BUILD_PY.read_text(encoding="utf-8")
    if "leverer ikke akkurat" in src:
        print("[health-banner] allerede patchet, hopper over")
        return
    for label, old, new in [("css", OLD_CSS, NEW_CSS), ("render", OLD_RENDER, NEW_RENDER)]:
        if old not in src:
            raise SystemExit("[health-banner] fant ikke anker for: " + label)
        if src.count(old) != 1:
            raise SystemExit("[health-banner] ankeret er ikke unikt: " + label)
        src = src.replace(old, new, 1)
        print("[health-banner] " + label + " OK")
    ast.parse(src)
    BUILD_PY.write_text(src, encoding="utf-8")
    print("[health-banner] ferdig (" + str(len(src)) + " bytes)")


if __name__ == "__main__":
    patch()
