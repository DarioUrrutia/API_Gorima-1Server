from n8n_api import req
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

WF_ID = "kwoD2OHZeWSMTdTC"
code, wf = req("GET", f"/workflows/{WF_ID}")

# Column by module, row by operation. Extras (create_event, add_comment) at the end.
COLS = {
    "Contacts":   0,   # x=600
    "Accounts":   1,   # x=900
    "Potentials": 2,   # x=1200
    "Extras":     3,   # x=1500
}
ROWS = {
    "search": 0,
    "get":    1,
    "create": 2,
    "update": 3,
    "extra":  4,
}
COL_W = 280
ROW_H = 200
X0 = 600
Y0 = 420

def slot(col, row):
    return [X0 + COLS[col]*COL_W, Y0 + ROWS[row]*ROW_H]

PLACEMENT = {
    # name               : (col,        row)
    "search_contacts":     ("Contacts",   "search"),
    "get_contact":         ("Contacts",   "get"),
    "create_contact":      ("Contacts",   "create"),
    "update_contact":      ("Contacts",   "update"),

    "search_accounts":     ("Accounts",   "search"),
    "get_account":         ("Accounts",   "get"),
    "create_account":      ("Accounts",   "create"),
    "update_account":      ("Accounts",   "update"),

    "search_potentials":   ("Potentials", "search"),
    "get_potential":       ("Potentials", "get"),
    "create_potential":    ("Potentials", "create"),
    "update_potential":    ("Potentials", "update"),
    "add_comment_to_potential": ("Potentials", "extra"),

    "create_event":        ("Extras",     "create"),
}

# Keep AI Agent and chat trigger on top
TOP_Y = 160
moved = 0
for n in wf["nodes"]:
    nm = n["name"]
    if nm in PLACEMENT:
        col, row = PLACEMENT[nm]
        n["position"] = slot(col, row)
        moved += 1
    elif nm == "AI Agent":
        n["position"] = [900, TOP_Y]
    elif nm == "When chat message received":
        n["position"] = [600, TOP_Y]
    elif nm == "OpenAI Chat Model":
        n["position"] = [760, TOP_Y + 140]
    elif nm == "Memory":
        n["position"] = [900, TOP_Y + 140]

print(f"moved {moved} tool nodes")

ALLOWED = {"executionOrder","saveDataErrorExecution","saveDataSuccessExecution","saveExecutionProgress","saveManualExecutions","timezone","executionTimeout","errorWorkflow","callerPolicy"}
if "settings" in wf:
    wf["settings"] = {k:v for k,v in wf["settings"].items() if k in ALLOWED}

payload = {k: wf[k] for k in ("name","nodes","connections","settings") if k in wf}
code3, resp = req("PUT", f"/workflows/{WF_ID}", payload)
print("PUT", code3, str(resp)[:200])
