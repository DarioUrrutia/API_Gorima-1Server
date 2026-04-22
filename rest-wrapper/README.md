# vtiger-rest-wrapper

Wrapper REST minimal (~300 líneas PHP) sobre el webservice nativo de vTiger 8.2 / PHP 8.3.

Sustituye a VTRestfulAPI (repo abandonado de 2017, incompatible con PHP 8). Expone URLs limpias tipo `/api/Potentials/123` y las traduce a llamadas internas contra `webservice.php`.

## Endpoints

| Método | Ruta | Efecto |
|---|---|---|
| `GET` | `/api/{Module}` | Lista. Params: `?q=...&f_<field>=<value>&limit=50&offset=0&fields=*` |
| `GET` | `/api/{Module}/describe` | Schema del módulo (campos, idPrefix, etc.) |
| `GET` | `/api/{Module}/{id}` | Lee un registro (id puede ser numérico o `11x123`) |
| `POST` | `/api/{Module}` | Crea registro. Body JSON con los campos |
| `PUT` | `/api/{Module}/{id}` | Actualiza parcial. Body JSON con los campos a cambiar |
| `DELETE` | `/api/{Module}/{id}` | Borra |
| `POST` | `/api/{Module}/{id}/comments` | Añade comentario (ModComments) al registro. Body `{"content":"..."}` |

### Parámetros de búsqueda (`GET /api/{Module}`)

- **`q=<keywords>`**: búsqueda textual multi-campo. Soporta múltiples tokens
  (combinados con AND), variantes letra↔dígito, y hit en campos custom
  relevantes por módulo (para Potentials: `cf_969` regione, `cf_919` strada,
  `cf_1009` stazione appaltante, `cf_891` CIG, `cf_859` CUP, etc.).
- **`f_<field>=<value>`**: filtro por igualdad exacta sobre un campo
  concreto. Ej. `?f_account_id=11x3358` → contactos de esa azienda.
  Se pueden combinar varios `f_*` (todos AND) y con `q` al mismo tiempo.
- **Soft-deletes**: se filtran automáticamente vía post-query a
  `vtiger_crmentity.deleted=0`. Requiere bloque `db` en `config.php`
  (ver `config.php.example`).

Módulos permitidos por defecto (editable en `config.php`): Accounts, Contacts, Potentials, Events, Calendar, ModComments.

## Autenticación

Todas las requests deben enviar el token:
```
Authorization: Bearer <API_TOKEN>
```

El `API_TOKEN` está en `config.php` (modo 600, protegido por `.htaccess`). Generación:
```bash
openssl rand -hex 32
```

El wrapper internamente se loguea en cada request al webservice nativo de vTiger usando `vtiger_user` + `vtiger_access_key` (también en `config.php`).

## Estructura

```
api/
├── index.php           # wrapper completo (entry point)
├── .htaccess           # rewrite /api/* → index.php, protege config.php
├── config.php          # credenciales (crear a partir del .example, chmod 600)
└── config.php.example  # plantilla
```

## Instalación en el VPS

Ver sección de despliegue en la conversación. Los pasos resumidos:

1. Crear `/var/www/html/vtigercrm/api/`
2. Subir los 3 archivos (`index.php`, `.htaccess`, `config.php.example`)
3. Copiar `config.php.example` → `config.php`
4. Editar `config.php`: pegar Access Key del admin, generar API_TOKEN
5. `chmod 600 config.php && chown www-data:www-data` en todo `api/`
6. `apache2ctl configtest && systemctl reload apache2` (no siempre necesario — `.htaccess` recarga solo)
7. Probar con curl

## Pruebas con curl

```bash
TOKEN=<tu_api_token>
BASE=http://146.59.192.163/api

# Listar cuentas
curl -s -H "Authorization: Bearer $TOKEN" "$BASE/Accounts?limit=5"

# Describir modulo
curl -s -H "Authorization: Bearer $TOKEN" "$BASE/Potentials/describe"

# Crear oportunidad
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"potentialname":"Test via wrapper","sales_stage":"Prospecting","closingdate":"2026-05-01","assigned_user_id":"19x1"}' \
  "$BASE/Potentials"

# Añadir comentario a una oportunidad (id 123)
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"content":"Cliente interesado, fijar demo"}' \
  "$BASE/Potentials/123/comments"
```

## Notas

- **Protocolo**: por ahora HTTP (no HTTPS por IP). El token viaja en claro. Aceptado para uso interno + n8n → VPS.
- **Login cacheado por request**: cada request hace un getchallenge + login al webservice nativo (~100ms overhead). Suficiente para uso conversacional. Si aumenta el tráfico, cachear sesión en APCu.
- **IDs**: el wrapper acepta IDs numéricos (`123`) o webservice IDs (`11x123`). Internamente resuelve el prefijo del módulo via describe.
- **Placeholders**: el wrapper descarta valores tipo `—`, `--`, `N/A`, `null`
  o cadenas vacías antes de enviar a `create/revise`. Evita que un LLM que
  confunde un campo vacío visual con un valor real rompa campos obligatorios.

### Garantías de validación (deploy 2026-04-22)

El wrapper no es un passthrough ciego: defiende ante LLMs que ignoran
las reglas del prompt.

- **Picklist whitelist** — `create`/`update` rechazan con HTTP `400`
  + `error: "picklist_invalid"` los valores fuera de whitelist para
  `Potentials.sales_stage`, `Potentials.cf_969`, `Events.eventstatus`,
  `Events.activitytype` (igual `Calendar.*`). El body incluye
  `details.allowed: [...]` con la lista DB válida — el agent debe
  traducirla a etiquetas UI y pedir al user que escoja.
- **404 cuando un id no existe** — `GET /Module/{id}` con un id
  inexistente o eliminado devuelve `404 not_found` (antes era `502`
  opaco). Permite al agent distinguir "id inventado" de "wrapper caído".
- **Eventos `parent_id` / `contact_id` reales** — para `Events`/`Calendar`,
  después de `create`/`retrieve` el wrapper consulta
  `vtiger_seactivityrel` y `vtiger_cntactivityrel` y rellena esos
  campos en la respuesta. Sin esto vTiger los devolvía vacíos aunque
  el enlace estuviera guardado, confundiendo al agent.

### Smoke tests post-deploy

`scripts/ssh/ssh_deploy_v2.py` despliega el wrapper y corre 8 smoke
tests vía `curl` desde el propio VPS:

1. picklist `sales_stage` inválido → `400`
2. picklist `cf_969` inválido → `400`
3. id inexistente → `404`
4. `GET` evento existente → `parent_id` real desde rel table
5. `POST` evento con `parent_id` → respuesta refleja `parent_id` real
6. picklist `activitytype` inválido → `400`
7. regression — `search_contacts?q=Luca Ferrari` → 1 hit
8. regression — `POST` Potential válido → record creado con valores DB

Cualquier cambio al wrapper debe pasar estos 8 antes de mergear.

## Agent de n8n (`/n8n/vtiger-agent-demo.json`)

Snapshot del workflow importable en otra instancia de n8n:

1. En n8n: Workflows → Import from File → seleccionar `vtiger-agent-demo.json`.
2. En cada nodo HTTP tool, buscar y reemplazar `__REPLACE_WITH_API_TOKEN__`
   por el Bearer real del wrapper (el mismo valor de `api_token` en
   `config.php`). El export lo sanitiza por seguridad.
3. Conectar las credenciales de OpenAI en el nodo "OpenAI Chat Model".
4. Ajustar el modelo si se prefiere (demostrado con `gpt-4o`; `-mini` no
   cumple las reglas).

El prompt y la lista de campos por entidad están versionados en el repo
principal bajo `scripts/n8n/_sys_prompt_current.txt` y
`scripts/n8n/n8n_keypair_body.py` respectivamente. Regenerar el workflow
tras cambios con `python scripts/n8n/n8n_export_workflow.py`.
