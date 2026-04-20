from n8n_api import req
import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

code, ex = req("GET", "/executions/423?includeData=true")
print(json.dumps(ex, indent=2, ensure_ascii=False)[:6000])
