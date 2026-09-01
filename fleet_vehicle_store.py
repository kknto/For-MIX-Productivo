from fleet_common import row_to_dict, rows_to_dicts


class FleetVehicleMixin:
    def list_vehicles(self, include_inactive: bool = False) -> list[dict]:
        with self._conn() as conn:
            if include_inactive:
                cur = conn.execute("SELECT * FROM vehicles ORDER BY unit_number")
            else:
                cur = conn.execute("SELECT * FROM vehicles WHERE status='activo' ORDER BY unit_number")
            return rows_to_dicts(cur)

    def save_vehicle(self, data: dict, actor: str = "") -> dict:
        now = self.get_now().strftime("%Y-%m-%d %H:%M:%S")
        unit = (data.get("unit_number") or "").strip()
        if not unit:
            raise ValueError("Numero de unidad es requerido.")
        vehicle_id = data.get("id")
        with self._conn() as conn:
            conn.execute(
                "UPDATE vehicles SET unit_number = unit_number || '_del_' || id WHERE unit_number = ? AND status = 'inactivo'",
                (unit,),
            )
            conn.commit()

            if vehicle_id:
                conn.execute(
                    """UPDATE vehicles SET unit_number=?, phone=?, year_model=?, serial_number=?,
                       plate=?, driver=?, tank_capacity=?, expected_kml=?, status=?, notes=?, updated_at=?
                       WHERE id=?""",
                    (
                        unit,
                        data.get("phone", ""),
                        data.get("year_model", ""),
                        data.get("serial_number", ""),
                        data.get("plate", ""),
                        data.get("driver", ""),
                        float(data.get("tank_capacity", 0)),
                        float(data.get("expected_kml", 0)),
                        data.get("status", "activo"),
                        data.get("notes", ""),
                        now,
                        int(vehicle_id),
                    ),
                )
                conn.commit()
                return {"id": int(vehicle_id), "saved": True}

            conn.execute(
                """INSERT INTO vehicles (unit_number, phone, year_model, serial_number, plate,
                   driver, tank_capacity, expected_kml, status, notes, created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    unit,
                    data.get("phone", ""),
                    data.get("year_model", ""),
                    data.get("serial_number", ""),
                    data.get("plate", ""),
                    data.get("driver", ""),
                    float(data.get("tank_capacity", 0)),
                    float(data.get("expected_kml", 0)),
                    data.get("status", "activo"),
                    data.get("notes", ""),
                    now,
                    now,
                ),
            )
            conn.commit()
            row = row_to_dict(conn.execute("SELECT id FROM vehicles WHERE unit_number=?", (unit,)))
            return {"id": row["id"] if row else 0, "saved": True}

    def delete_vehicle(self, vehicle_id: int, actor: str = "") -> bool:
        now = self.get_now().strftime("%Y-%m-%d %H:%M:%S")
        with self._conn() as conn:
            conn.execute(
                "UPDATE vehicles SET status='inactivo', unit_number=unit_number || '_del_' || id, updated_at=? WHERE id=?",
                (now, vehicle_id),
            )
            conn.commit()
            return True
