class DoserRepository:
    def __init__(self, store):
        self.store = store

    def load_qc(self, dataset_name: str | None = None):
        return self.store.load_qc(dataset_name=dataset_name)

    def save_qc(self, values, expected_version, dataset_name: str | None, actor: str):
        return self.store.save_qc(
            values=values,
            expected_version=expected_version,
            dataset_name=dataset_name,
            actor=actor,
        )

    def save_qc_humidity(self, values, expected_version, dataset_name: str | None, actor: str):
        return self.store.save_qc_humidity(
            values=values,
            expected_version=expected_version,
            dataset_name=dataset_name,
            actor=actor,
        )

    def get_all_recipes_global(self):
        return self.store.get_all_recipes_global()

    def load_doser_params(self, dataset_name: str | None = None):
        return self.store.load_doser_params(dataset_name=dataset_name)

    def save_doser_params(self, values, expected_version, dataset_name: str | None, actor: str):
        return self.store.save_doser_params(
            values=values,
            expected_version=expected_version,
            dataset_name=dataset_name,
            actor=actor,
        )

    def list_remisiones(
        self,
        dataset_name: str | None,
        query: str,
        limit: int,
        date_filter: str | None,
        remision_no: str = "",
        cliente: str = "",
        formula: str = "",
        source_file: str = "",
        date_from: str | None = None,
        date_to: str | None = None,
        page: int = 1,
        page_size: int | None = None,
    ):
        return self.store.list_remisiones(
            dataset_name=dataset_name,
            query=query,
            limit=limit,
            date_filter=date_filter,
            remision_no=remision_no,
            cliente=cliente,
            formula=formula,
            source_file=source_file,
            date_from=date_from,
            date_to=date_to,
            page=page,
            page_size=page_size,
        )

    def save_remision(self, remision_no: str, remision_date: str | None, snapshot, dataset_name: str | None, created_by: str):
        return self.store.save_remision(
            remision_no=remision_no,
            remision_date=remision_date,
            snapshot=snapshot,
            dataset_name=dataset_name,
            created_by=created_by,
        )

    def get_remision(self, remision_id: int, dataset_name: str | None = None):
        return self.store.get_remision(remision_id=remision_id, dataset_name=dataset_name)

    def delete_remision(self, remision_id: int, dataset_name: str | None, actor: str):
        return self.store.delete_remision(remision_id=remision_id, dataset_name=dataset_name, actor=actor)

    def update_remision(self, remision_id: int, data, dataset_name: str | None, actor: str):
        return self.store.update_remision(
            remision_id=remision_id,
            data=data,
            dataset_name=dataset_name,
            actor=actor,
        )
