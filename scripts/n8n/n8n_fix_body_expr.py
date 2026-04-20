"""
Convierte el body de los 7 tools create/update al patrón $fromAI-inline:
   jsonBody = "={{ $fromAI('body', '<desc>', 'json') }}"
   sin placeholder `body` en placeholderDefinitions.
Así n8n evalúa la expresión ANTES y mete el JSON ya listo, evitando el bug
donde parseaba el template literal '{body}' como JSON.
"""
from n8n_api import req

WID = "kwoD2OHZeWSMTdTC"

code, wf = req("GET", f"/workflows/{WID}")
fixed = []

for n in wf["nodes"]:
    if n.get("type") != "@n8n/n8n-nodes-langchain.toolHttpRequest":
        continue
    p = n.get("parameters", {})
    phs_wrap = p.get("placeholderDefinitions") or {}
    phs = phs_wrap.get("values", [])
    body_ph = next((x for x in phs if x.get("name") == "body"), None)
    if not body_ph:
        continue  # search tools o add_comment → no tocar

    desc = body_ph.get("description", "").replace("'", "\\'").replace("\n", " ")
    # nuevo jsonBody con expresión inline; type 'json' → LLM devuelve objeto,
    # n8n lo serializa correctamente como body JSON del HTTP request
    p["jsonBody"] = f"={{{{ $fromAI('body', '{desc}', 'json') }}}}"

    # quitar el placeholder body de placeholderDefinitions
    phs_wrap["values"] = [x for x in phs if x.get("name") != "body"]
    p["placeholderDefinitions"] = phs_wrap

    fixed.append(n["name"])

print(f"converted {len(fixed)} tools: {fixed}")

body = {
    "name": wf["name"], "nodes": wf["nodes"],
    "connections": wf["connections"],
    "settings": {"executionOrder": wf.get("settings", {}).get("executionOrder", "v1")},
}
code, resp = req("PUT", f"/workflows/{WID}", body)
print(f"PUT status={code}  updatedAt={resp.get('updatedAt') if isinstance(resp, dict) else resp[:300]}")
