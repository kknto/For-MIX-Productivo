from __future__ import annotations

import json
import re
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

from core.time import get_now, now_str


MAX_DB_SNAPSHOTS = 40


class DatasetBackupMixin:
    def _snapshot_db(self, reason: str):
        if self.is_postgres:
            return None
        safe_reason = re.sub(r"[^a-zA-Z0-9_-]+", "_", (reason or "op")).strip("_") or "op"
        stamp = get_now().strftime("%Y%m%d_%H%M%S")
        target = self.snapshot_dir / f"{stamp}_{safe_reason}.sqlite3"
        with closing(sqlite3.connect(self.db_path, timeout=30.0)) as src, closing(
            sqlite3.connect(target, timeout=30.0)
        ) as out:
            src.backup(out)
            out.commit()
        snapshots = sorted(self.snapshot_dir.glob("*.sqlite3"), key=lambda path: path.stat().st_mtime, reverse=True)
        for old in snapshots[MAX_DB_SNAPSHOTS:]:
            try:
                old.unlink()
            except OSError:
                pass
        return target

    def _backup_meta(self, path: Path) -> dict:
        name = path.name
        stamp_text = ""
        reason = ""
        match = re.match(r"^(\d{8}_\d{6})_(.+)\.sqlite3$", name)
        if match:
            stamp_text = match.group(1)
            reason = match.group(2)
        created = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        if stamp_text:
            try:
                created = datetime.strptime(stamp_text, "%Y%m%d_%H%M%S").strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                pass
        return {
            "file": name,
            "reason": reason or "manual",
            "size_bytes": int(path.stat().st_size),
            "created_at": created,
        }

    def list_backups(self, limit: int = 80) -> list[dict]:
        if self.is_postgres:
            return []
        max_limit = max(1, min(int(limit or 80), 300))
        items = sorted(self.snapshot_dir.glob("*.sqlite3"), key=lambda path: path.stat().st_mtime, reverse=True)
        return [self._backup_meta(path) for path in items[:max_limit]]

    def create_manual_backup(self, reason: str = "", actor: str = "") -> dict:
        if self.is_postgres:
            raise ValueError(
                "La creacion de respaldos manuales no esta disponible en modo PostgreSQL. Use las herramientas del proveedor (Render)."
            )
        note = re.sub(r"[^a-zA-Z0-9_-]+", "_", (reason or "manual")).strip("_")[:60] or "manual"
        with self.lock:
            target = self._snapshot_db(f"manual_{note}")
            with self._conn() as conn:
                self._audit(
                    conn,
                    action="backup.create",
                    username=actor,
                    entity="backup",
                    entity_id=target.name,
                    details={"reason": note},
                )
            return self._backup_meta(target)

    def restore_backup(self, backup_file: str, actor: str = "") -> dict:
        if self.is_postgres:
            raise ValueError(
                "La restauracion de respaldos no esta disponible en modo PostgreSQL. Use las herramientas del proveedor (Render)."
            )
        file_name = Path((backup_file or "").strip()).name
        if not file_name or "/" in file_name or "\\" in file_name or not file_name.lower().endswith(".sqlite3"):
            raise ValueError("Nombre de respaldo invalido.")
        source = (self.snapshot_dir / file_name).resolve()
        if source.parent != self.snapshot_dir.resolve() or not source.exists():
            raise FileNotFoundError("Respaldo no encontrado.")
        with self.lock:
            self._snapshot_db("before_backup_restore")
            with closing(sqlite3.connect(source, timeout=30.0)) as src, closing(
                sqlite3.connect(self.db_path, timeout=30.0)
            ) as dst:
                src.backup(dst)
                dst.commit()
            self._init_db()
            with self._conn() as conn:
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                aid = self._active_id(conn)
                active_file = self._load_by_id(conn, aid)["name"] if aid is not None else ""
                self._audit(
                    conn,
                    action="backup.restore",
                    username=actor,
                    entity="backup",
                    entity_id=file_name,
                    dataset_id=aid,
                    details={"active_file": active_file},
                )
            return {"backup": file_name, "active_file": active_file}

    def list_audit(self, dataset_name: str | None = None, limit: int = 120) -> dict:
        max_limit = max(1, min(int(limit or 120), 500))
        with self.lock:
            with self._conn() as conn:
                ds = None
                params: list = []
                where = []
                if dataset_name:
                    ds = self._resolve_dataset(conn, dataset_name)
                    where.append("dataset_id=?")
                    params.append(ds["id"])
                sql = "SELECT id,created_at,username,action,entity,entity_id,dataset_id,details_json FROM audit_log"
                if where:
                    sql += " WHERE " + " AND ".join(where)
                sql += " ORDER BY id DESC LIMIT ?"
                params.append(max_limit)
                rows = conn.execute(sql, tuple(params)).fetchall()
                out = []
                for row in rows:
                    try:
                        details = json.loads(row["details_json"] or "{}")
                    except Exception:
                        details = {}
                    out.append(
                        {
                            "id": int(row["id"]),
                            "created_at": row["created_at"] or "",
                            "username": row["username"] or "",
                            "action": row["action"] or "",
                            "entity": row["entity"] or "",
                            "entity_id": row["entity_id"] or "",
                            "dataset_id": int(row["dataset_id"]) if row["dataset_id"] is not None else None,
                            "details": details if isinstance(details, dict) else {},
                        }
                    )
                return {"file": ds["name"] if ds else "", "items": out}
