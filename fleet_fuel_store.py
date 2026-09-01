from fleet_common import row_to_dict, rows_to_dicts


class FleetFuelMixin:
    def list_fuel_records(
        self,
        vehicle_id: int | None = None,
        limit: int = 200,
        date_from: str = "",
        date_to: str = "",
    ) -> list[dict]:
        with self._conn() as conn:
            where = []
            params: list = []
            if vehicle_id:
                where.append("f.vehicle_id=?")
                params.append(vehicle_id)
            if date_from:
                where.append("f.record_date>=?")
                params.append(date_from)
            if date_to:
                where.append("f.record_date<=?")
                params.append(date_to + " 23:59:59")
            where_sql = ("WHERE " + " AND ".join(where)) if where else ""
            cur = conn.execute(
                f"SELECT f.*, v.unit_number FROM fuel_records f JOIN vehicles v ON v.id=f.vehicle_id "
                f"{where_sql} ORDER BY f.record_date DESC LIMIT ?",
                (*params, limit),
            )
            return rows_to_dicts(cur)

    def save_fuel_record(self, data: dict, actor: str = "") -> dict:
        now = self.get_now().strftime("%Y-%m-%d %H:%M:%S")
        vehicle_id = int(data.get("vehicle_id", 0))
        if not vehicle_id:
            raise ValueError("Vehiculo es requerido.")

        odometer = float(data.get("odometer_km", 0))
        liters = float(data.get("liters", 0))
        total_cost = float(data.get("total_cost", 0))
        if liters <= 0:
            raise ValueError("Litros debe ser mayor a 0.")

        price_per_liter = total_cost / liters
        record_date = data.get("record_date") or now
        km_traveled = 0.0
        kml_real = 0.0
        cost_per_km = 0.0
        with self._conn() as conn:
            prev = row_to_dict(
                conn.execute(
                    "SELECT odometer_km FROM fuel_records WHERE vehicle_id=? ORDER BY record_date DESC, id DESC LIMIT 1",
                    (vehicle_id,),
                )
            )
            if prev and prev.get("odometer_km") and odometer > 0:
                km_traveled = max(0, odometer - float(prev["odometer_km"]))
                if km_traveled > 0:
                    kml_real = km_traveled / liters
                    cost_per_km = total_cost / km_traveled

            conn.execute(
                """INSERT INTO fuel_records (vehicle_id, record_date, odometer_km, liters, total_cost,
                   price_per_liter, driver, station, km_traveled, kml_real, cost_per_km, notes,
                   created_by, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    vehicle_id,
                    record_date,
                    odometer,
                    liters,
                    total_cost,
                    price_per_liter,
                    data.get("driver", ""),
                    data.get("station", ""),
                    km_traveled,
                    kml_real,
                    cost_per_km,
                    data.get("notes", ""),
                    actor,
                    now,
                ),
            )
            conn.commit()
            return {
                "saved": True,
                "km_traveled": km_traveled,
                "kml_real": round(kml_real, 2),
                "cost_per_km": round(cost_per_km, 2),
            }

    def edit_fuel_record(self, record_id: int, data: dict) -> dict:
        now = self.get_now().strftime("%Y-%m-%d %H:%M:%S")
        liters = max(float(data.get("liters", 1)), 0.01)
        total_cost = float(data.get("total_cost", 0))
        with self._conn() as conn:
            conn.execute(
                """UPDATE fuel_records SET record_date=?, odometer_km=?, liters=?, total_cost=?,
                   price_per_liter=?, driver=?, station=?, notes=? WHERE id=?""",
                (
                    data.get("record_date", now),
                    float(data.get("odometer_km", 0)),
                    liters,
                    total_cost,
                    total_cost / liters,
                    data.get("driver", ""),
                    data.get("station", ""),
                    data.get("notes", ""),
                    record_id,
                ),
            )
            conn.commit()
            return {"saved": True}

    def delete_fuel_record(self, record_id: int) -> bool:
        with self._conn() as conn:
            conn.execute("DELETE FROM fuel_records WHERE id=?", (record_id,))
            conn.commit()
            return True

    def fleet_summary(self) -> list[dict]:
        with self._conn() as conn:
            cur = conn.execute(
                """
                SELECT v.id, v.unit_number, v.driver, v.expected_kml, v.plate,
                  COUNT(f.id) as total_records,
                  COALESCE(SUM(f.liters), 0) as total_liters,
                  COALESCE(SUM(f.total_cost), 0) as total_cost,
                  COALESCE(SUM(f.km_traveled), 0) as total_km,
                  CASE WHEN COALESCE(SUM(f.liters), 0) > 0
                       THEN COALESCE(SUM(f.km_traveled), 0) / SUM(f.liters)
                       ELSE 0 END as avg_kml,
                  CASE WHEN COALESCE(SUM(f.km_traveled), 0) > 0
                       THEN COALESCE(SUM(f.total_cost), 0) / SUM(f.km_traveled)
                       ELSE 0 END as avg_cost_per_km,
                  MAX(f.record_date) as last_record
                FROM vehicles v LEFT JOIN fuel_records f ON f.vehicle_id = v.id
                WHERE v.status = 'activo'
                GROUP BY v.id, v.unit_number, v.driver, v.expected_kml, v.plate
                ORDER BY v.unit_number
                """
            )
            return rows_to_dicts(cur)

    def fleet_kpi_stats(self) -> dict:
        month_start = self.get_now().strftime("%Y-%m-01")
        with self._conn() as conn:
            total_row = row_to_dict(conn.execute("SELECT COUNT(*) as cnt FROM vehicles WHERE status='activo'"))
            month = row_to_dict(
                conn.execute(
                    "SELECT COALESCE(SUM(liters),0) as sum_liters, COALESCE(SUM(total_cost),0) as sum_cost, "
                    "COALESCE(SUM(km_traveled),0) as sum_km, COUNT(*) as cnt "
                    "FROM fuel_records WHERE record_date >= ?",
                    (month_start,),
                )
            )
            avg_row = row_to_dict(
                conn.execute(
                    "SELECT CASE WHEN SUM(liters)>0 THEN SUM(km_traveled)/SUM(liters) ELSE 0 END as avg_kml "
                    "FROM fuel_records WHERE record_date >= ? AND km_traveled > 0",
                    (month_start,),
                )
            )
            return {
                "total_vehicles": total_row["cnt"] if total_row else 0,
                "month_liters": float(month["sum_liters"]) if month else 0,
                "month_cost": float(month["sum_cost"]) if month else 0,
                "month_km": float(month["sum_km"]) if month else 0,
                "month_records": int(month["cnt"]) if month else 0,
                "month_avg_kml": round(float(avg_row["avg_kml"]), 2) if avg_row and avg_row["avg_kml"] else 0,
            }

    def fuel_trend(self, vehicle_id: int, limit: int = 30) -> list[dict]:
        with self._conn() as conn:
            rows = rows_to_dicts(
                conn.execute(
                    "SELECT record_date, kml_real, cost_per_km, liters, total_cost, odometer_km, driver "
                    "FROM fuel_records WHERE vehicle_id=? AND kml_real > 0 "
                    "ORDER BY record_date ASC LIMIT ?",
                    (vehicle_id, limit),
                )
            )
            return [
                {
                    "date": row["record_date"],
                    "kml": row["kml_real"],
                    "cpk": row["cost_per_km"],
                    "liters": row["liters"],
                    "cost": row["total_cost"],
                    "km": row["odometer_km"],
                    "driver": row["driver"],
                }
                for row in rows
            ]
