from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from core.dataset_ops import (
    CANONICAL_HEADER_ALIASES,
    apply_header_mapping,
    content_hash,
    guess_family_from_filename,
    norm_header,
    normalize_family_code,
    parse_csv_bytes,
    validate_dataset,
)
from core.time import now_str


class DatasetCatalogMixin:
    def _insert_dataset(
        self,
        conn,
        name: str,
        headers: list[str],
        rows: list[list[str]],
        encoding: str,
        delimiter: str,
        family_code: str | None = None,
    ) -> int:
        base = name.strip() or "dataset.csv"
        candidate = base
        idx = 1
        while True:
            row = conn.execute("SELECT id, deleted_at FROM datasets WHERE name=?", (candidate,)).fetchone()
            if not row:
                break
            if row["deleted_at"] is not None:
                old_id = int(row["id"])
                unique_suffix = f"__deleted__{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
                conn.execute("UPDATE datasets SET name=name || ? WHERE id=?", (unique_suffix, old_id))
                break
            candidate = f"{Path(base).stem}_{idx}{Path(base).suffix or '.csv'}"
            idx += 1
        current_hash = content_hash(headers, rows)
        created = now_str()
        fam = (
            normalize_family_code(family_code, allow_empty=True)
            if family_code is not None
            else guess_family_from_filename(candidate)
        )
        cur = conn.execute(
            """
            INSERT INTO datasets(name,family_code,headers_json,rows_json,encoding,delimiter,content_hash,row_count,created_at,updated_at,version,deleted_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,1,NULL)
            """,
            (
                candidate,
                fam,
                json.dumps(headers, ensure_ascii=False),
                json.dumps(rows, ensure_ascii=False),
                encoding,
                delimiter,
                current_hash,
                len(rows),
                created,
                created,
            ),
        )
        if self.is_postgres:
            row = conn.execute(
                "SELECT id FROM datasets WHERE name=? AND deleted_at IS NULL ORDER BY id DESC LIMIT 1",
                (candidate,),
            ).fetchone()
            return int(row["id"])
        return int(cur.lastrowid)

    def _bootstrap(self, csv_file: str | None):
        with self.lock:
            with self._conn() as conn:
                count = conn.execute("SELECT COUNT(*) c FROM datasets WHERE deleted_at IS NULL").fetchone()["c"]
                if count > 0:
                    if self._active_id(conn) is None:
                        first = conn.execute("SELECT id FROM datasets WHERE deleted_at IS NULL ORDER BY id LIMIT 1").fetchone()
                        if first:
                            self._set_active(conn, int(first["id"]))
                    return
                path = (self.base_dir / csv_file).resolve() if csv_file else None
                if not path or not path.exists():
                    candidates = sorted(self.base_dir.glob("*.csv"))
                    path = candidates[0] if candidates else None
                if path and path.exists():
                    headers, rows, enc, delim = parse_csv_bytes(path.read_bytes())
                    headers, _ = apply_header_mapping(headers)
                    validation = validate_dataset(headers, rows)
                    if not validation["ok"]:
                        raise ValueError("CSV inicial invalido: " + "; ".join(validation["errors"]))
                    did = self._insert_dataset(conn, path.name, headers, rows, enc, delim)
                else:
                    did = self._insert_dataset(conn, "dataset_principal.csv", [], [], "utf-8", ";")
                self._set_active(conn, did)

    def list_file_infos(self) -> list[dict[str, str]]:
        with self._conn() as conn:
            rows = conn.execute("SELECT name,family_code FROM datasets WHERE deleted_at IS NULL ORDER BY name").fetchall()
            return [{"name": row["name"], "family": (row["family_code"] or "").strip()} for row in rows]

    def list_files(self) -> list[str]:
        return [item["name"] for item in self.list_file_infos()]

    def get_all_recipes_global(self) -> list[dict]:
        global_list = []
        with self._conn() as conn:
            datasets = conn.execute(
                "SELECT id, name, family_code, headers_json, rows_json, updated_at FROM datasets WHERE deleted_at IS NULL"
            ).fetchall()
            for ds in datasets:
                try:
                    headers = json.loads(ds["headers_json"])
                    rows = json.loads(ds["rows_json"])
                    family_ds = (ds["family_code"] or "").strip()
                    updated = ds["updated_at"]
                    norm_headers = [norm_header(h) for h in headers]
                    for row in rows:
                        entry = {"_source": ds["name"], "_updated": updated}
                        for index, header in enumerate(norm_headers):
                            if index < len(row):
                                entry[header] = row[index]
                        if not entry.get("family") and family_ds:
                            entry["family"] = family_ds
                        global_list.append(entry)
                except Exception:
                    continue
        return global_list

    def get_all_families_summary(self) -> list[dict]:
        summary = {}
        with self._conn() as conn:
            datasets = conn.execute(
                "SELECT id, name, family_code, headers_json, rows_json FROM datasets WHERE deleted_at IS NULL"
            ).fetchall()
            for ds in datasets:
                try:
                    headers = json.loads(ds["headers_json"])
                    rows = json.loads(ds["rows_json"])
                    tma_idx = -1
                    fam_idx = -1
                    for index, header in enumerate(headers):
                        normalized = norm_header(header)
                        if any(alias in normalized for alias in CANONICAL_HEADER_ALIASES["tma"]):
                            tma_idx = index
                        if any(alias in normalized for alias in CANONICAL_HEADER_ALIASES["family"]):
                            fam_idx = index
                    for row in rows:
                        tma = str(row[tma_idx]).strip() if 0 <= tma_idx < len(row) else "Sin TMA"
                        row_fam = str(row[fam_idx]).strip() if 0 <= fam_idx < len(row) else ""
                        family = (ds["family_code"] or row_fam or "Sin Familia").strip()
                        key = (tma, family)
                        if key not in summary:
                            summary[key] = {"tma": tma, "family": family, "file": ds["name"], "count": 0}
                        summary[key]["count"] += 1
                except Exception:
                    continue
        result = list(summary.values())
        result.sort(key=lambda item: (item["tma"], item["family"]))
        return result

    def set_dataset_family(self, family_code: str, dataset_name: str | None = None, actor: str = "") -> dict[str, str]:
        fam = normalize_family_code(family_code, allow_empty=False)
        with self.lock:
            self._snapshot_db("before_family_update")
            with self._conn() as conn:
                ds = self._resolve_dataset(conn, dataset_name)
                conn.execute(
                    "UPDATE datasets SET family_code=?, updated_at=?, version=version+1 WHERE id=?",
                    (fam, now_str(), ds["id"]),
                )
                self._audit(
                    conn,
                    action="dataset.family.update",
                    username=actor,
                    entity="dataset",
                    entity_id=str(ds["id"]),
                    dataset_id=ds["id"],
                    details={"file": ds["name"], "family": fam},
                )
                return {"file": ds["name"], "family": fam}

    def load_active(self) -> dict:
        with self.lock:
            with self._conn() as conn:
                did = self._active_id(conn)
                if did is None:
                    raise FileNotFoundError("No active dataset.")
                return self._load_by_id(conn, did)

    def set_active_file(self, dataset_name: str) -> str:
        clean = (dataset_name or "").strip()
        if not clean:
            raise ValueError("Dataset name is required.")
        with self.lock:
            with self._conn() as conn:
                row = conn.execute("SELECT id FROM datasets WHERE name=? AND deleted_at IS NULL", (clean,)).fetchone()
                if not row:
                    raise FileNotFoundError(f"Dataset not found: {clean}")
                self._set_active(conn, int(row["id"]))
                return clean
