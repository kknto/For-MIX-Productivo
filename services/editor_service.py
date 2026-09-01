from core.payloads import decode_json_payload

MODES = {"new", "replace", "merge"}


def sanitize_cell(value) -> str:
    text = str(value).replace("\x00", "").strip()
    if not text:
        return ""
    if text[0] in ("=", "@"):
        return "'" + text
    if text[0] in ("+", "-") and not text[1:].replace(".", "", 1).replace(",", "", 1).isdigit():
        return "'" + text
    return text


class EditorService:
    def __init__(self, repository):
        self.repository = repository

    def load_active_payload(self):
        ds = self.repository.load_active()
        return {
            "file": ds["name"],
            "family": ds["family_code"],
            "encoding": ds["encoding"],
            "delimiter": ds["delimiter"],
            "headers": ds["headers"],
            "rows": ds["rows"],
            "files": self.repository.list_files(),
            "file_infos": self.repository.list_file_infos(),
            "updated_at": ds["updated_at"],
            "version": ds["version"],
            "row_count": ds["row_count"],
        }

    def families_summary(self):
        return {"ok": True, "summary": self.repository.get_all_families_summary()}

    def select_file(self, file_name: str):
        active = self.repository.set_active_file(file_name)
        return {
            "ok": True,
            "file": active,
            "files": self.repository.list_files(),
            "file_infos": self.repository.list_file_infos(),
        }

    def upload_preview(self, file_storage):
        return self.repository.stage_upload_preview(file_storage)

    def commit_upload(self, token: str, mode: str, target_file: str | None, family_code: str | None, actor: str):
        res = self.repository.commit_staged_upload(
            token=token,
            mode=mode,
            target_name=target_file,
            family_code=family_code,
            actor=actor,
        )
        return {"ok": True, **res, "files": self.repository.list_files(), "file_infos": self.repository.list_file_infos()}

    def upload_legacy(self, file_storage, actor: str):
        preview = self.repository.stage_upload_preview(file_storage)
        if not preview["ok"]:
            return preview
        res = self.repository.commit_staged_upload(token=preview["token"], mode="new", actor=actor)
        return {"ok": True, "file": res["file"], "files": self.repository.list_files(), "file_infos": self.repository.list_file_infos()}

    def purge_deleted(self, actor: str):
        res = self.repository.purge_deleted_datasets(actor=actor)
        return {"ok": True, **res}

    def delete_dataset(self, file_name: str, actor: str):
        res = self.repository.delete_file(file_name, actor=actor)
        return {
            "ok": True,
            "deleted": res["deleted"],
            "file": res["active"],
            "files": self.repository.list_files(),
            "file_infos": self.repository.list_file_infos(),
        }

    def save_family(self, family_code: str, file_name: str | None, actor: str):
        out = self.repository.set_dataset_family(family_code=family_code, dataset_name=file_name, actor=actor)
        return {"ok": True, **out, "file_infos": self.repository.list_file_infos()}

    def save_dataset(self, raw_body: bytes, actor: str):
        payload = decode_json_payload(raw_body)
        headers = payload.get("headers", [])
        rows = payload.get("rows", [])
        version = payload.get("version")
        if version is not None:
            version = int(version)
        if not isinstance(headers, list) or not isinstance(rows, list):
            raise ValueError("Invalid payload format.")
        clean_headers = [sanitize_cell("" if x is None else str(x)) for x in headers]
        clean_rows = []
        for row in rows:
            if not isinstance(row, list):
                raise ValueError("Each row must be a list.")
            clean_rows.append([sanitize_cell("" if x is None else str(x)) for x in row])
        new_ver = self.repository.save_active(clean_headers, clean_rows, expected_version=version, actor=actor)
        return {"ok": True, "version": new_ver}

    def history(self, file_name: str | None, limit: int):
        return {"ok": True, **self.repository.get_history(dataset_name=file_name, limit=limit)}

    def restore_history(self, revision_id: int, file_name: str | None, version, actor: str):
        new_ver = self.repository.restore_revision(
            revision_id,
            dataset_name=file_name,
            expected_version=version,
            actor=actor,
        )
        return {"ok": True, "version": new_ver}

    def audit(self, file_name: str | None, limit: int):
        return {"ok": True, **self.repository.list_audit(dataset_name=file_name, limit=limit)}

    def backups(self, limit: int):
        return {"ok": True, "items": self.repository.list_backups(limit=limit)}

    def create_backup(self, reason: str, actor: str):
        item = self.repository.create_manual_backup(reason=reason or "manual", actor=actor)
        return {"ok": True, "backup": item, "items": self.repository.list_backups(limit=80)}

    def restore_backup(self, backup_file: str, actor: str):
        out = self.repository.restore_backup(backup_file=backup_file, actor=actor)
        return {
            "ok": True,
            **out,
            "files": self.repository.list_files(),
            "file_infos": self.repository.list_file_infos(),
        }
