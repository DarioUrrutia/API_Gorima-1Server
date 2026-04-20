from n8n_api import req
import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Full dump of exec 422 (last successful) update_contact node data
code, ex = req("GET", "/executions/422?includeData=true")
run = ex["data"]["resultData"]["runData"]
for node, runs in run.items():
    if "update_contact" not in node: continue
    for r in runs:
        print(json.dumps(r, indent=2, ensure_ascii=False)[:4000])
