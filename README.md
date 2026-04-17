# VPS Gorima — Notas de trabajo

Carpeta con la clave de acceso y documentación del VPS que originalmente alojaba el vTiger en `https://crm.gorimagroup.it/`.

## Contexto

- El dominio `crm.gorimagroup.it` fue reasignado a otro VPS (otro proyecto).
- Este VPS se reacondicionó para acceder a vTiger **directamente por IP** y quedar disponible para pruebas.

## Datos del VPS

| Dato | Valor |
|---|---|
| Proveedor | OVH (probable, sin acceso al panel) |
| IP pública | `146.59.192.163` |
| IPv6 | `2001:41d0:304:100::475b` |
| Usuario SSH | `ubuntu` (con `sudo`) |
| Hostname | `go` |
| OS | Ubuntu 24.04.1 LTS |
| Web server | Apache 2 |
| DB | MySQL 8.0.45 |
| vTiger path | `/var/www/html/vtigercrm/` |
| DB de vTiger | `vtiger` (user `ravi`) |

## Cómo conectar

1. Abrir **PuTTY**
2. Host: `146.59.192.163`, usuario `ubuntu`
3. Connection → SSH → Auth → Credentials → cargar `gorima-2024.ppk` (está en esta carpeta)

## Cómo acceder a vTiger

- URL: `http://146.59.192.163/`
- Solo **HTTP**. No hay SSL válido por IP (el cert Let's Encrypt es para el dominio viejo).

## Lo que se hizo (2026-04-17)

Único cambio aplicado:

- `/var/www/html/vtigercrm/config.inc.php` línea 82
  - Antes: `$site_URL = 'http://149.59.192.163/';` ← typo (IP no existente)
  - Después: `$site_URL = 'http://146.59.192.163/';`

No se tocó Apache, firewall, DNS, ni nada más. La sesión de diagnóstico y cambios está documentada en el historial de conversación con Claude.

## Backups en el VPS

A partir de ahora los backups viven en **`/home/ubuntu/backups/`** con un manifest (`BACKUPS.md`) que lista qué hay y de qué estado es cada uno. Consultar ese archivo en el VPS antes de restaurar nada.

### Convención de nombres

```
<tipo>-<YYYY-MM-DD>-<tag>.<ext>
```

Tags en uso:

| Tag | Significado |
|---|---|
| `pre-fix` | Estado anterior a corregir un bug |
| `working-by-ip` | Estado funcional accediendo por IP |
| `pre-kernel-update` | Antes de aplicar update de kernel |
| `pre-vhost-cleanup` | Antes de limpiar vhosts huérfanos |

### Inventario (actualizar al crear backup nuevo)

**2026-04-17 · pre-fix** (estado inicial con el typo `149.59.192.163`):
- `/var/www/html/vtigercrm/config.inc.php.bak-2026-04-17`
- `/etc/apache2/sites-available.bak-2026-04-17/`
- `/etc/apache2/sites-enabled.bak-2026-04-17/`
- `/home/ubuntu/vtiger-db-backup-2026-04-17.sql`

**2026-04-17 · working-by-ip** (primer estado funcional por IP):
- `/home/ubuntu/backups/config.inc.php-2026-04-17-working-by-ip`
- `/home/ubuntu/backups/vtiger-db-2026-04-17-working-by-ip.sql`

### Cómo crear un backup nuevo con tag

En el VPS:
```bash
TAG="pre-kernel-update"   # o el tag que toque
FECHA=$(date +%Y-%m-%d)
BKDIR=~/backups
sudo cp /var/www/html/vtigercrm/config.inc.php $BKDIR/config.inc.php-$FECHA-$TAG
DB_USER=$(sudo grep "'db_username'" /var/www/html/vtigercrm/config.inc.php | head -1 | awk -F"'" '{print $4}')
DB_PASS=$(sudo grep "'db_password'" /var/www/html/vtigercrm/config.inc.php | head -1 | awk -F"'" '{print $4}')
DB_NAME=$(sudo grep "'db_name'" /var/www/html/vtigercrm/config.inc.php | head -1 | awk -F"'" '{print $4}')
MYSQL_PWD="$DB_PASS" mysqldump --single-transaction --no-tablespaces --routines --triggers -u "$DB_USER" "$DB_NAME" > $BKDIR/vtiger-db-$FECHA-$TAG.sql
unset DB_USER DB_PASS DB_NAME MYSQL_PWD
# Después, editar a mano /home/ubuntu/backups/BACKUPS.md añadiendo la entrada nueva
```

## Rollback a un punto concreto

Usar la etiqueta (`<TAG>`) del estado al que se quiere volver. Consultar `~/backups/BACKUPS.md` para saber qué tags existen.

### Restaurar config a un tag
```bash
sudo cp /home/ubuntu/backups/config.inc.php-<FECHA>-<TAG> /var/www/html/vtigercrm/config.inc.php
```

### Restaurar DB a un tag
```bash
DB_USER=$(sudo grep "'db_username'" /var/www/html/vtigercrm/config.inc.php | head -1 | awk -F"'" '{print $4}')
DB_PASS=$(sudo grep "'db_password'" /var/www/html/vtigercrm/config.inc.php | head -1 | awk -F"'" '{print $4}')
DB_NAME=$(sudo grep "'db_name'" /var/www/html/vtigercrm/config.inc.php | head -1 | awk -F"'" '{print $4}')
MYSQL_PWD="$DB_PASS" mysql -u "$DB_USER" "$DB_NAME" < /home/ubuntu/backups/vtiger-db-<FECHA>-<TAG>.sql
unset DB_PASS MYSQL_PWD
```

## Pendientes / cosas a tener en cuenta

- **`System restart required`**: hay actualizaciones de kernel pendientes. Planear reinicio con ventana de mantenimiento cuando convenga.
- **153 paquetes actualizables**: `sudo apt list --upgradable`. Aplicar con cuidado (no combinar con cambios de vTiger).
- **Vhosts huérfanos** en `sites-available` que ya no se usan: `000-block-ip.conf`, `crm.gorimagroup.it.conf`, `vtigercrm-le-ssl.conf`, `default-ssl.conf`. Siguen inactivos (sin symlink en `sites-enabled`) — no molestan pero se pueden limpiar cuando se quiera.
- **Cert Let's Encrypt** de `crm.gorimagroup.it`: sigue en `/etc/letsencrypt/live/`. Inútil por ahora (el dominio apunta a otro VPS). No hace daño; renovarlo o borrarlo es decisión futura.
- **Sin acceso al panel OVH**: no hay forma de hacer snapshot completo del VPS ni rescue mode. Si se rompe algo grave, la única red de seguridad son los backups locales arriba.

## Archivos en esta carpeta

- `gorima-2024.ppk` — clave privada PuTTY para conectar al VPS.
- `README.md` — este documento.
