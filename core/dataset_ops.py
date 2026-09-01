import csv
import hashlib
import io
import json
import re
import unicodedata
from pathlib import Path

from core.qc import QC_AGGREGATES, QC_FIELDS, default_qc_values


MAX_ROWS = 100_000
MAX_COLUMNS = 400
DOSER_PARAM_FIELDS = (
    "cemento_pesp",
    "aire_pct",
    "pasa_malla_200_pct",
    "pxl_pond_pct",
    "densidad_agregado_fallback",
)
CANONICAL_HEADER_ALIASES = {
    "no": ("no", "numero", "num", "n"),
    "formula": ("formula", "formulacion", "mix", "diseno", "diseño"),
    "cod": ("cod", "codigo", "clave"),
    "fc": ("fc", "fcr", "resistencia", "resistenciadiseno", "resistenciadiseño"),
    "edad": ("edad", "dias", "dia"),
    "tipo": ("tipo", "coloc", "colocacion", "colocación"),
    "tma": ("tma", "tmamax", "tamanoagregado", "tamanomaximoagregado", "tamañomaximoagregado"),
    "rev": ("rev", "revenimiento", "slump"),
    "comp": ("comp", "complemento", "var", "aditivo"),
    "family": ("familia", "family", "familia_mix", "fam"),
    "fecha_modif": ("fechamodif", "fechamodificacion", "ultimafecha", "modificado"),
}
CANONICAL_HEADER_DISPLAY = {
    "no": "No",
    "formula": "Formula",
    "cod": "COD",
    "fc": "f'c",
    "edad": "Edad",
    "tipo": "Tipo",
    "tma": "T.M.A.",
    "rev": "Rev",
    "comp": "Comp",
    "family": "Familia",
    "fecha_modif": "FECHA_MODIF",
}


def configure_dataset_limits(*, max_rows: int | None = None, max_columns: int | None = None):
    global MAX_ROWS, MAX_COLUMNS
    if max_rows is not None:
        MAX_ROWS = int(max_rows)
    if max_columns is not None:
        MAX_COLUMNS = int(max_columns)


def norm_header(text: str) -> str:
    base = re.sub(r"\s*\([^)]*\)\s*$", "", (text or "").strip())
    decomp = unicodedata.normalize("NFD", base)
    no_acc = "".join(ch for ch in decomp if unicodedata.category(ch) != "Mn")
    return re.sub(r"[^a-zA-Z0-9]", "", no_acc).lower()


def sanitize_cell(value: str) -> str:
    text = str(value).replace("\x00", "").strip()
    if not text:
        return ""
    if text[0] in ("=", "@"):
        return "'" + text
    if text[0] in ("+", "-"):
        if re.fullmatch(r"[+-]?\d+([.,]\d+)?", text):
            return text
        return "'" + text
    return text


def detect_encoding(raw: bytes) -> str:
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            raw.decode(enc)
            return enc
        except UnicodeDecodeError:
            continue
    return "latin-1"


def detect_delim(text: str) -> str:
    try:
        return csv.Sniffer().sniff(text[:8192], delimiters=";,|\t").delimiter
    except csv.Error:
        return ";"


def parse_csv_bytes(raw: bytes) -> tuple[list[str], list[list[str]], str, str]:
    encoding = detect_encoding(raw)
    text = raw.decode(encoding, errors="replace")
    delim = detect_delim(text)
    rows = list(csv.reader(io.StringIO(text), delimiter=delim))
    if not rows:
        return [], [], encoding, delim
    headers = [sanitize_cell(h) for h in rows[0]]
    width = len(headers)
    body = []
    for row in rows[1:]:
        norm = (row + [""] * width)[:width]
        body.append([sanitize_cell(v) for v in norm])
    return headers, body, encoding, delim


def content_hash(headers: list[str], rows: list[list[str]]) -> str:
    payload = json.dumps({"headers": headers, "rows": rows}, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def normalize_family_code(value: str | None, allow_empty: bool = False) -> str:
    text = (value or "").strip().upper()
    if not text:
        if allow_empty:
            return ""
        raise ValueError("La familia es requerida.")
    if not re.fullmatch(r"[A-Z0-9]{1,12}", text):
        raise ValueError("Formato de familia invalido. Usa solo letras/numeros (max 12).")
    return text


def guess_family_from_filename(filename: str | None) -> str:
    stem = Path((filename or "").strip()).stem.upper()
    if not stem:
        return ""
    explicit = re.search(r"(?:^|[_-])FAM(?:ILIA)?[_-]?([A-Z0-9]{1,12})(?:[_-]|$)", stem)
    if explicit:
        try:
            return normalize_family_code(explicit.group(1), allow_empty=False)
        except ValueError:
            pass
    lead_digits = re.match(r"^\s*(\d{2,6})", stem)
    if lead_digits:
        digits = lead_digits.group(1)
        if len(digits) >= 4:
            return digits[:2]
        return digits
    token = re.search(r"(?:^|[_-])([A-Z]?\d{2,3})(?:[_-]|$)", stem)
    if token:
        candidate = token.group(1)
        try:
            return normalize_family_code(candidate, allow_empty=False)
        except ValueError:
            return ""
    return ""


def normalize_remision_no(value: str | None) -> str:
    text = (value or "").strip().upper()
    if not text:
        raise ValueError("El numero de remision es requerido.")
    if not re.fullmatch(r"[A-Z0-9/_-]{1,40}", text):
        raise ValueError("Formato de remision invalido. Usa letras/numeros y - _ / (max 40).")
    return text


def canonical_key_for_header(header: str) -> str | None:
    normalized = norm_header(header)
    if not normalized:
        return None
    for canonical, aliases in CANONICAL_HEADER_ALIASES.items():
        if normalized in {norm_header(alias) for alias in aliases}:
            return canonical
    return None


def apply_header_mapping(headers: list[str]) -> tuple[list[str], list[dict[str, str]]]:
    mapped = []
    changes = []
    used = set()
    for raw in headers:
        source = sanitize_cell(raw)
        canonical = canonical_key_for_header(source)
        target = source
        if canonical:
            candidate = CANONICAL_HEADER_DISPLAY.get(canonical, source)
            if candidate not in used:
                target = candidate
        if target in used:
            base = target or "Columna"
            suffix = 2
            while f"{base}_{suffix}" in used:
                suffix += 1
            target = f"{base}_{suffix}"
        used.add(target)
        mapped.append(target)
        if source != target:
            changes.append({"from": source, "to": target})
    return mapped, changes


def validate_dataset(headers: list[str], rows: list[list[str]]) -> dict:
    errors, warnings = [], []
    normalized_headers = [norm_header(header) for header in headers]
    header_set = set(normalized_headers)
    if len(headers) == 0:
        errors.append("El CSV no contiene encabezados.")
    if len(headers) > MAX_COLUMNS:
        errors.append(f"El CSV excede el maximo de columnas ({MAX_COLUMNS}).")
    if len(rows) > MAX_ROWS:
        errors.append(f"El CSV excede el maximo de filas ({MAX_ROWS}).")
    req_groups = {
        "formula": {"formula"},
        "cod": {"cod"},
        "fc": {"fc"},
        "edad": {"edad"},
        "coloc": {"coloc", "tipo"},
        "tma": {"tma"},
        "rev": {"rev"},
        "comp": {"var", "comp", "complemento"},
    }
    missing = [name for name, keys in req_groups.items() if not (header_set & keys)]
    if missing:
        errors.append(f"Faltan columnas requeridas: {', '.join(missing)}")
    duplicates = sorted({header for header in headers if headers.count(header) > 1})
    if duplicates:
        warnings.append("Encabezados duplicados: " + ", ".join(duplicates))
    return {
        "ok": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "stats": {"rows": len(rows), "columns": len(headers)},
    }


def _to_qc_number(value) -> float:
    text = str(value if value is not None else "").strip().replace(",", ".")
    if text == "":
        return 0.0
    num = float(text)
    if num < 0:
        raise ValueError("Los valores de control de calidad no pueden ser negativos.")
    if num > 1_000_000:
        raise ValueError("Un valor de control de calidad excede el limite permitido.")
    return num


def sanitize_qc_values(values: dict | None) -> dict:
    src = values if isinstance(values, dict) else {}
    clean = default_qc_values()
    for aggregate in QC_AGGREGATES:
        row = src.get(aggregate) if isinstance(src.get(aggregate), dict) else {}
        for field in QC_FIELDS:
            clean[aggregate][field] = _to_qc_number(row.get(field, 0))
    return clean


def default_doser_params() -> dict:
    return {
        "cemento_pesp": 3.10,
        "aire_pct": 2.0,
        "pasa_malla_200_pct": 19.0,
        "pxl_pond_pct": 6.4,
        "densidad_agregado_fallback": 2.20,
    }


def sanitize_doser_params(values: dict | None) -> dict:
    src = values if isinstance(values, dict) else {}
    base = default_doser_params()
    clean = {}
    for field in DOSER_PARAM_FIELDS:
        raw = src.get(field, base[field])
        text = str(raw if raw is not None else "").strip().replace(",", ".")
        num = float(text) if text else float(base[field])
        if num < 0:
            raise ValueError(f"Parametro invalido ({field}): no puede ser negativo.")
        if num > 1_000_000:
            raise ValueError(f"Parametro invalido ({field}): excede el limite permitido.")
        clean[field] = num
    return clean
