"""
Añade un nodo de memoria (Window Buffer) al AI Agent para que recuerde
el contexto de los mensajes anteriores en la misma sesión de chat.
"""
from n8n_api import req

WID = "kwoD2OHZeWSMTdTC"

MEMORY_NODE = {
    "parameters": {
        "contextWindowLength": 10,
    },
    "id": "memory-buffer-window",
    "name": "Memory",
    "type": "@n8n/n8n-nodes-langchain.memoryBufferWindow",
    "typeVersion": 1.3,
    "position": [600, 220],
}

code, wf = req("GET", f"/workflows/{WID}")
existing = {n["name"]: n for n in wf["nodes"]}

if "Memory" not in existing:
    wf["nodes"].append(MEMORY_NODE)
    print("Memory node added")
else:
    existing["Memory"]["position"] = [600, 220]
    print("Memory node already exists, repositioned")

conns = wf.get("connections", {})
conns.setdefault("Memory", {})
conns["Memory"]["ai_memory"] = [[{"node": "AI Agent", "type": "ai_memory", "index": 0}]]
wf["connections"] = conns

body = {
    "name": wf["name"],
    "nodes": wf["nodes"],
    "connections": wf["connections"],
    "settings": {"executionOrder": wf.get("settings", {}).get("executionOrder", "v1")},
}
code, resp = req("PUT", f"/workflows/{WID}", body)
print(f"PUT status={code}  updatedAt={resp.get('updatedAt') if isinstance(resp, dict) else resp[:300]}")
