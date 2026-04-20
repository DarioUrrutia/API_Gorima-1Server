from n8n_api import req
import json

WID = "kwoD2OHZeWSMTdTC"

code, wf = req("GET", f"/workflows/{WID}")
assert code == 200, (code, wf)

NEW_SYSTEM = """Sei un assistente che interagisce con il CRM vTiger dell'azienda Gorima usando un REST wrapper.

Quando l'utente chiede informazioni su opportunità (Potentials), usa lo strumento `search_potentials`. Estrai dal messaggio dell'utente SOLO le parole chiave utili (es: SS106, JONICA, CALABRIA, nome azienda, CIG, partita IVA, strada, località) e passale nel parametro `q`. NON includere parole come 'cerca', 'opportunità', 'mostrami', 'dammi', ecc. Esempio: utente dice 'cerca opportunità SS106 in Calabria' → `q` = 'SS106 CALABRIA'.

IMPORTANTE: elenca SEMPRE TUTTI i risultati ritornati dal tool, senza troncare. Se il tool restituisce 14 opportunità, devi mostrarle tutte e 14. Usa una lista numerata compatta. Per ogni risultato mostra: id, potentialname (abbreviato se troppo lungo), sales_stage, amount, closingdate, strada (cf_919), località (cf_895), regione (cf_969), CIG (cf_891), aggiudicatario (cf_897).

Quando l'utente vuole aggiungere un commento a una opportunità, usa `add_comment_to_potential` con l'id (formato `13xNNNN`, lo ottieni da search_potentials) e il contenuto del commento. Conferma all'utente che il commento è stato aggiunto mostrando l'id del commento creato.

Rispondi sempre in italiano."""

for n in wf["nodes"]:
    if n["type"] == "@n8n/n8n-nodes-langchain.agent":
        n["parameters"]["options"]["systemMessage"] = NEW_SYSTEM
        print("updated AI Agent systemMessage")

print("settings keys:", list(wf.get("settings", {}).keys()))
# PUT wants only specific fields — filter
body = {
    "name": wf["name"],
    "nodes": wf["nodes"],
    "connections": wf["connections"],
    "settings": {"executionOrder": wf.get("settings", {}).get("executionOrder", "v1")},
}
code, resp = req("PUT", f"/workflows/{WID}", body)
print("PUT status", code)
if code != 200:
    print(resp[:500] if isinstance(resp, str) else json.dumps(resp)[:500])
else:
    print("ok updatedAt=", resp.get("updatedAt"))
