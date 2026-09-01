from inventory_common import row_to_dict, rows_to_dicts


class InventoryMaterialMixin:
    def list_materials(self, include_inactive: bool = False) -> list[dict]:
        with self._conn() as conn:
            if include_inactive:
                cur = conn.execute("SELECT * FROM materials ORDER BY name")
            else:
                cur = conn.execute("SELECT * FROM materials WHERE status='activo' ORDER BY name")
            return rows_to_dicts(cur)

    def save_material(self, data: dict, actor: str = "") -> dict:
        now = self.get_now().strftime("%Y-%m-%d %H:%M:%S")
        name = (data.get("name") or "").strip()
        if not name:
            raise ValueError("El nombre del material es requerido.")

        doser_alias = (data.get("doser_alias") or "").strip()
        unit = (data.get("unit") or "kg").strip()
        min_stock = float(data.get("min_stock", 0))
        status = data.get("status", "activo")
        material_id = data.get("id")

        with self._conn() as conn:
            if material_id:
                conn.execute(
                    """UPDATE materials SET name=?, doser_alias=?, unit=?, min_stock=?, status=?, updated_at=?
                       WHERE id=?""",
                    (name, doser_alias, unit, min_stock, status, now, int(material_id)),
                )
                conn.commit()
                return {"id": int(material_id), "saved": True}

            conn.execute(
                """INSERT INTO materials (name, doser_alias, unit, current_stock, min_stock, status, created_at, updated_at)
                   VALUES (?, ?, ?, 0, ?, ?, ?, ?)""",
                (name, doser_alias, unit, min_stock, status, now, now),
            )
            conn.commit()
            row = row_to_dict(conn.execute("SELECT id FROM materials WHERE name=?", (name,)))
            return {"id": row["id"] if row else 0, "saved": True}

    def delete_material(self, material_id: int, actor: str = "", force: bool = False) -> bool:
        now = self.get_now().strftime("%Y-%m-%d %H:%M:%S")
        with self._conn() as conn:
            if force:
                conn.execute("DELETE FROM inventory_transactions WHERE material_id=?", (material_id,))
                conn.execute("DELETE FROM materials WHERE id=?", (material_id,))
            else:
                conn.execute(
                    "UPDATE materials SET name = name || '_del_' || id, status='inactivo', updated_at=? WHERE id=?",
                    (now, material_id),
                )
            conn.commit()
        return True

    def purge_all_inactive_materials(self) -> dict:
        with self._conn() as conn:
            cur = conn.execute("SELECT id FROM materials WHERE status='inactivo'")
            ids = [r["id"] for r in cur.fetchall()]
            if not ids:
                return {"count": 0}

            placeholders = ",".join(["?"] * len(ids))
            conn.execute(f"DELETE FROM inventory_transactions WHERE material_id IN ({placeholders})", ids)
            conn.execute(f"DELETE FROM materials WHERE id IN ({placeholders})", ids)
            conn.commit()
            return {"count": len(ids)}
