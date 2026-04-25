"""Mark-som-lest: saker du har klikket paa fader til 55% opacity ved neste lasting.

- Lagrer URL-er i localStorage (bydelsnytt:readUrls) som array, capped 1000 items FIFO
- Ved sidelasting: traverser .story, finn .readmore-href, legg til klassen .read
- Click-handler paa .readmore: marker saken som lest, persister
- CSS: .story.read fader, hover restorer opasiteten saa man fortsatt kan lese
"""
from __future__ import annotations
from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parent
BUILD_PY = ROOT / "build.py"

# 1) CSS: legg til .story.read regler. Putter dem rett etter .story.has-thumb-grid-blokken.
OLD_CSS = (
    ".story .story-body { min-width: 0; }\n"
    "@media (max-width: 540px) {\n"
    "  .story.has-thumb { grid-template-columns: 88px 1fr; gap: 10px; }\n"
    "}\n"
)
NEW_CSS = (
    ".story .story-body { min-width: 0; }\n"
    "@media (max-width: 540px) {\n"
    "  .story.has-thumb { grid-template-columns: 88px 1fr; gap: 10px; }\n"
    "}\n"
    "/* Markert som lest: faded for raskere skanning av nye saker */\n"
    ".story.read { opacity: 0.5; }\n"
    ".story.read:hover { opacity: 0.95; }\n"
    ".story.read .new-badge,\n"
    ".story.read .news-badge { opacity: 0.7; }\n"
)

# 2) JS-IIFE: legges helt sist i SCRIPT, inne i raw-string. Vi finner et stabilt sted —
#    rett foer den naa-eksisterende theme-toggle-IIFE.
OLD_JS_ANCHOR = (
    "(function() {\n"
    "  var TKEY = 'bydelsnytt:theme';\n"
)
NEW_JS_ANCHOR = (
    "(function() {\n"
    "  // Markér saker som lest: legger klassen .read paa saker bruker har klikket\n"
    "  // 'Les mer' paa, slik at de fader til 50% opacity neste gang siden lastes.\n"
    "  var KEY = 'bydelsnytt:readUrls';\n"
    "  var MAX = 1000;\n"
    "  var readSet = {};\n"
    "  var readOrder = [];\n"
    "  try {\n"
    "    var raw = window.localStorage.getItem(KEY);\n"
    "    if (raw) {\n"
    "      var arr = JSON.parse(raw);\n"
    "      if (Array.isArray(arr)) {\n"
    "        arr.forEach(function(u) { if (u && !readSet[u]) { readSet[u] = true; readOrder.push(u); } });\n"
    "      }\n"
    "    }\n"
    "  } catch (e) {}\n"
    "\n"
    "  function persist() {\n"
    "    try {\n"
    "      // Trim FIFO til MAX\n"
    "      while (readOrder.length > MAX) {\n"
    "        var dropped = readOrder.shift();\n"
    "        delete readSet[dropped];\n"
    "      }\n"
    "      window.localStorage.setItem(KEY, JSON.stringify(readOrder));\n"
    "    } catch (e) {}\n"
    "  }\n"
    "\n"
    "  function markStoryRead(storyEl, url) {\n"
    "    if (!storyEl || !url) return;\n"
    "    if (!readSet[url]) {\n"
    "      readSet[url] = true;\n"
    "      readOrder.push(url);\n"
    "      persist();\n"
    "    }\n"
    "    storyEl.classList.add('read');\n"
    "  }\n"
    "\n"
    "  // Initial pass: marker alle saker som finnes i lest-settet\n"
    "  document.querySelectorAll('article.story').forEach(function(st) {\n"
    "    var rm = st.querySelector('a.readmore');\n"
    "    if (!rm) return;\n"
    "    var url = rm.getAttribute('href');\n"
    "    if (url && readSet[url]) st.classList.add('read');\n"
    "  });\n"
    "\n"
    "  // Klikk paa 'Les mer' -> marker som lest\n"
    "  document.addEventListener('click', function(e) {\n"
    "    var rm = e.target.closest('a.readmore');\n"
    "    if (!rm) return;\n"
    "    var url = rm.getAttribute('href');\n"
    "    var st = rm.closest('article.story');\n"
    "    markStoryRead(st, url);\n"
    "  });\n"
    "})();\n"
    "\n"
    "(function() {\n"
    "  var TKEY = 'bydelsnytt:theme';\n"
)


def patch() -> None:
    src = BUILD_PY.read_text(encoding="utf-8")
    if "bydelsnytt:readUrls" in src:
        print("[mark-read] allerede patchet, hopper over")
        return
    if OLD_CSS not in src:
        raise SystemExit("[mark-read] fant ikke CSS-anker")
    if src.count(OLD_CSS) != 1:
        raise SystemExit("[mark-read] CSS-anker ikke unikt")
    src = src.replace(OLD_CSS, NEW_CSS, 1)
    print("[mark-read] css OK")

    if OLD_JS_ANCHOR not in src:
        raise SystemExit("[mark-read] fant ikke JS-anker (theme-IIFE)")
    if src.count(OLD_JS_ANCHOR) != 1:
        raise SystemExit("[mark-read] JS-anker ikke unikt")
    src = src.replace(OLD_JS_ANCHOR, NEW_JS_ANCHOR, 1)
    print("[mark-read] js OK")

    ast.parse(src)
    BUILD_PY.write_text(src, encoding="utf-8")
    print("[mark-read] ferdig (" + str(len(src)) + " bytes)")


if __name__ == "__main__":
    patch()
