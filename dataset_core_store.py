from __future__ import annotations

import json
import sqlite3

from auth_store import normalize_username
from core.time import now_str


class DatasetCoreMixin:
    def _active_id(self, conn) -> int | None:
        row = conn.execute("SELECT value FROM app_state WHERE key='active_dataset_id'").fetchone()
        if row:
            try:
                did = int(row["value"])
                ok = conn.execute("SELECT 1 FROM datasets WHERE id=? AND deleted_at IS NULL", (did,)).fetchone()
                if ok:
                    return did
            except ValueError:
                pass
        row = conn.execute("SELECT id FROM datasets WHERE deleted_at IS NULL ORDER BY id LIMIT 1").fetchone()
        return int(row["id"]) if row else None

    def _set_active(self, conn, did: int):
        conn.execute(
            """
            INSERT INTO app_state(key,value) VALUES('active_dataset_id',?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value
            """,
            (str(did),),
        )

    def _audit(
        self,
        conn,
        action: str,
        username: str = "",
        entity: str = "",
        entity_id: str = "",
        dataset_id: int | None = None,
        details: dict | None = None,
    ):
        payload = details if isinstance(details, dict) else {}
        conn.execute(
            """
            INSERT INTO audit_log(created_at,username,action,entity,entity_id,dataset_id,details_json)
            VALUES(?,?,?,?,?,?,?)
            """,
            (
                now_str(),
                normalize_username(username),
                (action or "").strip()[:80],
                (entity or "").strip()[:40],
                (entity_id or "").strip()[:80],
                int(dataset_id) if dataset_id is not None else None,
                json.dumps(payload, ensure_ascii=False),
            ),
        )

    def _load_by_id(self, conn, did: int) -> dict:
        row = conn.execute("SELECT * FROM datasets WHERE id=? AND deleted_at IS NULL", (did,)).fetchone()
        if not row:
            raise FileNotFoundError("Dataset not found.")
        headers = json.loads(row["headers_json"])
        rows = json.loads(row["rows_json"])
        width = len(headers)
        rows = [(r + [""] * width)[:width] for r in rows]
        return {
            "id": int(row["id"]),
            "name": row["name"],
            "family_code": (row["family_code"] or "").strip(),
            "headers": headers,
            "rows": rows,
            "encoding": row["encoding"],
            "delimiter": row["delimiter"],
            "content_hash": row["content_hash"],
            "row_count": int(row["row_count"]),
            "updated_at": row["updated_at"],
            "version": int(row["version"]),
        }

    def _resolve_dataset(self, conn: sqlite3.Connection, dataset_name: str | None = None) -> dict:
        if dataset_name:
            return self._get_by_name(conn, dataset_name.strip())
        did = self._active_id(conn)
        if did is None:
            raise FileNotFoundError("No active dataset.")
        return self._load_by_id(conn, did)

    def _save_revision(self, conn: sqlite3.Connection, ds: dict, note: str):
        conn.execute(
            """
            INSERT INTO dataset_revisions(dataset_id,headers_json,rows_json,content_hash,row_count,note,created_at)
            VALUES(?,?,?,?,?,?,?)
            """,
            (
                ds["id"],
                json.dumps(ds["headers"], ensure_ascii=False),
                json.dumps(ds["rows"], ensure_ascii=False),
                ds["content_hash"],
                len(ds["rows"]),
                note,
                now_str(),
            ),
        )
