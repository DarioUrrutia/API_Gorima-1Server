from n8n_api import req
import json
WID = "kwoD2OHZeWSMTdTC"
code, wf = req("GET", f"/workflows/{WID}")
# dump only add_comment_to_potential (has POST + body pattern we need)
for n in wf["nodes"]:
    if n["name"] in ("add_comment_to_potential", "search_potentials"):
        print(f"\n### {n['name']} ###")
        print(json.dumps(n["parameters"], indent=2, ensure_ascii=False))
