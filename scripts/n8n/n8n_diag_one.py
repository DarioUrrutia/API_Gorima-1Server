"""Dump completo de UNA execution: tools llamados con input/output sin truncar."""
from n8n_api import req
import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

EXEC_ID = sys.argv[1]
code, ex = req("GET", f"/executions/{EXEC_ID}?includeData=true")
print(f"EXEC {EXEC_ID} status={ex.get('status')} started={ex.get('startedAt')}")
d = ex.get("data") or {}
run = d.get("resultData", {}).get("runData", {})
for node, runs in run.items():
    if node.lower() in ("openai chat model", "memory", "when chat message received"):
        continue
    for i, r in enumerate(runs):
        inp = r.get("inputOverride") or r.get("data", {}).get("ai_tool") or r.get("data", {}).get("main")
        out = r.get("data", {}).get("main") or r.get("data", {}).get("ai_tool")
        print(f"\n--- {node} (run {i}) ---")
        print("INPUT:")
        print(json.dumps(inp, ensure_ascii=False, indent=2))
        print("OUTPUT:")
        print(json.dumps(out, ensure_ascii=False, indent=2))
