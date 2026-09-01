# Pre-productivo Render + PostgreSQL

Fecha de corte: 2026-09-01

## Objetivo

Ejecutar ForMIX en Render con PostgreSQL como fuente de verdad. En este modo no
se debe depender de `mix_data.sqlite3`, snapshots locales, archivos temporales ni
secretos guardados en el repositorio.

## Recursos Render

El `render.yaml` declara:

- Web service: `formix-preprod`
- Base PostgreSQL: `formix-preprod-db`
- Runtime: Python
- Start command: `gunicorn wsgi:app --bind 0.0.0.0:$PORT`
- Health check: `/healthz`
- `DATABASE_URL` inyectado desde `formix-preprod-db`

Variables configuradas por Blueprint:

- `DATABASE_URL`: desde Render PostgreSQL
- `APP_SECRET_KEY`: generado por Render
- `SESSION_COOKIE_SECURE=1`
- `FORMIX_ALLOW_DEFAULT_USERS=0`
- `APP_TIMEZONE=America/Cancun`
- `TZ=America/Cancun`

## Orden de migracion recomendado

1. Confirmar que el repo esta limpio de artefactos locales.
2. Desplegar el Blueprint en Render.
3. Esperar a que Render cree `formix-preprod-db` y arranque `formix-preprod`.
4. Tomar la URL externa de PostgreSQL desde Render solo para la migracion inicial.
5. Ejecutar localmente:

```bash
DATABASE_URL="<external-postgres-url>" py migrate_to_pg.py
```

En PowerShell:

```powershell
$env:DATABASE_URL="<external-postgres-url>"
py migrate_to_pg.py
Remove-Item Env:\DATABASE_URL
```

6. Reiniciar o redeployar el servicio web en Render.
7. Validar login y flujos operativos reales.

## Validaciones obligatorias

Local:

```bash
py verify_instance.py
py smoke_validation.py
```

Render:

- `GET /healthz` debe devolver `ok=true` y `database=postgres`.
- Login con usuario migrado.
- Flujo minimo: dataset -> consulta -> dosificador -> remision -> inventario.
- Flujo laboratorio: remision -> muestra -> cilindro -> ensayo.
- Redeploy del servicio y confirmacion de que los datos persisten.

## Lo que no debe ir a pre-productivo

- `.venv/`
- `__pycache__/`
- `.tmp_smoke/`
- `mix_data.sqlite3`
- `database.db`
- `backups/`
- `.app_secret_key`
- `reflog_output.txt`
- CSVs y XLS historicos si ya fueron migrados o respaldados fuera del repo
- logos historicos que no use el branding ForMIX

## Pendientes externos

- Confirmar region de Render para web y base.
- Confirmar plan de PostgreSQL para pre-productivo.
- Confirmar usuario inicial migrado o crear usuario administrador por proceso
  controlado.
- Confirmar politica de backups de Render PostgreSQL.
- Confirmar dominio y HTTPS antes de uso con usuarios reales.
