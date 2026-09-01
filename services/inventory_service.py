class InventoryService:
    def __init__(self, repository):
        self.repository = repository

    def list_materials(self):
        return {"ok": True, "materials": self.repository.list_materials()}

    def save_material(self, payload, actor: str):
        result = self.repository.save_material(payload, actor=actor)
        return {"ok": True, **result, "materials": self.repository.list_materials()}

    def delete_material(self, material_id: int, actor: str, force: bool = False):
        self.repository.delete_material(material_id, actor=actor, force=force)
        return {"ok": True, "materials": self.repository.list_materials()}

    def purge_inactive(self):
        result = self.repository.purge_inactive()
        return {"ok": True, "purged": result["count"], "materials": self.repository.list_materials()}

    def list_transactions(self, material_id: int | None = None, limit: int = 100):
        return {"ok": True, "transactions": self.repository.list_transactions(material_id=material_id, limit=limit)}

    def save_transaction(self, payload, actor: str):
        result = self.repository.record_transaction(
            material_id=int(payload.get("material_id", 0)),
            transaction_type=payload.get("transaction_type", "ENTRADA"),
            amount=float(payload.get("amount", 0)),
            reference=payload.get("reference", ""),
            actor=actor,
        )
        return {"ok": True, **result, "materials": self.repository.list_materials()}

    def delete_transaction(self, transaction_id: int, actor: str):
        self.repository.delete_transaction(transaction_id, actor=actor)
        return {
            "ok": True,
            "materials": self.repository.list_materials(),
            "transactions": self.repository.list_transactions(),
        }

    def clear_transactions(self):
        self.repository.clear_transactions()
        return {"ok": True, "transactions": self.repository.list_transactions()}

    def daily_summary(self, date_str: str):
        return {"ok": True, "summary": self.repository.get_daily_summary(date_str)}
