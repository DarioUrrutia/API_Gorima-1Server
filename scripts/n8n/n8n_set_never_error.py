"""Patch all toolHttpRequest nodes so the agent receives the wrapper response
body even when status is 4xx/5xx.

By default n8n's HTTP tool replaces a non-2xx response with a generic
"Request failed with status code XXX" string and the agent never sees the
JSON body the wrapper returns (e.g. {"error":"not_found", ...} or
{"error":"picklist_invalid", "details":{"allowed":[...]}}).

Setting parameters.options.response.response.neverError = true makes n8n
treat 4xx/5xx as a normal output, so the agent gets the actual JSON body
and can react intelligently (ask for clarification, present allowed
picklist values, etc).
"""
import json
from n8n_api import req

WF_ID = "kwoD2OHZeWSMTdTC"


def ensure_never_error(node: dict) -> bool:
    p = node.setdefault("parameters", {})
    opts = p.setdefault("options", {})
    resp = opts.setdefault("response", {})
    inner = resp.setdefault("response", {})
    if inner.get("neverError") is True:
        return False
    inner["neverError"] = True
    return True


def main() -> None:
    code, wf = req("GET", f"/workflows/{WF_ID}")
    if code != 200:
        raise SystemExit(f"GET failed: {code} {wf}")

    http_nodes = [n for n in wf["nodes"] if "toolHttpRequest" in n.get("type", "")]
    changed = []
    for n in http_nodes:
        if ensure_never_error(n):
            changed.append(n["name"])

    if not changed:
        print("All HTTP tool nodes already have neverError=true. Nothing to do.")
        return

    allowed_settings = {
        "executionOrder", "saveDataErrorExecution", "saveDataSuccessExecution",
        "saveExecutionProgress", "saveManualExecutions", "timezone",
        "executionTimeout", "errorWorkflow", "callerPolicy",
    }
    settings = {k: v for k, v in wf.get("settings", {}).items() if k in allowed_settings}
    payload = {
        "name": wf["name"],
        "nodes": wf["nodes"],
        "connections": wf["connections"],
        "settings": settings,
    }
    code, resp = req("PUT", f"/workflows/{WF_ID}", payload)
    if code != 200:
        raise SystemExit(f"PUT failed: {code} {resp}")

    print(f"Patched {len(changed)}/{len(http_nodes)} nodes:")
    for name in changed:
        print(f"  - {name}")


if __name__ == "__main__":
    main()
