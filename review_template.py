"""Reusable, label-agnostic engine for the offline slide-review page.

Nothing here is specific to any dataset — colours, buttons and keyboard shortcuts are
generated from whatever label set you pass in. `make_review_page.py` is the CLI that
feeds a manifest + labels into these builders. See README.md.
"""
import json

# distinct, muted colours cycled over the label set (H&E-ish first, then generic)
PALETTE = ["#c2185b", "#3f51b5", "#2e7d32", "#b26a00", "#00838f",
           "#6a1b9a", "#5d4037", "#546e7a", "#ad1457", "#283593"]


def _esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def label_colors(labels):
    return {lab: PALETTE[i % len(PALETTE)] for i, lab in enumerate(labels)}


BASE_STYLE = """
*{box-sizing:border-box} body{font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;margin:0;background:#f4f6f8;color:#1c2b3a}
header{position:sticky;top:0;z-index:10;background:#12233b;color:#fff;padding:10px 16px;box-shadow:0 2px 6px rgba(0,0,0,.2)}
header h1{font-size:16px;margin:0 0 6px}
.help{background:#1c3350;border-radius:6px;padding:8px 12px;font-size:13px;line-height:1.6;margin-bottom:8px}
.help b{color:#fff}.pill{background:#2e7d32;padding:1px 7px;border-radius:4px}
.ctl{display:flex;flex-wrap:wrap;gap:6px;align-items:center;font-size:13px}
.ctl button,.ctl select{font-size:13px;padding:5px 9px;border-radius:5px;border:1px solid #3a5170;background:#1c3350;color:#fff;cursor:pointer}
.ctl .prim{background:#2e7d32;border-color:#2e7d32;font-weight:600} .ctl .warn{background:#b26a00;border-color:#b26a00} .ctl .dngr{background:#7a1f1f;border-color:#7a1f1f}
#prog{margin-left:auto;font-variant-numeric:tabular-nums}
#grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:12px;padding:14px}
.card{background:#fff;border:3px dashed #cfd8e0;border-radius:8px;padding:8px;scroll-margin-top:150px}
.card[data-action=confirmed]{border:3px solid #2e7d32} .card[data-action=changed]{border:3px solid #e07b00}
.card[data-action=unsure]{border:3px solid #888;background:#fafafa} .card.foc{box-shadow:0 0 0 2px #fff,0 0 0 4px #4a90d9}
.card img{width:100%;height:190px;object-fit:contain;background:#fff;cursor:zoom-in;border-radius:4px}
.meta{font-size:12px;margin:6px 2px 4px}.p{color:#666}
.tag{padding:1px 6px;border-radius:4px;color:#fff;font-size:11px}
.desc{font-size:12px;color:#333;background:#f7f9fb;border-left:3px solid #90a4ae;padding:4px 8px;margin:0 2px 7px;border-radius:3px;font-style:italic;max-height:64px;overflow:auto}
.agree{width:100%;padding:10px;margin-bottom:6px;border:2px solid #2e7d32;background:#eaf6ea;color:#1b5e20;border-radius:6px;font-size:14px;font-weight:700;cursor:pointer}
.agree.on{background:#2e7d32;color:#fff}
.ov{display:flex;flex-wrap:wrap;gap:4px}.ovl{font-size:11px;color:#999;margin:1px 2px 4px}
.b{flex:1 1 40%;min-width:0;padding:7px 2px;border:1px solid #b8c4d0;background:#eef2f6;border-radius:5px;cursor:pointer;font-size:12px}
.b.on[data-call=unsure]{background:#777;color:#fff;border-color:#777}
.k{display:inline-block;min-width:14px;margin-left:4px;padding:0 3px;border:1px solid currentColor;border-radius:3px;font-size:10px;opacity:.65;vertical-align:middle}
.note{width:100%;margin-top:6px;padding:4px 6px;border:1px solid #dce3ea;border-radius:4px;font-size:12px}
#lb{display:none;position:fixed;inset:0;background:rgba(0,0,0,.85);align-items:center;justify-content:center;z-index:99;cursor:zoom-out}#lb img{max-width:92vw;max-height:92vh}
"""


def dynamic_style(labels):
    """Per-label tag + active-button colours."""
    col = label_colors(labels)
    out = []
    for lab, c in col.items():
        e = _esc(lab)
        out.append(f'.tag[data-lab="{e}"]{{background:{c}}}')
        out.append(f'.b.on[data-call="{e}"]{{background:{c};color:#fff;border-color:{c}}}')
    return "\n".join(out)


JS = r"""
let decisions={}; try{decisions=JSON.parse(localStorage.getItem(KEY)||'{}')}catch(e){decisions={}}
let focused=null;
const cards=()=>[...document.querySelectorAll('.card')];
const cardOf=id=>document.querySelector('.card[data-id="'+CSS.escape(id)+'"]');
function apply(c){const d=decisions[c.dataset.id];c.dataset.action=d.action;
  c.querySelectorAll('.b').forEach(b=>b.classList.toggle('on',b.dataset.call===d.call));
  const ag=c.querySelector('.agree'); if(ag)ag.classList.toggle('on',d.action==='confirmed');
  const n=c.querySelector('.note'); if(n&&d.note!=null)n.value=d.note;}
function focus(c){if(!c)return; if(focused)focused.classList.remove('foc'); focused=c; c.classList.add('foc');}
function initCard(c){const id=c.dataset.id; if(!decisions[id])decisions[id]={call:c.dataset.default,action:'default',note:''}; apply(c);
  c.addEventListener('mousedown',()=>focus(c));}
function setCall(id,call,viaKey){const c=cardOf(id),def=c.dataset.default;
  const action = call==='unsure'?'unsure':((def&&call===def)?'confirmed':'changed');
  decisions[id]=Object.assign({},decisions[id],{call:call,action:action}); apply(c); save(); prog();
  focus(c); if(viaKey) advance();}
function agree(id,viaKey){const def=cardOf(id).dataset.default; if(def)setCall(id,def,viaKey);}
function setNote(id,v){decisions[id]=decisions[id]||{};decisions[id].note=v;save();}
function save(){localStorage.setItem(KEY,JSON.stringify(decisions));}
function prog(){const cs=cards();let cf=0,ch=0,un=0,df=0;
  cs.forEach(c=>{const a=decisions[c.dataset.id].action;a==='confirmed'?cf++:a==='changed'?ch++:a==='unsure'?un++:df++});
  document.getElementById('prog').textContent=`reviewed ${cs.length-df}/${cs.length} · agreed ${cf} · changed ${ch} · unsure ${un} · left ${df}`;}
function advance(){const vis=cards().filter(c=>c.style.display!=='none');let i=focused?vis.indexOf(focused):-1;
  for(let j=i+1;j<vis.length;j++){if(vis[j].dataset.action==='default'){focus(vis[j]);vis[j].scrollIntoView({block:'center',behavior:'smooth'});return;}}
  if(i+1<vis.length){focus(vis[i+1]);vis[i+1].scrollIntoView({block:'center',behavior:'smooth'});}}
function markRest(){if(!confirm('Mark all remaining (not-reviewed) items as AGREED at the pre-label?'))return;
  cards().forEach(c=>{const id=c.dataset.id;if(decisions[id].action==='default'&&c.dataset.default){decisions[id].action='confirmed';apply(c)}});save();prog();}
function resetAll(){if(!confirm('Clear ALL decisions on this page and start fresh? Cannot be undone.'))return;
  localStorage.removeItem(KEY);decisions={};
  cards().forEach(c=>{decisions[c.dataset.id]={call:c.dataset.default,action:'default',note:''};apply(c)});prog();}
function sortBy(m){const g=document.getElementById('grid'),
  k={id:c=>c.dataset.id,prelabel:c=>c.dataset.prelabel||'~',order:c=>+c.dataset.order}[m];
  cards().sort((a,b)=>{const ka=k(a),kb=k(b);return ka<kb?-1:ka>kb?1:0;}).forEach(c=>g.appendChild(c));}
function filterBy(m){cards().forEach(c=>{const a=decisions[c.dataset.id].action,p=c.dataset.prelabel;let s=true;
  if(m==='notreviewed')s=a==='default';else if(m==='changed')s=a==='changed';else if(m&&m[0]==='='){s=p===m.slice(1);}
  c.style.display=s?'':'none'});}
function exportCSV(){const rows=[['id','prelabel','reviewer_call','action','note']];
  cards().forEach(c=>{const d=decisions[c.dataset.id];rows.push([c.dataset.id,c.dataset.prelabel,d.call,d.action,(d.note||'').replace(/[\n,]/g,' ')])});
  const csv=rows.map(r=>r.map(x=>/[",]/.test(x)?'"'+x.replace(/"/g,'""')+'"':x).join(',')).join('\n');
  const b=new Blob([csv],{type:'text/csv'}),a=document.createElement('a');
  a.href=URL.createObjectURL(b);a.download='review_'+KEY+'.csv';a.click();}
function zoom(img){const lb=document.getElementById('lb');lb.querySelector('img').src=img.src;lb.style.display='flex';}
document.getElementById('lb').addEventListener('click',function(){this.style.display='none'});
document.addEventListener('keydown',e=>{
  if(e.target.tagName==='INPUT'||e.target.tagName==='TEXTAREA')return;
  const k=e.key.toLowerCase();
  if(!focused&&cards().length)focus(cards()[0]);
  if(!focused)return;
  const id=focused.dataset.id;
  if(k==='a'){agree(id,true);e.preventDefault();}
  else if(k==='u'){setCall(id,'unsure',true);e.preventDefault();}
  else if(/^[1-9]$/.test(k)){const b=focused.querySelectorAll('.ov .b')[parseInt(k)-1];
    if(b&&b.dataset.call!=='unsure'){setCall(id,b.dataset.call,true);e.preventDefault();}}
  else if(['arrowright','arrowdown','arrowleft','arrowup'].includes(k)){const vis=cards().filter(c=>c.style.display!=='none');
    let i=vis.indexOf(focused);i=(k==='arrowright'||k==='arrowdown')?Math.min(vis.length-1,i+1):Math.max(0,i-1);
    focus(vis[i]);vis[i].scrollIntoView({block:'center'});e.preventDefault();}});
cards().forEach(initCard); sortBy(DEFAULT_SORT); if(cards().length)focus(cards()[0]); prog();
"""


def card_html(item, labels, b64):
    """item: dict with id, prelabel(optional), description(optional), meta(optional), order(optional)."""
    iid = _esc(item["id"]); pre = item.get("prelabel") or ""; pre_e = _esc(pre)
    default = pre_e  # agree accepts the pre-label; '' if none
    meta = item.get("meta") or ""; desc = item.get("description") or ""
    tag = f' · <span class="tag" data-lab="{pre_e}">{pre_e}</span>' if pre else ""
    meta_h = f' <span class="p">{_esc(meta)}</span>' if meta else ""
    desc_h = f'<div class="desc">"{_esc(desc)}"</div>' if desc else ""
    agree_h = (f'<button class="agree" onclick="agree(\'{iid}\')">✓ Agree — {pre_e}'
               f' <span class="k">A</span></button>') if pre else ""
    btns = "".join(
        f'<button class="b" data-call="{_esc(l)}" onclick="setCall(\'{iid}\',\'{_esc(l)}\')">'
        f'{_esc(l)}{f"<span class=k>{i+1}</span>" if i < 9 else ""}</button>'
        for i, l in enumerate(labels))
    btns += f'<button class="b" data-call="unsure" onclick="setCall(\'{iid}\',\'unsure\')">Unsure<span class="k">U</span></button>'
    return (f'<div class="card" data-id="{iid}" data-prelabel="{pre_e}" data-default="{default}" '
            f'data-order="{item.get("order",0)}">\n'
            f'  <img loading="lazy" src="data:image/jpeg;base64,{b64}" onclick="zoom(this)">\n'
            f'  <div class="meta"><b>{iid}</b>{tag}{meta_h}</div>\n  {desc_h}\n  {agree_h}\n'
            f'  <div class="ovl">wrong? set the correct label:</div>\n  <div class="ov">{btns}</div>\n'
            f'  <input class="note" placeholder="note (optional)" oninput="setNote(\'{iid}\',this.value)">\n</div>')


def build_page(cards_html, labels, title, help_text, storage_key, default_sort="order"):
    filt = "".join(f'<button onclick="filterBy(\'={_esc(l)}\')">{_esc(l)}</button>' for l in labels)
    style = BASE_STYLE + "\n" + dynamic_style(labels)
    boot = (f'const KEY={json.dumps(storage_key)};'
            f'const DEFAULT_SORT={json.dumps(default_sort)};')
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>{_esc(title)}</title><style>{style}</style></head>
<body><header><h1>{_esc(title)}</h1>
<div class="help">{help_text}</div>
<div class="ctl">
 sort: <select onchange="sortBy(this.value)"><option value="order">default</option><option value="id">id</option><option value="prelabel">pre-label</option></select>
 show: <button onclick="filterBy('all')">all</button>{filt}<button onclick="filterBy('notreviewed')">not reviewed</button><button onclick="filterBy('changed')">changed</button>
 <button class="warn" onclick="markRest()">agree with all remaining</button>
 <button class="prim" onclick="exportCSV()">⬇ download CSV</button>
 <button class="dngr" onclick="resetAll()">↺ start over</button>
 <span id="prog"></span>
</div></header>
<div id="grid">
{cards_html}
</div>
<div id="lb"><img></div>
<script>{boot}</script>
<script>{JS}</script>
</body></html>"""
