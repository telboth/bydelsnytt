"""Legg til 2-kolonners desktop-visning som user-preferanse.

- Ny seksjon 'Visning' i Preferanser-modal med checkbox 'Vis saker i to kolonner (kun desktop)'
- Lagrer paa noekkel bydelsnytt:twoCols ('1' / '0')
- Toggler body.two-cols ved init og ved checkbox-change
- CSS: ved min-width 768px gir body.two-cols et 2-kolonners grid for sakene
  innenfor hver bydel-section (h2 spenner over begge kolonnene)
- Mobil holder seg som er (en kolonne)
"""
from __future__ import annotations
from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parent
BUILD_PY = ROOT / "build.py"

# 1) CSS: legg til to-kolonners-regel rett etter den eksisterende mobile thumb-regelen
OLD_CSS = (
    "@media (max-width: 540px) {\n"
    "  .story.has-thumb { grid-template-columns: 88px 1fr; gap: 10px; }\n"
    "}\n"
)
NEW_CSS = (
    "@media (max-width: 540px) {\n"
    "  .story.has-thumb { grid-template-columns: 88px 1fr; gap: 10px; }\n"
    "}\n"
    "/* To-kolonners desktop-visning naar bruker har valgt det i Preferanser */\n"
    "@media (min-width: 768px) {\n"
    "  body.two-cols .bydel {\n"
    "    display: grid;\n"
    "    grid-template-columns: 1fr 1fr;\n"
    "    column-gap: 14px;\n"
    "  }\n"
    "  body.two-cols .bydel h2 { grid-column: 1 / -1; }\n"
    "}\n"
)

# 2) Modal HTML: legg 'Visning'-seksjon rett foer 'Fjern alle preferanser'-knappen
OLD_MODAL = (
    "    + '  <div class=\"prefs-section\">'\n"
    "    + '    <h4>Vis kategorier</h4>'\n"
    "    + '    <p class=\"prefs-section-hint\">Hak av kategoriene du vil se. Alle er p&aring; som standard.</p>'\n"
    "    + '    <div class=\"prefs-checkbox-grid\" id=\"prefs-cat-grid\"></div>'\n"
    "    + '  </div>'\n"
    "    + '  <button class=\"clear-all\" id=\"prefs-clear-all\">Fjern alle preferanser</button>'\n"
)
NEW_MODAL = (
    "    + '  <div class=\"prefs-section\">'\n"
    "    + '    <h4>Vis kategorier</h4>'\n"
    "    + '    <p class=\"prefs-section-hint\">Hak av kategoriene du vil se. Alle er p&aring; som standard.</p>'\n"
    "    + '    <div class=\"prefs-checkbox-grid\" id=\"prefs-cat-grid\"></div>'\n"
    "    + '  </div>'\n"
    "    + '  <div class=\"prefs-section\">'\n"
    "    + '    <h4>Visning</h4>'\n"
    "    + '    <label><input type=\"checkbox\" id=\"prefs-two-cols\"> Vis saker i to kolonner (kun desktop)</label>'\n"
    "    + '  </div>'\n"
    "    + '  <button class=\"clear-all\" id=\"prefs-clear-all\">Fjern alle preferanser</button>'\n"
)

# 3) JS init: applyTwoCols ved sidelasting, og wire-up av checkbox
OLD_JS = (
    "  // Initial filtrering ved sidelasting\n"
    "  applyHidden();\n"
    "  updatePrefsButton();\n"
    "})();\n"
)
NEW_JS = (
    "  // Two-cols (desktop) preferanse: lagrer som '1' / '0' i localStorage\n"
    "  var TC_KEY = 'bydelsnytt:twoCols';\n"
    "  function readTwoCols() {\n"
    "    try { return window.localStorage.getItem(TC_KEY) === '1'; } catch (e) { return false; }\n"
    "  }\n"
    "  function applyTwoCols(on) {\n"
    "    if (on) document.body.classList.add('two-cols');\n"
    "    else document.body.classList.remove('two-cols');\n"
    "  }\n"
    "  function syncTwoColsCheckbox() {\n"
    "    var cb = modal.querySelector('#prefs-two-cols');\n"
    "    if (cb) cb.checked = readTwoCols();\n"
    "  }\n"
    "  modal.addEventListener('change', function(e) {\n"
    "    var cb = e.target.closest('#prefs-two-cols');\n"
    "    if (!cb) return;\n"
    "    try { window.localStorage.setItem(TC_KEY, cb.checked ? '1' : '0'); } catch (e2) {}\n"
    "    applyTwoCols(cb.checked);\n"
    "  });\n"
    "  // Sett checkbox-state hver gang modalen aapnes\n"
    "  var origOpenBtn = document.getElementById('open-prefs-btn');\n"
    "  if (origOpenBtn) {\n"
    "    origOpenBtn.addEventListener('click', function() { setTimeout(syncTwoColsCheckbox, 0); });\n"
    "  }\n"
    "\n"
    "  // Initial filtrering ved sidelasting\n"
    "  applyHidden();\n"
    "  applyTwoCols(readTwoCols());\n"
    "  updatePrefsButton();\n"
    "})();\n"
)

# 4) Clear-all skal ogsaa nullstille two-cols
OLD_CLEAR = (
    "  clearAllBtn.addEventListener('click', function() {\n"
    "    if (!window.confirm('Fjern alle skjulte kilder, bydeler og kategorier?')) return;\n"
    "    hiddenSources = {};\n"
    "    hiddenBydeler = {};\n"
    "    hiddenCats = {};\n"
    "    saveMap(HS_KEY, hiddenSources);\n"
    "    saveSet(HB_KEY, hiddenBydeler);\n"
    "    saveSet(HC_KEY, hiddenCats);\n"
    "    renderModalList();\n"
    "    renderBydelGrid();\n"
    "    renderCatGrid();\n"
    "    applyHidden();\n"
    "  });\n"
)
NEW_CLEAR = (
    "  clearAllBtn.addEventListener('click', function() {\n"
    "    if (!window.confirm('Fjern alle preferanser (skjulte kilder/bydeler/kategorier + 2-kolonner)?')) return;\n"
    "    hiddenSources = {};\n"
    "    hiddenBydeler = {};\n"
    "    hiddenCats = {};\n"
    "    saveMap(HS_KEY, hiddenSources);\n"
    "    saveSet(HB_KEY, hiddenBydeler);\n"
    "    saveSet(HC_KEY, hiddenCats);\n"
    "    try { window.localStorage.removeItem(TC_KEY); } catch (e) {}\n"
    "    applyTwoCols(false);\n"
    "    syncTwoColsCheckbox();\n"
    "    renderModalList();\n"
    "    renderBydelGrid();\n"
    "    renderCatGrid();\n"
    "    applyHidden();\n"
    "  });\n"
)

REPLACEMENTS = [
    ("css", OLD_CSS, NEW_CSS),
    ("modal-html", OLD_MODAL, NEW_MODAL),
    ("clear-all", OLD_CLEAR, NEW_CLEAR),
    ("js-init", OLD_JS, NEW_JS),
]


def patch() -> None:
    src = BUILD_PY.read_text(encoding="utf-8")
    if "bydelsnytt:twoCols" in src:
        print("[two-cols] allerede patchet, hopper over")
        return
    for label, old, new in REPLACEMENTS:
        if old not in src:
            raise SystemExit("[two-cols] fant ikke anker for: " + label)
        if src.count(old) != 1:
            raise SystemExit("[two-cols] ankeret er ikke unikt: " + label)
        src = src.replace(old, new, 1)
        print("[two-cols] " + label + " OK")
    ast.parse(src)
    BUILD_PY.write_text(src, encoding="utf-8")
    print("[two-cols] ferdig (" + str(len(src)) + " bytes)")


if __name__ == "__main__":
    patch()
