from __future__ import annotations

import json
from datetime import datetime

from auth_store import normalize_username
from core.dataset_ops import normalize_remision_no
from core.time import get_now, now_str
from remision_inventory_store import RemisionInventoryMixin
from remision_query_store import RemisionQueryMixin


class RemisionStoreMixin(RemisionQueryMixin, RemisionInventoryMixin):
    def _resolve_remision_created_at(self, remision_date: str | None) -> str:
        raw_value = str(remision_date or "").strip()
        if not raw_value:
            return now_str()
        try:
            selected_date = datetime.strptime(raw_value, "%Y-%m-%d").date()
        except ValueError as exc:
            raise ValueError("La fecha de la remision debe usar formato YYYY-MM-DD.") from exc
        now = get_now()
        if selected_date > now.date():
            raise ValueError("La fecha de la remision no puede ser futura.")
        return f"{raw_value} {now.strftime('%H:%M:%S')}"

    def save_remision(
        self,
        remision_no: str,
        snapshot: dict,
        remision_date: str | None = None,
        dataset_name: str | None = None,
        created_by: str = "",
    ) -> dict:
        remision = normalize_remision_no(remision_no)
        snap = dict(snapshot) if isinstance(snapshot, dict) else {}

        with self.lock:
            self._snapshot_db("before_remision_save")
            with self._conn() as conn:
                ds = self._resolve_dataset(conn, dataset_name)
                exists = conn.execute("SELECT 1 FROM remisiones WHERE remision_no=?", (remision,)).fetchone()
                if exists:
                    raise ValueError(f"La remision '{remision}' ya existe.")
                ts = self._resolve_remision_created_at(remision_date)
                snap["timestamp"] = ts
                conn.execute(
                    """
                    INSERT INTO remisiones(
                      dataset_id,remision_no,cliente,ubicacion,formula,fc,edad,tipo,tma,rev,comp,
                      dosificacion_m3,peso_receta,peso_teorico_total,peso_real_total,
                      status,snapshot_json,created_at,created_by,updated_at,version
                    )
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1)
                    """,
                    (
                        ds["id"],
                        remision,
                        self._remision_text(snap, "cliente"),
                        self._remision_text(snap, "ubicacion"),
                        self._remision_text(snap, "formula"),
                        self._remision_text(snap, "fc"),
                        self._remision_text(snap, "edad"),
                        self._remision_text(snap, "tipo"),
                        self._remision_text(snap, "tma"),
                        self._remision_text(snap, "rev"),
                        self._remision_text(snap, "comp"),
                        self._remision_number(snap, "dose"),
                        self._remision_number(snap, "recipeWeight"),
                        self._remision_number(snap, "theoreticalWeight"),
                        self._remision_number(snap, "realWeight"),
                        "abierta",
                        json.dumps(snap, ensure_ascii=False),
                        ts,
                        normalize_username(created_by),
                        ts,
                    ),
                )
                row = conn.execute(
                    """
                    SELECT id,remision_no,cliente,ubicacion,formula,fc,edad,tipo,tma,rev,comp,dosificacion_m3,
                           peso_receta,peso_teorico_total,peso_real_total,status,created_at,created_by
                    FROM remisiones
                    WHERE remision_no=?
                    LIMIT 1
                    """,
                    (remision,),
                ).fetchone()
                self._audit(
                    conn,
                    action="remision.create",
                    username=created_by,
                    entity="remision",
                    entity_id=str(int(row["id"])),
                    dataset_id=ds["id"],
                    details={"file": ds["name"], "remision_no": remision},
                )

                qc_data = self.load_qc(dataset_name=dataset_name)
                self._apply_remision_inventory_outputs(
                    conn,
                    remision_no=remision,
                    snapshot=snap,
                    qc_values=qc_data.get("values", {}),
                    created_at=ts,
                    dataset_name=dataset_name,
                )

                return {
                    "id": int(row["id"]),
                    "remision_no": row["remision_no"],
                    "cliente": row["cliente"] or "",
                    "ubicacion": row["ubicacion"] or "",
                    "formula": row["formula"] or "",
                    "fc": row["fc"] or "",
                    "edad": row["edad"] or "",
                    "tipo": row["tipo"] or "",
                    "tma": row["tma"] or "",
                    "rev": row["rev"] or "",
                    "comp": row["comp"] or "",
                    "dosificacion_m3": float(row["dosificacion_m3"] or 0),
                    "peso_receta": float(row["peso_receta"] or 0),
                    "peso_teorico_total": float(row["peso_teorico_total"] or 0),
                    "peso_real_total": float(row["peso_real_total"] or 0),
                    "status": row["status"] or "abierta",
                    "created_at": row["created_at"] or "",
                    "created_by": row["created_by"] or "",
                    "file": ds["name"],
                }

    def delete_remision(self, remision_id: int, dataset_name: str | None = None, actor: str = "") -> dict:
        rid = int(remision_id)
        if rid <= 0:
            raise ValueError("ID de remision invalido.")
        with self.lock:
            self._snapshot_db("before_remision_delete")
            with self._conn() as conn:
                row = conn.execute(
                    """
                    SELECT r.id, r.remision_no, r.dataset_id, d.name as source_file
                    FROM remisiones r
                    JOIN datasets d ON r.dataset_id = d.id
                    WHERE r.id = ?
                    LIMIT 1
                    """,
                    (rid,),
                ).fetchone()
                if not row:
                    raise FileNotFoundError(f"Remision {rid} no encontrada.")

                target_name = row["source_file"]
                did = row["dataset_id"]
                conn.execute("DELETE FROM remisiones WHERE id=?", (rid,))
                self._audit(
                    conn,
                    action="remision.delete",
                    username=actor,
                    entity="remision",
                    entity_id=str(int(row["id"])),
                    dataset_id=did,
                    details={"file": target_name, "remision_no": row["remision_no"] or ""},
                )
                return {
                    "id": int(row["id"]),
                    "remision_no": row["remision_no"] or "",
                    "file": target_name,
                }

    def update_remision(self, remision_id: int, data: dict, dataset_name: str | None = None, actor: str = "") -> dict:
        rid = int(remision_id)
        if rid <= 0:
            raise ValueError("ID de remision invalido.")
        with self.lock:
            ts = now_str()
            with self._conn() as conn:
                exists = conn.execute(
                    """
                    SELECT r.dataset_id, r.snapshot_json, d.name as source_file
                    FROM remisiones r
                    JOIN datasets d ON r.dataset_id = d.id
                    WHERE r.id=?
                    """,
                    (rid,),
                ).fetchone()
                if not exists:
                    raise FileNotFoundError("Remision no encontrada.")
                target_dataset_id = exists["dataset_id"]
                ds = {"id": target_dataset_id, "name": exists["source_file"] or (dataset_name or "Global")}

                formula = str(data.get("formula", "")).strip()
                m3 = float(data.get("dosificacion_m3", 0))
                peso_real = float(data.get("peso_real_total", 0))
                remision_no = str(data.get("remision_no", "")).strip()
                cliente = str(data.get("cliente", "")).strip()
                ubicacion = str(data.get("ubicacion", "")).strip()
                created_at = data.get("created_at")

                sql = "UPDATE remisiones SET formula=?, dosificacion_m3=?, peso_real_total=?, remision_no=?, cliente=?, ubicacion=?, updated_at=?"
                params = [formula, m3, peso_real, remision_no, cliente, ubicacion, ts]
                if created_at:
                    sql += ", created_at=?"
                    params.append(created_at)
                sql += " WHERE id=? AND dataset_id=?"
                params.extend([rid, target_dataset_id])
                conn.execute(sql, params)

                if created_at:
                    conn.execute(
                        "UPDATE inventory_transactions SET created_at=? WHERE reference=?",
                        (created_at, f"Remision #{remision_no}"),
                    )

                try:
                    snap = json.loads(exists["snapshot_json"] or "{}")
                    snap["formula"] = formula
                    snap["dose"] = m3
                    snap["realWeight"] = peso_real
                    snap["remisionNo"] = remision_no
                    snap["cliente"] = cliente
                    snap["ubicacion"] = ubicacion
                    if created_at:
                        snap["timestamp"] = created_at
                    conn.execute(
                        "UPDATE remisiones SET snapshot_json=? WHERE id=?",
                        (json.dumps(snap, ensure_ascii=False), rid),
                    )
                except Exception:
                    pass

                self._audit(
                    conn,
                    action="remision.update",
                    username=actor,
                    entity="remision",
                    entity_id=str(rid),
                    dataset_id=target_dataset_id,
                    details={
                        "file": ds["name"],
                        "remision_no": remision_no,
                        "formula": formula,
                        "m3": m3,
                        "peso_real": peso_real,
                        "created_at": created_at,
                    },
                )
                return {"id": rid, "ok": True}
