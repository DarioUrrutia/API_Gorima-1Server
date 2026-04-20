from n8n_api import req
import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

code, data = req("GET", "/workflows")
wf = [w for w in data["data"] if w["name"] != "My workflow"][0]
code2, d2 = req("GET", f"/workflows/{wf['id']}")

# Contact fields that are commonly updated; LLM passes only what user asks for.
CONTACT_FIELDS = [
    ("firstname", "Nome"),
    ("lastname", "Cognome"),
    ("title", "Qualifica / titolo lavorativo (es: Proprietario, Acquisto, Responsabile Tecnico)"),
    ("email", "Email"),
    ("phone", "Telefono principale"),
    ("mobile", "Cellulare"),
    ("account_id", "Id azienda (11xNNNN)"),
    ("description", "Note / descrizione"),
]
ACCOUNT_FIELDS = [
    ("accountname", "Nome dell'azienda"),
    ("industry", "Settore / industria"),
    ("phone", "Telefono"),
    ("email1", "Email principale"),
    ("website", "Sito web"),
    ("description", "Note"),
]
OPP_FIELDS = [
    ("potentialname", "Nome opportunita'"),
    ("related_to", "Id azienda (11xNNNN)"),
    ("sales_stage", "Fase vendita (Qualification, Needs Analysis, Value Proposition, Id. Decision Makers, Perception Analysis, Proposal/Price Quote, Negotiation/Review, Closed Won, Closed Lost)"),
    ("amount", "Importo (numero)"),
    ("closingdate", "Data chiusura (YYYY-MM-DD)"),
    ("description", "Descrizione / note"),
]
EVENT_FIELDS = [
    ("subject", "Oggetto dell'evento"),
    ("date_start", "Data inizio (YYYY-MM-DD)"),
    ("time_start", "Ora inizio (HH:MM:SS)"),
    ("due_date", "Data fine (YYYY-MM-DD)"),
    ("time_end", "Ora fine (HH:MM:SS)"),
    ("parent_id", "Id azienda / contatto / opportunita' collegata"),
    ("description", "Note"),
]
COMMENT_FIELDS = [
    ("commentcontent", "Testo del commento"),
    ("related_to", "Id record collegato (11xNNNN, 12xNNNN, 13xNNNN)"),
]

def bp(fields):
    # Wrap with `|| undefined` so empty-string fields are dropped from the HTTP body.
    # $fromAI signature: (key, description, type, defaultValue) — providing a default makes it optional.
    vals = []
    for key, desc in fields:
        expr = "={{ $fromAI('" + key + "', '" + desc.replace("'","\\'") + "', 'string', '') || undefined }}"
        vals.append({"name": key, "value": expr})
    return {"values": vals}

TARGETS = {
    "update_contact":  CONTACT_FIELDS,
    "update_account":  ACCOUNT_FIELDS,
    "update_opportunity": OPP_FIELDS,
    "create_contact":  CONTACT_FIELDS,
    "create_account":  ACCOUNT_FIELDS,
    "create_opportunity": OPP_FIELDS,
    "create_event":    EVENT_FIELDS,
    "add_comment":     COMMENT_FIELDS,
}

for n in d2["nodes"]:
    nm = n.get("name")
    if nm not in TARGETS:
        continue
    p = n["parameters"]
    p["specifyBody"] = "keypair"
    p.pop("jsonBody", None)
    p.pop("body", None)
    p["parametersBody"] = bp(TARGETS[nm])
    # Note: Content-Type json is fine — n8n serializes keypair to JSON object when header says json
    print(f"  patched {nm} with {len(TARGETS[nm])} fields")

ALLOWED = {"executionOrder","saveDataErrorExecution","saveDataSuccessExecution","saveExecutionProgress","saveManualExecutions","timezone","executionTimeout","errorWorkflow","callerPolicy"}
if "settings" in d2:
    d2["settings"] = {k:v for k,v in d2["settings"].items() if k in ALLOWED}

payload = {k: d2[k] for k in ("name","nodes","connections","settings") if k in d2}
code3, resp = req("PUT", f"/workflows/{wf['id']}", payload)
print("PUT", code3, str(resp)[:300])
