from n8n_api import req
import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

WF_ID = "kwoD2OHZeWSMTdTC"
code2, d2 = req("GET", f"/workflows/{WF_ID}")

# Contact fields that are commonly updated; LLM passes only what user asks for.
CONTACT_FIELDS = [
    ("firstname", "Nome"),
    ("lastname", "Cognome (obbligatorio in creazione)"),
    ("title", "Qualifica / titolo lavorativo (es: Proprietario, Acquisto, Responsabile Tecnico)"),
    ("department", "Dipartimento / reparto"),
    ("account_id", "Id azienda collegata (formato 11xNNNN)"),
    ("assigned_user_id", "Id dell'utente assegnato (formato 19xN; obbligatorio in creazione)"),
    ("phone", "Telefono ufficio"),
    ("mobile", "Cellulare"),
    ("email", "Email principale"),
]
ACCOUNT_FIELDS = [
    ("accountname", "Nome Azienda (obbligatorio in creazione)"),
    ("cf_1103", "Regione"),
    ("cf_1111", "Provincia"),
    ("cf_1105", "Citta"),
    ("cf_1033", "Indirizzo (ufficio / sede)"),
    ("cf_1061", "Coordinate GPS (ufficio / sede)"),
    ("email1", "Email Principale"),
    ("phone", "Telefono Principale"),
    ("website", "Sito Web"),
    ("cf_1107", "P.IVA / Partita IVA"),
    ("assigned_user_id", "Id dell'utente assegnato (formato 19xN; obbligatorio in creazione)"),
]
OPP_FIELDS = [
    ("potentialname", "Nome opportunita'"),
    ("related_to", "Id azienda collegata (formato 11xNNNN)"),
    ("assigned_user_id", "Id dell'utente assegnato (formato 19xN; obbligatorio in creazione)"),
    ("closingdate", "Data chiusura prevista (YYYY-MM-DD; obbligatorio in creazione; se l'utente non la fornisce usa oggi + 90 giorni)"),
    ("description", "Descrizione"),
    ("sales_stage", "Stadio di vendita. Valori esatti accettati: Prospecting, Lavoro in Corso, Closed Won, Closed Lost. (Etichette UI IT: In Prospettiva=Prospecting, Chiuso VINTO=Closed Won, Chiuso PERSO=Closed Lost — NON passare le etichette UI.)"),
    ("cf_969", "Regione — SOLO una di queste 5 in maiuscolo: BASILICATA, PUGLIA, CALABRIA, SICILIA, CAMPANIA. Altre regioni italiane non sono ammesse."),
    ("cf_919", "Nome Strada"),
    ("cf_909", "Importo Totale (numero)"),
    ("cf_907", "Importo OG3 (numero)"),
    ("cf_921", "Data consegna o aggiudicazione (YYYY-MM-DD)"),
    ("cf_897", "Aggiudicatario"),
    ("cf_1009", "Stazione Appaltante"),
    ("cf_891", "CIG"),
    ("cf_859", "CUP"),
    ("cf_877", "Coordinate GPS"),
]
EVENT_FIELDS = [
    ("subject", "Oggetto dell'evento"),
    ("assigned_user_id", "Id utente assegnato (formato 19xN; default 19x5 Jean)"),
    ("date_start", "Data inizio (YYYY-MM-DD)"),
    ("time_start", "Ora inizio (HH:MM:SS)"),
    ("due_date", "Data fine (YYYY-MM-DD). Se non fornita dall'utente, copia date_start."),
    ("time_end", "Ora fine (HH:MM:SS). Se non fornita dall'utente, calcola come time_start + 1 ora."),
    ("duration_hours", "Durata in ore (intero; default 1)"),
    ("eventstatus", "Stato evento (Planned, Held, Not Held). Se l'evento e' gia' avvenuto usa Held."),
    ("activitytype", "Tipo attivita' (Call, Meeting, Mobile Call)"),
    ("description", "Descrizione / note"),
    ("contact_id", "Id contatto collegato (formato 12xNNNN)"),
    ("parent_id", "Id record collegato, tipicamente azienda (formato 11xNNNN). Puo' essere anche 12xNNNN o 13xNNNN."),
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
    "update_contact":    CONTACT_FIELDS,
    "update_account":    ACCOUNT_FIELDS,
    "update_potential":  OPP_FIELDS,
    "create_contact":    CONTACT_FIELDS,
    "create_account":    ACCOUNT_FIELDS,
    "create_potential":  OPP_FIELDS,
    "create_event":      EVENT_FIELDS,
    "add_comment_to_potential": COMMENT_FIELDS,
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
code3, resp = req("PUT", f"/workflows/{WF_ID}", payload)
print("PUT", code3, str(resp)[:300])
