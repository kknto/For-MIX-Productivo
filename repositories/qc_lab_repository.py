class QcLabRepository:
    def __init__(self, store):
        self.store = store

    def list_samples(self, limit: int = 100):
        return self.store.list_qc_samples(limit=limit)

    def get_sample(self, sample_id: int):
        return self.store.get_qc_sample(sample_id)

    def delete_sample(self, sample_id: int):
        return self.store.delete_qc_sample(sample_id)

    def lookup_remision(self, remision_no: str):
        return self.store.get_remision_by_no(remision_no)

    def save_sample(self, payload, actor: str):
        return self.store.save_qc_sample(payload, actor)

    def list_cylinders(self, pending_only: bool = False, limit: int = 500):
        return self.store.list_qc_cylinders(pending_only=pending_only, limit=limit)

    def test_cylinder(self, cylinder_id: int, payload, image_path: str = "", image_data=None):
        return self.store.test_qc_cylinder(cylinder_id, payload, image_path, image_data)
