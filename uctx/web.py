"""uctx web UI — a local dashboard for your context store.

See, add, edit, search, and delete everything your agents remember about you.
Reads and writes the SAME local store (~/.uctx/context.db) the MCP server uses,
so what you see here is exactly what Claude / Cursor see.

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


def _norm_tags(tags):
    if isinstance(tags, str):
        return [t for t in tags.replace(",", " ").split() if t]
    return tags or []


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
    item_id = store.save(content, type=data.get("type", "note"),
                         tags=_norm_tags(data.get("tags")), source_app="uctx-web")
    return JSONResponse({"id": item_id})


async def api_update(request):
    data = await request.json()
    content = data.get("content")
    if content is not None and not content.strip():
        return JSONResponse({"error": "content cannot be empty"}, status_code=400)
    ok = store.update(int(request.path_params["item_id"]), content=content,
                      type=data.get("type"), tags=_norm_tags(data.get("tags")) if "tags" in data else None)
    return JSONResponse({"updated": ok})


async def api_delete(request):
    ok = store.forget(int(request.path_params["item_id"]))
    return JSONResponse({"deleted": ok})


routes = [
    Route("/", index),
    Route("/api/context", api_list, methods=["GET"]),
    Route("/api/context", api_add, methods=["POST"]),
    Route("/api/context/{item_id:int}", api_update, methods=["PUT"]),
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
.add.open{display:flex}
textarea{width:100%;min-height:60px;padding:10px;border:1px solid var(--border);border-radius:9px;background:var(--bg);resize:vertical}
.row{display:flex;gap:8px;flex-wrap:wrap}
select,.tags{padding:9px 10px;border:1px solid var(--border);border-radius:9px;background:var(--bg)}
.tags{flex:1;min-width:120px}
.count{color:var(--muted);font-size:13px;margin:0 0 10px}
.card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:13px 15px;margin-bottom:10px;position:relative}
.card .content{font-size:15px;margin:0 0 6px;padding-right:56px}
.badge{display:inline-block;font-size:11px;text-transform:uppercase;letter-spacing:.4px;
  color:var(--muted);border:1px solid var(--border);border-radius:6px;padding:1px 6px;margin-right:6px}
.chip{display:inline-block;font-size:12px;background:var(--chip);border-radius:20px;padding:1px 9px;margin-right:5px;color:var(--muted)}
.meta{color:var(--muted);font-size:12px;margin-top:7px}
.actions{position:absolute;top:10px;right:10px;display:flex;gap:2px}
.icon{border:none;background:none;color:var(--muted);font-size:15px;line-height:1;padding:3px 6px;border-radius:6px}
.icon:hover{background:var(--chip)}
.icon.del:hover{color:var(--danger)}
.empty{color:var(--muted);text-align:center;padding:40px 0}
.edit{display:flex;flex-direction:column;gap:8px}
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
    <input class="tags" id="tags" placeholder="tags (space or comma separated)">
    <button class="primary" id="saveBtn">Save</button>
  </div>
</div>
<p class="count" id="count"></p>
<div id="list"></div>
</div>
<script>
const $=s=>document.querySelector(s);
const esc=s=>(s||"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const TYPES=["preference","fact","note"];
let items=[];
function typeSelect(sel){return '<select class="etype">'+TYPES.map(t=>'<option'+(t===sel?' selected':'')+'>'+t+'</option>').join("")+'</select>';}
function cardHTML(i){
  const tags=(i.tags||"").split(" ").filter(Boolean).map(t=>'<span class="chip">'+esc(t)+'</span>').join("");
  return '<div class="card" data-id="'+i.id+'">'+
    '<div class="actions"><button class="icon edit" title="Edit">&#9998;</button>'+
    '<button class="icon del" title="Delete">&times;</button></div>'+
    '<p class="content"><span class="badge">'+esc(i.type)+'</span>'+esc(i.content)+'</p>'+
    tags+'<div class="meta">from '+esc(i.source_app)+' · '+esc((i.created_at||"").slice(0,10))+' · #'+i.id+'</div></div>';
}
function editHTML(i){
  return '<div class="card" data-id="'+i.id+'"><div class="edit">'+
    '<textarea class="econtent">'+esc(i.content)+'</textarea>'+
    '<div class="row">'+typeSelect(i.type)+
    '<input class="tags etags" value="'+esc(i.tags||"")+'" placeholder="tags">'+
    '<button class="primary esave">Save</button><button class="ecancel">Cancel</button>'+
    '</div></div></div>';
}
async function load(){
  const q=$("#q").value.trim();
  const r=await fetch("/api/context"+(q?"?q="+encodeURIComponent(q):""));
  items=await r.json();
  $("#count").textContent=items.length+(q?" match"+(items.length==1?"":"es"):" item"+(items.length==1?"":"s"));
  $("#list").innerHTML=items.length?items.map(cardHTML).join(""):
    '<div class="empty">'+(q?"No matches.":"Nothing saved yet. Add something, or let an agent do it.")+'</div>';
}
$("#addBtn").onclick=()=>{const f=$("#addForm");f.classList.toggle("open");if(f.classList.contains("open"))$("#content").focus();};
$("#saveBtn").onclick=async()=>{
  const content=$("#content").value.trim();if(!content)return;
  await fetch("/api/context",{method:"POST",headers:{"content-type":"application/json"},
    body:JSON.stringify({content,type:$("#type").value,tags:$("#tags").value})});
  $("#content").value="";$("#tags").value="";$("#addForm").classList.remove("open");load();
};
$("#list").onclick=async e=>{
  const card=e.target.closest(".card");if(!card)return;
  const id=+card.dataset.id;
  if(e.target.closest(".del")){if(confirm("Delete this?")){await fetch("/api/context/"+id,{method:"DELETE"});load();}return;}
  if(e.target.closest(".edit")){card.outerHTML=editHTML(items.find(i=>i.id===id));return;}
  if(e.target.closest(".ecancel")){load();return;}
  if(e.target.closest(".esave")){
    const content=card.querySelector(".econtent").value.trim();if(!content)return;
    await fetch("/api/context/"+id,{method:"PUT",headers:{"content-type":"application/json"},
      body:JSON.stringify({content,type:card.querySelector(".etype").value,tags:card.querySelector(".etags").value})});
    load();return;
  }
};
let t;$("#q").oninput=()=>{clearTimeout(t);t=setTimeout(load,180);};
load();
</script></body></html>"""
