#!/usr/bin/env python3
"""Build the hosted Bay Area rental finder page from raw_listings.json.

The DAILY SCHEDULED TASK (running in the Claude app, where Zillow & SUpost
render) fetches listings from Craigslist + Zillow + SUpost, writes the rows to
raw_listings.json, then runs this script. This script is pure: it ranks the rows
by city priority (Menlo Park > Palo Alto > other spots near Stanford), then by
distance to 469 Sherwood Way, then price, and writes index.html + listings.json
(served by GitHub Pages). No network, no scraping here.

raw_listings.json schema:
{
  "updated": "Sunday, June 14, 2026 at 7:00 AM",
  "rows": [ [title, price:int, city, coord_key, url, source], ... ]
}
If raw_listings.json is missing/empty, the built-in SEED snapshot is used.
"""
import json, math, datetime, html, pathlib, sys

TARGET = (37.4471, -122.1881)          # 469 Sherwood Way, Menlo Park CA 94025
HERE = pathlib.Path(__file__).resolve().parent

COORDS = {
    "menlo_downtown": (37.4520, -122.1820), "menlo_west": (37.4471, -122.1881),
    "menlo_coleman": (37.4565, -122.1790),  "menlo_east": (37.4760, -122.1580),
    "atherton": (37.4585, -122.1970),       "pa_downtown": (37.4440, -122.1630),
    "pa_east": (37.4560, -122.1180),        "pa_general": (37.4419, -122.1430),
    "stanford": (37.4275, -122.1700),       "rwc_downtown": (37.4860, -122.2320),
    "rwc_general": (37.4848, -122.2280),    "mtv_downtown": (37.3940, -122.0800),
    "mtv_general": (37.4000, -122.0790),    "epa": (37.4688, -122.1411),
}
CITY_DEFAULT = {"Menlo Park": "menlo_west", "Palo Alto": "pa_general", "Stanford": "stanford",
                "Atherton": "atherton", "Redwood City": "rwc_general",
                "Mountain View": "mtv_general", "East Palo Alto": "epa"}
PRIORITY = {"Menlo Park": 0, "Palo Alto": 1}
TIER_LABEL = {0: "Priority 1 · Menlo Park", 1: "Priority 2 · Palo Alto",
              2: "Other locations near Stanford"}

def haversine_mi(a, b):
    R = 3958.8
    la1, lo1, la2, lo2 = map(math.radians, [a[0], a[1], b[0], b[1]])
    h = math.sin((la2-la1)/2)**2 + math.cos(la1)*math.cos(la2)*math.sin((lo2-lo1)/2)**2
    return R * 2 * math.asin(math.sqrt(h))

def load_rows():
    f = HERE / "raw_listings.json"
    if f.exists():
        try:
            d = json.loads(f.read_text())
            rows, updated = d.get("rows", []), d.get("updated")
            if rows:
                return [tuple(r) for r in rows], updated
        except Exception as e:
            print("raw_listings.json unreadable, using seed:", e, file=sys.stderr)
    return SEED, None

def rank(rows):
    out, seen = [], set()
    for r in rows:
        title, price, city, key, url, source = (list(r) + [None]*6)[:6]
        price = int(price)
        if url in seen:
            continue
        seen.add(url)
        if key not in COORDS:
            key = CITY_DEFAULT.get(city, "menlo_west")
        dist = round(haversine_mi(TARGET, COORDS[key]), 1)
        tier = PRIORITY.get(city, 2)
        out.append({"title": title, "price": price, "city": city, "dist": dist,
                    "tier": tier, "tierLabel": TIER_LABEL[tier], "url": url,
                    "source": source or "Craigslist"})
    out.sort(key=lambda x: (x["tier"], x["dist"], x["price"]))
    for i, l in enumerate(out, 1):
        l["rank"] = i
    return out

EXTERNAL = [
    ("Zillow – Menlo Park · 1BR", "https://www.zillow.com/menlo-park-ca/rentals/1-bedrooms/"),
    ("Zillow – Palo Alto · 1BR", "https://www.zillow.com/palo-alto-ca/rentals/1-bedrooms/"),
    ("SUpost – apts/housing (Stanford login)", "https://supost.com/search/cat/3/sub/60"),
    ("Apartments.com – Menlo Park · 1BR ≤ $3,500", "https://www.apartments.com/menlo-park-ca/1-bedrooms-under-3500/"),
    ("Stanford Community Housing (R&DE)", "https://rde.stanford.edu/studenthousing/community-housing"),
    ("Craigslist – full Peninsula 1BR search", "https://sfbay.craigslist.org/search/pen/apa?max_price=3500&min_price=1900&min_bedrooms=1&max_bedrooms=1&min_bathrooms=1&max_bathrooms=1"),
]

# Minimal fallback so the page is never empty.
SEED = [
    ("Charming 1 bed / 1 bath in lovely Menlo Park", 2525, "Menlo Park", "menlo_west", "https://sfbay.craigslist.org/pen/apa/d/menlo-park-charming-bed-bath-in-lovely/7940598058.html", "Craigslist"),
    ("541 Pierce Rd Apt 3, Menlo Park (1bd/1ba)", 2000, "Menlo Park", "menlo_east", "https://www.zillow.com/homedetails/541-Pierce-Rd-APT-3-Menlo-Park-CA-94025/2064137302_zpid/", "Zillow"),
    ("Palo Alto Furnished 1B1B – Entire Unit", 2495, "Palo Alto", "pa_general", "https://supost.com/post/index/130032377", "SUpost"),
]

def build():
    rows, updated = load_rows()
    listings = rank(rows)
    if not updated:
        updated = datetime.datetime.now().strftime("%A, %B %d, %Y at %I:%M %p").replace(" 0", " ")
    counts = {}
    for l in listings:
        counts[l["source"]] = counts.get(l["source"], 0) + 1
    (HERE / "listings.json").write_text(json.dumps({"updated": updated, "listings": listings}, indent=2))
    ext = "".join(f'<a class="ext" href="{html.escape(u)}" target="_blank" rel="noopener">{html.escape(t)} ↗</a>' for t, u in EXTERNAL)
    page = (TEMPLATE.replace("__DATA__", json.dumps(listings))
                    .replace("__NOW__", html.escape(updated))
                    .replace("__COUNT__", str(len(listings)))
                    .replace("__EXT__", ext))
    (HERE / "index.html").write_text(page, encoding="utf-8")
    print(f"Wrote {len(listings)} listings  ({', '.join(f'{k}:{v}' for k,v in counts.items())})")
    for l in listings[:6]:
        print(f"  #{l['rank']:>2} {l['city']:<13} ${l['price']:<5} {l['dist']:>4}mi  [{l['source']:<10}] {l['title'][:40]}")

TEMPLATE = r"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Bay Area Rental Finder · near 469 Sherwood Way, Menlo Park</title>
<style>
  :root{--bg:#f6f7f9;--card:#fff;--ink:#1c2024;--muted:#6b7280;--line:#e6e8eb;
        --p1:#0f7b4f;--p1bg:#e7f5ee;--p2:#1d5fb4;--p2bg:#e8f0fb;--p3:#8a6d1f;--p3bg:#fbf5e3;--accent:#b4451f;}
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
  header{background:linear-gradient(135deg,#1c2b3a,#33495e);color:#fff;padding:26px 20px}
  .wrap{max-width:940px;margin:0 auto;padding:0 16px}
  header h1{margin:0 0 4px;font-size:22px} header p{margin:2px 0;color:#cdd6df;font-size:13px}
  .crit{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px}
  .crit span{background:rgba(255,255,255,.13);border:1px solid rgba(255,255,255,.2);padding:3px 10px;border-radius:999px;font-size:12px}
  .bar{position:sticky;top:0;z-index:5;background:var(--card);border-bottom:1px solid var(--line);padding:12px 0;box-shadow:0 1px 4px rgba(0,0,0,.04)}
  .controls{display:flex;flex-wrap:wrap;gap:10px;align-items:center}
  .controls input,.controls select{padding:8px 10px;border:1px solid var(--line);border-radius:8px;font-size:14px;background:#fff;color:var(--ink)}
  .controls input[type=text]{flex:1;min-width:140px}
  #refresh{background:var(--accent);color:#fff;border:none;cursor:pointer;font-weight:600;padding:8px 16px;border-radius:8px}
  #refresh:hover{filter:brightness(1.08)}
  .meta{color:var(--muted);font-size:12px;margin:10px 0 0}
  main{padding:18px 0 60px}
  .group-h{font-size:13px;font-weight:700;letter-spacing:.04em;text-transform:uppercase;color:var(--muted);margin:22px 0 10px}
  .card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px;margin-bottom:10px;display:flex;gap:14px;align-items:flex-start;transition:box-shadow .15s}
  .card:hover{box-shadow:0 4px 14px rgba(0,0,0,.07)}
  .rank{flex:none;width:30px;height:30px;border-radius:8px;background:#eef0f3;color:#444;font-weight:700;display:flex;align-items:center;justify-content:center;font-size:14px}
  .body{flex:1;min-width:0} .title{font-weight:600;margin:0 0 4px}
  .tags{display:flex;flex-wrap:wrap;gap:6px;align-items:center;font-size:12px;color:var(--muted)}
  .pill{padding:2px 8px;border-radius:999px;font-weight:600}
  .t0{background:var(--p1bg);color:var(--p1)} .t1{background:var(--p2bg);color:var(--p2)} .t2{background:var(--p3bg);color:var(--p3)}
  .src{padding:2px 8px;border-radius:999px;font-weight:600;background:#eef0f3;color:#555}
  .src.Zillow{background:#e8f0fb;color:#1d5fb4} .src.SUpost{background:#f3e9fb;color:#7a3aa6} .src.Craigslist{background:#eaf6ec;color:#2c7a3f}
  .right{flex:none;text-align:right;display:flex;flex-direction:column;gap:8px;align-items:flex-end}
  .price{font-size:18px;font-weight:700}
  .contact{background:var(--p2);color:#fff;text-decoration:none;font-size:13px;font-weight:600;padding:7px 12px;border-radius:8px;white-space:nowrap}
  .contact:hover{filter:brightness(1.08)}
  .empty{text-align:center;color:var(--muted);padding:40px}
  .ext-sec{margin-top:30px;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px}
  .ext-sec h3{margin:0 0 4px;font-size:15px} .ext-sec p{margin:0 0 12px;color:var(--muted);font-size:13px}
  .ext-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}
  .ext{display:block;padding:9px 12px;border:1px solid var(--line);border-radius:8px;text-decoration:none;color:var(--p2);font-size:13px;background:#fbfcfd}
  .ext:hover{background:#f1f5fb}
  footer{color:var(--muted);font-size:12px;padding:26px 0 50px;border-top:1px solid var(--line);margin-top:30px}
  @media(max-width:560px){.card{flex-wrap:wrap}.ext-grid{grid-template-columns:1fr}.right{flex-direction:row;width:100%;justify-content:space-between;align-items:center}}
</style></head><body>
<header><div class="wrap">
  <h1>Bay Area Rental Finder</h1>
  <p>Ranked for a move near <strong>469 Sherwood Way, Menlo Park</strong> · close to Stanford · sources: Craigslist, Zillow, SUpost</p>
  <div class="crit"><span>≤ $3,500 / mo</span><span>1 bed · 1 bath</span><span>No roommates</span>
    <span>Menlo Park › Palo Alto › nearby</span><span>Closest to Sherwood Way wins</span></div>
</div></header>
<div class="bar"><div class="wrap">
  <div class="controls">
    <input type="text" id="q" placeholder="Search title or city…">
    <select id="city"><option value="">All cities</option></select>
    <select id="source"><option value="">All sources</option><option>Craigslist</option><option>Zillow</option><option>SUpost</option></select>
    <select id="maxp"><option value="3500">≤ $3,500</option><option value="3000">≤ $3,000</option><option value="2700">≤ $2,700</option><option value="2400">≤ $2,400</option></select>
    <select id="sort"><option value="rank">Sort: Priority + closest</option><option value="dist">Sort: Closest to Sherwood Way</option><option value="price">Sort: Lowest price</option></select>
    <button id="refresh" title="Reload the latest published listings">↻ Refresh</button>
  </div>
  <p class="meta">Showing <b id="shown">0</b> of <b id="total">__COUNT__</b> listings · data as of <span id="updated">__NOW__</span></p>
</div></div>
<main><div class="wrap" id="list"></div>
<div class="wrap"><div class="ext-sec"><h3>Search these sources directly</h3>
  <p>One-click pre-filtered searches to double-check the live sites yourself. SUpost requires a Stanford (@stanford.edu) login to view contact details.</p>
  <div class="ext-grid">__EXT__</div></div></div>
<div class="wrap"><footer>
  <p><strong>How this works.</strong> Listings are pulled daily from Craigslist, Zillow, and SUpost, filtered to 1 bed / 1 bath ≤ $3,500 with no roommates, then ranked by city priority (Menlo Park → Palo Alto → other locations near Stanford) and distance to 469 Sherwood Way. Distances are straight-line estimates from each listing's area (Zillow posts include exact addresses). Suspiciously cheap posts and room/roommate listings are filtered out. Always verify before sending money.</p>
  <p>This page rebuilds automatically every day. <strong>Refresh</strong> reloads the most recently published listings. Each "View &amp; contact" button opens the original posting — on SUpost you'll need to be signed in with a Stanford email.</p>
</footer></div></main>
<script>
const EMBEDDED=__DATA__; let DATA=EMBEDDED.slice();
const TIERS={0:"Priority 1 · Menlo Park",1:"Priority 2 · Palo Alto",2:"Other locations near Stanford"};
function fillCities(){const sel=document.getElementById('city'),cur=sel.value;
  const c=[...new Set(DATA.map(d=>d.city))].sort();
  sel.innerHTML='<option value="">All cities</option>'+c.map(x=>`<option>${x}</option>`).join('');sel.value=cur;}
function esc(s){return String(s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));}
function render(){
  const q=document.getElementById('q').value.toLowerCase().trim();
  const city=document.getElementById('city').value, src=document.getElementById('source').value,
        maxp=+document.getElementById('maxp').value, sort=document.getElementById('sort').value;
  let rows=DATA.filter(d=>d.price<=maxp&&(!city||d.city===city)&&(!src||d.source===src)&&
    (!q||d.title.toLowerCase().includes(q)||d.city.toLowerCase().includes(q)));
  if(sort==='dist')rows.sort((a,b)=>a.dist-b.dist||a.price-b.price);
  else if(sort==='price')rows.sort((a,b)=>a.price-b.price||a.dist-b.dist);
  else rows.sort((a,b)=>a.tier-b.tier||a.dist-b.dist||a.price-b.price);
  const list=document.getElementById('list');
  document.getElementById('shown').textContent=rows.length; document.getElementById('total').textContent=DATA.length;
  if(!rows.length){list.innerHTML='<p class="empty">No listings match these filters.</p>';return;}
  let html='',grouped=(sort==='rank'),lastTier=null,n=0;
  rows.forEach(d=>{ if(grouped&&d.tier!==lastTier){lastTier=d.tier;html+=`<div class="group-h">${TIERS[d.tier]}</div>`;}
    n++; html+=`<div class="card"><div class="rank">${grouped?n:''}</div>
      <div class="body"><p class="title">${esc(d.title)}</p>
      <div class="tags"><span class="pill t${d.tier}">${esc(d.city)}</span><span class="src ${esc(d.source)}">${esc(d.source)}</span><span>📍 ${d.dist} mi from Sherwood Way</span></div></div>
      <div class="right"><div class="price">$${d.price.toLocaleString()}</div>
      <a class="contact" href="${d.url}" target="_blank" rel="noopener">View &amp; contact ↗</a></div></div>`; });
  list.innerHTML=html;
}
async function refresh(){const b=document.getElementById('refresh');b.textContent='↻ Refreshing…';
  try{const r=await fetch('listings.json',{cache:'no-store'});if(r.ok){const j=await r.json();
    if(Array.isArray(j.listings)){DATA=j.listings;fillCities();
      if(j.updated)document.getElementById('updated').textContent=j.updated;}}}catch(e){}
  render();b.textContent='↻ Refresh';}
['q','city','source','maxp','sort'].forEach(id=>document.getElementById(id).addEventListener('input',render));
document.getElementById('refresh').addEventListener('click',refresh);
fillCities();render();
</script></body></html>"""

if __name__ == "__main__":
    build()
