from n8n_api import req
import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

code, data = req("GET", "/workflows")
for w in data["data"]:
    code2, d2 = req("GET", f"/workflows/{w['id']}")
    for n in d2.get("nodes", []):
        name = n.get("name", "").lower()
        params = json.dumps(n.get("parameters", {})).lower()
        if "update" in name and "contact" in name:
            print(f"=== {w['id']} / {n['name']} ===")
            print(json.dumps(n, indent=2, ensure_ascii=False))
            print()
