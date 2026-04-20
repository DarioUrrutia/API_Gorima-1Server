from n8n_api import req
import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

code, data = req("GET", "/workflows")
wf = [w for w in data["data"] if w["name"] != "My workflow"][0]
code2, d2 = req("GET", f"/workflows/{wf['id']}")

TARGETS = {
    "update_contact":  ("Contacts", "contact_id", "12xNNNN",
        "Aggiorna i campi di un contatto. PARAMETRI OBBLIGATORI: `contact_id` (12xNNNN) e `body` (stringa JSON con i campi). Esempio body: {\"title\":\"Acquisto\"}"),
    "update_account":  ("Accounts", "account_id", "11xNNNN",
        "Aggiorna i campi di un'azienda. PARAMETRI OBBLIGATORI: `account_id` (11xNNNN) e `body` (stringa JSON). Esempio body: {\"industry\":\"Retail\"}"),
    "update_opportunity": ("Potentials", "opportunity_id", "13xNNNN",
        "Aggiorna un'opportunita'. PARAMETRI OBBLIGATORI: `opportunity_id` (13xNNNN) e `body` (stringa JSON). Esempio body: {\"sales_stage\":\"Qualification\"}"),
    "create_contact":  ("Contacts", None, None,
        "Crea un nuovo contatto. PARAMETRO OBBLIGATORIO: `body` (stringa JSON). Esempio: {\"lastname\":\"Rossi\",\"account_id\":\"11x324\"}"),
    "create_account":  ("Accounts", None, None,
        "Crea una nuova azienda. PARAMETRO OBBLIGATORIO: `body` (stringa JSON). Esempio: {\"accountname\":\"ACME Srl\"}"),
    "create_opportunity": ("Potentials", None, None,
        "Crea una nuova opportunita'. PARAMETRO OBBLIGATORIO: `body` (stringa JSON). Esempio: {\"potentialname\":\"SS999\",\"related_to\":\"11x324\",\"sales_stage\":\"Qualification\",\"closingdate\":\"2026-12-31\"}"),
    "create_event":    ("Events", None, None,
        "Crea un evento. PARAMETRO OBBLIGATORIO: `body` (stringa JSON)."),
    "add_comment":     ("ModComments", None, None,
        "Aggiunge un commento. PARAMETRO OBBLIGATORIO: `body` (stringa JSON con commentcontent e related_to)."),
}

for n in d2["nodes"]:
    nm = n.get("name")
    if nm not in TARGETS:
        continue
    mod, id_name, id_fmt, desc = TARGETS[nm]
    p = n["parameters"]

    p["toolDescription"] = desc
    p["specifyBody"] = "json"
    p.pop("body", None)
    p["jsonBody"] = "={{ $fromAI('body', 'Stringa JSON VALIDA con i campi. OBBLIGATORIO — se non lo passi l\\'operazione fallisce. Esempio: {\"title\":\"Acquisto\"}', 'string') }}"
    pd = []
    if id_name:
        pd.append({"name": id_name, "description": f"Id {id_fmt}", "type": "string"})
    p["placeholderDefinitions"] = {"values": pd}

    # bump typeVersion to try newer behavior
    n["typeVersion"] = 1.2
    print(f"  patched {nm}")

ALLOWED = {"executionOrder","saveDataErrorExecution","saveDataSuccessExecution","saveExecutionProgress","saveManualExecutions","timezone","executionTimeout","errorWorkflow","callerPolicy"}
if "settings" in d2:
    d2["settings"] = {k:v for k,v in d2["settings"].items() if k in ALLOWED}

payload = {k: d2[k] for k in ("name","nodes","connections","settings") if k in d2}
code3, resp = req("PUT", f"/workflows/{wf['id']}", payload)
print("PUT", code3, str(resp)[:300])
