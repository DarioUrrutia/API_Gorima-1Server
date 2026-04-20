from n8n_api import req

WID = "kwoD2OHZeWSMTdTC"
code, wf = req("GET", f"/workflows/{WID}")
for n in wf["nodes"]:
    print(f"{n['name']:35}  type={n['type']:55}  pos={n.get('position')}")
