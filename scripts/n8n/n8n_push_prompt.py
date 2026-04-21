from n8n_api import req
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

WF_ID = "kwoD2OHZeWSMTdTC"
SRC = r"c:\Users\JeanUrrutia\VPS - Gorima 1mo\scripts\n8n\_sys_prompt_current.txt"

with open(SRC, encoding='utf-8') as f:
    new_prompt = f.read()

code, d = req("GET", f"/workflows/{WF_ID}")
for n in d["nodes"]:
    if n.get("type", "").endswith("agent"):
        n["parameters"].setdefault("options", {})["systemMessage"] = new_prompt
        print(f"  patched agent system prompt ({len(new_prompt)} chars)")

ALLOWED = {"executionOrder","saveDataErrorExecution","saveDataSuccessExecution","saveExecutionProgress","saveManualExecutions","timezone","executionTimeout","errorWorkflow","callerPolicy"}
if "settings" in d:
    d["settings"] = {k:v for k,v in d["settings"].items() if k in ALLOWED}

payload = {k: d[k] for k in ("name","nodes","connections","settings") if k in d}
code3, resp = req("PUT", f"/workflows/{WF_ID}", payload)
print("PUT", code3, str(resp)[:200])
