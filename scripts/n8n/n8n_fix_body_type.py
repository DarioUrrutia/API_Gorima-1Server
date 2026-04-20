"""
Recorre todos los nodos toolHttpRequest del workflow y cambia el placeholder `body`
de tipo `json` a `string`, para que n8n sustituya el JSON producido por el LLM
directamente en jsonBody sin intentar serializarlo él (lo que rompía con
'Could not replace placeholders in body').
"""
from n8n_api import req

WID = "kwoD2OHZeWSMTdTC"

EXTRA_HINT = (
    " IMPORTANTE: fornisci il body come STRINGA di JSON VALIDO, "
    "con virgolette doppie attorno a chiavi e valori testuali. "
    "Esempio corretto: {\"title\":\"Proprietario\",\"phone\":\"+39012345\"}"
)

code, wf = req("GET", f"/workflows/{WID}")
fixed = []

for n in wf["nodes"]:
    if n.get("type") != "@n8n/n8n-nodes-langchain.toolHttpRequest":
        continue
    p = n.get("parameters", {})
    phs = (p.get("placeholderDefinitions") or {}).get("values", [])
    changed = False
    for item in phs:
        if item.get("name") == "body" and item.get("type") == "json":
            item["type"] = "string"
            # añade hint si no lo tiene ya
            desc = item.get("description", "")
            if "JSON VALIDO" not in desc:
                item["description"] = desc + EXTRA_HINT
            changed = True
    if changed:
        # asegura jsonBody = "={body}"
        p["jsonBody"] = "={body}"
        fixed.append(n["name"])

print(f"fixed {len(fixed)} tools: {fixed}")

body = {
    "name": wf["name"], "nodes": wf["nodes"],
    "connections": wf["connections"],
    "settings": {"executionOrder": wf.get("settings", {}).get("executionOrder", "v1")},
}
code, resp = req("PUT", f"/workflows/{WID}", body)
print(f"PUT status={code}  updatedAt={resp.get('updatedAt') if isinstance(resp, dict) else resp[:300]}")
