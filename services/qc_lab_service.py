class QcLabService:
    def __init__(self, repository):
        self.repository = repository

    def list_samples(self, limit: int = 100):
        return {"ok": True, "samples": self.repository.list_samples(limit=limit)}

    def get_sample(self, sample_id: int):
        sample = self.repository.get_sample(sample_id)
        if not sample:
            raise FileNotFoundError("Muestra no encontrada")
        return {"ok": True, "sample": sample}

    def delete_sample(self, sample_id: int):
        success = self.repository.delete_sample(sample_id)
        if not success:
            raise FileNotFoundError("Muestra no encontrada")
        return {"ok": True}

    def lookup_remision(self, remision_no: str):
        remision = self.repository.lookup_remision(remision_no)
        if not remision:
            raise FileNotFoundError("Remision no encontrada")
        return {"ok": True, "remision": remision}

    def save_sample(self, payload, actor: str):
        return {"ok": True, "sample": self.repository.save_sample(payload, actor)}

    def list_cylinders(self, pending_only: bool = False, limit: int = 500):
        return {"ok": True, "cylinders": self.repository.list_cylinders(pending_only=pending_only, limit=limit)}

    def test_cylinder(self, cylinder_id: int, payload, image_path: str = "", image_data=None):
        return {"ok": True, "sample": self.repository.test_cylinder(cylinder_id, payload, image_path, image_data)}
