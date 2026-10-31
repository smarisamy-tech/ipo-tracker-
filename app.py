from flask import Flask, jsonify, request, Response
from scraper import get_live_data
from datetime import datetime, timezone
import os
import threading
import time

app = Flask(__name__)
lock = threading.Lock()
CACHE_TTL = int(os.environ.get("CACHE_TTL_SECONDS", "60"))
cache = {"ts": 0, "payload": None}

HTML = '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width,initial-scale=1">\n<title>IPO Live Dashboard</title>\n<style>\nbody{margin:0;background:#07111f;color:#f0f7ff;font-family:Arial,sans-serif}\n.wrap{max-width:1100px;margin:auto;padding:24px}\nheader{display:flex;justify-content:space-between;gap:16px;align-items:center}\nh1{margin:0 0 8px;font-size:42px}\np{color:#91a7c0}\nbutton{background:#45e3a1;color:#04130d;border:0;border-radius:12px;padding:11px 14px;font-weight:700;cursor:pointer}\n.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:20px 0}\n.stat,.card,.diag{background:#102036;border:1px solid #223a57;border-radius:16px;padding:14px}\n.stat span{display:block;color:#91a7c0;font-size:12px}.stat strong{font-size:20px}\n.tabs{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:14px}\n.tabs button{background:#132842;color:#f0f7ff;border:1px solid #223a57}\n.cards{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}\n.card h2{margin-top:0}\n.metrics{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}\n.metric{background:#0c192b;border-radius:10px;padding:9px}\n.metric span{display:block;color:#91a7c0;font-size:11px}\n.profit{color:#45e3a1}.reject{color:#ff7382}.ok{color:#45e3a1}\na{color:#71a9ff}pre{white-space:pre-wrap;color:#91a7c0}\n@media(max-width:720px){.stats{grid-template-columns:repeat(2,1fr)}.cards{grid-template-columns:1fr}.metrics{grid-template-columns:repeat(2,1fr)}header{display:block}header button{margin-top:12px}}\n</style>\n</head>\n<body>\n<div class="wrap">\n<header>\n<div>\n<div style="color:#45e3a1;font-weight:800;font-size:12px">TRUE LIVE • INVESTORGAIN</div>\n<h1>Mainboard IPO Signals</h1>\n<p>Mainboard only • Subscription ≥100x • Estimated profit per lot &gt; ₹500</p>\n</div>\n<button id="refresh">Refresh live</button>\n</header>\n\n<div class="stats">\n<div class="stat"><span>Status</span><strong id="status">Loading...</strong></div>\n<div class="stat"><span>Checked</span><strong id="checked">-</strong></div>\n<div class="stat"><span>Qualified</span><strong id="qualified">-</strong></div>\n<div class="stat"><span>Fetched</span><strong id="fetched">-</strong></div>\n</div>\n\n<div class="tabs">\n<button onclick="setView(\'qualified\')">Qualified</button>\n<button onclick="setView(\'rejected\')">Rejected</button>\n<button onclick="setView(\'all\')">All</button>\n</div>\n\n<div id="notice" style="color:#91a7c0;margin-bottom:12px">Fetching live data...</div>\n<div id="cards" class="cards"></div>\n\n<div class="diag" style="margin-top:14px">\n<strong>Live scraper diagnostics</strong>\n<pre id="errors">No errors.</pre>\n</div>\n</div>\n\n<script>\nlet payload=null;\nlet view=\'qualified\';\n\nconst money=v=>v==null?\'—\':\'₹\'+Number(v).toLocaleString(\'en-IN\',{maximumFractionDigits:2});\nconst num=(v,s=\'\')=>v==null?\'—\':Number(v).toLocaleString(\'en-IN\',{maximumFractionDigits:2})+s;\n\nfunction setView(v){view=v;render();}\n\nfunction render(){\n  if(!payload)return;\n  let items=view===\'qualified\'\n    ? (payload.qualified||[])\n    : view===\'rejected\'\n      ? (payload.rejected||[])\n      : [...(payload.qualified||[]),...(payload.rejected||[])];\n\n  document.getElementById(\'cards\').innerHTML = items.length ? items.map(x=>`\n    <div class="card">\n      <div class="${x.qualifies?\'ok\':\'reject\'}">${x.qualifies?\'QUALIFIED\':\'REJECTED\'}</div>\n      <h2>${x.ipo_name||\'Unknown IPO\'}</h2>\n      <div class="metrics">\n        <div class="metric"><span>Subscription</span><strong>${num(x.subscription,\'x\')}</strong></div>\n        <div class="metric"><span>GMP</span><strong>${money(x.gmp)}</strong></div>\n        <div class="metric"><span>Upper price</span><strong>${money(x.upper_price)}</strong></div>\n        <div class="metric"><span>Est. listing</span><strong>${money(x.estimated_listing_price)}</strong></div>\n        <div class="metric"><span>Est. profit</span><strong class="profit">${money(x.estimated_profit)}</strong></div>\n        <div class="metric"><span>Trend</span><strong>${x.trend||\'—\'}</strong></div>\n      </div>\n      ${x.rejection_reason?`<p class="reject">${x.rejection_reason}</p>`:\'\'}\n      ${x.subscription_url?`<a href="${x.subscription_url}" target="_blank">Subscription source</a>`:\'\'}\n      ${x.gmp_url?` &nbsp; <a href="${x.gmp_url}" target="_blank">GMP source</a>`:\'\'}\n    </div>\n  `).join(\'\') : \'<p>No IPOs in this view.</p>\';\n}\n\nasync function load(force=false){\n  const button=document.getElementById(\'refresh\');\n  button.disabled=true;\n  try{\n    const r=await fetch(force?\'/api/refresh\':\'/api/live\',{\n      method:force?\'POST\':\'GET\',\n      cache:\'no-store\'\n    });\n    if(!r.ok)throw new Error(\'HTTP \'+r.status);\n\n    payload=await r.json();\n    document.getElementById(\'status\').textContent=payload.status||\'ok\';\n    document.getElementById(\'checked\').textContent=payload.checked??\'-\';\n    document.getElementById(\'qualified\').textContent=(payload.qualified||[]).length;\n    document.getElementById(\'fetched\').textContent=payload.fetched_at\n      ? new Date(payload.fetched_at).toLocaleTimeString()\n      : \'-\';\n    document.getElementById(\'errors\').textContent=(payload.errors||[]).join(\'\\n\')||\'No errors.\';\n    document.getElementById(\'notice\').textContent=\'Live fetch complete\';\n    render();\n  }catch(e){\n    document.getElementById(\'status\').textContent=\'Offline\';\n    document.getElementById(\'errors\').textContent=String(e);\n    document.getElementById(\'notice\').textContent=\'Live fetch failed\';\n  }finally{\n    button.disabled=false;\n  }\n}\n\ndocument.getElementById(\'refresh\').onclick=()=>load(true);\nload();\nsetInterval(()=>load(false),60000);\n</script>\n</body>\n</html>\n'


def live(force=False):
    now = time.time()
    if not force and cache["payload"] and now - cache["ts"] < CACHE_TTL:
        return cache["payload"]

    with lock:
        now = time.time()
        if not force and cache["payload"] and now - cache["ts"] < CACHE_TTL:
            return cache["payload"]

        payload = get_live_data()
        payload["fetched_at"] = datetime.now(timezone.utc).isoformat()
        cache["payload"] = payload
        cache["ts"] = time.time()
        return payload

@app.get("/")
def index():
    return Response(HTML, mimetype="text/html")

@app.get("/api/live")
def api_live():
    return jsonify(live(request.args.get("force") == "1"))

@app.post("/api/refresh")
def api_refresh():
    return jsonify(live(True))

@app.get("/api/health")
def api_health():
    return jsonify({
        "ok": True,
        "source": "InvestorGain",
        "cache_ttl_seconds": CACHE_TTL
    })

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "5000"))
    )
