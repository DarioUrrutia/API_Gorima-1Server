"""
Limpia el sufijo genérico con ejemplo de contact fields que quedó pegado
a cada body description. Lo reemplaza por un recordatorio corto de sintaxis.
"""
from n8n_api import req

WID = "kwoD2OHZeWSMTdTC"

BAD_SUFFIX = (
    " IMPORTANTE: fornisci il body come STRINGA di JSON VALIDO, "
    "con virgolette doppie attorno a chiavi e valori testuali. "
    "Esempio corretto: {\"title\":\"Proprietario\",\"phone\":\"+39012345\"}"
)

GOOD_SUFFIX = (
    " ⚠ Il body deve essere una STRINGA di JSON VALIDO: tutte le chiavi e "
    "i valori testuali tra virgolette doppie, numeri e booleani senza virgolette."
)

code, wf = req("GET", f"/workflows/{WID}")
fixed = []
for n in wf["nodes"]:
    if n.get("type") != "@n8n/n8n-nodes-langchain.toolHttpRequest":
        continue
    phs = (n["parameters"].get("placeholderDefinitions") or {}).get("values", [])
    for item in phs:
        if item.get("name") != "body": continue
        d = item.get("description", "")
        if BAD_SUFFIX in d:
            item["description"] = d.replace(BAD_SUFFIX, GOOD_SUFFIX)
            fixed.append(n["name"])

print(f"cleaned {len(fixed)} tools: {fixed}")

body = {
    "name": wf["name"], "nodes": wf["nodes"],
    "connections": wf["connections"],
    "settings": {"executionOrder": wf.get("settings", {}).get("executionOrder", "v1")},
}
code, resp = req("PUT", f"/workflows/{WID}", body)
print(f"PUT status={code}  updatedAt={resp.get('updatedAt') if isinstance(resp, dict) else resp[:300]}")
