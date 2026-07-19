"""uctx web UI — a local dashboard for your context store.

See, add, search, and delete everything your agents remember about you. Reads
and writes the SAME local store (~/.uctx/context.db) the MCP server uses, so
what you see here is exactly what Claude / Cursor see.

Run:  uctx-web        (installed script)
  or: python -m uctx.web
Then open http://127.0.0.1:8787  (override with $UCTX_WEB_PORT).

Binds to localhost only — this is a personal, single-user tool.
"""

from __future__ import annotations

import os

from starlette.applications import Starlette
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Route

from . import store


async def index(_request):
    return HTMLResponse(PAGE)


async def api_list(request):
    q = request.query_params.get("q", "").strip()
    items = store.search(q, limit=500) if q else store.list_all(limit=500)
    return JSONResponse(items)


async def api_add(request):
    data = await request.json()
    content = (data.get("content") or "").strip()
    if not content:
        return JSONResponse({"error": "content is required"}, status_code=400)
    tags = data.get("tags") or []
    if isinstance(tags, str):
        tags = [t for t in tags.replace(",", " ").split() if t]
    item_id = store.save(content, type=data.get("type", "note"), tags=tags, source_app="uctx-web")
    return JSONResponse({"id": item_id})


async def api_delete(request):
    ok = store.forget(int(request.path_params["item_id"]))
    return JSONResponse({"deleted": ok})


routes = [
    Route("/", index),
    Route("/api/context", api_list, methods=["GET"]),
    Route("/api/context", api_add, methods=["POST"]),
    Route("/api/context/{item_id:int}", api_delete, methods=["DELETE"]),
]

app = Starlette(routes=routes)


def main() -> None:
    import uvicorn

    port = int(os.environ.get("UCTX_WEB_PORT", "8787"))
    print(f"uctx web UI  ->  http://127.0.0.1:{port}")
    uvicorn.run(app, host="127.0.0.1", port=port)


if __name__ == "__main__":
    main()


PAGE = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>uctx — your context</title>
<style>
:root{--bg:#f7f8fa;--fg:#1f2328;--muted:#59636e;--card:#fff;--border:#d8dee4;
  --accent:#2563eb;--chip:#eef2f7;--danger:#b42318;}
@media (prefers-color-scheme:dark){:root{--bg:#0d1117;--fg:#e6edf3;--muted:#9198a1;
  --card:#161b22;--border:#30363d;--accent:#4493f8;--chip:#21262d;--danger:#ff7b72;}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;line-height:1.5}
.wrap{max-width:760px;margin:0 auto;padding:28px 18px 80px}
h1{font-size:22px;margin:0 0 2px}
.sub{color:var(--muted);font-size:14px;margin:0 0 20px}
.bar{display:flex;gap:8px;margin-bottom:16px}
input,select,textarea,button{font:inherit;color:inherit}
#q{flex:1;padding:9px 12px;border:1px solid var(--border);border-radius:9px;background:var(--card)}
button{cursor:pointer;border:1px solid var(--border);background:var(--card);border-radius:9px;padding:9px 14px}
button.primary{background:var(--accent);color:#fff;border-color:transparent}
.add{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:14px;margin-bottom:18px;display:none;gap:10px;flex-direction:column}
.add textarea{width:100%;min-height:60px;padding:10px;border:1px solid var(--border);border-radius:9px;background:var(--bg);resize:vertical}
.add .row{display:flex;gap:8px}
.add select,.add input{padding:9px 10px;border:1px solid var(--border);border-radius:9px;background:var(--bg)}
.add input{flex:1}
.count{color:var(--muted);font-size:13px;margin:0 0 10px}
.card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:13px 15px;margin-bottom:10px;position:relative}
.card .content{font-size:15px;margin:0 0 6px;padding-right:28px}
.badge{display:inline-block;font-size:11px;text-transform:uppercase;letter-spacing:.4px;
  color:var(--muted);border:1px solid var(--border);border-radius:6px;padding:1px 6px;margin-right:6px}
.chip{display:inline-block;font-size:12px;background:var(--chip);border-radius:20px;padding:1px 9px;margin-right:5px;color:var(--muted)}
.meta{color:var(--muted);font-size:12px;margin-top:7px}
.del{position:absolute;top:10px;right:10px;border:none;background:none;color:var(--muted);font-size:18px;line-height:1;padding:2px 6px;border-radius:6px}
.del:hover{color:var(--danger);background:var(--chip)}
.empty{color:var(--muted);text-align:center;padding:40px 0}
</style></head><body><div class="wrap">
<h1>Your context</h1>
<p class="sub">Everything your agents remember — stored locally, owned by you.</p>
<div class="bar">
  <input id="q" placeholder="Search your context…" autocomplete="off">
  <button class="primary" id="addBtn">+ Add</button>
</div>
<div class="add" id="addForm">
  <textarea id="content" placeholder="Something to remember, e.g. 'I prefer Python and tabs over spaces'"></textarea>
  <div class="row">
    <select id="type"><option value="preference">preference</option><option value="fact">fact</option><option value="note" selected>note</option></select>
    <input id="tags" placeholder="tags (space or comma separated)">
    <button class="primary" id="saveBtn">Save</button>
  </div>
</div>
<p class="count" id="count"></p>
<div id="list"></div>
</div>
<script>
const $=s=>document.querySelector(s);
const esc=s=>(s||"").replace(/[&<>]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]));
async function load(){
  const q=$("#q").value.trim();
  const r=await fetch("/api/context"+(q?"?q="+encodeURIComponent(q):""));
  const items=await r.json();
  $("#count").textContent=items.length+(q?" match"+(items.length==1?"":"es"):" item"+(items.length==1?"":"s"));
  if(!items.length){$("#list").innerHTML='<div class="empty">'+(q?"No matches.":"Nothing saved yet. Add something, or let an agent do it.")+'</div>';return;}
  $("#list").innerHTML=items.map(i=>{
    const tags=(i.tags||"").split(" ").filter(Boolean).map(t=>'<span class="chip">'+esc(t)+'</span>').join("");
    return '<div class="card"><button class="del" data-id="'+i.id+'" title="Delete">×</button>'+
      '<p class="content"><span class="badge">'+esc(i.type)+'</span>'+esc(i.content)+'</p>'+
      tags+'<div class="meta">from '+esc(i.source_app)+' · '+esc((i.created_at||"").slice(0,10))+' · #'+i.id+'</div></div>';
  }).join("");
}
$("#addBtn").onclick=()=>{const f=$("#addForm");f.style.display=f.style.display==="flex"?"none":"flex";if(f.style.display==="flex")$("#content").focus();};
$("#saveBtn").onclick=async()=>{
  const content=$("#content").value.trim();if(!content)return;
  await fetch("/api/context",{method:"POST",headers:{"content-type":"application/json"},
    body:JSON.stringify({content,type:$("#type").value,tags:$("#tags").value})});
  $("#content").value="";$("#tags").value="";$("#addForm").style.display="none";load();
};
$("#list").onclick=async e=>{const b=e.target.closest(".del");if(!b)return;
  if(!confirm("Delete this?"))return;
  await fetch("/api/context/"+b.dataset.id,{method:"DELETE"});load();};
let t;$("#q").oninput=()=>{clearTimeout(t);t=setTimeout(load,180);};
load();
</script></body></html>"""
