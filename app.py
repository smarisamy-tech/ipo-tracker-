<div id="notice" style="color:#91a7c0;margin-bottom:12px">Fetching live data...</div>
<div id="cards" class="cards"></div>

<div class="diag" style="margin-top:14px">
<strong>Live scraper diagnostics</strong>
<pre id="errors">No errors.</pre>
</div>
</div>

<script>
let payload=null;
let view='qualified';

const money=v=>v==null?'—':'₹'+Number(v).toLocaleString('en-IN',{maximumFractionDigits:2});
const num=(v,s='')=>v==null?'—':Number(v).toLocaleString('en-IN',{maximumFractionDigits:2})+s;

function setView(v){view=v;render()}

function render(){
  if(!payload)return;
  let items=view==='qualified'?payload.qualified:view==='rejected'?payload.rejected:[...(payload.qualified||[]),...(payload.rejected||[])];
  document.getElementById('cards').innerHTML = items.length ? items.map(x=>`
    <div class="card">
      <div class="badge ${x.qualifies?'ok':'reject'}">${x.qualifies?'QUALIFIED':'REJECTED'}</div>
      <h2>${x.ipo_name||'Unknown IPO'}</h2>
      <div class="metrics">
        <div class="metric"><span>Subscription</span><strong>${num(x.subscription,'x')}</strong></div>
        <div class="metric"><span>GMP</span><strong>${money(x.gmp)}</strong></div>
        <div class="metric"><span>Upper price</span><strong>${money(x.upper_price)}</strong></div>
        <div class="metric"><span>Est. listing</span><strong>${money(x.estimated_listing_price)}</strong></div>
        <div class="metric"><span>Est. profit</span><strong class="profit">${money(x.estimated_profit)}</strong></div>
        <div class="metric"><span>Trend</span><strong>${x.trend||'—'}</strong></div>
      </div>
      ${x.rejection_reason?`<p class="reject">${x.rejection_reason}</p>`:''}
      ${x.subscription_url?`<a href="${x.subscription_url}" target="_blank">Subscription source</a>`:''}
      ${x.gmp_url?` &nbsp; <a href="${x.gmp_url}" target="_blank">GMP source</a>`:''}
    </div>
  `).join('') : '<p>No IPOs in this view.</p>';
}

async function load(force=false){
  const button=document.getElementById('refresh');
  button.disabled=true;
  try{
    const r=await fetch(force?'/api/refresh':'/api/live',{method:force?'POST':'GET',cache:'no-store'});
    if(!r.ok) throw new Error('HTTP '+r.status);
    payload=await r.json();
    document.getElementById('status').textContent=payload.status||'ok';
    document.getElementById('checked').textContent=payload.checked??'-';
    document.getElementById('qualified').textContent=(payload.qualified||[]).length;
    document.getElementById('fetched').textContent=payload.fetched_at?new Date(payload.fetched_at).toLocaleTimeString():'-';
    document.getElementById('errors').textContent=(payload.errors||[]).join('\\n')||'No errors.';
    document.getElementById('notice').textContent='Live fetch complete';
    render();
  }catch(e){
    document.getElementById('status').textContent='Offline';
    document.getElementById('errors').textContent=String(e);
    document.getElementById('notice').textContent='Live fetch failed';
  }finally{
    button.disabled=false;
  }
}
document.getElementById('refresh').onclick=()=>load(true);
load();
setInterval(()=>load(false),60000);
</script>
</body>
</html>
"""

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
    return render_template_string(HTML)

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
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))

