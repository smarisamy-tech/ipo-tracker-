let payload=null, view="qualified";
const $=s=>document.querySelector(s);
const money=v=>v==null?"—":"₹"+Number(v).toLocaleString("en-IN",{maximumFractionDigits:2});
const n=(v,s="")=>v==null?"—":Number(v).toLocaleString("en-IN",{maximumFractionDigits:2})+s;
function esc(v){const d=document.createElement("div");d.textContent=v??"";return d.innerHTML}
function itemCard(x){
  return `<article class="card">
    <div class="head"><div><h2>${esc(x.ipo_name)}</h2><div class="meta">Mainboard IPO</div></div>
    <span class="badge ${x.qualifies?"ok":"no"}">${x.qualifies?"QUALIFIED":"REJECTED"}</span></div>
    <div class="metrics">
      <div class="metric"><span>Subscription</span><strong>${n(x.subscription,"x")}</strong></div>
      <div class="metric"><span>GMP</span><strong>${money(x.gmp)}</strong></div>
      <div class="metric"><span>Upper price</span><strong>${money(x.upper_price)}</strong></div>
      <div class="metric"><span>Est. listing</span><strong>${money(x.estimated_listing_price)}</strong></div>
      <div class="metric"><span>Est. profit / lot</span><strong class="profit">${money(x.estimated_profit)}</strong></div>
      <div class="metric"><span>Trend</span><strong>${esc(x.trend||"—")}</strong></div>
    </div>
    ${x.gmp_date?`<div class="meta">Latest GMP row: ${esc(x.gmp_date)}</div>`:""}
    ${!x.qualifies&&x.rejection_reason?`<div class="reason">${esc(x.rejection_reason)}</div>`:""}
    <div class="links">
      <a href="${x.subscription_url}" target="_blank" rel="noopener">Subscription source</a>
      ${x.gmp_url?`<a href="${x.gmp_url}" target="_blank" rel="noopener">GMP source</a>`:""}
    </div>
  </article>`;
}
function render(){
  if(!payload)return;
  const q=$("#search").value.toLowerCase().trim();
  let items=view==="qualified"?payload.qualified:view==="rejected"?payload.rejected:[...payload.qualified,...payload.rejected];
  if(q)items=items.filter(x=>(x.ipo_name||"").toLowerCase().includes(q));
  $("#cards").innerHTML=items.length?items.map(itemCard).join(""):`<div class="notice">No IPOs match this view.</div>`;
}
async function load(force=false){
  const btn=$("#refresh");btn.disabled=true;btn.textContent="Fetching…";
  $("#notice").classList.remove("hidden");$("#notice").textContent="Fetching current InvestorGain Mainboard and GMP data…";
  try{
    const r=await fetch(force?"/api/refresh":"/api/live",{method:force?"POST":"GET",cache:"no-store"});
    if(!r.ok)throw new Error("HTTP "+r.status);
    payload=await r.json();
    $("#status").textContent=payload.status||"—";
    $("#checked").textContent=payload.checked??"—";
    $("#qualifiedCount").textContent=(payload.qualified||[]).length;
    $("#fetched").textContent=payload.fetched_at?new Date(payload.fetched_at).toLocaleTimeString([], {hour:"2-digit",minute:"2-digit"}):"—";
    $("#errors").textContent=payload.errors?.length?payload.errors.join("\n"):"No scraper errors.";
    $("#notice").textContent=`Live fetch complete: ${(payload.qualified||[]).length} qualifying IPO(s).`;
    render();
  }catch(e){
    $("#status").textContent="Offline";
    $("#notice").textContent="Live fetch failed. Check diagnostics and backend internet access.";
    $("#errors").textContent=e.stack||String(e);
  }finally{btn.disabled=false;btn.textContent="↻ Refresh live"}
}
document.querySelectorAll(".tab").forEach(b=>b.onclick=()=>{document.querySelectorAll(".tab").forEach(x=>x.classList.remove("active"));b.classList.add("active");view=b.dataset.view;render()});
$("#search").oninput=render;$("#refresh").onclick=()=>load(true);
load(false);
setInterval(()=>load(false),60000);
