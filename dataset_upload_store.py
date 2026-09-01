from __future__ import annotations

import json
import sqlite3
from datetime import timedelta
from uuid import uuid4

from werkzeug.utils import secure_filename

from core.dataset_ops import (
    apply_header_mapping,
    content_hash,
    guess_family_from_filename,
    norm_header,
    normalize_family_code,
    parse_csv_bytes,
    validate_dataset,
)
from core.time import get_now, now_str


STAGING_TTL_MIN = 30
MODES = {"new", "replace", "merge"}


class DatasetUploadMixin:
    def _cleanup_staging(self, conn: sqlite3.Connection):
        conn.execute("DELETE FROM upload_staging WHERE expires_at < ?", (now_str(),))

    def _dup_by_hash(self, conn: sqlite3.Connection, hash_value: str):
        return conn.execute(
            "SELECT id,name FROM datasets WHERE content_hash=? AND deleted_at IS NULL LIMIT 1",
            (hash_value,),
        ).fetchone()

    def stage_upload_preview(self, uploaded) -> dict:
        if not uploaded or not uploaded.filename:
            raise ValueError("No file selected.")
        fname = secure_filename(uploaded.filename or "")
        if not fname:
            fname = f"uploaded_{get_now().strftime('%Y%m%d_%H%M%S')}.csv"
        if not fname.lower().endswith(".csv"):
            raise ValueError("Only .csv files are allowed.")
        max_upload_bytes = int(getattr(self, "max_upload_bytes", 10 * 1024 * 1024))
        raw = uploaded.stream.read(max_upload_bytes + 1)
        if len(raw) > max_upload_bytes:
            raise ValueError(f"File too large. Max allowed: {max_upload_bytes} bytes.")
        if not raw:
            raise ValueError("Uploaded file is empty.")
        headers, rows, enc, delim = parse_csv_bytes(raw)
        headers, header_mapping = apply_header_mapping(headers)
        validation = validate_dataset(headers, rows)
        current_hash = content_hash(headers, rows)
        token = uuid4().hex
        created = now_str()
        expires = (get_now() + timedelta(minutes=STAGING_TTL_MIN)).strftime("%Y-%m-%d %H:%M:%S")
        with self.lock:
            with self._conn() as conn:
                self._cleanup_staging(conn)
                dup = self._dup_by_hash(conn, current_hash)
                conn.execute(
                    """
                    INSERT INTO upload_staging(token,original_name,headers_json,rows_json,encoding,delimiter,content_hash,validation_json,created_at,expires_at)
                    VALUES(?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        token,
                        fname,
                        json.dumps(headers, ensure_ascii=False),
                        json.dumps(rows, ensure_ascii=False),
                        enc,
                        delim,
                        current_hash,
                        json.dumps(validation, ensure_ascii=False),
                        created,
                        expires,
                    ),
                )
        return {
            "ok": validation["ok"],
            "token": token,
            "file": fname,
            "family_guess": guess_family_from_filename(fname),
            "hash": current_hash,
            "duplicate_of": dup["name"] if dup else None,
            "header_mapping": header_mapping,
            "validation": validation,
            "allowed_modes": ["new", "replace", "merge"],
            "suggested_mode": "merge" if dup else "new",
        }

    def _get_by_name(self, conn: sqlite3.Connection, name: str) -> dict:
        row = conn.execute("SELECT id FROM datasets WHERE name=? AND deleted_at IS NULL", (name,)).fetchone()
        if not row:
            raise FileNotFoundError(f"Dataset not found: {name}")
        return self._load_by_id(conn, int(row["id"]))

    def _merge_rows(
        self,
        target_headers: list[str],
        target_rows: list[list[str]],
        incoming_headers: list[str],
        incoming_rows: list[list[str]],
    ) -> tuple[list[list[str]], int, int]:
        tnorm = [norm_header(h) for h in target_headers]
        inorm = [norm_header(h) for h in incoming_headers]
        if set(tnorm) != set(inorm):
            missing = sorted(set(tnorm) - set(inorm))
            extra = sorted(set(inorm) - set(tnorm))
            raise ValueError(f"Headers mismatch for merge. Missing: {missing}. Extra: {extra}.")
        index_map = {header: index for index, header in enumerate(inorm)}
        aligned = [[row[index_map[key]] for key in tnorm] for row in incoming_rows]
        key_preference_groups = [
            ("formula",),
            ("fc",),
            ("edad",),
            ("tipo", "coloc"),
            ("tma",),
            ("rev",),
            ("comp", "var", "complemento"),
            ("cod",),
        ]
        key_order = []
        for options in key_preference_groups:
            selected = next((key for key in options if key in tnorm), None)
            if selected:
                key_order.append(selected)
        idxs = [tnorm.index(key) for key in key_order] or list(range(len(target_headers)))

        def key_of(row: list[str]) -> tuple:
            key = tuple((row[index] or "").strip().lower() for index in idxs)
            if any(key):
                return key
            return tuple((cell or "").strip().lower() for cell in row)

        merged = [list(row) for row in target_rows]
        pos = {key_of(row): index for index, row in enumerate(merged)}
        inserted = 0
        updated = 0
        for row in aligned:
            key = key_of(row)
            if key in pos:
                merged[pos[key]] = row
                updated += 1
            else:
                merged.append(row)
                pos[key] = len(merged) - 1
                inserted += 1
        return merged, inserted, updated

    def commit_staged_upload(
        self,
        token: str,
        mode: str,
        target_name: str | None = None,
        family_code: str | None = None,
        actor: str = "",
    ) -> dict:
        if mode not in MODES:
            raise ValueError("Mode must be new|replace|merge.")
        fam_override = normalize_family_code(family_code, allow_empty=True) if family_code is not None else None
        with self.lock:
            self._snapshot_db(f"before_upload_{mode}")
            with self._conn() as conn:
                self._cleanup_staging(conn)
                st = conn.execute("SELECT * FROM upload_staging WHERE token=?", (token,)).fetchone()
                if not st:
                    raise FileNotFoundError("Upload token not found or expired.")
                validation = json.loads(st["validation_json"])
                if not validation.get("ok", False):
                    raise ValueError("Cannot commit invalid upload.")
                headers = json.loads(st["headers_json"])
                rows = json.loads(st["rows_json"])
                current_hash = st["content_hash"]
                dup = self._dup_by_hash(conn, current_hash)
                result = {"mode": mode, "inserted": 0, "updated": 0, "replaced": 0, "rows": len(rows)}
                if mode == "new":
                    if dup:
                        raise ValueError(
                            f"Duplicate content detected with dataset '{dup['name']}'. Use replace or merge."
                        )
                    fam_to_use = fam_override if fam_override else guess_family_from_filename(st["original_name"])
                    did = self._insert_dataset(
                        conn,
                        st["original_name"],
                        headers,
                        rows,
                        st["encoding"],
                        st["delimiter"],
                        family_code=fam_to_use,
                    )
                    self._set_active(conn, did)
                    loaded = self._load_by_id(conn, did)
                    result["file"] = loaded["name"]
                    result["family"] = loaded["family_code"]
                elif mode == "replace":
                    if target_name:
                        ds = self._get_by_name(conn, target_name)
                    else:
                        aid = self._active_id(conn)
                        if aid is None:
                            raise FileNotFoundError("No active dataset.")
                        ds = self._load_by_id(conn, aid)
                    self._save_revision(conn, ds, f"before replace by upload token {token}")
                    conn.execute(
                        """
                        UPDATE datasets
                        SET headers_json=?, rows_json=?, encoding=?, delimiter=?, content_hash=?, row_count=?, family_code=COALESCE(NULLIF(?,''),family_code), updated_at=?, version=version+1
                        WHERE id=?
                        """,
                        (
                            json.dumps(headers, ensure_ascii=False),
                            json.dumps(rows, ensure_ascii=False),
                            st["encoding"],
                            st["delimiter"],
                            current_hash,
                            len(rows),
                            fam_override or "",
                            now_str(),
                            ds["id"],
                        ),
                    )
                    self._set_active(conn, ds["id"])
                    result["file"] = ds["name"]
                    result["replaced"] = len(rows)
                    refreshed = self._load_by_id(conn, ds["id"])
                    result["family"] = refreshed["family_code"]
                else:
                    if target_name:
                        ds = self._get_by_name(conn, target_name)
                    else:
                        aid = self._active_id(conn)
                        if aid is None:
                            raise FileNotFoundError("No active dataset.")
                        ds = self._load_by_id(conn, aid)
                    merged, inserted, updated = self._merge_rows(ds["headers"], ds["rows"], headers, rows)
                    self._save_revision(conn, ds, f"before merge by upload token {token}")
                    merged_hash = content_hash(ds["headers"], merged)
                    conn.execute(
                        """
                        UPDATE datasets
                        SET rows_json=?, content_hash=?, row_count=?, family_code=COALESCE(NULLIF(?,''),family_code), updated_at=?, version=version+1
                        WHERE id=?
                        """,
                        (
                            json.dumps(merged, ensure_ascii=False),
                            merged_hash,
                            len(merged),
                            fam_override or "",
                            now_str(),
                            ds["id"],
                        ),
                    )
                    self._set_active(conn, ds["id"])
                    result["file"] = ds["name"]
                    result["inserted"] = inserted
                    result["updated"] = updated
                    refreshed = self._load_by_id(conn, ds["id"])
                    result["family"] = refreshed["family_code"]
                conn.execute("DELETE FROM upload_staging WHERE token=?", (token,))
                dataset_id = None
                if result.get("file"):
                    try:
                        dataset_id = self._get_by_name(conn, result["file"])["id"]
                    except Exception:
                        dataset_id = None
                self._audit(
                    conn,
                    action="dataset.upload.commit",
                    username=actor,
                    entity="dataset",
                    entity_id=str(dataset_id or ""),
                    dataset_id=dataset_id,
                    details={
                        "mode": mode,
                        "file": result.get("file", ""),
                        "inserted": int(result.get("inserted", 0) or 0),
                        "updated": int(result.get("updated", 0) or 0),
                        "replaced": int(result.get("replaced", 0) or 0),
                        "rows": int(result.get("rows", 0) or 0),
                    },
                )
                return result
