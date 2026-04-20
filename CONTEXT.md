# Contexto de trabajo — vTiger + REST wrapper + n8n agent

> Documento vivo. Lo escribo **yo (Claude)** y lo releo al inicio de cada sesión
> para retomar sin perder el hilo. Si el usuario me dice "lee el contexto",
> empiezo por este archivo y por `scripts/n8n/n8n_api.py`.

Última actualización: 2026-04-20

---

## 1. Objetivo global

Construir un **AI agent en n8n** (workflow "vTiger Agent - Demo (SS106 + comentar)",
id `kwoD2OHZeWSMTdTC` en https://n8n.gm47.it) que conversa en IT/ES/EN y
opera sobre vTiger 8.2 a través del **wrapper REST propio** que vive en el VPS.

El agente debe soportar (con coherencia entre tools):

- Oportunidades (Potentials): search / create / update / add_comment
- Aziende (Accounts): search / create / update
- Contactos: search / create / update
- Eventi: create (parent_id = account/contact/opportunity)

Reglas clave del agente:

- Responde en el idioma del usuario **pero escribe en vTiger en el idioma
  que el usuario usa al dictar los datos** (no traducir valores de campos).
- Resuelve automáticamente nombre → ID buscando antes de actualizar.
- Acepta selección natural de una lista previa ("el 3", "tercero", "Di Dio",
  no solo 12xNNNN).

---

## 2. Topología

```
Usuario
   │  (chat en n8n)
   ▼
n8n Agent (OpenAI gpt-4o)  ← Memory Window Buffer (ctx=10)
   │
   ├── search_* tools        → GET  http://146.59.192.163/api/{Module}?q=...
   ├── create_* tools        → POST http://146.59.192.163/api/{Module}
   ├── update_* tools        → PUT  http://146.59.192.163/api/{Module}/{id}
   └── add_comment_to_pot.   → POST /api/ModComments
                    │
                    ▼
     rest-wrapper/api/index.php  (en /var/www/html/vtigercrm/api/)
                    │
                    ▼
              webservice.php nativo de vTiger (revise / create / query)
```

- **VPS**: `ubuntu@146.59.192.163`, key `keys/gorima-2024.pem` (Claude tiene
  acceso SSH directo, ver `scripts/ssh/`).
- **vhost**: `/etc/apache2/sites-enabled/vtigercrm.conf` → `crmtest.gorimagroup.it`
  con DocumentRoot `/var/www/html/vtigercrm`. Apache es el único vhost en :80,
  así que **incluso peticiones por IP caen en él** — el `.htaccess` en
  `/api/` reescribe a `index.php/$1`.
- **PHP**: mod_php + opcache con `validate_timestamps=on` (cambios en disco
  se recogen en segundos). Apache corre con **`PrivateTmp=true`** → todo
  `file_put_contents('/tmp/...')` hecho desde Apache va a
  `/tmp/systemd-private-*apache2*/tmp/`, no a `/tmp` real. Trampa que me
  gastó 30 min. Ver `scripts/ssh/ssh_privatetmp.py`.
- **API token** del wrapper está en `/var/www/html/vtigercrm/api/config.php`
  (clave `api_token`), llega en `Authorization: Bearer …` o `X-API-Token`.

---

## 3. Estado actual del agent n8n

Workflow id: `kwoD2OHZeWSMTdTC`.

Nodos relevantes:

- **AI Agent** (typeVersion ~2) con systemMessage extenso en IT/ES que incluye
  reglas sobre selección de listas y ⛔ banner "body obbligatorio" (aunque ya
  no se usa body único — ver siguiente punto).
- **OpenAI Chat Model**: `gpt-4o` (no el -mini; con mini el agente ignoraba
  reglas y pasaba argumentos incompletos).
- **Memory**: `@n8n/n8n-nodes-langchain.memoryBufferWindow`, contextWindowLength 10.
- **Tools** (`@n8n/n8n-nodes-langchain.toolHttpRequest`, typeVersion 1.2):
  - `search_potentials`, `search_accounts`, `search_contacts`
  - `update_potential`, `update_account`, `update_contact`
  - `create_potential`, `create_account`, `create_contact`, `create_event`
  - `add_comment_to_potential`

### Forma final del cuerpo (muy importante)

Al principio había `specifyBody: "json"` + `jsonBody: "={{ $fromAI('body', …, 'string') }}"`.
**No funcionaba**: el LLM nunca pasaba `body`, n8n mandaba body vacío, y
como el wrapper usa `revise` (update parcial) → HTTP 200 pero sin cambios.
Diagnosticado con patch `readJsonBody()` + `/tmp/vt_body.log` en el wrapper.

Varias iteraciones fallidas (placeholder `{body}`, specifyBody `string`…)
hasta llegar a la que **funciona**:

- `specifyBody: "keypair"`
- `parametersBody.values` = un par `name`/`value` **por cada campo** (title,
  firstname, lastname, email, phone, mobile, account_id, description, …).
- Cada `value` es:
  `={{ $fromAI('<key>', '<desc>', 'string', '') || undefined }}`
  - el 4º arg `''` hace el parámetro **opcional** en el schema del tool
    (sin eso todos eran Required y el agente daba "Received tool input did
    not match expected schema").
  - `|| undefined` descarta los campos que el LLM no rellenó (no se envían
    valores vacíos al wrapper).

Script que aplica esta forma: `scripts/n8n/n8n_keypair_body.py`.
Última prueba del usuario: **"parece funcionar"** tras aplicar esto.

### Scripts n8n activos

- `scripts/n8n/n8n_api.py` — cliente HTTP a la API de n8n. Lee el JWT desde
  `N8N_API_KEY` env, o `scripts/n8n/n8n.local.json`, o `N8N.local.txt` en
  la raíz / `rest-wrapper/`. **Ningún token hardcodeado en git.**
- `n8n_keypair_body.py` — regenera los body-params como keypair + $fromAI opcional.
- `n8n_last_exec.py`, `n8n_exec_detail.py`, `n8n_exec_full.py` — depurar
  ejecuciones (muy útiles para ver qué argumentos pasó el LLM).
- `n8n_dump_update_contact.py` — inspecciona un tool concreto.
- `n8n_add_memory.py`, `n8n_switch_model.py`, `n8n_reorganize.py`,
  `n8n_update_prompt.py` — utilidades aplicadas en sesiones anteriores.

Todos los scripts que mutan el workflow deben filtrar `settings` a las keys
permitidas por la API (`ALLOWED_SETTINGS` en `n8n_keypair_body.py`), si no
el PUT devuelve 400 "settings must NOT have additional properties".

---

## 4. REST wrapper (rest-wrapper/api/index.php)

- Parcheada la lógica de búsqueda (`list()`): soporte multi-token con AND,
  variantes letra↔dígito, campos custom extra para Potentials
  (cf_969/915/913/1009).
- `update()` usa operación `revise` del webservice nativo → update parcial.
- Token se valida en `Authorization: Bearer` o `X-API-Token`.

> El índex.php en el VPS puede tener un patch temporal de debug:
> `@file_put_contents('/tmp/vt_body.log', … , FILE_APPEND);` dentro de
> `readJsonBody()`. Se lee con `scripts/ssh/ssh_read_log_now.py`. Esa línea
> **no está en el repo** (el repo trae la versión limpia). Si vuelvo a debuggear,
> acordarme que `/tmp` de Apache es `/tmp/systemd-private-*apache2*/tmp/`.

---

## 5. Estructura de carpetas

```
VPS - Gorima 1mo/
├── README.md
├── CONTEXT.md                ← este archivo
├── .gitignore
├── rest-wrapper/             ← producto: wrapper REST (en git)
│   ├── api/index.php         ← versión limpia
│   ├── api/config.php.example
│   ├── describes/            ← dumps de /api/{Module}/describe
│   ├── n8n/vtiger-agent-demo.json  ← export del workflow (snapshot)
│   └── N8N.local.txt         ← JWT n8n (gitignorado)
├── keys/                     ← gitignorado (.pem/.ppk)
├── VTRestfulAPI/             ← gitignorado (repo upstream de terceros)
└── scripts/
    ├── n8n/                  ← EN GIT (tras refactor sin tokens hardcoded)
    ├── ssh/                  ← gitignorado (tokens + paths absolutos)
    ├── vtiger/               ← parcialmente gitignorado (los que tienen tokens)
    └── _archive/             ← gitignorado (exploración desechada)
```

Reglas personales:

- **No tocar `VTRestfulAPI/`** (tiene su propio .git y se descartó hace tiempo).
- **Nunca commitear** `api/config.php`, `keys/*`, `*.local.*`, `*.pem`, `*.ppk`.
- Para scripts nuevos de debug, usar `scripts/_archive/` o `scripts/ssh/`
  (ambos gitignorados) hasta que estén listos para producto.

---

## 6. Decisiones clave ya tomadas (no re-debatir)

1. El agente habla el idioma del usuario, **pero no traduce valores**
   (si el usuario dice "Acquisto", en vTiger va "Acquisto").
2. Modelo: `gpt-4o` (mini es inviable para este agente).
3. Update/Create: **campos individuales con $fromAI opcional**, no un JSON
   genérico. El LLM rellena solo lo pedido, n8n manda solo eso al wrapper.
4. Memory: Buffer Window 10 mensajes.
5. URL del wrapper: IP pública `http://146.59.192.163/api/…`. No pasa por
   DNS/HTTPS — está bien para este demo interno.
6. El gerente evalúa el agent directamente en **su propia cuenta de n8n**
   (importa el JSON exportado en `rest-wrapper/n8n/vtiger-agent-demo.json`).

---

## 7. Pendientes

- [ ] Probar `update_account`, `update_potential` con la nueva forma keypair.
- [ ] Probar `create_*` y `add_comment_to_potential`.
- [ ] Eliminar el patch de debug de `readJsonBody()` en el wrapper del VPS
      cuando el flujo esté 100% validado. Script:
      `scripts/ssh/ssh_fix_debug.py` hace el inverso fácilmente
      (subir versión limpia).
- [ ] Exportar el workflow al JSON del repo (`rest-wrapper/n8n/vtiger-agent-demo.json`)
      cuando quede estable.
- [ ] Opcional: reestructurar description fields de Opportunities y decidir
      enum de `sales_stage` visible en la UI (gerente pidió flujo coloquial).

---

## 8. Arranque rápido para la próxima sesión

1. Leer este archivo completo.
2. `git log --oneline -10` para ver últimos commits.
3. Si hay dudas sobre el estado real del agente:
   `python scripts/n8n/n8n_dump_update_contact.py` (o similar).
4. Para ver la última ejecución: `python scripts/n8n/n8n_last_exec.py`.
5. SSH al VPS: `ssh -i keys/gorima-2024.pem ubuntu@146.59.192.163`.
