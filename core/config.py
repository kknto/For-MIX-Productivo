import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path


def _as_bool(value, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    return default


def _section(data: dict, name: str) -> dict:
    value = data.get(name, {})
    return value if isinstance(value, dict) else {}


@dataclass(frozen=True)
class InstanceSettings:
    base_dir: Path
    instance_file: Path
    secret_file: Path
    sqlite_db_path: Path
    snapshot_dir: Path
    qc_uploads_dir: Path
    site_title: str
    login_title: str
    brand_name: str
    product_name: str
    plant_name: str
    municipality: str
    timezone: str
    logo_path: str
    brand_tagline: str
    system_subtitle: str
    admin_subtitle: str
    database_mode: str
    session_cookie_secure: bool
    allow_default_users: bool
    max_upload_bytes: int
    max_rows: int
    max_columns: int
    features: dict[str, bool] = field(default_factory=dict)

    def template_context(self) -> dict:
        return {
            "site_title": self.site_title,
            "login_title": self.login_title,
            "brand_name": self.brand_name,
            "product_name": self.product_name,
            "plant_name": self.plant_name,
            "municipality": self.municipality,
            "timezone": self.timezone,
            "logo_path": self.logo_path,
            "brand_tagline": self.brand_tagline,
            "system_subtitle": self.system_subtitle,
            "admin_subtitle": self.admin_subtitle,
            "features": dict(self.features),
        }


def load_instance_settings(base_dir: Path) -> InstanceSettings:
    base_dir = base_dir.resolve()
    instance_file = base_dir / "instance.toml"
    data = {}
    if instance_file.exists():
        data = tomllib.loads(instance_file.read_text(encoding="utf-8"))

    instance = _section(data, "instance")
    paths = _section(data, "paths")
    limits = _section(data, "limits")
    security = _section(data, "security")
    feature_section = _section(data, "features")
    features = {
        "editor": True,
        "consulta": True,
        "dosificador": True,
        "remisiones": True,
        "inventario": True,
        "laboratorio": True,
        "flotilla": True,
        "usuarios": True,
    }
    features.update(feature_section)
    if "remisiones" not in feature_section:
        features["remisiones"] = bool(features.get("dosificador", True))

    brand_name = str(instance.get("brand_name") or "ForMIX")
    product_name = str(instance.get("product_name") or "ForMIX")
    plant_name = str(instance.get("plant_name") or "Planta Base")
    municipality = str(instance.get("municipality") or "Municipio Base")
    site_title = str(instance.get("site_title") or f"{brand_name} | Control de Planta")
    login_title = str(instance.get("login_title") or f"Acceso - {brand_name}")
    timezone = (
        os.getenv("APP_TIMEZONE", "").strip()
        or str(instance.get("timezone") or "").strip()
        or os.getenv("TZ", "").strip()
        or "America/Cancun"
    )
    database_mode = str(instance.get("database_mode") or "auto")
    session_cookie_secure = _as_bool(
        os.getenv("SESSION_COOKIE_SECURE"),
        default=_as_bool(security.get("session_cookie_secure"), default=False),
    )

    default_allow_users = not bool(os.getenv("DATABASE_URL"))
    allow_default_users = _as_bool(
        os.getenv("FORMIX_ALLOW_DEFAULT_USERS"),
        default=_as_bool(security.get("allow_default_users"), default=default_allow_users),
    )

    sqlite_db_path = base_dir / str(paths.get("sqlite_db_path") or "mix_data.sqlite3")
    snapshot_dir = base_dir / str(paths.get("snapshot_dir") or "backups/db_snapshots")
    qc_uploads_dir = base_dir / str(paths.get("qc_uploads_dir") or "static/uploads/qc_images")

    return InstanceSettings(
        base_dir=base_dir,
        instance_file=instance_file,
        secret_file=base_dir / ".app_secret_key",
        sqlite_db_path=sqlite_db_path,
        snapshot_dir=snapshot_dir,
        qc_uploads_dir=qc_uploads_dir,
        site_title=site_title,
        login_title=login_title,
        brand_name=brand_name,
        product_name=product_name,
        plant_name=plant_name,
        municipality=municipality,
        timezone=timezone,
        logo_path=str(instance.get("logo_path") or "img/logo_formix.svg"),
        brand_tagline=str(instance.get("brand_tagline") or "ForMIX Pilot"),
        system_subtitle=str(
            instance.get("system_subtitle")
            or "Sistema base para control operativo de planta de concreto"
        ),
        admin_subtitle=str(
            instance.get("admin_subtitle")
            or "Modulo de administracion parametrizable"
        ),
        database_mode=database_mode,
        session_cookie_secure=session_cookie_secure,
        allow_default_users=allow_default_users,
        max_upload_bytes=int(limits.get("max_upload_bytes") or 10 * 1024 * 1024),
        max_rows=int(limits.get("max_rows") or 100_000),
        max_columns=int(limits.get("max_columns") or 400),
        features=features,
    )
