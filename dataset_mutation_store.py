from __future__ import annotations

import json
from datetime import datetime

from core.dataset_ops import content_hash, sanitize_cell, validate_dataset
from core.errors import ConcurrencyError
from core.time import now_str


class DatasetMutationMixin:
    def save_active(
        self,
        headers: list[str],
        rows: list[list[str]],
        expected_version: int | None = None,
        actor: str = "",
    ) -> int:
        validation = validate_dataset(headers, rows)
        if not validation["ok"]:
            raise ValueError("; ".join(validation["errors"]))
        width = len(headers)
        clean_rows = [[sanitize_cell(x) for x in (row + [""] * width)[:width]] for row in rows]
        with self.lock:
            self._snapshot_db("before_save")
            with self._conn() as conn:
                did = self._active_id(conn)
                if did is None:
                    raise FileNotFoundError("No active dataset.")
                ds = self._load_by_id(conn, did)
                if expected_version is not None and ds["version"] != expected_version:
                    raise ConcurrencyError(
                        f"Version conflict. Current version is {ds['version']}, expected {expected_version}."
                    )
                self._save_revision(conn, ds, "before save from editor")
                new_ver = ds["version"] + 1
                conn.execute(
                    """
                    UPDATE datasets
                    SET headers_json=?, rows_json=?, content_hash=?, row_count=?, updated_at=?, version=?
                    WHERE id=?
                    """,
                    (
                        json.dumps(headers, ensure_ascii=False),
                        json.dumps(clean_rows, ensure_ascii=False),
                        content_hash(headers, clean_rows),
                        len(clean_rows),
                        now_str(),
                        new_ver,
                        did,
                    ),
                )
                self._audit(
                    conn,
                    action="dataset.save",
                    username=actor,
                    entity="dataset",
                    entity_id=str(did),
                    dataset_id=did,
                    details={"file": ds["name"], "rows": len(clean_rows), "version": new_ver},
                )
                return new_ver

    def delete_file(self, dataset_name: str, actor: str = "") -> dict[str, str]:
        clean = (dataset_name or "").strip()
        if not clean:
            raise ValueError("Dataset name is required.")
        with self.lock:
            self._snapshot_db("before_delete")
            with self._conn() as conn:
                row = conn.execute("SELECT id FROM datasets WHERE name=? AND deleted_at IS NULL", (clean,)).fetchone()
                if not row:
                    raise FileNotFoundError(f"Dataset not found: {clean}")
                count = conn.execute("SELECT COUNT(*) c FROM datasets WHERE deleted_at IS NULL").fetchone()["c"]
                if count <= 1:
                    raise ValueError("No puedes eliminar el unico dataset disponible.")
                did = int(row["id"])
                ts = now_str()
                unique_suffix = f"__deleted__{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
                new_name = f"{clean}{unique_suffix}"
                conn.execute("UPDATE datasets SET name=?, deleted_at=? WHERE id=?", (new_name, ts, did))
                self._audit(
                    conn,
                    action="dataset.delete",
                    username=actor,
                    entity="dataset",
                    entity_id=str(did),
                    dataset_id=did,
                    details={"file": clean, "renamed_to": new_name},
                )
                aid = self._active_id(conn)
                if aid == did or aid is None:
                    nxt = conn.execute("SELECT id,name FROM datasets WHERE deleted_at IS NULL ORDER BY id LIMIT 1").fetchone()
                    self._set_active(conn, int(nxt["id"]))
                    active_name = nxt["name"]
                else:
                    active_name = self._load_by_id(conn, aid)["name"]
                return {"deleted": clean, "active": active_name}

    def purge_deleted_datasets(self, actor: str = "") -> dict:
        with self.lock:
            self._snapshot_db("before_purge")
            with self._conn() as conn:
                rows = conn.execute("SELECT id, name FROM datasets WHERE deleted_at IS NOT NULL").fetchall()
                if not rows:
                    return {"purged_count": 0, "message": "No hay datasets borrados para purgar."}
                deleted_ids = [int(row["id"]) for row in rows]
                deleted_names = [row["name"] for row in rows]
                placeholders = ",".join("?" * len(deleted_ids))
                rem_rows = conn.execute(
                    f"SELECT remision_no FROM remisiones WHERE dataset_id IN ({placeholders})",
                    tuple(deleted_ids),
                ).fetchall()
                remision_nos = [row["remision_no"] for row in rem_rows]
                if remision_nos:
                    for remision_no in remision_nos:
                        conn.execute("DELETE FROM inventory_transactions WHERE reference=?", (f"Remision #{remision_no}",))
                conn.execute(f"DELETE FROM remisiones WHERE dataset_id IN ({placeholders})", tuple(deleted_ids))
                conn.execute(f"DELETE FROM dataset_revisions WHERE dataset_id IN ({placeholders})", tuple(deleted_ids))
                conn.execute(f"DELETE FROM qc_profiles WHERE dataset_id IN ({placeholders})", tuple(deleted_ids))
                conn.execute(f"DELETE FROM doser_profiles WHERE dataset_id IN ({placeholders})", tuple(deleted_ids))
                conn.execute(f"UPDATE audit_log SET dataset_id = NULL WHERE dataset_id IN ({placeholders})", tuple(deleted_ids))
                conn.execute(f"DELETE FROM datasets WHERE id IN ({placeholders})", tuple(deleted_ids))
                self._audit(
                    conn,
                    action="datasets.purge",
                    username=actor,
                    entity="system",
                    entity_id="bulk_purge",
                    details={"files_purged": deleted_names},
                )
                return {"purged_count": len(deleted_ids), "files": deleted_names}
