# Arquitectura Actual

## Objetivo

La aplicacion ya no esta organizada como un monolito unico. El objetivo actual es:

- mantener una sola instancia por planta
- parametrizar branding, limites y features por `instance.toml`
- aislar cada dominio para poder evolucionarlo sin romper el resto

## Backend

### Bootstrap

- `app.py`: ensamblador principal
- `app_feature_routes.py`: registro condicional de modulos por feature
- `auth_routes.py`: login, logout, cambio de contrasena, sesion
- `http_security.py`: CSRF, sesion y decoradores de autorizacion

### Configuracion

- `core/config.py`: carga de configuracion de instancia
- `instance.example.toml`: contrato de parametrizacion
- `verify_instance.py`: validacion rapida de una instalacion nueva

### Persistencia base

- `app_db_init.py`: orquestacion de inicializacion de base
- `app_db_schema.py`: esquema base
- `app_db_migrations.py`: columnas y ajustes incrementales
- `app_db_seed.py`: usuarios default y backfills
- `app_db_runtime.py`: wrappers SQLite/PostgreSQL

### Store principal por mixins

`AppStore` compone mixins por dominio:

- `auth_store.py`
- `dataset_store.py`
- `qc_doser_store.py`
- `remision_store.py`
- `inventory_store.py`
- `fleet_store.py`
- `qc_store.py`
- `user_store.py`

### Dataset / Editor

- `dataset_core_store.py`: dataset activo, auditoria, revision base
- `dataset_catalog_store.py`: bootstrap, insercion, familias, listados
- `dataset_mutation_store.py`: save, delete, purge
- `dataset_upload_store.py`: upload preview/commit
- `dataset_history_store.py`: historial y restore
- `dataset_backup_store.py`: backups y auditoria

### Remisiones

- `remision_store.py`: mutaciones principales
- `remision_query_store.py`: listados y consulta
- `remision_inventory_store.py`: descuento de inventario ligado a remisiones

### Inventario

- `inventory_store.py`: composicion
- `inventory_material_store.py`: catalogo y stock base
- `inventory_transaction_store.py`: kardex y resumen diario
- `inventory_common.py`: adaptadores fila/dict

### Flotilla

- `fleet_store.py`: composicion
- `fleet_vehicle_store.py`: unidades
- `fleet_fuel_store.py`: combustible, resumen, KPIs, tendencias
- `fleet_maintenance_store.py`: mantenimiento y alertas
- `fleet_common.py`: adaptadores fila/dict

### QC / Dosificador

- `qc_doser_store.py`: composicion
- `qc_profile_store.py`: perfiles QC
- `doser_param_store.py`: parametros del dosificador

### Rutas por feature

- `editor_routes.py`
- `doser_routes.py`
- `inventory_routes.py`
- `fleet_routes.py`
- `qc_lab_routes.py`
- `user_routes.py`

### Services / Repositories

Cada modulo HTTP usa:

- `repositories/*`
- `services/*`

La intencion es que las rutas no contengan logica de negocio mas alla de validacion HTTP y mapeo de errores.

## Frontend

### Shell

- `static/js/app.js`: shell principal, navegacion, wiring entre modulos

### Modulos por pestaña

- `static/js/editor.js`
- `static/js/consulta.js`
- `static/js/doser.js`
- `static/js/inventory.js`
- `static/js/fleet.js`
- `static/js/qc_lab.js`
- `static/js/users.js`

### Submodulos internos

#### Editor

- `static/js/editor_table.js`
- `static/js/editor_dataset.js`

#### Consulta

- `static/js/consulta_flow.js`
- `static/js/consulta_costs.js`
- `static/js/consulta_report.js`

#### Dosificador

- `static/js/doser_search.js`
- `static/js/doser_render.js`
- `static/js/doser_reports.js`
- `static/js/doser_params.js`
- `static/js/qc_sync.js`

#### Shell compartido

- `static/js/shell_time.js`
- `static/js/shell_format.js`
- `static/js/shell_ui.js`
- `static/js/shell_recipe_core.js`
- `static/js/shell_dataset_core.js`

## Base de datos

### Modos soportados

- local: SQLite
- produccion: PostgreSQL por `DATABASE_URL`

### Principales tablas

- `datasets`
- `dataset_revisions`
- `upload_staging`
- `qc_profiles`
- `doser_profiles`
- `remisiones`
- `audit_log`
- `materials`
- `inventory_transactions`
- `vehicles`
- `fuel_records`
- `maintenance_records`
- `qc_samples`
- `qc_cylinders`
- `users`
- `auth_locks`

## Pruebas y validacion

- `smoke_validation.py`: regresion funcional de flujos criticos
- `verify_instance.py`: validacion de instalacion/configuracion

## Estado actual

La base ya esta preparada para:

- replicar una instalacion por planta con configuracion propia
- desactivar modulos por feature toggle
- evolucionar backend por dominio sin tocar `app.py`
- seguir refinando frontend sin volver a un estado global monolitico
