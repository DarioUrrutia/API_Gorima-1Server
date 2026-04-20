from n8n_api import req
import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

code, data = req("GET", "/executions?limit=5&includeData=true")
for ex in data.get("data", []):
    print(f"\n=== exec {ex['id']} wf={ex.get('workflowId')} status={ex.get('status')} ===")
    d = ex.get("data") or {}
    run = d.get("resultData", {}).get("runData", {})
    for node, runs in run.items():
        if "update" not in node and "contact" not in node.lower():
            continue
        for r in runs:
            inp = r.get("inputOverride") or r.get("data", {}).get("main")
            print(f"  node={node}")
            print("  input:", json.dumps(inp, ensure_ascii=False)[:600])
            out = r.get("data", {}).get("main")
            print("  output:", json.dumps(out, ensure_ascii=False)[:600])
