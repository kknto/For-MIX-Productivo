from __future__ import annotations

import json
import math

from core.time import get_now


class RemisionQueryMixin:
    def _serialize_remision_row(self, row, snapshot: dict | None = None) -> dict:
        resolved_snapshot = snapshot
        if resolved_snapshot is None:
            raw_snapshot = row["snapshot_json"] if "snapshot_json" in row.keys() else "{}"
            resolved_snapshot = json.loads(raw_snapshot or "{}") if raw_snapshot else {}
        return {
            "id": int(row["id"]),
            "remision_no": row["remision_no"] or "",
            "cliente": row["cliente"] if "cliente" in row.keys() else ((resolved_snapshot or {}).get("cliente", "") or ""),
            "ubicacion": row["ubicacion"] if "ubicacion" in row.keys() else ((resolved_snapshot or {}).get("ubicacion", "") or ""),
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
            "source_file": row["source_file"] if "source_file" in row.keys() else "",
            "updated_at": row["updated_at"] if "updated_at" in row.keys() else "",
            "version": int(row["version"] or 1) if "version" in row.keys() else 1,
            "file": row["source_file"] if "source_file" in row.keys() else "",
            "snapshot": resolved_snapshot if isinstance(resolved_snapshot, dict) else {},
        }

    def list_remisiones(
        self,
        dataset_name: str | None = None,
        query: str = "",
        limit: int = 80,
        date_filter: str | None = None,
        remision_no: str = "",
        cliente: str = "",
        formula: str = "",
        source_file: str = "",
        date_from: str | None = None,
        date_to: str | None = None,
        page: int = 1,
        page_size: int | None = None,
    ) -> dict:
        q = (query or "").strip().upper()
        remision_no_q = (remision_no or "").strip().upper()
        cliente_q = (cliente or "").strip().upper()
        formula_q = (formula or "").strip().upper()
        source_file_q = (source_file or "").strip().upper()
        effective_page_size = max(1, min(int(page_size or limit or 80), 500))
        current_page = max(1, int(page or 1))
        legacy_date = date_filter if date_filter is not None else get_now().strftime("%Y-%m-%d")
        final_date_from = date_from
        final_date_to = date_to
        if not final_date_from and not final_date_to and legacy_date:
            final_date_from = legacy_date
            final_date_to = legacy_date

        with self.lock:
            with self._conn() as conn:
                sql_where = []
                params = []
                if dataset_name and dataset_name.strip():
                    target_name = dataset_name.strip()
                    pattern = f"{target_name}__deleted__%"
                    ds_rows = conn.execute(
                        "SELECT id FROM datasets WHERE name = ? OR name LIKE ?",
                        (target_name, pattern),
                    ).fetchall()
                    ds_ids = [int(r["id"]) for r in ds_rows]
                    if ds_ids:
                        placeholders = ",".join(["?"] * len(ds_ids))
                        sql_where.append(f"r.dataset_id IN ({placeholders})")
                        params.extend(ds_ids)
                    else:
                        return {"file": target_name, "items": [], "global": False, "is_global": False}
                if q:
                    sql_where.append(
                        "(UPPER(r.remision_no) LIKE ? OR UPPER(r.formula) LIKE ? OR UPPER(r.cliente) LIKE ? OR UPPER(r.ubicacion) LIKE ?)"
                    )
                    params.extend([f"%{q}%"] * 4)
                if remision_no_q:
                    sql_where.append("UPPER(r.remision_no) LIKE ?")
                    params.append(f"%{remision_no_q}%")
                if cliente_q:
                    sql_where.append("UPPER(r.cliente) LIKE ?")
                    params.append(f"%{cliente_q}%")
                if formula_q:
                    sql_where.append("UPPER(r.formula) LIKE ?")
                    params.append(f"%{formula_q}%")
                if source_file_q:
                    sql_where.append("UPPER(d.name) LIKE ?")
                    params.append(f"%{source_file_q}%")
                if final_date_from:
                    sql_where.append("r.created_at >= ?")
                    params.append(f"{final_date_from} 00:00:00")
                if final_date_to:
                    sql_where.append("r.created_at <= ?")
                    params.append(f"{final_date_to} 23:59:59")

                where_clause = ("WHERE " + " AND ".join(sql_where)) if sql_where else ""
                count_sql = f"""
                    SELECT COUNT(*) as total
                    FROM remisiones r
                    JOIN datasets d ON r.dataset_id = d.id
                    {where_clause}
                """
                total_row = conn.execute(count_sql, params).fetchone()
                total = int(total_row["total"] or 0) if total_row else 0
                total_pages = max(1, math.ceil(total / effective_page_size)) if total else 1
                current_page = min(current_page, total_pages)
                offset = (current_page - 1) * effective_page_size
                sql = f"""
                    SELECT r.id, r.remision_no, r.cliente, r.ubicacion, r.formula, r.fc, r.edad, r.tipo, r.tma, r.rev, r.comp, r.dosificacion_m3,
                           r.peso_receta, r.peso_teorico_total, r.peso_real_total, r.status, r.created_at, r.created_by,
                           r.updated_at, r.version, r.snapshot_json, d.name as source_file
                    FROM remisiones r
                    JOIN datasets d ON r.dataset_id = d.id
                    {where_clause}
                    ORDER BY r.created_at DESC, r.id DESC LIMIT ? OFFSET ?
                """
                rows = conn.execute(sql, [*params, effective_page_size, offset]).fetchall()
                return {
                    "file": dataset_name or "Global",
                    "date_filter": legacy_date,
                    "date_from": final_date_from,
                    "date_to": final_date_to,
                    "global": not bool(dataset_name),
                    "is_global": not bool(dataset_name),
                    "page": current_page,
                    "page_size": effective_page_size,
                    "total": total,
                    "total_pages": total_pages,
                    "items": [self._serialize_remision_row(row) for row in rows],
                }

    def get_remision(self, remision_id: int, dataset_name: str | None = None) -> dict:
        rid = int(remision_id)
        if rid <= 0:
            raise ValueError("ID de remision invalido.")
        with self.lock:
            with self._conn() as conn:
                row = conn.execute(
                    """
                    SELECT r.id, r.remision_no, r.cliente, r.ubicacion, r.formula, r.fc, r.edad, r.tipo, r.tma, r.rev, r.comp, r.dosificacion_m3,
                           r.peso_receta, r.peso_teorico_total, r.peso_real_total, r.status, r.snapshot_json,
                           r.created_at, r.created_by, r.updated_at, r.version, r.dataset_id,
                           d.name as source_file
                    FROM remisiones r
                    JOIN datasets d ON r.dataset_id = d.id
                    WHERE r.id = ?
                    LIMIT 1
                    """,
                    (rid,),
                ).fetchone()
                if not row:
                    raise FileNotFoundError(f"Remision {rid} no encontrada.")

                snapshot = json.loads(row["snapshot_json"] or "{}")
                if not isinstance(snapshot, dict):
                    snapshot = {}
                if not snapshot.get("remisionNo"):
                    snapshot["remisionNo"] = row["remision_no"] or "-"
                if not snapshot.get("file"):
                    snapshot["file"] = row["source_file"]
                payload = self._serialize_remision_row(row, snapshot=snapshot)
                payload["source_file"] = row["source_file"] or ""
                payload["file"] = row["source_file"] or ""
                return payload
