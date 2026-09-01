from fleet_common import rows_to_dicts


class FleetMaintenanceMixin:
    def list_maintenance(self, vehicle_id: int | None = None, limit: int = 100) -> list[dict]:
        with self._conn() as conn:
            if vehicle_id:
                cur = conn.execute(
                    "SELECT m.*, v.unit_number FROM maintenance_records m JOIN vehicles v ON v.id=m.vehicle_id "
                    "WHERE m.vehicle_id=? ORDER BY m.record_date DESC LIMIT ?",
                    (vehicle_id, limit),
                )
            else:
                cur = conn.execute(
                    "SELECT m.*, v.unit_number FROM maintenance_records m JOIN vehicles v ON v.id=m.vehicle_id "
                    "ORDER BY m.record_date DESC LIMIT ?",
                    (limit,),
                )
            return rows_to_dicts(cur)

    def save_maintenance(self, data: dict, actor: str = "") -> dict:
        now = self.get_now().strftime("%Y-%m-%d %H:%M:%S")
        vehicle_id = int(data.get("vehicle_id", 0))
        if not vehicle_id:
            raise ValueError("Vehiculo es requerido.")
        maintenance_id = data.get("id")
        with self._conn() as conn:
            if maintenance_id:
                conn.execute(
                    """UPDATE maintenance_records SET maintenance_type=?, description=?, cost=?,
                       odometer_km=?, next_km=?, record_date=?, provider=?, notes=? WHERE id=?""",
                    (
                        data.get("maintenance_type", ""),
                        data.get("description", ""),
                        float(data.get("cost", 0)),
                        float(data.get("odometer_km", 0)),
                        float(data.get("next_km", 0)),
                        data.get("record_date", now),
                        data.get("provider", ""),
                        data.get("notes", ""),
                        int(maintenance_id),
                    ),
                )
            else:
                conn.execute(
                    """INSERT INTO maintenance_records (vehicle_id, maintenance_type, description, cost,
                       odometer_km, next_km, record_date, provider, notes, created_by, created_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        vehicle_id,
                        data.get("maintenance_type", ""),
                        data.get("description", ""),
                        float(data.get("cost", 0)),
                        float(data.get("odometer_km", 0)),
                        float(data.get("next_km", 0)),
                        data.get("record_date", now),
                        data.get("provider", ""),
                        data.get("notes", ""),
                        actor,
                        now,
                    ),
                )
            conn.commit()
            return {"saved": True}

    def delete_maintenance(self, record_id: int) -> bool:
        with self._conn() as conn:
            conn.execute("DELETE FROM maintenance_records WHERE id=?", (record_id,))
            conn.commit()
            return True

    def maintenance_alerts(self) -> list[dict]:
        with self._conn() as conn:
            rows = rows_to_dicts(
                conn.execute(
                    """
                    SELECT m.id, m.vehicle_id, v.unit_number, m.maintenance_type, m.next_km,
                      (SELECT MAX(f.odometer_km) FROM fuel_records f WHERE f.vehicle_id=m.vehicle_id) as current_km
                    FROM maintenance_records m JOIN vehicles v ON v.id=m.vehicle_id
                    WHERE m.next_km > 0 AND v.status='activo'
                    ORDER BY m.next_km
                    """
                )
            )
            alerts = []
            for row in rows:
                next_km = float(row.get("next_km") or 0)
                current_km = float(row.get("current_km") or 0)
                if current_km <= 0 or next_km <= 0:
                    continue
                remaining = next_km - current_km
                if remaining <= 1000:
                    alerts.append(
                        {
                            "vehicle_id": row["vehicle_id"],
                            "unit_number": row["unit_number"],
                            "maintenance_type": row["maintenance_type"],
                            "next_km": next_km,
                            "current_km": current_km,
                            "remaining_km": remaining,
                            "overdue": remaining < 0,
                        }
                    )
            return alerts
