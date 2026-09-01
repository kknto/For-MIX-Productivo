from inventory_common import row_to_dict, rows_to_dicts


class InventoryTransactionMixin:
    def list_inventory_transactions(self, material_id: int | None = None, limit: int = 100) -> list[dict]:
        with self._conn() as conn:
            if material_id:
                cur = conn.execute(
                    """SELECT t.*, m.name as material_name, m.unit
                       FROM inventory_transactions t
                       JOIN materials m ON m.id = t.material_id
                       WHERE t.material_id=?
                       ORDER BY t.created_at DESC LIMIT ?""",
                    (material_id, limit),
                )
            else:
                cur = conn.execute(
                    """SELECT t.*, m.name as material_name, m.unit
                       FROM inventory_transactions t
                       JOIN materials m ON m.id = t.material_id
                       ORDER BY t.created_at DESC LIMIT ?""",
                    (limit,),
                )
            return rows_to_dicts(cur)

    def record_inventory_transaction(
        self,
        material_id: int,
        transaction_type: str,
        amount: float,
        reference: str = "",
        actor: str = "",
    ) -> dict:
        if transaction_type not in ("ENTRADA", "SALIDA"):
            raise ValueError("El tipo de transaccion debe ser ENTRADA o SALIDA.")
        if amount <= 0:
            raise ValueError("La cantidad debe ser mayor a 0.")

        now = self.get_now().strftime("%Y-%m-%d %H:%M:%S")
        with self.lock:
            with self._conn() as conn:
                mat_row = row_to_dict(conn.execute("SELECT id, current_stock FROM materials WHERE id=?", (material_id,)))
                if not mat_row:
                    raise ValueError(f"Material {material_id} no encontrado.")

                current_stock = float(mat_row["current_stock"])
                new_stock = current_stock + amount if transaction_type == "ENTRADA" else current_stock - amount
                conn.execute(
                    """INSERT INTO inventory_transactions (material_id, transaction_type, amount, reference, actor, created_at)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (material_id, transaction_type, amount, reference, actor, now),
                )
                conn.execute(
                    "UPDATE materials SET current_stock=?, updated_at=? WHERE id=?",
                    (new_stock, now, material_id),
                )
                conn.commit()
                return {
                    "ok": True,
                    "material_id": material_id,
                    "previous_stock": current_stock,
                    "new_stock": new_stock,
                }

    def delete_inventory_transaction(self, transaction_id: int, actor: str = "") -> dict:
        now = self.get_now().strftime("%Y-%m-%d %H:%M:%S")
        with self.lock:
            with self._conn() as conn:
                trx_row = conn.execute("SELECT * FROM inventory_transactions WHERE id=?", (transaction_id,)).fetchone()
                if not trx_row:
                    raise ValueError(f"Transaccion {transaction_id} no encontrada.")

                trx = dict(trx_row)
                material_id = trx["material_id"]
                transaction_type = trx["transaction_type"]
                amount = float(trx["amount"])
                mat_row = conn.execute("SELECT id, current_stock FROM materials WHERE id=?", (material_id,)).fetchone()
                if not mat_row:
                    raise ValueError(f"Material afectado {material_id} no encontrado.")

                current_stock = float(mat_row["current_stock"])
                if transaction_type == "ENTRADA":
                    new_stock = current_stock - amount
                elif transaction_type == "SALIDA":
                    new_stock = current_stock + amount
                else:
                    raise ValueError(f"Tipo de transaccion desconocido: {transaction_type}")

                conn.execute("DELETE FROM inventory_transactions WHERE id=?", (transaction_id,))
                conn.execute(
                    "UPDATE materials SET current_stock=?, updated_at=? WHERE id=?",
                    (new_stock, now, material_id),
                )
                conn.commit()
                return {
                    "ok": True,
                    "transaction_id": transaction_id,
                    "material_id": material_id,
                    "previous_stock": current_stock,
                    "new_stock": new_stock,
                }

    def clear_inventory_transactions(self) -> bool:
        with self.lock:
            with self._conn() as conn:
                conn.execute("DELETE FROM inventory_transactions")
                conn.commit()
                return True

    def get_daily_summary(self, date_str: str) -> dict:
        with self._conn() as conn:
            prod = row_to_dict(
                conn.execute(
                    """SELECT
                        COUNT(*) as total_remisiones,
                        SUM(dosificacion_m3) as total_m3,
                        SUM(peso_teorico_total) as total_teorico_kg,
                        SUM(peso_real_total) as total_real_kg
                       FROM remisiones
                       WHERE created_at LIKE ?""",
                    (f"{date_str}%",),
                )
            ) or {"total_remisiones": 0, "total_m3": 0, "total_teorico_kg": 0, "total_real_kg": 0}

            consumption = rows_to_dicts(
                conn.execute(
                    """SELECT
                        m.name, m.unit, m.doser_alias,
                        SUM(CASE WHEN t.transaction_type='SALIDA' THEN t.amount ELSE 0 END) as total_salida,
                        SUM(CASE WHEN t.transaction_type='ENTRADA' THEN t.amount ELSE 0 END) as total_entrada
                       FROM inventory_transactions t
                       JOIN materials m ON m.id = t.material_id
                       WHERE t.created_at LIKE ?
                       GROUP BY m.id, m.name, m.unit, m.doser_alias
                       ORDER BY m.name""",
                    (f"{date_str}%",),
                )
            )

            remisiones = rows_to_dicts(
                conn.execute(
                    """SELECT id, remision_no, formula, dosificacion_m3, created_at, snapshot_json
                       FROM remisiones
                       WHERE created_at LIKE ?
                       ORDER BY created_at ASC""",
                    (f"{date_str}%",),
                )
            )

            current_inventory = rows_to_dicts(
                conn.execute(
                    """SELECT name, current_stock, unit, min_stock, doser_alias
                       FROM materials
                       WHERE status='activo'
                       ORDER BY name"""
                )
            )

            return {
                "date": date_str,
                "production": {
                    "total_remisiones": int(prod.get("total_remisiones") or 0),
                    "total_m3": float(prod.get("total_m3") or 0),
                    "total_teorico_kg": float(prod.get("total_teorico_kg") or 0),
                    "total_real_kg": float(prod.get("total_real_kg") or 0),
                },
                "consumption": consumption,
                "remisiones": remisiones,
                "current_inventory": current_inventory,
            }
