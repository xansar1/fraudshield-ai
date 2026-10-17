/* FraudShield AI — plain JavaScript, no build tooling or icon CDNs. */
(() => {
  'use strict';
  const $ = s => document.querySelector(s);
  const $$ = s => [...document.querySelectorAll(s)];
  let cachedOverview = null;
  let latestRows = [];
  const money = n => new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',maximumFractionDigits:0}).format(n);
  const integer = n => new Intl.NumberFormat('en-US').format(n);
  const pct = n => `${(n * 100).toFixed(1)}%`;
  const clean = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const icon = id => `<svg aria-hidden="true"><use href="#i-${id}"/></svg>`;
  const tierClass = tier => tier === 'High' ? 'high' : tier === 'Elevated' ? 'elevated' : 'low';
  const riskColor = t => t === 'High' ? 'var(--pink)' : t === 'Elevated' ? '#d9b77b' : 'var(--mint)';
  async function getJson(path, opts) {
    const response = await fetch(path,opts);
    if (!response.ok) {
      let info='';try {const error=await response.json();info=typeof error.detail==='string'?error.detail:JSON.stringify(error.detail).slice(0,300)}catch(_){}
      throw new Error(info || `Server returned ${response.status}`);
    }
    return response.json();
  }
  function viewFromHash(){let hash=window.location.hash.slice(1);if(!['overview','transactions','risk-lab','model'].includes(hash))hash='overview';return hash;}
  function setView(){
    const view=viewFromHash();
    $$('.view').forEach(el => el.classList.toggle('active',el.id===view));
    $$('.nav-link').forEach(a => {const active=a.dataset.view===view;a.classList.toggle('active',active);a.setAttribute('aria-current',active?'page':'false')});
    $('#breadcrumb').textContent=({overview:'Overview',transactions:'Transactions','risk-lab':'Risk Lab',model:'Model Insights'})[view];
    $('#sidebar').classList.remove('open');$('#backdrop').classList.remove('show');$('#menuBtn').setAttribute('aria-expanded','false');
    window.scrollTo({top:0,behavior:'auto'});
    if(view==='transactions')loadTransactions();
    if(view==='model')loadModel();
  }
  window.addEventListener('hashchange',setView);
  $('#menuBtn').addEventListener('click',()=>{const open=$('#sidebar').classList.toggle('open');$('#backdrop').classList.toggle('show',open);$('#menuBtn').setAttribute('aria-expanded',String(open))});
  $('#backdrop').addEventListener('click',()=>{ $('#sidebar').classList.remove('open');$('#backdrop').classList.remove('show'); });
  $('#year').textContent=new Date().getFullYear();
  function rowHtml(item, expanded=false){
    const risk=Math.max(0,Math.min(100,item.risk*100));
    const when=new Date(item.timestamp).toLocaleString('en-US',{timeZone:'UTC',month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'});
    const start=`<td class="id-text">${clean(item.id)}</td>`;
    const amount=`<td class="amount-text">${money(item.amount)}</td>`;
    const score=`<td><span class="table-score"><span class="score-line"><i style="width:${risk.toFixed(1)}%;background:${riskColor(item.tier)}"></i></span>${risk.toFixed(1)}%</span></td>`;
    const level=`<td><span class="tier tier-${tierClass(item.tier)}">${clean(item.tier)}</span></td>`;
    if(expanded) return `<tr>${start}<td>${when}</td><td>${clean(item.channel)}</td><td>${clean(item.category)}</td>${amount}${score}${level}</tr>`;
    return `<tr>${start}<td>${clean(item.channel)}</td>${amount}${score}${level}</tr>`;
  }
  function drawChart(timeline){
    if(!timeline?.length){$('#activityChart').textContent='No activity available';return}
    const w=750,h=217,left=35,right=15,top=12,bottom=31;
    const plotW=w-left-right, plotH=h-top-bottom;
    const maxTx=Math.max(1,...timeline.map(x=>x.transactions))*1.15;
    const points=(key,max)=>timeline.map((x,i)=>[left+i*(plotW/Math.max(1,timeline.length-1)),top+plotH-(x[key]/max)*plotH]);
    const a=points('transactions',maxTx),b=points('high_risk',maxTx);
    const path=points=>points.map(([x,y],i)=>`${i?'L':'M'}${x.toFixed(1)},${y.toFixed(1)}`).join(' ');
    const area=`${path(a)} L${a.at(-1)[0]},${top+plotH} L${a[0][0]},${top+plotH} Z`;
    const grid=[0,.25,.5,.75,1].map(p=>`<line class="gridline" x1="${left}" y1="${top+p*plotH}" x2="${w-right}" y2="${top+p*plotH}"/>`).join('');
    const ticks=timeline.map((d,i)=>i%(timeline.length>10?3:2)===0||i===timeline.length-1?`<text text-anchor="middle" x="${left+i*plotW/Math.max(1,timeline.length-1)}" y="${h-8}">${clean(d.date)}</text>`:'').join('');
    $('#activityChart').innerHTML=`<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="Transaction counts and flagged items over a 14-day simulated period"><defs><linearGradient id="lineFill" x1="0" x2="0" y1="0" y2="1"><stop stop-color="#89f7d1" stop-opacity=".23"/><stop offset="1" stop-color="#89f7d1" stop-opacity="0"/></linearGradient></defs>${grid}<path class="area" d="${area}"/><path class="mainline" d="${path(a)}"/><path class="highline" d="${path(b)}"/>${ticks}</svg>`;
  }
  function displayOverview(data){
    $('#statTransactions').textContent=integer(data.total);
    $('#statFlagged').textContent=integer(data.high_risk);
    $('#statVolume').textContent=money(data.total_volume);
    $('#statRisk').textContent=pct(data.avg_risk);
    $('#lowCount').textContent=integer(data.low_risk);
    $('#elevatedCount').textContent=integer(data.elevated);
    $('#highCount').textContent=integer(data.high_risk);
    $('#donutTotal').textContent=integer(data.total);
    const low=100*data.low_risk/data.total,med=100*(data.low_risk+data.elevated)/data.total;
    $('#donut').style.background=`conic-gradient(var(--mint) 0% ${low}%,var(--purple) ${low}% ${med}%,var(--pink) ${med}% 100%)`;
    $('#recentBody').innerHTML=data.recent.map(row=>rowHtml(row)).join('');
    drawChart(data.timeline);
  }
  async function loadOverview(){
    try {cachedOverview=await getJson('/api/overview');displayOverview(cachedOverview)}
    catch(e){$('#statTransactions').textContent='Offline';$('#recentBody').innerHTML=`<tr><td colspan="5">${clean(e.message)}. Run scripts/start_mac.sh first.</td></tr>`;$('#activityChart').textContent='API unavailable'}
  }
  $('#refreshBtn').addEventListener('click',()=>{loadOverview();if(viewFromHash()==='transactions')loadTransactions()});
  async function loadTransactions(){
    const tier=$('#tierFilter').value;
    try{const res=await getJson('/api/transactions?tier='+encodeURIComponent(tier)+'&limit=80');latestRows=res.items;$('#allTransactionsBody').innerHTML=res.items.length?res.items.map(row=>rowHtml(row,true)).join(''):'<tr><td colspan="7">No matching transactions.</td></tr>';$('#tableFooter').textContent=`Showing ${res.items.length} of ${integer(res.matching)} synthetic records`}
    catch(e){$('#allTransactionsBody').innerHTML=`<tr><td colspan="7">${clean(e.message)}</td></tr>`}
  }
  $('#tierFilter').addEventListener('change',loadTransactions);
  $('#exportBtn').addEventListener('click',()=>{
    if(!latestRows.length){alert('Load transactions first.');return}
    const headers=['id','timestamp','channel','category','amount','risk','tier'];
    const csv=[headers.join(','),...latestRows.map(r=>headers.map(k=>`"${String(r[k]).replaceAll('"','""')}"`).join(','))].join('\r\n');
    const blob=new Blob([csv],{type:'text/csv;charset=utf-8'});
    const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='fraudshield_demo_transactions.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  });
  const form=$('#scoreForm');
  $('#loadRisky').addEventListener('click',()=>{
    const values={amount_usd:2850,amount_ratio:8.2,transactions_1h:8,hour_of_day:2,account_age_days:12,device_trust_score:.13,merchant_risk_score:.84,payment_channel:'Bank transfer',merchant_category:'Digital goods'};
    Object.entries(values).forEach(([name,val])=>form.elements[name].value=val);
    form.elements.is_international.checked=true;form.elements.card_present.checked=false;form.elements.is_new_payee.checked=true;
    $('#scoreError').textContent='';
  });
  function renderResult(data){
    $('#resultEmpty').hidden=true;$('#resultContent').hidden=false;
    $('#resultPct').textContent=`${data.risk_percent.toFixed(1)}%`;
    $('#scoreRing').style.background=`conic-gradient(${riskColor(data.tier)} 0 ${data.risk_percent}%,#223047 ${data.risk_percent}% 100%)`;
    $('#resultTier').textContent=`${data.tier} risk`;
    $('#resultTier').style.color=riskColor(data.tier);
    $('#resultTier').style.background=`${data.tier==='High'?'#f58db516':data.tier==='Elevated'?'#d9b77b19':'#87f8d211'}`;
    $('#resultMessage').textContent=data.tier==='High'?'Synthetic model cutoff exceeded: flag for human review in this demo.':data.tier==='Elevated'?'Score is below the review cutoff, but above the elevated boundary.':'No review flag from this synthetic demo model.';
    const drivers=data.drivers||[];
    const reducing=data.mitigating_signals||[];
    function modelShiftRows(items, className){
      const highest=Math.max(.1,...items.map(d=>Math.abs(d.log_odds_shift)));
      return items.map(d=>{
        const amount=Math.abs(d.log_odds_shift);
        return `<div class="driver-row ${className}"><div class="driver-name"><span>${clean(d.label)}</span><strong>${d.log_odds_shift>0?'+':'−'}${amount.toFixed(2)} log-odds</strong></div><div class="driver-bar"><i style="width:${Math.max(2,100*amount/highest)}%"></i></div></div>`;
      }).join('');
    }
    $('#drivers').innerHTML=drivers.length?modelShiftRows(drivers,''):'<p class="minor">No input exceeded the model-sensitivity display threshold relative to its training reference.</p>';
    $('#mitigatingSignals').hidden=!reducing.length;
    $('#mitigatingDrivers').innerHTML=modelShiftRows(reducing,'reducing');
    const caution=$('#scoreCaution');
    const saturated=data.risk_percent>=99.9 || data.risk_percent<=.1;
    caution.hidden=!saturated;
    if(saturated)caution.textContent='This score is near a numerical extreme. Its displayed percentage is a rounded model output, not certainty of fraud or safety.';
  }
  form.addEventListener('submit',async event=>{
    event.preventDefault();$('#scoreError').textContent='';
    const button=$('#scoreBtn');button.disabled=true;
    const data={};
    const numeric=['amount_usd','amount_ratio','transactions_1h','hour_of_day','account_age_days','device_trust_score','merchant_risk_score'];
    numeric.forEach(key=>{data[key]=Number(form.elements[key].value)});
    ['is_international','card_present','is_new_payee'].forEach(key=>data[key]=form.elements[key].checked);
    ['payment_channel','merchant_category'].forEach(key=>data[key]=form.elements[key].value);
    try{const result=await getJson('/api/score',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});renderResult(result)}
    catch(e){$('#scoreError').textContent=`Could not score transaction: ${e.message}`}
    finally{button.disabled=false}
  });
  let modelLoaded=false;
  async function loadModel(){
    if(modelLoaded)return;
    try{
      const m=await getJson('/api/model');modelLoaded=true;
      $('#modelName').textContent=m.model_name;
      $('#modelMeta').innerHTML=`<span>${integer(m.dataset_rows)} fictional records</span><span>Train / validate / test: ${integer(m.split.train)} / ${integer(m.split.validation)} / ${integer(m.split.test)}</span><span>Review cutoff: ${pct(m.threshold)}</span>`;
      $('#mPRAUC').textContent=m.test.pr_auc.toFixed(3);
      $('#mPrecision').textContent=pct(m.test.precision);
      $('#mRecall').textContent=pct(m.test.recall);
      $('#mROC').textContent=m.test.roc_auc.toFixed(3);
      const c=m.test.confusion;
      const positives=c.tp+c.fn;
      const flagged=c.tp+c.fp;
      const baseRate=m.synthetic_fraud_rate || positives/m.split.test;
      $('#modelRealityText').textContent=`On ${integer(m.split.test)} held-out synthetic records, ${integer(flagged)} were flagged: ${integer(c.tp)} simulated positives found, ${integer(c.fp)} false alerts, and ${integer(c.fn)} missed positives. Precision ${pct(m.test.precision)}; recall ${pct(m.test.recall)}. PR-AUC ${m.test.pr_auc.toFixed(3)} compared with roughly ${pct(baseRate)} simulated positive prevalence. This is a modest research baseline, not a live fraud-protection system.`;
      const imp=m.feature_importance.slice(0,7),max=Math.max(.001,...imp.map(d=>d.importance));
      $('#importanceBars').innerHTML=imp.map(f=>`<div class="importance-row"><div class="feature-heading"><span>${clean(f.label)}</span><span>${f.importance.toFixed(3)}</span></div><div class="feature-track"><i style="width:${Math.max(2,100*f.importance/max)}%"></i></div></div>`).join('');
      $('#confusionGrid').innerHTML=`<div class="confusion-cell good"><strong>${integer(c.tn)}</strong><small>TRUE NEGATIVES</small></div><div class="confusion-cell warn"><strong>${integer(c.fp)}</strong><small>FALSE ALERTS</small></div><div class="confusion-cell warn"><strong>${integer(c.fn)}</strong><small>MISSED POSITIVES</small></div><div class="confusion-cell good"><strong>${integer(c.tp)}</strong><small>TRUE POSITIVES</small></div>`;
    }catch(e){$('#modelName').textContent='Model unavailable: '+e.message}
  }
  setView();loadOverview();
})();
