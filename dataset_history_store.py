from __future__ import annotations

import json

from core.dataset_ops import content_hash
from core.errors import ConcurrencyError
from core.time import now_str


class DatasetHistoryMixin:
    def get_history(self, dataset_name: str | None = None, limit: int = 50) -> dict:
        with self.lock:
            with self._conn() as conn:
                if dataset_name:
                    ds = self._get_by_name(conn, dataset_name)
                else:
                    aid = self._active_id(conn)
                    if aid is None:
                        raise FileNotFoundError("No active dataset.")
                    ds = self._load_by_id(conn, aid)
                rows = conn.execute(
                    """
                    SELECT id,created_at,row_count,note
                    FROM dataset_revisions
                    WHERE dataset_id=?
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (ds["id"], limit),
                ).fetchall()
                return {
                    "file": ds["name"],
                    "version": ds["version"],
                    "updated_at": ds["updated_at"],
                    "revisions": [
                        {
                            "id": int(row["id"]),
                            "created_at": row["created_at"],
                            "row_count": int(row["row_count"] or 0),
                            "note": row["note"] or "",
                        }
                        for row in rows
                    ],
                }

    def restore_revision(
        self,
        revision_id: int,
        dataset_name: str | None = None,
        expected_version: int | None = None,
        actor: str = "",
    ) -> int:
        with self.lock:
            self._snapshot_db("before_restore")
            with self._conn() as conn:
                if dataset_name:
                    ds = self._get_by_name(conn, dataset_name)
                else:
                    aid = self._active_id(conn)
                    if aid is None:
                        raise FileNotFoundError("No active dataset.")
                    ds = self._load_by_id(conn, aid)
                if expected_version is not None and ds["version"] != expected_version:
                    raise ConcurrencyError(
                        f"Version conflict. Current version is {ds['version']}, expected {expected_version}."
                    )
                rev = conn.execute(
                    "SELECT headers_json,rows_json,content_hash,row_count FROM dataset_revisions WHERE id=? AND dataset_id=?",
                    (revision_id, ds["id"]),
                ).fetchone()
                if not rev:
                    raise FileNotFoundError("Revision not found for selected dataset.")
                self._save_revision(conn, ds, f"before restore revision {revision_id}")
                headers = json.loads(rev["headers_json"])
                rows = json.loads(rev["rows_json"])
                revision_hash = rev["content_hash"] or content_hash(headers, rows)
                new_ver = ds["version"] + 1
                conn.execute(
                    """
                    UPDATE datasets
                    SET headers_json=?, rows_json=?, content_hash=?, row_count=?, updated_at=?, version=?
                    WHERE id=?
                    """,
                    (
                        json.dumps(headers, ensure_ascii=False),
                        json.dumps(rows, ensure_ascii=False),
                        revision_hash,
                        int(rev["row_count"] or len(rows)),
                        now_str(),
                        new_ver,
                        ds["id"],
                    ),
                )
                self._audit(
                    conn,
                    action="dataset.revision.restore",
                    username=actor,
                    entity="dataset",
                    entity_id=str(ds["id"]),
                    dataset_id=ds["id"],
                    details={"file": ds["name"], "revision_id": revision_id, "version": new_ver},
                )
                return new_ver
