from __future__ import annotations

import json

from core.dataset_ops import sanitize_qc_values
from core.errors import ConcurrencyError
from core.qc import QC_AGGREGATES, default_qc_values
from core.time import now_str


class QCProfileStoreMixin:
    def load_qc(self, dataset_name: str | None = None) -> dict:
        with self.lock:
            with self._conn() as conn:
                ds = self._resolve_dataset(conn, dataset_name)
                row = conn.execute(
                    "SELECT values_json,version,updated_at FROM qc_profiles WHERE dataset_id=?",
                    (ds["id"],),
                ).fetchone()
                if not row:
                    row = conn.execute(
                        "SELECT values_json,version,updated_at FROM qc_profiles ORDER BY updated_at DESC LIMIT 1"
                    ).fetchone()
                if not row:
                    return {"file": ds["name"], "version": 0, "updated_at": "", "values": default_qc_values()}
                raw = json.loads(row["values_json"] or "{}")
                try:
                    values = sanitize_qc_values(raw)
                except Exception:
                    values = default_qc_values()
                return {
                    "file": ds["name"],
                    "version": int(row["version"] or 0),
                    "updated_at": row["updated_at"] or "",
                    "values": values,
                }

    def save_qc(
        self,
        values: dict,
        expected_version: int | None = None,
        dataset_name: str | None = None,
        actor: str = "",
    ) -> dict:
        clean_values = sanitize_qc_values(values)
        with self.lock:
            self._snapshot_db("before_qc_save")
            with self._conn() as conn:
                ds = self._resolve_dataset(conn, dataset_name)
                row = conn.execute("SELECT version FROM qc_profiles WHERE dataset_id=?", (ds["id"],)).fetchone()
                ts = now_str()
                if row:
                    curr_ver = int(row["version"] or 0)
                    if expected_version is not None and curr_ver != expected_version:
                        raise ConcurrencyError(
                            f"Version conflict. Current QC version is {curr_ver}, expected {expected_version}."
                        )
                    new_ver = curr_ver + 1
                    conn.execute(
                        """
                        UPDATE qc_profiles
                        SET values_json=?, version=?, updated_at=?
                        WHERE dataset_id=?
                        """,
                        (json.dumps(clean_values, ensure_ascii=False), new_ver, ts, ds["id"]),
                    )
                else:
                    if expected_version not in (None, 0):
                        raise ConcurrencyError(
                            f"Version conflict. Current QC version is 0, expected {expected_version}."
                        )
                    new_ver = 1
                    conn.execute(
                        """
                        INSERT INTO qc_profiles(dataset_id,values_json,version,updated_at)
                        VALUES(?,?,?,?)
                        """,
                        (ds["id"], json.dumps(clean_values, ensure_ascii=False), new_ver, ts),
                    )
                self._audit(
                    conn,
                    action="qc.save",
                    username=actor,
                    entity="qc_profile",
                    entity_id=str(ds["id"]),
                    dataset_id=ds["id"],
                    details={"file": ds["name"], "version": new_ver},
                )
                return {"file": ds["name"], "version": new_ver, "updated_at": ts, "values": clean_values}

    def save_qc_humidity(
        self,
        values: dict,
        expected_version: int | None = None,
        dataset_name: str | None = None,
        actor: str = "",
    ) -> dict:
        def qc_number(value) -> float:
            text = str(value if value is not None else "").strip().replace(",", ".")
            if text == "":
                return 0.0
            num = float(text)
            if num < 0:
                raise ValueError("Los valores de control de calidad no pueden ser negativos.")
            if num > 1_000_000:
                raise ValueError("Un valor de control de calidad excede el limite permitido.")
            return num

        src = values if isinstance(values, dict) else {}
        humidity_by_agg = {}
        for agg in QC_AGGREGATES:
            row = src.get(agg) if isinstance(src.get(agg), dict) else {}
            humidity_by_agg[agg] = qc_number(row.get("humedad", 0))

        with self.lock:
            self._snapshot_db("before_qc_humidity_save")
            with self._conn() as conn:
                ds = self._resolve_dataset(conn, dataset_name)
                row = conn.execute(
                    "SELECT values_json,version FROM qc_profiles WHERE dataset_id=?",
                    (ds["id"],),
                ).fetchone()
                ts = now_str()
                if row:
                    curr_ver = int(row["version"] or 0)
                    if expected_version is not None and curr_ver != expected_version:
                        raise ConcurrencyError(
                            f"Version conflict. Current QC version is {curr_ver}, expected {expected_version}."
                        )
                    raw = json.loads(row["values_json"] or "{}")
                    try:
                        clean_values = sanitize_qc_values(raw)
                    except Exception:
                        clean_values = default_qc_values()
                    for agg in QC_AGGREGATES:
                        clean_values[agg]["humedad"] = humidity_by_agg[agg]
                    new_ver = curr_ver + 1
                    conn.execute(
                        """
                        UPDATE qc_profiles
                        SET values_json=?, version=?, updated_at=?
                        WHERE dataset_id=?
                        """,
                        (json.dumps(clean_values, ensure_ascii=False), new_ver, ts, ds["id"]),
                    )
                else:
                    if expected_version not in (None, 0):
                        raise ConcurrencyError(
                            f"Version conflict. Current QC version is 0, expected {expected_version}."
                        )
                    clean_values = default_qc_values()
                    for agg in QC_AGGREGATES:
                        clean_values[agg]["humedad"] = humidity_by_agg[agg]
                    new_ver = 1
                    conn.execute(
                        """
                        INSERT INTO qc_profiles(dataset_id,values_json,version,updated_at)
                        VALUES(?,?,?,?)
                        """,
                        (ds["id"], json.dumps(clean_values, ensure_ascii=False), new_ver, ts),
                    )
                self._audit(
                    conn,
                    action="qc.humidity.save",
                    username=actor,
                    entity="qc_profile",
                    entity_id=str(ds["id"]),
                    dataset_id=ds["id"],
                    details={"file": ds["name"], "version": new_ver},
                )
                return {"file": ds["name"], "version": new_ver, "updated_at": ts, "values": clean_values}
