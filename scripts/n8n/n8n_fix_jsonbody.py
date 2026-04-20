"""
Cambia jsonBody de '={body}' (expresión n8n) a '{body}' (sustitución de placeholder).
Con el '=' n8n intenta evaluarlo como expresión JS → falla al parsear como JSON.
Sin el '=' hace sustitución literal del placeholder `body`.
"""
from n8n_api import req

WID = "kwoD2OHZeWSMTdTC"

code, wf = req("GET", f"/workflows/{WID}")
fixed = []
for n in wf["nodes"]:
    if n.get("type") != "@n8n/n8n-nodes-langchain.toolHttpRequest":
        continue
    p = n.get("parameters", {})
    if p.get("jsonBody") == "={body}":
        p["jsonBody"] = "{body}"
        fixed.append(n["name"])

print(f"fixed {len(fixed)} tools: {fixed}")

body = {
    "name": wf["name"], "nodes": wf["nodes"],
    "connections": wf["connections"],
    "settings": {"executionOrder": wf.get("settings", {}).get("executionOrder", "v1")},
}
code, resp = req("PUT", f"/workflows/{WID}", body)
print(f"PUT status={code}  updatedAt={resp.get('updatedAt') if isinstance(resp, dict) else resp[:300]}")
