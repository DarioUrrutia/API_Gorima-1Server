# vtiger-rest-wrapper

Wrapper REST minimal (~300 líneas PHP) sobre el webservice nativo de vTiger 8.2 / PHP 8.3.

Sustituye a VTRestfulAPI (repo abandonado de 2017, incompatible con PHP 8). Expone URLs limpias tipo `/api/Potentials/123` y las traduce a llamadas internas contra `webservice.php`.

## Endpoints

| Método | Ruta | Efecto |
|---|---|---|
| `GET` | `/api/{Module}` | Lista. Params: `?q=...&limit=50&offset=0&fields=*` |
| `GET` | `/api/{Module}/describe` | Schema del módulo (campos, idPrefix, etc.) |
| `GET` | `/api/{Module}/{id}` | Lee un registro (id puede ser numérico o `11x123`) |
| `POST` | `/api/{Module}` | Crea registro. Body JSON con los campos |
| `PUT` | `/api/{Module}/{id}` | Actualiza parcial. Body JSON con los campos a cambiar |
| `DELETE` | `/api/{Module}/{id}` | Borra |
| `POST` | `/api/{Module}/{id}/comments` | Añade comentario (ModComments) al registro. Body `{"content":"..."}` |

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
