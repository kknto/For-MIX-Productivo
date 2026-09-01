from __future__ import annotations

import json

from core.dataset_ops import default_doser_params, sanitize_doser_params
from core.errors import ConcurrencyError
from core.time import now_str


class DoserParamStoreMixin:
    def load_doser_params(self, dataset_name: str | None = None) -> dict:
        with self.lock:
            with self._conn() as conn:
                ds = self._resolve_dataset(conn, dataset_name)
                row = conn.execute(
                    "SELECT params_json,version,updated_at FROM doser_profiles WHERE dataset_id=?",
                    (ds["id"],),
                ).fetchone()
                if not row:
                    return {"file": ds["name"], "version": 0, "updated_at": "", "values": default_doser_params()}
                raw = json.loads(row["params_json"] or "{}")
                try:
                    values = sanitize_doser_params(raw)
                except Exception:
                    values = default_doser_params()
                return {
                    "file": ds["name"],
                    "version": int(row["version"] or 0),
                    "updated_at": row["updated_at"] or "",
                    "values": values,
                }

    def save_doser_params(
        self,
        values: dict,
        expected_version: int | None = None,
        dataset_name: str | None = None,
        actor: str = "",
    ) -> dict:
        clean_values = sanitize_doser_params(values)
        with self.lock:
            self._snapshot_db("before_doser_params_save")
            with self._conn() as conn:
                ds = self._resolve_dataset(conn, dataset_name)
                row = conn.execute("SELECT version FROM doser_profiles WHERE dataset_id=?", (ds["id"],)).fetchone()
                ts = now_str()
                if row:
                    curr_ver = int(row["version"] or 0)
                    if expected_version is not None and curr_ver != expected_version:
                        raise ConcurrencyError(
                            f"Version conflict. Current doser params version is {curr_ver}, expected {expected_version}."
                        )
                    new_ver = curr_ver + 1
                    conn.execute(
                        """
                        UPDATE doser_profiles
                        SET params_json=?, version=?, updated_at=?
                        WHERE dataset_id=?
                        """,
                        (json.dumps(clean_values, ensure_ascii=False), new_ver, ts, ds["id"]),
                    )
                else:
                    if expected_version not in (None, 0):
                        raise ConcurrencyError(
                            f"Version conflict. Current doser params version is 0, expected {expected_version}."
                        )
                    new_ver = 1
                    conn.execute(
                        """
                        INSERT INTO doser_profiles(dataset_id,params_json,version,updated_at)
                        VALUES(?,?,?,?)
                        """,
                        (ds["id"], json.dumps(clean_values, ensure_ascii=False), new_ver, ts),
                    )
                self._audit(
                    conn,
                    action="doser.params.save",
                    username=actor,
                    entity="doser_profile",
                    entity_id=str(ds["id"]),
                    dataset_id=ds["id"],
                    details={"file": ds["name"], "version": new_ver},
                )
                return {"file": ds["name"], "version": new_ver, "updated_at": ts, "values": clean_values}
