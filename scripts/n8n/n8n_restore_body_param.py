from n8n_api import req
import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add `body` back to placeholderDefinitions for every update_* / create_* / add_comment tool
# and keep jsonBody as a plain {body} template (no $fromAI in the body) — n8n will substitute
# the string the LLM provides in the `body` arg, which is the simplest contract.

code, data = req("GET", "/workflows")
wf = next(w for w in data["data"] if w["name"] != "My workflow")  # single real one
code2, d2 = req("GET", f"/workflows/{wf['id']}")

TARGETS = {
    "update_contact":  "Oggetto JSON (come STRINGA) con i campi da aggiornare. Es: {\"title\":\"Acquisto\",\"phone\":\"+390123\"}",
    "update_account":  "Oggetto JSON (come STRINGA) con i campi da aggiornare. Es: {\"industry\":\"Retail\",\"phone\":\"+390123\"}",
    "update_opportunity": "Oggetto JSON (come STRINGA) con i campi da aggiornare. Es: {\"sales_stage\":\"Qualification\",\"amount\":\"5000\"}",
    "create_contact":  "Oggetto JSON (come STRINGA) con i campi del nuovo contatto. Es: {\"lastname\":\"Rossi\",\"firstname\":\"Mario\",\"account_id\":\"11x324\"}",
    "create_account":  "Oggetto JSON (come STRINGA) con i campi della nuova azienda. Es: {\"accountname\":\"ACME Srl\",\"industry\":\"Retail\"}",
    "create_opportunity": "Oggetto JSON (come STRINGA) con i campi della nuova oportunit\u00e0. Es: {\"potentialname\":\"SS999\",\"related_to\":\"11x324\",\"sales_stage\":\"Qualification\",\"closingdate\":\"2026-12-31\"}",
    "create_event":    "Oggetto JSON (come STRINGA). Es: {\"subject\":\"Sopralluogo\",\"date_start\":\"2026-05-01\",\"time_start\":\"10:00:00\",\"due_date\":\"2026-05-01\",\"time_end\":\"11:00:00\",\"parent_id\":\"11x324\"}",
    "add_comment":     "Oggetto JSON (come STRINGA). Es: {\"commentcontent\":\"Chiamata fatta, cliente interessato\",\"related_to\":\"13x2480\"}",
}

changed = 0
for n in d2["nodes"]:
    nm = n.get("name")
    if nm not in TARGETS:
        continue
    p = n["parameters"]
    desc = TARGETS[nm]
    # jsonBody: use placeholder substitution, not $fromAI
    p["jsonBody"] = "={{ $fromAI('body', '" + desc.replace("'", "\\'") + "', 'string') }}"
    # ensure 'body' is NOT in placeholderDefinitions (keep only contact/account/etc ids)
    pd = p.get("placeholderDefinitions", {}).get("values", [])
    p["placeholderDefinitions"] = {"values": [v for v in pd if v["name"] != "body"]}
    changed += 1
    print(f"  patched {nm}")

print(f"patched {changed}")

# update the AI Agent systemMessage to HEAVILY emphasize body is mandatory
agent = next(n for n in d2["nodes"] if n.get("type") == "@n8n/n8n-nodes-langchain.agent")
sm = agent["parameters"].get("options", {}).get("systemMessage", "")
banner = (
    "\n\n"
    "### ⛔ REGOLA CRITICA — TUTTI I TOOL update_* / create_* / add_comment\n"
    "Questi tool RICHIEDONO SEMPRE il parametro `body` (stringa JSON).\n"
    "MAI chiamarli senza `body`. Se non hai i dati per comporre il JSON, "
    "PRIMA chiedi all'utente cosa deve contenere, POI chiama il tool.\n"
    "Formato del `body`: stringa JSON con SOLO i campi da aggiornare/creare.\n"
    "Esempio update_contact: body = '{\"title\":\"Acquisto\"}'\n"
    "Esempio create_account: body = '{\"accountname\":\"ACME Srl\"}'\n"
)
if "REGOLA CRITICA — TUTTI I TOOL" not in sm:
    agent["parameters"].setdefault("options", {})["systemMessage"] = sm + banner
    print("agent systemMessage updated")

# PUT
ALLOWED_SETTINGS = {"executionOrder","saveDataErrorExecution","saveDataSuccessExecution","saveExecutionProgress","saveManualExecutions","timezone","executionTimeout","errorWorkflow","callerPolicy"}
if "settings" in d2:
    d2["settings"] = {k:v for k,v in d2["settings"].items() if k in ALLOWED_SETTINGS}
payload = {k: d2[k] for k in ("name","nodes","connections","settings") if k in d2}
code3, resp = req("PUT", f"/workflows/{wf['id']}", payload)
print("PUT", code3)
if code3 != 200:
    print(str(resp)[:500])
