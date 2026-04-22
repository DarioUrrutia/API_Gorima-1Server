"""Diagnostic dump: para las ultimas N ejecuciones, lista cada tool call
del agent con su input (params) y output (respuesta del wrapper).

Objetivo: ver de un vistazo si el agent llama los tools correctos con los
params correctos, y si el wrapper devuelve OK o error. Sirve para
distinguir "el agent no sabe llamar al tool" vs "el wrapper falla" vs
"el wrapper dice OK pero vTiger no guarda".
"""
from n8n_api import req
import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

LIMIT = int(sys.argv[1]) if len(sys.argv) > 1 else 10

code, data = req("GET", f"/executions?limit={LIMIT}&includeData=true")
for ex in data.get("data", []):
    print(f"\n{'='*70}\nEXEC {ex['id']}  status={ex.get('status')}  started={ex.get('startedAt')}")
    d = ex.get("data") or {}
    run = d.get("resultData", {}).get("runData", {})
    # Print user message if we can find it
    for node, runs in run.items():
        if node.lower() in ("when chat message received", "trigger", "webhook"):
            for r in runs:
                out = r.get("data", {}).get("main", [])
                if out and out[0]:
                    msg = out[0][0].get("json", {})
                    print(f"  USER: {msg.get('chatInput') or msg.get('message') or json.dumps(msg)[:200]}")
    # Print every tool node call
    for node, runs in run.items():
        # skip the agent itself, the chat trigger, the model
        if node.lower() in ("ai agent", "openai chat model", "memory", "when chat message received"):
            continue
        for r in runs:
            inp = r.get("inputOverride") or r.get("data", {}).get("ai_tool") or r.get("data", {}).get("main")
            out = r.get("data", {}).get("main") or r.get("data", {}).get("ai_tool")
            err = r.get("error")
            print(f"\n  TOOL: {node}")
            print(f"    input : {json.dumps(inp, ensure_ascii=False)[:500]}")
            print(f"    output: {json.dumps(out, ensure_ascii=False)[:500]}")
            if err:
                print(f"    ERROR : {json.dumps(err, ensure_ascii=False)[:500]}")
