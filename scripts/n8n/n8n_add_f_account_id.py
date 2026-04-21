from n8n_api import req
import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

WF_ID = "kwoD2OHZeWSMTdTC"
code, d = req("GET", f"/workflows/{WF_ID}")

desc = (
    "Id azienda collegata (formato 11xNNNN). Passa questo parametro SOLO quando "
    "stai cercando contatti di una azienda specifica (es: per offrire i contatti "
    "disponibili prima di creare un evento). In caso contrario lascia vuoto."
)
f_account_val = "={{ $fromAI('f_account_id', '" + desc.replace("'", "\\'") + "', 'string', '') || undefined }}"

for n in d["nodes"]:
    if n.get("name") != "search_contacts":
        continue
    p = n["parameters"]
    qv = p.setdefault("parametersQuery", {}).setdefault("values", [])
    qv = [v for v in qv if v.get("name") not in ("f_account_id", "q")]
    # q diventa opzionale: quando l'agente filtra per azienda (f_account_id) puo'
    # non avere keyword testuali. Il wrapper accetta WHERE con solo f_*.
    q_desc = (
        "Parole chiave di ricerca testuale (nome, cognome, email, telefono). "
        "Opzionale: se stai cercando TUTTI i contatti di una azienda specifica, "
        "lascia vuoto e passa solo f_account_id."
    )
    q_val = "={{ $fromAI('q', '" + q_desc.replace("'", "\\'") + "', 'string', '') || undefined }}"
    qv.insert(0, {
        "name": "q",
        "valueProvider": "fieldValue",
        "value": q_val,
    })
    qv.append({
        "name": "f_account_id",
        "valueProvider": "fieldValue",
        "value": f_account_val,
    })
    p["parametersQuery"]["values"] = qv
    p["toolDescription"] = (
        "Cerca contatti (Contacts) nel CRM vTiger. Passa `q` con le keywords "
        "(nome, cognome, email, telefono). Se vuoi SOLO contatti di una azienda "
        "specifica, passa `f_account_id` con l'id azienda (11xNNNN) e lascia `q` "
        "vuoto. Puoi anche combinare i due. La risposta include l'id '12xNNNN'."
    )
    print(f"  patched search_contacts (query params: {len(qv)})")

ALLOWED = {"executionOrder","saveDataErrorExecution","saveDataSuccessExecution","saveExecutionProgress","saveManualExecutions","timezone","executionTimeout","errorWorkflow","callerPolicy"}
if "settings" in d:
    d["settings"] = {k:v for k,v in d["settings"].items() if k in ALLOWED}

payload = {k: d[k] for k in ("name","nodes","connections","settings") if k in d}
code3, resp = req("PUT", f"/workflows/{WF_ID}", payload)
print("PUT", code3, str(resp)[:300])
