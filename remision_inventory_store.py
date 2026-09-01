from __future__ import annotations

from core.qc import QC_AGGREGATES
from core.time import now_str


class RemisionInventoryMixin:
    def _remision_text(self, snapshot: dict, key: str) -> str:
        return str((snapshot or {}).get(key, "")).strip()

    def _remision_number(self, snapshot: dict, key: str) -> float:
        try:
            return float((snapshot or {}).get(key, 0) or 0)
        except (TypeError, ValueError):
            return 0.0

    def _compute_remision_inventory_deduction(
        self,
        alias: str,
        peso_kg: float,
        unit: str,
        qc_values: dict,
        dataset_name: str | None = None,
    ) -> float:
        final_deduction = float(peso_kg or 0)
        normalized_unit = str(unit or "kg").lower()
        if alias not in QC_AGGREGATES or normalized_unit not in {"m3", "m³", "mã‚â³"}:
            return final_deduction

        qc_component = qc_values.get(alias, {})
        pvs = float(qc_component.get("pvs", 0) or 0)
        pvc = float(qc_component.get("pvc", 0) or 0)

        avg_pv = 0.0
        if pvs > 0 and pvc > 0:
            avg_pv = (pvs + pvc) / 2
        elif pvs > 0:
            avg_pv = pvs
        elif pvc > 0:
            avg_pv = pvc

        if avg_pv > 0:
            pv_kg_l = avg_pv / 1000.0 if avg_pv > 50 else avg_pv
            return (peso_kg / pv_kg_l) / 1000.0

        params_data = self.load_doser_params(dataset_name=dataset_name)
        fallback = float(params_data.get("values", {}).get("densidad_agregado_fallback", 2.20) or 2.20)
        return (peso_kg / fallback) / 1000.0

    def _apply_remision_inventory_outputs(
        self,
        conn,
        remision_no: str,
        snapshot: dict,
        qc_values: dict,
        created_at: str | None = None,
        dataset_name: str | None = None,
    ) -> None:
        ts = created_at or now_str()
        for rr in (snapshot or {}).get("realRows", []):
            alias = str(rr.get("name", "")).strip()
            material_id = rr.get("material_id")
            peso_kg = float(rr.get("real", 0) or 0)
            if peso_kg <= 0:
                continue

            mat_row = None
            if material_id:
                mat_row = conn.execute(
                    "SELECT id, current_stock, unit FROM materials WHERE id=? AND status='activo'",
                    (material_id,),
                ).fetchone()
            if not mat_row and alias:
                mat_row = conn.execute(
                    "SELECT id, current_stock, unit FROM materials WHERE doser_alias=? AND status='activo' LIMIT 1",
                    (alias,),
                ).fetchone()
            if not mat_row:
                continue

            deduction = self._compute_remision_inventory_deduction(
                alias=alias,
                peso_kg=peso_kg,
                unit=str(mat_row["unit"] or "kg"),
                qc_values=qc_values,
                dataset_name=dataset_name,
            )
            new_stock = float(mat_row["current_stock"] or 0) - deduction
            conn.execute(
                """INSERT INTO inventory_transactions (material_id, transaction_type, amount, reference, actor, created_at)
                   VALUES (?, 'SALIDA', ?, ?, ?, ?)""",
                (int(mat_row["id"]), deduction, f"Remision #{remision_no}", "Auto", ts),
            )
            conn.execute(
                "UPDATE materials SET current_stock=?, updated_at=? WHERE id=?",
                (new_stock, ts, int(mat_row["id"])),
            )
