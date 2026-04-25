"""Pakk 'Topp saker i dag' inn i en lukket details/summary-expander.

- Endrer <section class="topp-saker"> til <details class="topp-saker">
- Endrer <h2> til <summary>
- Default lukket (ingen 'open'-attributt)
- Legger CSS for chevron + body-padding (matcher .upcoming-stilen)
"""
from __future__ import annotations
from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parent
BUILD_PY = ROOT / "build.py"

# 1) Render-funksjonen: bytt section/h2 -> details/summary
OLD_RENDER = (
    "    return (\n"
    "        '<section class=\"topp-saker\" aria-label=\"Topp saker i dag\">'\n"
    "        '<h2>Topp saker i dag <small>utvalgt av algoritmen</small></h2>'\n"
    "        '<div class=\"topp-grid\">'\n"
    "        + \"\".join(cards)\n"
    "        + '</div>'\n"
    "        '</section>'\n"
    "    )\n"
)
NEW_RENDER = (
    "    return (\n"
    "        '<details class=\"topp-saker\" id=\"topp-saker\" aria-label=\"Topp saker i dag\">'\n"
    "        '<summary>Topp saker i dag <small>utvalgt av algoritmen</small> '\n"
    "        f'<span class=\"topp-count\">{len(cards)} saker</span>'\n"
    "        '</summary>'\n"
    "        '<div class=\"topp-body\"><div class=\"topp-grid\">'\n"
    "        + \"\".join(cards)\n"
    "        + '</div></div>'\n"
    "        '</details>'\n"
    "    )\n"
)

# 2) CSS: re-bruke .upcoming-mønsteret. Erstatt h2-blokken og legg til summary/body-styling
OLD_CSS_BLOCK = (
    ".topp-saker {\n"
    "  margin: 0 0 26px 0;\n"
    "  padding: 16px 18px 14px;\n"
    "  background: linear-gradient(180deg, #fffbee 0%, #fff 100%);\n"
    "  border: 1px solid #e8d68a;\n"
    "  border-radius: 12px;\n"
    "}\n"
)
NEW_CSS_BLOCK = (
    ".topp-saker {\n"
    "  margin: 0 0 26px 0;\n"
    "  padding: 0;\n"
    "  background: linear-gradient(180deg, #fffbee 0%, #fff 100%);\n"
    "  border: 1px solid #e8d68a;\n"
    "  border-radius: 12px;\n"
    "  overflow: hidden;\n"
    "}\n"
    ".topp-saker > summary {\n"
    "  padding: 14px 18px;\n"
    "  cursor: pointer;\n"
    "  list-style: none;\n"
    "  font-size: 15px; font-weight: 700;\n"
    "  color: #7a5e00;\n"
    "  text-transform: uppercase; letter-spacing: 0.6px;\n"
    "  display: flex; align-items: baseline; gap: 10px;\n"
    "}\n"
    ".topp-saker > summary::-webkit-details-marker { display: none; }\n"
    ".topp-saker > summary::before {\n"
    '  content: "\\25B6"; font-size: 10px; color: #7a5e00;\n'
    "  transform: translateY(-1px); transition: transform 0.15s;\n"
    "}\n"
    ".topp-saker[open] > summary::before { transform: rotate(90deg) translateX(-1px); }\n"
    ".topp-saker > summary small {\n"
    "  font-size: 11px; font-weight: 400; color: #a08947;\n"
    "  text-transform: none; letter-spacing: 0;\n"
    "}\n"
    ".topp-saker .topp-count {\n"
    "  font-size: 11px; font-weight: 400; color: #a08947;\n"
    "  text-transform: none; letter-spacing: 0; margin-left: auto;\n"
    "}\n"
    ".topp-saker .topp-body { padding: 4px 18px 16px 18px; }\n"
)

REPLACEMENTS = [
    ("render", OLD_RENDER, NEW_RENDER),
    ("css", OLD_CSS_BLOCK, NEW_CSS_BLOCK),
]


def patch() -> None:
    src = BUILD_PY.read_text(encoding="utf-8")
    if "<details class=\\\"topp-saker\\\"" in src or 'topp-saker[open]' in src:
        print("[topp-expander] allerede patchet, hopper over")
        return
    for label, old, new in REPLACEMENTS:
        if old not in src:
            raise SystemExit("[topp-expander] fant ikke anker for: " + label)
        if src.count(old) != 1:
            raise SystemExit("[topp-expander] ankeret er ikke unikt: " + label)
        src = src.replace(old, new, 1)
        print("[topp-expander] " + label + " OK")
    ast.parse(src)
    BUILD_PY.write_text(src, encoding="utf-8")
    print("[topp-expander] ferdig (" + str(len(src)) + " bytes)")


if __name__ == "__main__":
    patch()
