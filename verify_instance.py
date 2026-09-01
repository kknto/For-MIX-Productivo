import os
import sys
import importlib.util
from pathlib import Path


KNOWN_FEATURES = {
    "editor",
    "consulta",
    "dosificador",
    "remisiones",
    "inventario",
    "laboratorio",
    "flotilla",
    "usuarios",
}


def load_settings_loader():
    config_path = Path(__file__).resolve().parent / "core" / "config.py"
    spec = importlib.util.spec_from_file_location("formix_core_config", config_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module.load_instance_settings


def check(condition: bool, label: str, detail: str = "") -> bool:
    status = "OK" if condition else "FAIL"
    suffix = f" - {detail}" if detail else ""
    print(f"[{status}] {label}{suffix}")
    return condition


def main() -> int:
    base_dir = Path.cwd()
    load_instance_settings = load_settings_loader()
    settings = load_instance_settings(base_dir)
    failures = 0

    print("ForMIX instance verification")
    print(f"Base dir: {settings.base_dir}")
    print(f"Instance file: {settings.instance_file}")
    print("")

    if not check(settings.base_dir.exists(), "Base directory exists", str(settings.base_dir)):
        failures += 1

    instance_exists = settings.instance_file.exists()
    if instance_exists:
        check(True, "instance.toml present", str(settings.instance_file))
    else:
        print("[WARN] instance.toml present - using defaults")
        print("[WARN] No instance.toml found. The app will run with built-in defaults.")

    if not check(settings.database_mode in {"auto", "sqlite", "postgres"}, "Database mode", settings.database_mode):
        failures += 1

    uses_postgres = settings.database_mode == "postgres" or bool(os.getenv("DATABASE_URL"))
    if uses_postgres:
        if not check(bool(os.getenv("DATABASE_URL")), "DATABASE_URL set for postgres mode"):
            failures += 1
    else:
        sqlite_parent = settings.sqlite_db_path.parent
        if not check(sqlite_parent.exists(), "SQLite directory exists", str(sqlite_parent)):
            failures += 1

    snapshot_root = settings.snapshot_dir.parent if settings.snapshot_dir.parent.exists() else settings.snapshot_dir.parent.parent
    if not check(snapshot_root.exists(), "Snapshot path root exists", str(snapshot_root)):
        failures += 1

    qc_uploads_root = settings.qc_uploads_dir.parent if settings.qc_uploads_dir.parent.exists() else settings.qc_uploads_dir.parent.parent
    if not check(qc_uploads_root.exists(), "QC uploads path root exists", str(qc_uploads_root)):
        failures += 1

    logo_path = settings.base_dir / "static" / Path(settings.logo_path)
    if not check(logo_path.exists(), "Brand logo exists", str(logo_path)):
        failures += 1

    if not check(settings.timezone.strip() != "", "Timezone configured", settings.timezone):
        failures += 1

    if not check(settings.max_upload_bytes > 0, "Upload limit is positive", str(settings.max_upload_bytes)):
        failures += 1

    if not check(settings.max_rows > 0, "Row limit is positive", str(settings.max_rows)):
        failures += 1

    if not check(settings.max_columns > 0, "Column limit is positive", str(settings.max_columns)):
        failures += 1

    unknown_features = sorted(set(settings.features) - KNOWN_FEATURES)
    if not check(not unknown_features, "Feature keys are recognized", ", ".join(unknown_features)):
        failures += 1

    enabled_views = sorted(name for name, enabled in settings.features.items() if enabled)
    if not check(bool(enabled_views), "At least one feature enabled", ", ".join(enabled_views)):
        failures += 1

    secret_ready = bool(os.getenv("APP_SECRET_KEY")) or settings.secret_file.exists()
    if not check(secret_ready, "App secret available", "env" if os.getenv("APP_SECRET_KEY") else str(settings.secret_file)):
        failures += 1

    print("")
    print("Enabled features:", ", ".join(enabled_views) if enabled_views else "-")
    print("Brand:", settings.brand_name)
    print("Plant:", settings.plant_name)

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
