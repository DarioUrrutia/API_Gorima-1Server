import urllib.request, json, os, sys
from pathlib import Path

BASE = "https://n8n.gm47.it/api/v1"

# Token lookup order:
# 1) N8N_API_KEY env var
# 2) scripts/n8n/n8n.local.json  ->  {"key": "eyJ..."}
# 3) repo-root/N8N.local.txt     (first non-empty line)
def _load_key() -> str:
    k = os.environ.get("N8N_API_KEY", "").strip()
    if k:
        return k
    here = Path(__file__).resolve().parent
    local_json = here / "n8n.local.json"
    if local_json.exists():
        try:
            return json.loads(local_json.read_text(encoding="utf-8"))["key"].strip()
        except Exception:
            pass
    # fall back: find a JWT-looking token (eyJ...) in any N8N.local.txt
    import re
    jwt = re.compile(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")
    for p in [here.parents[1] / "N8N.local.txt", here.parents[1] / "rest-wrapper" / "N8N.local.txt"]:
        if p.exists():
            m = jwt.search(p.read_text(encoding="utf-8"))
            if m:
                return m.group(0)
    sys.exit(
        "n8n_api: no API key found. Set env N8N_API_KEY, "
        "or create scripts/n8n/n8n.local.json with {\"key\": \"...\"}, "
        "or put the token in N8N.local.txt at repo root."
    )

KEY = _load_key()

def req(method, path, body=None):
    url = BASE + path
    data = None
    headers = {
        "X-N8N-API-KEY": KEY,
        "accept": "application/json",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    }
    if body is not None:
        data = json.dumps(body).encode()
        headers["content-type"] = "application/json"
    r = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()

if __name__ == "__main__":
    code, data = req("GET", "/workflows")
    print("status", code)
    if isinstance(data, dict) and "data" in data:
        for w in data["data"]:
            print(f"  id={w['id']}  active={w.get('active')}  name={w['name']}")
    else:
        print(json.dumps(data, indent=2)[:500])
