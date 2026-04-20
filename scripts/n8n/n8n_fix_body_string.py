"""
Cambia $fromAI('body', ..., 'json') a type='string' para que el LLM devuelva
directamente una cadena con el JSON formateado, que n8n inserta tal cual en el
body del request HTTP. Con type='json', n8n serializaba el objeto como
[object Object] rompiendo el body.
"""
import re
from n8n_api import req

WID = "kwoD2OHZeWSMTdTC"

code, wf = req("GET", f"/workflows/{WID}")
fixed = []

PATTERN = re.compile(r"\$fromAI\(\s*'body'\s*,\s*'(.*)'\s*,\s*'json'\s*\)", re.DOTALL)

for n in wf["nodes"]:
    if n.get("type") != "@n8n/n8n-nodes-langchain.toolHttpRequest":
        continue
    p = n.get("parameters", {})
    jb = p.get("jsonBody") or ""
    if "$fromAI('body'" in jb and "'json'" in jb:
        # reemplaza type 'json' → 'string' y añade instrucción explícita
        new = PATTERN.sub(
            lambda m: f"$fromAI('body', '{m.group(1)} [TORNA UNA STRINGA JSON VALIDA, NON UN OGGETTO]', 'string')",
            jb,
        )
        if new != jb:
            p["jsonBody"] = new
            fixed.append(n["name"])

print(f"converted {len(fixed)} tools: {fixed}")

body = {
    "name": wf["name"], "nodes": wf["nodes"],
    "connections": wf["connections"],
    "settings": {"executionOrder": wf.get("settings", {}).get("executionOrder", "v1")},
}
code, resp = req("PUT", f"/workflows/{WID}", body)
print(f"PUT status={code}  updatedAt={resp.get('updatedAt') if isinstance(resp, dict) else resp[:300]}")
