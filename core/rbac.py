ROLE_ALLOWED_VIEWS = {
    "administrador": {"editor", "consulta", "dosificador", "remisiones", "flotilla", "inventario", "laboratorio", "usuarios"},
    "jefe-de-planta": {"editor", "consulta", "dosificador", "remisiones", "flotilla", "inventario", "laboratorio"},
    "dosificador": {"dosificador", "remisiones", "flotilla", "inventario"},
    "presupuestador": {"consulta", "remisiones"},
    "laboratorista": {"laboratorio"},
}

EDITOR_ROLES = {"administrador", "jefe-de-planta"}
QC_HUMIDITY_ROLES = {"dosificador"}
QC_LAB_WRITE_ROLES = ("administrador", "laboratorista")

DEFAULT_USERS = (
    {"username": "admin", "role": "administrador", "password": "Admin#2026!"},
    {"username": "jefe_planta", "role": "jefe-de-planta", "password": "Planta#2026!"},
    {"username": "dosificador", "role": "dosificador", "password": "Dosi#2026!"},
    {"username": "presupuestador", "role": "presupuestador", "password": "Presu#2026!"},
    {"username": "laboratorista", "role": "laboratorista", "password": "Lab#2026!"},
)

DEFAULT_USER_PASSWORD = {
    (item["username"] or "").strip().lower(): item["password"]
    for item in DEFAULT_USERS
}


def allowed_views(role: str) -> list[str]:
    return sorted(ROLE_ALLOWED_VIEWS.get(role, set()))


def roles_for_view(view: str) -> tuple[str, ...]:
    return tuple(sorted(role for role, views in ROLE_ALLOWED_VIEWS.items() if view in views))


DOSIFICADOR_ROLES = roles_for_view("dosificador")
REMISIONES_ROLES = roles_for_view("remisiones")
REMISION_DELETE_ROLES = ("administrador", "jefe-de-planta", "dosificador")
LABORATORIO_ROLES = roles_for_view("laboratorio")
