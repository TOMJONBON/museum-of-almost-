#!/usr/bin/env python3
"""
Applies the mobile + security fixes to your Museum of Almost index.html.

Usage:
    python3 apply_fixes.py index.html
Output:
    index.fixed.html   (your original file is left untouched)

Each step prints OK or FAILED. If a step fails, the rest still run, and the
message tells you what to change by hand.
"""
import re
import sys
from pathlib import Path

if len(sys.argv) != 2:
    sys.exit("Usage: python3 apply_fixes.py index.html")

src = Path(sys.argv[1])
html = src.read_text(encoding="utf-8")
report = []


def step(name, ok):
    report.append((name, ok))
    print(("  OK      " if ok else "  FAILED  ") + name)


# ---------------------------------------------------------------- SECURITY
# 1. remove the service key and curator password
html, n1 = re.subn(r"^[ \t]*const SUPABASE_SERVICE_KEY\s*=.*\n", "", html, flags=re.M)
html, n2 = re.subn(r"^[ \t]*const CURATOR_PASSWORD\s*=.*\n", "", html, flags=re.M)
step("Remove SUPABASE_SERVICE_KEY and CURATOR_PASSWORD", n1 == 1 and n2 == 1)

# 2. remove the whole curator panel function
start = html.find("async function initCurator()")
end = html.find("function placeMarkers()")
if start != -1 and end != -1 and start < end:
    html = html[:start] + html[end:]
    step("Remove initCurator() function", True)
else:
    step("Remove initCurator() function", False)

# 3. remove the call to it
html, n = re.subn(r"^[ \t]*initCurator\(\);[ \t]*\n", "", html, flags=re.M)
step("Remove initCurator() call", n == 1)

# 4. safer escapeHtml (also escapes quotes, so it is safe inside attributes)
new_escape = r"""function escapeHtml(text) {
      if (!text) return '';
      return String(text).replace(/[&<>"']/g, c => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
      }[c]));
    }"""
html, n = re.subn(
    r"function escapeHtml\(text\) \{.*?return div\.innerHTML;\s*\}",
    lambda m: new_escape,
    html,
    count=1,
    flags=re.S,
)
step("Replace escapeHtml with attribute-safe version", n == 1)

# 5. harden createCardFromStory
fn_start = html.find("function createCardFromStory(story) {")
fn_end = html.find("async function loadApprovedStories()")
if fn_start != -1 and fn_end != -1 and fn_start < fn_end:
    body = html[fn_start:fn_end]
    body = body.replace("story.image_url", "imgUrl")
    body = body.replace('alt="${story.title}"', 'alt="${escapeHtml(story.title)}"')
    body = body.replace('data-id="${story.id}"', 'data-id="${escapeHtml(story.id)}"')
    body = body.replace(
        "MoA / ${story.id.slice(0,8)}", "MoA / ${escapeHtml(String(story.id).slice(0,8))}"
    )
    header = "function createCardFromStory(story) {"
    guard = (
        "\n      const imgUrl = (story.image_url && "
        "String(story.image_url).startsWith(SUPABASE_URL + '/storage/')) "
        "? story.image_url : null;"
    )
    body = body.replace(header, header + guard, 1)
    html = html[:fn_start] + body + html[fn_end:]
    step("Escape title/id and validate image_url in story cards", True)
else:
    step("Escape title/id and validate image_url in story cards", False)

# ------------------------------------------------------------------ MOBILE
mobile_css = r"""
    /* ===== Mobile fixes ===== */
    html { -webkit-text-size-adjust: 100%; }
    body { overflow-x: hidden; }
    .hero { min-height: 88vh; min-height: 88svh; }
    .exhibit-grid { grid-template-columns: repeat(auto-fit, minmax(min(100%, 340px), 1fr)); }
    #backRoomGrid { grid-template-columns: repeat(auto-fit, minmax(min(100%, 320px), 1fr)) !important; }
    #backRoom { height: 100dvh; -webkit-overflow-scrolling: touch; overscroll-behavior: contain; }
    .timeline-wrapper { -webkit-overflow-scrolling: touch; }

    @media (hover: none) {
      .card:hover { transform: none; box-shadow: 0 20px 44px -26px rgba(0,0,0,.6); }
      .timeline-item:hover, .toggle-btn:hover { transform: none; }
    }

    .map-caption { display: none; margin: 1rem auto 0; text-align: center;
      font-family: 'Special Elite', monospace; font-size: .9rem; }
    .map-caption button { margin-top: .5rem; min-height: 44px; padding: .5rem 1.2rem;
      background: var(--rust); color: var(--paper); border: 0; border-radius: 4px;
      font-family: inherit; text-transform: uppercase; letter-spacing: .06em; }
    .map-marker-group circle.hit { fill: transparent; stroke: none; filter: none; r: 22px !important; }

    @media (max-width: 768px) {
      .container { padding: 0 1rem; }
      section { padding-top: 3.5rem; }
      footer { padding-bottom: 6rem; }

      .menu-toggle { position: fixed; top: .6rem; left: .6rem; z-index: 30; margin: 0; padding: 0;
        width: 44px; height: 44px; background: rgba(16,21,18,.9);
        border: 1px solid rgba(176,146,92,.3); border-radius: 8px; }
      .wing-nav { position: fixed; top: 0; left: 0; right: 0; z-index: 25;
        padding-top: 64px; max-height: 100svh; overflow-y: auto; }
      .wing-nav a { padding: .9rem .2rem; font-size: .9rem; }

      .card h3 { font-size: 1.4rem; }
      .accession-tag, .portrait-role, .reading-time, .timeline-item .label { font-size: .75rem; }
      .status-tag { font-size: .7rem; }
      .timeline-item .year { font-size: .8rem; }
      .toggle-btn, .share-btn { min-height: 44px; padding: .5rem 1rem; font-size: .75rem; }
      .portrait-frame { flex-wrap: wrap; }
      .accession-tag { margin-left: 0; width: 100%; }

      .map-wrapper { padding: 1rem .5rem; }
      .map-container { aspect-ratio: 2 / 1 !important; }
      .map-marker-group text, .map-marker-group .label-bg { display: none; }
      .map-caption.show { display: block; }

      .mood-toggle { bottom: .6rem; right: .6rem; max-width: calc(100vw - 1.2rem);
        flex-wrap: wrap; justify-content: center; padding: .3rem .5rem; }
      .mood-toggle button { font-size: 1rem; padding: .25rem .4rem; }
      #modeIndicator { display: none; }
      #backToTop { right: auto; left: .8rem; bottom: .8rem; }
    }
"""
idx = html.find("</style>")
if idx != -1:
    html = html[:idx] + mobile_css + "  " + html[idx:]
    step("Add mobile CSS", True)
else:
    step("Add mobile CSS", False)

# duplicate id="timeline"
old = '<div class="timeline" id="timeline">'
step("Rename duplicate id=timeline", old in html)
html = html.replace(old, '<div class="timeline" id="timelineTrack">', 1)

# map caption element
old = '<div class="map-legend">'
step("Add map caption element", old in html)
html = html.replace(old, '<div class="map-caption" id="mapCaption"></div>\n      ' + old, 1)

# bigger tap target for map pins
old = "g.setAttribute('transform', `translate(${x.toFixed(2)},${y.toFixed(2)})`);"
hit_js = old + r"""
        if (window.matchMedia('(max-width: 768px)').matches) {
          const hit = document.createElementNS(SVG_NS, 'circle');
          hit.setAttribute('class', 'hit');
          hit.setAttribute('cx', '0');
          hit.setAttribute('cy', '0');
          hit.setAttribute('r', '22');
          g.appendChild(hit);
        }"""
step("Add bigger map tap targets", old in html)
html = html.replace(old, hit_js, 1)

# tap-to-open behaviour for pins on phones
click_js = r"""g.addEventListener('click', (e) => {
          e.stopPropagation();
          if (window.matchMedia('(max-width: 768px)').matches) {
            document.querySelectorAll('.map-marker-group').forEach(m => m.classList.remove('active'));
            g.classList.add('active');
            const cap = document.getElementById('mapCaption');
            if (!cap) { if (id && window.__scrollToCard) window.__scrollToCard(id); return; }
            cap.textContent = '';
            const label = document.createElement('div');
            label.textContent = name;
            const go = document.createElement('button');
            go.type = 'button';
            go.textContent = 'Read the story';
            go.onclick = () => window.__scrollToCard(id);
            cap.append(label, go);
            cap.classList.add('show');
          } else if (id && window.__scrollToCard) {
            window.__scrollToCard(id);
          }
        });"""
html, n = re.subn(
    r"g\.addEventListener\('click', \(e\) => \{\s*e\.stopPropagation\(\);\s*"
    r"if \(id && window\.__scrollToCard\) window\.__scrollToCard\(id\);\s*\}\);",
    lambda m: click_js,
    html,
    count=1,
)
step("Tap-to-open map pins on phones", n == 1)

# no auto-scroll to Today's Pick on phones
wrapped = r"""if (!window.matchMedia('(max-width: 768px)').matches) {
            setTimeout(() => {
              daily.scrollIntoView({ behavior: 'smooth', block: 'center' });
              daily.classList.add('highlight');
              setTimeout(() => daily.classList.remove('highlight'), 1500);
            }, 800);
          }"""
html, n = re.subn(
    r"setTimeout\(\(\) => \{\s*daily\.scrollIntoView\(\{ behavior: 'smooth', block: 'center' \}\);\s*"
    r"daily\.classList\.add\('highlight'\);\s*"
    r"setTimeout\(\(\) => daily\.classList\.remove\('highlight'\), 1500\);\s*\}, 800\);",
    lambda m: wrapped,
    html,
    count=1,
)
step("Skip auto-scroll to Today's Pick on phones", n == 1)

# ------------------------------------------------------------------ FINISH
out = src.with_name("index.fixed.html")
out.write_text(html, encoding="utf-8")

leaked = [w for w in ("SUPABASE_SERVICE_KEY", "CURATOR_PASSWORD", "museum2026") if w in html]
print()
if leaked:
    print("WARNING: these are still in the file, remove by hand:", ", ".join(leaked))
failed = [n for n, ok in report if not ok]
if failed:
    print(f"{len(failed)} step(s) failed. Everything else was applied.")
else:
    print("All steps applied.")
print(f"Wrote {out}")
print("Reminder: rotate your Supabase keys and run supabase_security.sql.")
