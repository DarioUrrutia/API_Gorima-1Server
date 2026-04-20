"""Imprime la estructura de cada tool para auditar consistencia."""
from n8n_api import req
import json

WID = "kwoD2OHZeWSMTdTC"
code, wf = req("GET", f"/workflows/{WID}")

for n in wf["nodes"]:
    if n.get("type") != "@n8n/n8n-nodes-langchain.toolHttpRequest":
        continue
    p = n.get("parameters", {})
    print(f"\n### {n['name']}  ({p.get('method')}  {p.get('url')}) ###")
    print(f"  jsonBody     : {p.get('jsonBody')!r}")
    print(f"  specifyBody  : {p.get('specifyBody')!r}")
    print(f"  sendBody     : {p.get('sendBody')}")
    print(f"  sendQuery    : {p.get('sendQuery')}")
    if p.get("parametersQuery"):
        for q in p["parametersQuery"]["values"]:
            print(f"    query: {q}")
    phs = (p.get("placeholderDefinitions") or {}).get("values", [])
    for item in phs:
        d = item.get("description", "")[:70]
        print(f"    placeholder {item.get('name')}  type={item.get('type')}  desc={d}")
