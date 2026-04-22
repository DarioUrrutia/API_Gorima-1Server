"""Add `X-Session-Id` header to all toolHttpRequest nodes.

The wrapper's SessionGuard reads this header to scope id-validity per
chat session. Without it the guard bypasses (which would make the agent
free to pass hallucinated ids again). The value is the n8n chat
sessionId from the chatTrigger node.
"""
import json
from n8n_api import req

WF_ID = "kwoD2OHZeWSMTdTC"
HEADER_NAME = "X-Session-Id"
# Expression: pull sessionId from the chatTrigger node's first item.
HEADER_VALUE = "={{ $('When chat message received').item.json.sessionId }}"


def ensure_session_header(node: dict) -> bool:
    p = node.setdefault("parameters", {})
    p["sendHeaders"] = True
    headers = p.setdefault("parametersHeaders", {"values": []})
    values = headers.setdefault("values", [])
    for v in values:
        if v.get("name") == HEADER_NAME:
            if v.get("value") == HEADER_VALUE:
                return False
            v["value"] = HEADER_VALUE
            v["valueProvider"] = "fieldValue"
            return True
    values.append({
        "name": HEADER_NAME,
        "valueProvider": "fieldValue",
        "value": HEADER_VALUE,
    })
    return True


def main() -> None:
    code, wf = req("GET", f"/workflows/{WF_ID}")
    if code != 200:
        raise SystemExit(f"GET failed: {code} {wf}")

    http_nodes = [n for n in wf["nodes"] if "toolHttpRequest" in n.get("type", "")]
    changed = []
    for n in http_nodes:
        if ensure_session_header(n):
            changed.append(n["name"])

    if not changed:
        print("All HTTP tool nodes already send X-Session-Id. Nothing to do.")
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
