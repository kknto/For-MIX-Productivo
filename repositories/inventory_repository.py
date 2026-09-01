class InventoryRepository:
    def __init__(self, store):
        self.store = store

    def list_materials(self):
        return self.store.list_materials()

    def save_material(self, data, actor: str):
        return self.store.save_material(data, actor=actor)

    def delete_material(self, material_id: int, actor: str, force: bool = False):
        return self.store.delete_material(material_id, actor=actor, force=force)

    def purge_inactive(self):
        return self.store.purge_all_inactive_materials()

    def list_transactions(self, material_id: int | None = None, limit: int = 100):
        return self.store.list_inventory_transactions(material_id=material_id, limit=limit)

    def record_transaction(self, material_id: int, transaction_type: str, amount: float, reference: str, actor: str):
        return self.store.record_inventory_transaction(
            material_id=material_id,
            transaction_type=transaction_type,
            amount=amount,
            reference=reference,
            actor=actor,
        )

    def delete_transaction(self, transaction_id: int, actor: str):
        return self.store.delete_inventory_transaction(transaction_id, actor=actor)

    def clear_transactions(self):
        return self.store.clear_inventory_transactions()

    def get_daily_summary(self, date_str: str):
        return self.store.get_daily_summary(date_str)
