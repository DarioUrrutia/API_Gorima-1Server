from n8n_api import req
import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

code, data = req("GET", "/workflows")
wf = [w for w in data["data"] if w["name"] != "My workflow"][0]
code2, d2 = req("GET", f"/workflows/{wf['id']}")

TARGETS = {
    "update_contact":  ("contact_id", "Id del contatto da aggiornare (12xNNNN)",
        "Oggetto JSON (stringa) con SOLO i campi da aggiornare. Esempio: {\"title\":\"Acquisto\",\"phone\":\"+390123\"}. DEVE essere JSON valido."),
    "update_account":  ("account_id", "Id dell'azienda da aggiornare (11xNNNN)",
        "Oggetto JSON (stringa) con SOLO i campi da aggiornare. Esempio: {\"industry\":\"Retail\"}."),
    "update_opportunity": ("opportunity_id", "Id dell'opportunita' (13xNNNN)",
        "Oggetto JSON (stringa) con SOLO i campi da aggiornare. Esempio: {\"sales_stage\":\"Qualification\",\"amount\":\"5000\"}."),
    "create_contact":  (None, None,
        "Oggetto JSON (stringa) del nuovo contatto. Esempio: {\"lastname\":\"Rossi\",\"firstname\":\"Mario\",\"account_id\":\"11x324\"}."),
    "create_account":  (None, None,
        "Oggetto JSON (stringa) della nuova azienda. Esempio: {\"accountname\":\"ACME Srl\",\"industry\":\"Retail\"}."),
    "create_opportunity": (None, None,
        "Oggetto JSON (stringa) della nuova opportunita'. Esempio: {\"potentialname\":\"SS999\",\"related_to\":\"11x324\",\"sales_stage\":\"Qualification\",\"closingdate\":\"2026-12-31\"}."),
    "create_event":    (None, None,
        "Oggetto JSON (stringa). Esempio: {\"subject\":\"Sopralluogo\",\"date_start\":\"2026-05-01\",\"time_start\":\"10:00:00\",\"due_date\":\"2026-05-01\",\"time_end\":\"11:00:00\",\"parent_id\":\"11x324\"}."),
    "add_comment":     (None, None,
        "Oggetto JSON (stringa). Esempio: {\"commentcontent\":\"Chiamata fatta\",\"related_to\":\"13x2480\"}."),
}

for n in d2["nodes"]:
    nm = n.get("name")
    if nm not in TARGETS:
        continue
    id_name, id_desc, body_desc = TARGETS[nm]
    p = n["parameters"]

    # switch body to RAW STRING mode with {body} placeholder
    p["specifyBody"] = "string"
    p["body"] = "={{ $fromAI('body', '" + body_desc.replace("'", "\\'") + "', 'string') }}"
    # drop jsonBody if present
    p.pop("jsonBody", None)

    # placeholderDefinitions: keep id placeholder (if any); body is via $fromAI in expression
    pd_values = []
    if id_name:
        pd_values.append({"name": id_name, "description": id_desc, "type": "string"})
    p["placeholderDefinitions"] = {"values": pd_values}
    print(f"  patched {nm}")

ALLOWED = {"executionOrder","saveDataErrorExecution","saveDataSuccessExecution","saveExecutionProgress","saveManualExecutions","timezone","executionTimeout","errorWorkflow","callerPolicy"}
if "settings" in d2:
    d2["settings"] = {k:v for k,v in d2["settings"].items() if k in ALLOWED}

payload = {k: d2[k] for k in ("name","nodes","connections","settings") if k in d2}
code3, resp = req("PUT", f"/workflows/{wf['id']}", payload)
print("PUT", code3, str(resp)[:300])
