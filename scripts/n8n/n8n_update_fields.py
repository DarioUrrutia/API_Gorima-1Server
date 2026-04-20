from n8n_api import req
import json

WID = "kwoD2OHZeWSMTdTC"
code, wf = req("GET", f"/workflows/{WID}")
assert code == 200

ESSENTIAL = "id,potentialname,potential_no,sales_stage,amount,closingdate,cf_919,cf_895,cf_969,cf_891,cf_897,cf_859,cf_915,cf_1009"

for n in wf["nodes"]:
    if n["name"] == "search_potentials":
        p = n["parameters"]
        # parametersQuery format: {values: [{name, valueProvider, value/description}, ...]}
        vals = p.get("parametersQuery", {}).get("values", [])
        # remove any existing 'fields' param
        vals = [v for v in vals if v.get("name") != "fields"]
        # append
        vals.append({
            "name": "fields",
            "valueProvider": "fieldValue",
            "value": ESSENTIAL,
        })
        p["parametersQuery"]["values"] = vals
        print("added fields param to search_potentials")
        print(json.dumps(vals, indent=2))

body = {
    "name": wf["name"],
    "nodes": wf["nodes"],
    "connections": wf["connections"],
    "settings": {"executionOrder": wf.get("settings", {}).get("executionOrder", "v1")},
}
code, resp = req("PUT", f"/workflows/{WID}", body)
print("PUT", code, resp.get("updatedAt") if isinstance(resp, dict) else resp[:300])
