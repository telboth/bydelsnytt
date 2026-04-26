"""Generer health.html, api/stories.json, manifest.json og sw.js.

Kjor etter build.py. Skriver til samme outputs-mappe.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HEALTH_JSON = ROOT / "source_health.json"
STORIES_JSON = ROOT / "stories.json"
HEALTH_HTML = ROOT / "health.html"
API_DIR = ROOT / "api"
MANIFEST = ROOT / "manifest.json"
SW = ROOT / "sw.js"


def gen_health_html() -> None:
    health = json.load(open(HEALTH_JSON, encoding="utf-8"))
    sources = health.get("sources", {})
    updated = health.get("updatedAt", "")

    # Build rows sortert paa siste antall (synkende). Stale = ingen success siste 48t.
    now = datetime.now(timezone.utc)
    rows = []
    for sid, s in sources.items():
        history = s.get("history", [])[-30:]
        last_count = s.get("last_count", 0)
        last_success = s.get("last_success_iso") or ""
        last_new = s.get("last_new_story_iso") or ""
        last_error = s.get("last_error")
        consec_empty = s.get("consecutive_empty_runs", 0)
        # Status
        status = "ok"
        try:
            ls = datetime.fromisoformat(last_success) if last_success else None
            if not ls or (now - ls).total_seconds() > 48 * 3600:
                status = "stale"
        except Exception:
            status = "stale"
        if last_error:
            status = "error"
        if consec_empty >= 3:
            status = "empty"
        # Stille-doed: leverer noe, men ingen nye saker paa 14 dager
        if status == "ok" and last_new:
            try:
                ln = datetime.fromisoformat(last_new)
                if (now - ln).total_seconds() > 14 * 86400:
                    status = "frozen"
            except Exception:
                pass
        rows.append({
            "id": sid, "name": s.get("name", sid),
            "last_count": last_count,
            "last_success": last_success,
            "last_new": last_new,
            "last_error": last_error,
            "history": history,
            "status": status,
        })
    rows.sort(key=lambda r: (-(r["last_count"] or 0), r["id"]))

    # Build SVG sparklines
    def sparkline(history: list[dict]) -> str:
        if not history:
            return ""
        counts = [h.get("count", 0) or 0 for h in history]
        cmax = max(counts) or 1
        w, h = 120, 22
        step = w / max(1, len(counts) - 1)
        pts = []
        for i, c in enumerate(counts):
            x = i * step
            y = h - (c / cmax) * (h - 4) - 2
            pts.append(f"{x:.1f},{y:.1f}")
        path = " ".join(pts)
        return (f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
                f'xmlns="http://www.w3.org/2000/svg">'
                f'<polyline fill="none" stroke="#1862a8" stroke-width="1.5" '
                f'points="{path}"/></svg>')

    body_rows = []
    for r in rows:
        status_color = {
            "ok": "#2a8b4a", "stale": "#d4a017",
            "empty": "#dc6a3e", "error": "#b32a2a",
            "frozen": "#7a4ec3",
        }.get(r["status"], "#888")
        last_succ_short = r["last_success"][:16].replace("T", " ") if r["last_success"] else "—"
        err_str = (r["last_error"] or "")[:80]
        body_rows.append(
            f'<tr>'
            f'<td><span class="dot" style="background:{status_color}"></span> '
            f'<strong>{r["name"]}</strong></td>'
            f'<td class="num">{r["last_count"]}</td>'
            f'<td class="num">{last_succ_short}</td>'
            f'<td>{sparkline(r["history"])}</td>'
            f'<td class="err">{err_str}</td>'
            f'</tr>'
        )

    html = f'''<!DOCTYPE html>
<html lang="no"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Bydelsnytt — kildehelse</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif; color:#1a1a1a; background:#fafafa; padding:24px; max-width:980px; margin:0 auto; }}
  h1 {{ margin: 0 0 4px; font-size: 22px; }}
  .meta {{ color: #777; font-size: 13px; margin-bottom: 18px; }}
  table {{ border-collapse: collapse; width: 100%; background:#fff; border-radius:8px; overflow:hidden; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }}
  th, td {{ padding: 8px 12px; text-align: left; border-bottom: 1px solid #f0f0f0; font-size: 13px; vertical-align: middle; }}
  th {{ background:#f7f7f7; font-weight: 600; font-size: 12px; text-transform: uppercase; letter-spacing: 0.04em; color:#555; }}
  td.num {{ font-variant-numeric: tabular-nums; }}
  .dot {{ display:inline-block; width:10px; height:10px; border-radius:50%; margin-right:6px; vertical-align: middle; }}
  .err {{ color:#b32a2a; font-size: 11px; }}
  .legend {{ display:flex; gap:14px; margin: 8px 0 14px; font-size:12px; color:#555; }}
  .legend .dot {{ width: 8px; height: 8px; }}
  a {{ color:#1862a8; }}
  .back {{ display:inline-block; margin-bottom: 12px; }}
</style>
</head><body>
  <a class="back" href="./">&larr; Tilbake til Bydelsnytt</a>
  <h1>Kildehelse</h1>
  <div class="meta">Oppdatert {updated[:16].replace("T", " ")} &middot; {len(rows)} kilder</div>
  <div class="legend">
    <span><span class="dot" style="background:#2a8b4a"></span>OK (kjorte siste 48t)</span>
    <span><span class="dot" style="background:#d4a017"></span>Stale (ingen kjoring 48t+)</span>
    <span><span class="dot" style="background:#dc6a3e"></span>Empty (3+ tomme kjoringer)</span>
    <span><span class="dot" style="background:#b32a2a"></span>Feilet</span>
    <span><span class="dot" style="background:#7a4ec3"></span>Fryst (svar OK, men ingen nye saker 14 dager+)</span>
  </div>
  <table>
    <thead><tr>
      <th>Kilde</th>
      <th class="num">Sist antall</th>
      <th class="num">Sist OK</th>
      <th>Trend (30 kjoringer)</th>
      <th>Sist feil</th>
    </tr></thead>
    <tbody>{"".join(body_rows)}</tbody>
  </table>
  <p style="margin-top: 16px; font-size: 12px; color: #777;">
    Rapport bygges sammen med pipeline. Datafil: <a href="source_health.json">source_health.json</a>
  </p>
</body></html>'''
    HEALTH_HTML.write_text(html, encoding="utf-8")
    print(f"[health] {HEALTH_HTML.name}: {len(html)} bytes ({len(rows)} kilder)")


def gen_api() -> None:
    API_DIR.mkdir(exist_ok=True)
    stories = json.load(open(STORIES_JSON, encoding="utf-8"))
    # Pakk inn i metadata-konvolutt
    items = stories.get("stories", []) if isinstance(stories, dict) else stories
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(items),
        "stories": items,
    }
    out = API_DIR / "stories.json"
    out.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    print(f"[api] {out.name}: {len(items)} stories, {out.stat().st_size} bytes")

    # Lett-versjon: kun id, title, url, bydel, category, date_iso
    light = [
        {k: s.get(k) for k in ("id", "title", "url", "bydel", "category", "date_iso", "source")}
        for s in items
    ]
    payload_light = {
        "generated_at": payload["generated_at"],
        "count": len(light),
        "stories": light,
    }
    out_light = API_DIR / "stories-light.json"
    out_light.write_text(json.dumps(payload_light, ensure_ascii=False), encoding="utf-8")
    print(f"[api] {out_light.name}: {len(light)} stories, {out_light.stat().st_size} bytes")


def gen_pwa() -> None:
    manifest = {
        "name": "Bydelsnytt Oslo",
        "short_name": "Bydelsnytt",
        "description": "Lokalnytt og arrangementer fra Oslos 15 bydeler",
        "start_url": "./",
        "display": "standalone",
        "background_color": "#fafafa",
        "theme_color": "#1862a8",
        "lang": "no",
        "icons": [
            {
                "src": "icon.svg",
                "sizes": "any",
                "type": "image/svg+xml",
                "purpose": "any",
            }
        ],
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[pwa] manifest.json: {MANIFEST.stat().st_size} bytes")

    icon = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 192 192">
<rect width="192" height="192" rx="32" fill="#1862a8"/>
<text x="50%" y="50%" font-family="-apple-system,sans-serif" font-size="56" font-weight="700"
      fill="#fff" text-anchor="middle" dominant-baseline="central">BN</text>
<circle cx="48" cy="48" r="8" fill="#ffd966"/>
<circle cx="144" cy="48" r="6" fill="#88c4ff"/>
<circle cx="48" cy="144" r="6" fill="#88c4ff"/>
<circle cx="144" cy="144" r="8" fill="#ffd966"/>
</svg>'''
    (ROOT / "icon.svg").write_text(icon, encoding="utf-8")

    sw = '''/* Bydelsnytt service worker — minimal offline-cache.
   Cacher index, manifest, ikon og siste API-snapshot.
*/
const CACHE = 'bydelsnytt-v1';
const ASSETS = [
  './',
  'index.html',
  'manifest.json',
  'icon.svg',
  'feed.xml',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(ASSETS)).catch(() => {})
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(
      keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))
    ))
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;
  // Network-first med cache-fallback for navigasjon
  if (req.mode === 'navigate') {
    event.respondWith(
      fetch(req).then((res) => {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(req, copy));
        return res;
      }).catch(() => caches.match(req).then((m) => m || caches.match('./')))
    );
    return;
  }
  // Stale-while-revalidate for andre GET
  event.respondWith(
    caches.match(req).then((cached) => {
      const fetchP = fetch(req).then((res) => {
        if (res && res.status === 200 && res.type === 'basic') {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(req, copy));
        }
        return res;
      }).catch(() => cached);
      return cached || fetchP;
    })
  );
});
'''
    SW.write_text(sw, encoding="utf-8")
    print(f"[pwa] sw.js: {SW.stat().st_size} bytes")


if __name__ == "__main__":
    gen_health_html()
    gen_api()
    gen_pwa()
