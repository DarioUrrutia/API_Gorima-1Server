"""Make `q` a REQUIRED parameter in search_contacts and drop f_account_id.

Previous attempt: we added f_account_id and made q optional (4th $fromAI arg=''),
so the LLM could list contacts of an azienda without keywords. Consequence:
the LangChain zod schema marked q as optional and the LLM started calling
search_contacts with query={} on plain name searches too, which returns the
first N contacts unrelated to what was asked.

Fix:
- q: drop the 4th arg → required in the tool schema.
- f_account_id: remove from query params (feature deferred; handled differently
  in the create_event flow at the prompt level).
- toolDescription updated accordingly.
"""
from n8n_api import req
import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

WF_ID = "kwoD2OHZeWSMTdTC"
code, d = req("GET", f"/workflows/{WF_ID}")

q_desc = (
    "Parole chiave di ricerca testuale (nome, cognome, email, telefono) "
    "con cui cercare contatti nel CRM. Devi sempre estrarle dal messaggio "
    "dell'utente (es: 'aggiorna contatto Luca Ferrari' -> q='Luca Ferrari'). "
    "Non includere mai verbi conversazionali tipo 'cerca', 'trova'."
)
# 3 args → REQUIRED. This is the whole point of this patch.
q_val = "={{ $fromAI('q', '" + q_desc.replace("'", "\\'") + "', 'string') }}"

for n in d["nodes"]:
    if n.get("name") != "search_contacts":
        continue
    p = n["parameters"]
    qv = p.setdefault("parametersQuery", {}).setdefault("values", [])
    # Strip previous q and f_account_id entries; keep limit/fields etc.
    qv = [v for v in qv if v.get("name") not in ("q", "f_account_id")]
    qv.insert(0, {
        "name": "q",
        "valueProvider": "fieldValue",
        "value": q_val,
    })
    p["parametersQuery"]["values"] = qv
    p["toolDescription"] = (
        "Cerca contatti (Contacts) nel CRM vTiger PER NOME/EMAIL/TELEFONO. "
        "Parametro `q` OBBLIGATORIO: estrai sempre dal messaggio utente il "
        "nome/cognome/azienda/email/telefono che serve a identificare il "
        "contatto (es: 'Luca Ferrari'). La risposta include l'id '12xNNNN'."
    )
    print(f"  patched search_contacts: q required, f_account_id removed ({len(qv)} query params)")

ALLOWED = {"executionOrder","saveDataErrorExecution","saveDataSuccessExecution","saveExecutionProgress","saveManualExecutions","timezone","executionTimeout","errorWorkflow","callerPolicy"}
if "settings" in d:
    d["settings"] = {k: v for k, v in d["settings"].items() if k in ALLOWED}

payload = {k: d[k] for k in ("name", "nodes", "connections", "settings") if k in d}
code3, resp = req("PUT", f"/workflows/{WF_ID}", payload)
print("PUT", code3, str(resp)[:200])
