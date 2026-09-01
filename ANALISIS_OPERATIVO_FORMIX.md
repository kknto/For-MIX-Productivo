# Analisis Operativo ForMIX

Fecha de corte: 2026-09-01

## Resumen ejecutivo

ForMIX es una aplicacion Flask para operar una planta de concreto desde un
nucleo de disenos de mezcla. El producto ya tiene una separacion funcional clara:
Editor CSV, Consulta Mix, Dosificador, Remisiones, Inventario, Laboratorio,
Flotilla y Usuarios. La arquitectura actual tambien apunta a una instalacion por
planta mediante `instance.toml`, con SQLite local y PostgreSQL opcional por
`DATABASE_URL`.

El estado operativo no esta listo para entrega porque la validacion de humo no
arranca. La causa observada es una incompatibilidad entre el esquema esperado y
la base local `mix_data.sqlite3`: la tabla `remisiones` existe sin las columnas
`cliente` y `ubicacion`, mientras el esquema crea un indice sobre `cliente`
antes de que las migraciones agreguen esa columna.

## Evidencia revisada

- Documentacion: `README.md`, `ARCHITECTURE.md`, `INSTALL_INSTANCE.md`,
  `CLEANUP_CANDIDATES.md`.
- Backend: `app.py`, `app_feature_routes.py`, `app_db_schema.py`,
  `app_db_migrations.py`, `core/config.py`, `core/rbac.py`.
- Rutas: `auth_routes.py`, `editor_routes.py`, `doser_routes.py`,
  `remision_routes.py`, `inventory_routes.py`, `fleet_routes.py`,
  `qc_lab_routes.py`, `user_routes.py`.
- UI: `templates/index.html`, `static/js/app.js`.
- Validaciones ejecutadas:
  - `py verify_instance.py`
  - `py smoke_validation.py`
  - inspeccion read-only de `mix_data.sqlite3`.

## Estado real de validacion

### `py verify_instance.py`

Resultado: pasa con advertencias.

Observaciones:

- No existe `instance.toml`; la aplicacion opera con defaults.
- La marca activa queda como `ForMIX`.
- La planta activa queda como `Planta Base`.
- La zona horaria queda como `America/Cancun`.
- Estan habilitados los features: `consulta`, `dosificador`, `editor`,
  `flotilla`, `inventario`, `laboratorio`, `remisiones`, `usuarios`.
- El logo default `static/img/logo_formix.svg` existe.
- Hay secret local en `.app_secret_key`.

Conclusion operativa: la instancia base puede configurarse, pero todavia no
tiene identidad real de planta. Antes de entregar, debe existir un
`instance.toml` propio de la planta.

### `py smoke_validation.py`

Resultado: falla antes de ejecutar pruebas.

Error observado:

```text
sqlite3.OperationalError: no such column: cliente
```

Punto de falla:

- `smoke_validation.py` importa `create_app` desde `app.py`.
- Al importar `app.py`, se crea una app global con `app = create_app(base_dir=Path.cwd())`.
- Esa inicializacion usa `mix_data.sqlite3` del proyecto.
- `app_db_schema.py` intenta crear `idx_remisiones_cliente_created` sobre
  `remisiones(cliente, created_at DESC)`.
- La tabla local `remisiones` no tiene columna `cliente`.

Inspeccion read-only de `mix_data.sqlite3`:

```text
remisiones_cols = [
  'id', 'dataset_id', 'remision_no', 'formula', 'fc', 'edad', 'tipo',
  'tma', 'rev', 'comp', 'dosificacion_m3', 'peso_receta',
  'peso_teorico_total', 'peso_real_total', 'status', 'snapshot_json',
  'created_at', 'created_by', 'updated_at', 'version'
]
```

Conclusion operativa: no se puede declarar la version como validada mientras el
smoke este bloqueado. La correccion debe priorizar migracion/orden de indice y
evitar que importar `app.py` inicialice la base real cuando se quiere crear una
app aislada de pruebas.

## Inventario operativo por modulo

| Modulo | Usuarios principales | Entrada | Acciones | Salida operativa | Dependencias |
| --- | --- | --- | --- | --- | --- |
| Editor CSV | administrador, jefe-de-planta | CSV o dataset activo | preview, commit, merge, replace, save, historial, restore, backups | catalogo confiable de mezclas y familias | permisos editor, dataset valido, backups |
| Consulta Mix | administrador, jefe-de-planta, presupuestador | filtros de familia, fc, edad, tipo, TMA, rev, complemento | busqueda, seleccion, estimacion de receta y costos | receta consultable y reporte de consulta | dataset activo, QC sincronizado |
| Dosificador | administrador, jefe-de-planta, dosificador | seleccion de mezcla, m3, humedad, pesos reales | calcular carga teorica, registrar real, comparar tolerancias | dosificacion controlada y reporte | dataset, parametros, QC, remisiones |
| Remisiones | administrador, jefe-de-planta, dosificador, presupuestador lectura | datos de cliente, ubicacion, mezcla y carga | guardar, listar, consultar, actualizar, eliminar segun rol | historial de produccion y trazabilidad de entrega | dosificador, inventario, dataset |
| Inventario | administrador, jefe-de-planta, dosificador | materiales, alias dosificador, movimientos | entradas, salidas, bajas, purgas, resumen diario | stock actualizado y kardex | remisiones para descuento automatico |
| Laboratorio | administrador, laboratorista | muestras, remision, cilindros, resultados | crear muestra, consultar remision, ensayar cilindro, adjuntar imagen, tendencias | control de calidad y reportes de resistencia | remisiones, uploads QC |
| Flotilla | administrador, jefe-de-planta, dosificador | vehiculos, combustible, mantenimiento | alta/baja, consumo, KPIs, alertas | control de unidades, costos y rendimiento | datos de vehiculos y registros diarios |
| Usuarios | administrador | usuarios y roles | crear, listar, eliminar, resetear password | administracion de acceso | RBAC y autenticacion |

## Mapa de proceso de planta

1. **Carga y mantenimiento de mezclas**
   - El administrador o jefe de planta carga un CSV en el Editor.
   - El sistema valida, clasifica familia, crea revision y permite restore.
   - El dataset activo alimenta Consulta Mix y Dosificador.

2. **Consulta comercial/operativa**
   - Presupuestador o jefe de planta filtra mezclas.
   - Consulta Mix devuelve receta, componentes y costo estimado por m3.
   - El reporte de consulta sirve como soporte de decision/precio.

3. **Dosificacion**
   - Dosificador selecciona mezcla y volumen.
   - El sistema aplica parametros de dosificador y datos QC de agregados.
   - Se capturan cargas reales y se comparan contra tolerancias.
   - Se genera reporte de dosificacion.

4. **Remision y trazabilidad**
   - Desde Dosificador se registra remision con snapshot de la operacion.
   - Remisiones permite busqueda por fecha, cliente, remision, formula y archivo.
   - El registro conserva version, fecha, actor y snapshot.

5. **Inventario**
   - Materiales y transacciones forman el kardex.
   - Las remisiones descuentan materiales cuando existe alias/material vinculado.
   - El resumen diario permite revisar stock y movimientos.

6. **Laboratorio**
   - Laboratorista consulta remision, crea muestra y cilindros.
   - Registra ruptura, resistencia, tipo de falla, imagen y notas.
   - Tendencias y reportes permiten analizar resultados.

7. **Flotilla**
   - Se administran unidades, combustible, mantenimiento y alertas.
   - KPIs y tendencias apoyan costos operativos de transporte.

## Datos y trazabilidad

Entidades centrales observadas:

- Catalogo de mezclas: `datasets`, `dataset_revisions`, `upload_staging`.
- Control tecnico de mezcla: `qc_profiles`, `doser_profiles`.
- Produccion/remision: `remisiones`, `audit_log`.
- Inventario: `materials`, `inventory_transactions`.
- Laboratorio: `qc_samples`, `qc_cylinders`.
- Flotilla: `vehicles`, `fuel_records`, `maintenance_records`.
- Seguridad: `users`, `auth_locks`.

Cobertura de trazabilidad:

- Editor: historial, auditoria, backups y control de version.
- Remisiones: numero unico, snapshot, actor, fechas y version.
- Inventario: movimientos por material, referencia y actor.
- Laboratorio: muestra, cilindros, fecha esperada, fecha de ruptura, resultado e
  imagen.
- Flotilla: vehiculo, kilometraje, consumo, costo, proveedor y fechas.

Gaps/riesgos observados:

- El orden actual de inicializacion/migracion impide migrar una base antigua de
  `remisiones` si falta `cliente`.
- La app global en `app.py` dificulta aislar pruebas porque inicializa la base
  real al importar el modulo.
- Sin `instance.toml`, la entrega no representa una planta real.
- El repo tiene muchos cambios sin consolidar; antes de entregar hay que
  confirmar que la modernizacion completa esta incluida de forma intencional.
- Hay residuos/archivos historicos ya identificados en `CLEANUP_CANDIDATES.md`.

## Roles y permisos operativos

| Rol | Vistas esperadas | Uso operativo |
| --- | --- | --- |
| administrador | todas | configuracion, usuarios, dataset, backups, remisiones, inventario, laboratorio y flotilla |
| jefe-de-planta | editor, consulta, dosificador, remisiones, flotilla, inventario, laboratorio | operacion completa sin administrar usuarios |
| dosificador | dosificador, remisiones, flotilla, inventario | producir, remisionar y consultar recursos operativos |
| presupuestador | consulta, remisiones | consultar mezclas y revisar remisiones sin modificar operacion critica |
| laboratorista | laboratorio | capturar muestras, cilindros y ensayes |

Validacion requerida por flujo:

- Confirmar que cada pestana visible coincide con `allowed_views`.
- Confirmar que cada endpoint critico devuelve 403 o 404 segun rol/feature.
- Confirmar que acciones destructivas queden restringidas a administrador o
  roles operativos definidos.

## Preparacion para instalacion por planta

Checklist minimo:

- Crear `instance.toml` desde `instance.example.toml`.
- Definir marca, nombre de planta, municipio, subtitulos y logo.
- Confirmar `APP_TIMEZONE=America/Cancun` o la zona que aplique.
- Definir modo de base:
  - SQLite local si sera instalacion local.
  - PostgreSQL con `DATABASE_URL` si sera despliegue productivo.
- Definir `APP_SECRET_KEY` fuera del repo.
- En produccion, dejar `FORMIX_ALLOW_DEFAULT_USERS=0`.
- Confirmar `SESSION_COOKIE_SECURE=true` cuando haya HTTPS.
- Confirmar carpetas de snapshots y uploads QC con permisos.
- Cargar dataset inicial o documentar arranque sin CSV.
- Ejecutar `py verify_instance.py`.
- Ejecutar `py smoke_validation.py`.
- Cambiar credenciales iniciales si se usaron usuarios default.

Pendientes externos:

- Secretos de entorno reales.
- Decision SQLite vs PostgreSQL.
- Hosting/servidor final.
- Identidad visual definitiva de la planta.
- Dataset inicial autorizado por operacion.

## Riesgos priorizados

| Prioridad | Tipo | Riesgo | Impacto | Criterio de cierre |
| --- | --- | --- | --- | --- |
| P0 | bloqueante operativo | `smoke_validation.py` falla por `no such column: cliente` | no hay regresion verificable ni entrega confiable | smoke corre en base aislada y pasa |
| P0 | bloqueante tecnico | `app.py` crea app global al importarse | pruebas y herramientas pueden tocar/inicializar la base real | import de `create_app` no inicializa base productiva |
| P1 | entrega | falta `instance.toml` real | instalacion queda como Planta Base | `verify_instance.py` pasa sin advertencia de defaults |
| P1 | datos | migraciones e indices no son robustos ante bases previas | upgrades locales pueden fallar | migracion agrega columnas antes de indices/backfills |
| P1 | control de version | arbol Git con muchos cambios nuevos/modificados/eliminados | dificil auditar que entra a entrega | cambios agrupados y revisados por alcance |
| P2 | operacion | roles deben validarse por flujo completo | riesgo de acceso excesivo o bloqueo operativo | matriz rol/accion validada con smoke |
| P2 | mantenimiento | residuos y archivos historicos en repo | ruido y riesgo de empaquetado | limpieza/archivo ejecutado y validado |

## Backlog accionable

1. Corregir inicializacion/migracion de base.
   - Ajustar el orden para que `cliente` y `ubicacion` existan antes de crear
     indices o ejecutar backfills.
   - Revisar que PostgreSQL conserve equivalencia.
   - Criterio: una base antigua de `remisiones` migra sin error.

2. Separar import de fabrica Flask e inicializacion WSGI.
   - Evitar que `from app import create_app` cree una instancia global contra
     `Path.cwd()`.
   - Mantener compatibilidad con Gunicorn/Render mediante una instancia WSGI
     explicita o patron equivalente.
   - Criterio: `smoke_validation.py` usa su base temporal desde `.tmp_smoke`.

3. Recuperar validacion de humo.
   - Ejecutar toda la suite.
   - Registrar resultados de sesion, permisos, uploads, historial, backups,
     remisiones, inventario, flotilla, laboratorio y feature toggles.
   - Criterio: `py smoke_validation.py` termina en OK.

4. Crear configuracion real de planta.
   - Generar `instance.toml` fuera de versionado con identidad final.
   - Validar logo, timezone, features y limites.
   - Criterio: `py verify_instance.py` sin advertencias de defaults.

5. Validar flujo operativo end-to-end.
   - CSV -> Consulta -> Dosificador -> Remision -> Inventario -> Laboratorio.
   - Confirmar reportes de Consulta, Dosificador y Laboratorio.
   - Criterio: cada rol completa su flujo sin permisos extra.

6. Cerrar entregabilidad del repositorio.
   - Revisar `git status`.
   - Confirmar archivos archivados/eliminados intencionalmente.
   - Aplicar limpieza de temporales cuando se autorice.
   - Criterio: diff listo para commit o paquete de entrega.

## Definicion de terminado

El proyecto podra considerarse analizado y listo para la siguiente fase cuando:

- Este documento este revisado contra la operacion real esperada.
- Los P0 esten corregidos o aceptados formalmente como bloqueos.
- Exista evidencia actualizada de `verify_instance.py` y `smoke_validation.py`.
- Haya `instance.toml` real para la planta o una decision explicita de operar
  con defaults.
- El backlog este priorizado para implementacion.
- Los pendientes externos esten separados de los pendientes de codigo.
