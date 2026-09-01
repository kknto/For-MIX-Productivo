# Limpieza Recomendada

Este archivo separa los elementos detectados en la raiz del proyecto entre:

- `seguro borrar`: temporales, caches o residuos sin valor operativo
- `mejor archivar primero`: no son necesarios para la app actual, pero podrian tener valor historico o de referencia

No se incluyen archivos del sistema que la app usa activamente.

## Seguro borrar

Estos no aportan al funcionamiento actual:

- `__pycache__/` (`596687` bytes)
  Cache de Python regenerable.
- `.tmp_smoke/` (`503808` bytes)
  Temporales de pruebas de humo.
- `reflog_output.txt` (`692` bytes)
  Residuo manual.
- `database.db` (`0` bytes)
  Archivo vacio, sin uso.

Tambien puedes vaciar snapshots si no necesitas historial local:

- `backups/db_snapshots/20260309_105604_before_save.sqlite3` (`204800` bytes)
- `backups/db_snapshots/20260309_105723_before_remision_save.sqlite3` (`278528` bytes)

Nota:
- conservar `backups/` como carpeta es util, pero el contenido puede limpiarse si no quieres respaldos locales viejos

## Mejor archivar primero

No estan en uso por la configuracion actual, pero podrian servir como referencia o historico:

- `7020_ALMEX_Grava20__Are_Seca_5_NAVA-EUCO.csv` (`20420` bytes)
- `7020_ALMEX_Grava20__Are_Seca_5_NAVA-EUCO_20260303_101444.csv` (`20710` bytes)
- `7020_ALMEX_Grava20__Are_Seca_5_NAVA-EUCO_20260303_103105.csv` (`25511` bytes)
- `CONTEXTO_PROYECTO.md` (`15906` bytes)
- `Formato para Dosificar.xls` (`429568` bytes)

## Branding historico no activo

La configuracion actual usa `static/img/logo_formix.svg`.
Estos archivos ya no estan activos por defecto y pueden archivarse o eliminarse si no piensas reutilizar branding viejo:

- `static/img/logo_almex.svg` (`790074` bytes)
- `static/img/logo_almex.png` (`592403` bytes)
- `static/img/Logo_ALMEX.jpeg` (`47875` bytes)
- `static/img/Labsico-Logo.jpg` (`28473` bytes)

## No borrar

Conviene conservar:

- `app.py`
- `core/`
- `services/`
- `repositories/`
- `templates/`
- `static/js/`
- `static/css/`
- `instance.example.toml`
- `README.md`
- `ARCHITECTURE.md`
- `INSTALL_INSTANCE.md`
- `verify_instance.py`
- `smoke_validation.py`
- `mix_data.sqlite3`
- `.app_secret_key`
- `render.yaml`
- `Procfile`

## Orden recomendado de limpieza

1. borrar `__pycache__/`, `.tmp_smoke/`, `reflog_output.txt`, `database.db`
2. decidir si quieres conservar snapshots de `backups/db_snapshots/`
3. mover CSVs viejos, logos viejos y `Formato para Dosificar.xls` a una carpeta `archive/`
4. probar la app
5. si todo sigue bien, eliminar definitivamente lo archivado
