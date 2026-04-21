"""Dump the current workflow definition to rest-wrapper/n8n/vtiger-agent-demo.json
so the repo always ships the latest snapshot importable from another n8n instance.

The wrapper Bearer token is redacted to a placeholder before writing. Whoever
imports the workflow into their own n8n must paste their real token in place
of `__REPLACE_WITH_API_TOKEN__` in every Authorization header.
"""
from n8n_api import req
import json, re, sys, io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

WF_ID = "kwoD2OHZeWSMTdTC"
OUT = Path(__file__).resolve().parents[2] / "rest-wrapper" / "n8n" / "vtiger-agent-demo.json"
TOKEN_RE = re.compile(r"Bearer\s+[A-Fa-f0-9]{32,}")
PLACEHOLDER = "Bearer __REPLACE_WITH_API_TOKEN__"

code, d = req("GET", f"/workflows/{WF_ID}")
if code >= 300:
    sys.exit(f"GET workflow failed: {code} {d}")

keep = {k: d[k] for k in ("name", "nodes", "connections", "settings") if k in d}
keep.setdefault("settings", {})
keep["settings"] = {k: v for k, v in keep["settings"].items() if k in {
    "executionOrder", "saveDataErrorExecution", "saveDataSuccessExecution",
    "saveExecutionProgress", "saveManualExecutions", "timezone",
    "executionTimeout", "errorWorkflow", "callerPolicy",
}}

raw = json.dumps(keep, indent=2, ensure_ascii=False)
sanitized, n = TOKEN_RE.subn(PLACEHOLDER, raw)
OUT.write_text(sanitized, encoding="utf-8")
print(f"wrote {OUT} ({OUT.stat().st_size} bytes, {len(keep.get('nodes', []))} nodes, {n} tokens redacted)")
