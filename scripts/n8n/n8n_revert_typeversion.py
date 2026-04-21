from n8n_api import req
import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

code, data = req("GET", "/workflows")
wf = [w for w in data["data"] if w["name"] != "My workflow"][0]
code2, d2 = req("GET", f"/workflows/{wf['id']}")

patched = 0
for n in d2["nodes"]:
    if n.get("type") == "@n8n/n8n-nodes-langchain.toolHttpRequest" and n.get("typeVersion") != 1.1:
        n["typeVersion"] = 1.1
        patched += 1
        print(f"  reverted {n.get('name')} -> 1.1")

print(f"patched {patched} tool nodes")

ALLOWED = {"executionOrder","saveDataErrorExecution","saveDataSuccessExecution","saveExecutionProgress","saveManualExecutions","timezone","executionTimeout","errorWorkflow","callerPolicy"}
if "settings" in d2:
    d2["settings"] = {k:v for k,v in d2["settings"].items() if k in ALLOWED}

payload = {k: d2[k] for k in ("name","nodes","connections","settings") if k in d2}
code3, resp = req("PUT", f"/workflows/{wf['id']}", payload)
print("PUT", code3, str(resp)[:200])
