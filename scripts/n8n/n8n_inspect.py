from n8n_api import req
import json

code, data = req("GET", "/workflows")
for w in data["data"]:
    print(f"\n=== {w['id']} {w['name']} (active={w.get('active')}) ===")
    code2, d2 = req("GET", f"/workflows/{w['id']}")
    if code2 != 200:
        print("  GET failed", code2, d2[:200] if isinstance(d2,str) else d2)
        continue
    # show node summary
    for n in d2.get("nodes", []):
        print(f"  node: name={n['name']}  type={n['type']}")
    # look for archived flag or other markers
    keys = set(d2.keys())
    print("  top keys:", sorted(keys))
    print("  createdAt:", d2.get("createdAt"), "updatedAt:", d2.get("updatedAt"))
    print("  isArchived:", d2.get("isArchived"))
