from n8n_api import req
import re, sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

WF_ID = "kwoD2OHZeWSMTdTC"
# Tools that now use keypair body — only placeholders used in URL should remain.
BODY_TOOLS = {
    "update_contact", "update_account", "update_potential",
    "create_contact", "create_account", "create_potential",
    "create_event", "add_comment_to_potential",
    "get_contact", "get_account", "get_potential",
}

code, wf = req("GET", f"/workflows/{WF_ID}")

def url_placeholders(url: str):
    return set(re.findall(r"\{([A-Za-z_][A-Za-z0-9_]*)\}", url or ""))

changed = 0
for n in wf["nodes"]:
    if n["name"] not in BODY_TOOLS:
        continue
    p = n.get("parameters", {})
    url = p.get("url", "")
    used = url_placeholders(url)
    pd = p.get("placeholderDefinitions", {})
    vals = pd.get("values", []) if isinstance(pd, dict) else []
    kept = [v for v in vals if v.get("name") in used]
    removed = [v.get("name") for v in vals if v.get("name") not in used]
    if removed or len(kept) != len(vals):
        p["placeholderDefinitions"] = {"values": kept}
        print(f"  {n['name']}: kept={[v['name'] for v in kept]} removed={removed}")
        changed += 1

print(f"changed {changed} nodes")

ALLOWED = {"executionOrder","saveDataErrorExecution","saveDataSuccessExecution","saveExecutionProgress","saveManualExecutions","timezone","executionTimeout","errorWorkflow","callerPolicy"}
if "settings" in wf:
    wf["settings"] = {k:v for k,v in wf["settings"].items() if k in ALLOWED}

payload = {k: wf[k] for k in ("name","nodes","connections","settings") if k in wf}
code3, resp = req("PUT", f"/workflows/{WF_ID}", payload)
print("PUT", code3, str(resp)[:200])
