# Instalacion de una Nueva Planta

## 1. Preparar entorno

- instalar Python
- instalar dependencias:

```bash
py -m pip install -r requirements.txt
```

## 2. Crear identidad de instancia

- copiar `instance.example.toml` a `instance.toml`
- ajustar al menos:
  - nombre comercial
  - nombre de planta
  - municipio o referencia local
  - logo
  - colores
  - features habilitados
  - limites operativos

## 3. Configurar variables de entorno

Minimas recomendadas:

- `APP_SECRET_KEY`
- `SESSION_COOKIE_SECURE`
- `APP_TIMEZONE`

Segun modo de base:

- local SQLite: no definir `DATABASE_URL`
- produccion PostgreSQL: definir `DATABASE_URL`

Para entornos productivos:

- dejar `FORMIX_ALLOW_DEFAULT_USERS=0`

## 4. Colocar dataset inicial

Opciones:

- colocar un CSV inicial en la carpeta raiz de la instancia
- o arrancar sin CSV y cargarlo despues desde `Editor CSV`

En el primer arranque, si existe un CSV bootstrap valido, se crea el dataset inicial en base de datos.

## 5. Verificar instalacion antes de arrancar

```bash
py verify_instance.py
```

Esto valida:

- configuracion de instancia
- rutas base
- branding
- features
- modo de base de datos

## 6. Validar humo funcional

```bash
py smoke_validation.py
```

## 7. Arrancar aplicacion

```bash
py app.py
```

Abrir:

```text
http://127.0.0.1:8080
```

## 8. Endurecimiento post-instalacion

- cambiar contrasenas iniciales si se habilitaron usuarios default
- revisar `instance.toml`
- revisar si realmente deben estar activados todos los modulos
- confirmar que backup y carpeta de snapshots tengan permisos correctos

## 9. Checklist de entrega por planta

- `instance.toml` propio
- logo correcto
- timezone correcta
- modulos correctos
- credenciales iniciales cambiadas
- dataset inicial validado
- `verify_instance.py` en verde
- `smoke_validation.py` en verde
