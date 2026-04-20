"""Cambia el modelo del OpenAI Chat Model al indicado (default: gpt-4o)."""
from n8n_api import req
import sys, json

WID = "kwoD2OHZeWSMTdTC"
NEW_MODEL = sys.argv[1] if len(sys.argv) > 1 else "gpt-4o"

code, wf = req("GET", f"/workflows/{WID}")
changed = None
for n in wf["nodes"]:
    if n["type"] == "@n8n/n8n-nodes-langchain.lmChatOpenAi":
        old = json.dumps(n["parameters"].get("model", {}))
        n["parameters"]["model"] = {"__rl": True, "mode": "list", "value": NEW_MODEL}
        # compat: some versions use just the string
        n["parameters"]["options"] = n["parameters"].get("options", {})
        changed = (old, NEW_MODEL)
        break

if not changed:
    print("OpenAI Chat Model node not found"); sys.exit(1)

body = {
    "name": wf["name"], "nodes": wf["nodes"],
    "connections": wf["connections"],
    "settings": {"executionOrder": wf.get("settings", {}).get("executionOrder", "v1")},
}
code, resp = req("PUT", f"/workflows/{WID}", body)
print(f"old model: {changed[0]}")
print(f"new model: {changed[1]}")
print(f"PUT status={code}  updatedAt={resp.get('updatedAt') if isinstance(resp, dict) else resp[:300]}")
