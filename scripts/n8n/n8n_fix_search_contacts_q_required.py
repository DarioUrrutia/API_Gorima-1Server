"""Make `q` a REQUIRED parameter in search_contacts using the SIMPLE n8n form.

Why the simple form: search_potentials and search_accounts both use
`{"name": "q"}` with no valueProvider/value. This is the native
toolHttpRequest convention — n8n auto-derives an AI-fillable, REQUIRED
parameter from it. That form works in practice.

The earlier $fromAI-based form with explicit descriptions (even 3-arg,
"should be required") did NOT force the LLM to fill q in query params;
the tool kept being called with `query: {}`. Switching to the native
form aligns search_contacts with the two sibling tools that work.

The prompt/tool-description still carries the name-extraction guidance
(e.g. "aggiorna Luca Ferrari" -> q='Luca Ferrari').
"""
from n8n_api import req
import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

WF_ID = "kwoD2OHZeWSMTdTC"
code, d = req("GET", f"/workflows/{WF_ID}")

for n in d["nodes"]:
    if n.get("name") != "search_contacts":
        continue
    p = n["parameters"]
    qv = p.setdefault("parametersQuery", {}).setdefault("values", [])
    # Strip previous q entries (and any leftover f_account_id)
    qv = [v for v in qv if v.get("name") not in ("q", "f_account_id")]
    # Native AI-fillable form: just a name, no value/valueProvider → required.
    qv.insert(0, {"name": "q"})
    p["parametersQuery"]["values"] = qv
    p["toolDescription"] = (
        "Cerca contatti (Contacts) nel CRM vTiger per parole chiave. "
        "Il parametro `q` deve contenere nome, cognome, email o telefono "
        "del contatto cercato. Estrai sempre queste keywords dal messaggio "
        "utente (es: utente 'aggiorna contatto Luca Ferrari' -> q='Luca Ferrari'; "
        "utente 'trova mario.rossi@gmail.com' -> q='mario.rossi@gmail.com'). "
        "NON includere verbi conversazionali tipo 'cerca', 'trova', 'aggiorna'. "
        "La risposta include l'id nel formato '12xNNNN'."
    )
    print(f"  patched search_contacts: q as native required AI param ({len(qv)} query params)")

ALLOWED = {"executionOrder","saveDataErrorExecution","saveDataSuccessExecution","saveExecutionProgress","saveManualExecutions","timezone","executionTimeout","errorWorkflow","callerPolicy"}
if "settings" in d:
    d["settings"] = {k: v for k, v in d["settings"].items() if k in ALLOWED}

payload = {k: d[k] for k in ("name", "nodes", "connections", "settings") if k in d}
code3, resp = req("PUT", f"/workflows/{WF_ID}", payload)
print("PUT", code3, str(resp)[:200])
