class EditorRepository:
    def __init__(self, store):
        self.store = store

    def load_active(self):
        return self.store.load_active()

    def list_files(self):
        return self.store.list_files()

    def list_file_infos(self):
        return self.store.list_file_infos()

    def get_all_families_summary(self):
        return self.store.get_all_families_summary()

    def set_active_file(self, file_name: str):
        return self.store.set_active_file(file_name)

    def stage_upload_preview(self, file_storage):
        return self.store.stage_upload_preview(file_storage)

    def commit_staged_upload(self, **kwargs):
        return self.store.commit_staged_upload(**kwargs)

    def purge_deleted_datasets(self, actor: str):
        return self.store.purge_deleted_datasets(actor=actor)

    def delete_file(self, file_name: str, actor: str):
        return self.store.delete_file(file_name, actor=actor)

    def set_dataset_family(self, family_code: str, dataset_name: str | None, actor: str):
        return self.store.set_dataset_family(family_code=family_code, dataset_name=dataset_name, actor=actor)

    def save_active(self, headers, rows, expected_version, actor: str):
        return self.store.save_active(headers, rows, expected_version=expected_version, actor=actor)

    def get_history(self, dataset_name: str | None, limit: int):
        return self.store.get_history(dataset_name=dataset_name, limit=limit)

    def restore_revision(self, revision_id: int, dataset_name: str | None, expected_version, actor: str):
        return self.store.restore_revision(
            revision_id,
            dataset_name=dataset_name,
            expected_version=expected_version,
            actor=actor,
        )

    def list_audit(self, dataset_name: str | None, limit: int):
        return self.store.list_audit(dataset_name=dataset_name, limit=limit)

    def list_backups(self, limit: int):
        return self.store.list_backups(limit=limit)

    def create_manual_backup(self, reason: str, actor: str):
        return self.store.create_manual_backup(reason=reason, actor=actor)

    def restore_backup(self, backup_file: str, actor: str):
        return self.store.restore_backup(backup_file=backup_file, actor=actor)
