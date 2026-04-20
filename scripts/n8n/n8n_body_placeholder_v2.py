from n8n_api import req
import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

code, data = req("GET", "/workflows")
wf = [w for w in data["data"] if w["name"] != "My workflow"][0]
code2, d2 = req("GET", f"/workflows/{wf['id']}")

# For each tool: use placeholder {body} in raw string body,
# and declare body in placeholderDefinitions so LLM sees it as a required param.
TARGETS = {
    "update_contact":  [
        {"name":"contact_id","description":"Id contatto (12xNNNN)","type":"string"},
        {"name":"body","description":"Stringa JSON con SOLO i campi da aggiornare. Es: {\"title\":\"Acquisto\",\"phone\":\"+390123\"}","type":"string"},
    ],
    "update_account":  [
        {"name":"account_id","description":"Id azienda (11xNNNN)","type":"string"},
        {"name":"body","description":"Stringa JSON con SOLO i campi da aggiornare. Es: {\"industry\":\"Retail\"}","type":"string"},
    ],
    "update_opportunity": [
        {"name":"opportunity_id","description":"Id opportunita' (13xNNNN)","type":"string"},
        {"name":"body","description":"Stringa JSON con SOLO i campi da aggiornare. Es: {\"sales_stage\":\"Qualification\",\"amount\":\"5000\"}","type":"string"},
    ],
    "create_contact":  [
        {"name":"body","description":"Stringa JSON del nuovo contatto. Es: {\"lastname\":\"Rossi\",\"firstname\":\"Mario\",\"account_id\":\"11x324\"}","type":"string"},
    ],
    "create_account":  [
        {"name":"body","description":"Stringa JSON della nuova azienda. Es: {\"accountname\":\"ACME Srl\",\"industry\":\"Retail\"}","type":"string"},
    ],
    "create_opportunity": [
        {"name":"body","description":"Stringa JSON della nuova opportunita'. Es: {\"potentialname\":\"SS999\",\"related_to\":\"11x324\",\"sales_stage\":\"Qualification\",\"closingdate\":\"2026-12-31\"}","type":"string"},
    ],
    "create_event":    [
        {"name":"body","description":"Stringa JSON. Es: {\"subject\":\"Sopralluogo\",\"date_start\":\"2026-05-01\",\"time_start\":\"10:00:00\",\"due_date\":\"2026-05-01\",\"time_end\":\"11:00:00\",\"parent_id\":\"11x324\"}","type":"string"},
    ],
    "add_comment":     [
        {"name":"body","description":"Stringa JSON. Es: {\"commentcontent\":\"Chiamata fatta\",\"related_to\":\"13x2480\"}","type":"string"},
    ],
}

for n in d2["nodes"]:
    nm = n.get("name")
    if nm not in TARGETS:
        continue
    p = n["parameters"]
    p["specifyBody"] = "string"
    p["body"] = "{body}"
    p.pop("jsonBody", None)
    p["placeholderDefinitions"] = {"values": TARGETS[nm]}
    print(f"  patched {nm}")

ALLOWED = {"executionOrder","saveDataErrorExecution","saveDataSuccessExecution","saveExecutionProgress","saveManualExecutions","timezone","executionTimeout","errorWorkflow","callerPolicy"}
if "settings" in d2:
    d2["settings"] = {k:v for k,v in d2["settings"].items() if k in ALLOWED}

payload = {k: d2[k] for k in ("name","nodes","connections","settings") if k in d2}
code3, resp = req("PUT", f"/workflows/{wf['id']}", payload)
print("PUT", code3, str(resp)[:300])
