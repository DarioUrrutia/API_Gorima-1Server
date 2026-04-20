import json, os, glob

D = r"c:\Users\JeanUrrutia\VPS - Gorima 1mo\rest-wrapper\describes"
for path in sorted(glob.glob(os.path.join(D, "*.json"))):
    mod = os.path.splitext(os.path.basename(path))[0]
    with open(path, "r", encoding="utf-8") as f:
        try:
            d = json.load(f)
        except Exception as e:
            print(mod, "parse err", e); continue
    print(f"\n=== {mod} ===")
    fields = d.get("fields", []) if isinstance(d, dict) else []
    for f in fields:
        if f.get("mandatory"):
            t = f.get("type", {})
            tname = t.get("name") if isinstance(t, dict) else t
            pick = ""
            if isinstance(t, dict) and t.get("picklistValues"):
                pick = "  picklist=" + ",".join(p.get("value","") for p in t["picklistValues"][:15])
            print(f"  {f.get('name'):25} type={tname}  label={f.get('label','')}{pick}")
