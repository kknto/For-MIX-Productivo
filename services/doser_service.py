from datetime import datetime

from core.qc import QC_AGGREGATES, default_qc_values


class DoserService:
    def __init__(self, repository):
        self.repository = repository

    def load_qc(self, file_name: str | None):
        data = self.repository.load_qc(dataset_name=file_name)
        return {"ok": True, **data}

    def save_qc(self, payload: dict, actor: str):
        values = payload.get("values", {})
        file_name = payload.get("file")
        version = payload.get("version")
        if version is not None:
            version = int(version)
        current = self.repository.load_qc(dataset_name=file_name)
        current_values = current.get("values", default_qc_values())
        merged_values = values if isinstance(values, dict) else {}
        for agg in QC_AGGREGATES:
            row = merged_values.get(agg) if isinstance(merged_values.get(agg), dict) else {}
            row["humedad"] = current_values.get(agg, {}).get("humedad", 0)
            merged_values[agg] = row
        out = self.repository.save_qc(
            values=merged_values,
            expected_version=version,
            dataset_name=file_name,
            actor=actor,
        )
        return {"ok": True, **out}

    def save_qc_humidity(self, payload: dict, actor: str):
        values = payload.get("values", {})
        file_name = payload.get("file")
        version = payload.get("version")
        if version is not None:
            version = int(version)
        out = self.repository.save_qc_humidity(
            values=values,
            expected_version=version,
            dataset_name=file_name,
            actor=actor,
        )
        return {"ok": True, **out}

    def recipes_global(self):
        return {"ok": True, "recipes": self.repository.get_all_recipes_global()}

    def _normalize_optional_date(self, value, label: str) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        try:
            datetime.strptime(text, "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError(f"{label} debe usar formato YYYY-MM-DD.") from exc
        return text

    def load_params(self, file_name: str | None):
        data = self.repository.load_doser_params(dataset_name=file_name)
        return {"ok": True, **data}

    def save_params(self, payload: dict, actor: str):
        values = payload.get("values", {})
        file_name = payload.get("file")
        version = payload.get("version")
        if version is not None:
            version = int(version)
        out = self.repository.save_doser_params(
            values=values,
            expected_version=version,
            dataset_name=file_name,
            actor=actor,
        )
        return {"ok": True, **out}

    def list_remisiones(
        self,
        file_name: str | None,
        query: str,
        limit,
        date_filter: str | None,
        remision_no: str = "",
        cliente: str = "",
        formula: str = "",
        source_file: str = "",
        date_from: str | None = None,
        date_to: str | None = None,
        page=1,
        page_size=None,
    ):
        normalized_date = self._normalize_optional_date(date_filter, "date")
        normalized_date_from = self._normalize_optional_date(date_from, "date_from")
        normalized_date_to = self._normalize_optional_date(date_to, "date_to")
        if normalized_date_from and normalized_date_to and normalized_date_from > normalized_date_to:
            raise ValueError("date_from no puede ser mayor que date_to.")
        page = max(1, int(page or 1))
        clean_limit = max(1, min(int(limit or 80), 500))
        clean_page_size = None if page_size in (None, "") else max(1, min(int(page_size), 200))
        out = self.repository.list_remisiones(
            dataset_name=file_name,
            query=query,
            limit=clean_limit,
            date_filter=normalized_date,
            remision_no=remision_no,
            cliente=cliente,
            formula=formula,
            source_file=source_file,
            date_from=normalized_date_from,
            date_to=normalized_date_to,
            page=page,
            page_size=clean_page_size,
        )
        return {"ok": True, **out}

    def save_remision(self, payload: dict, actor: str):
        remision_date = payload.get("remision_date")
        if remision_date is not None and not isinstance(remision_date, str):
            raise ValueError("remision_date must be string.")
        out = self.repository.save_remision(
            remision_no=payload.get("remision_no", ""),
            remision_date=remision_date,
            snapshot=payload.get("snapshot", {}),
            dataset_name=payload.get("file"),
            created_by=actor,
        )
        return {"ok": True, **out}

    def get_remision(self, remision_id: int, file_name: str | None):
        out = self.repository.get_remision(remision_id=remision_id, dataset_name=file_name)
        return {"ok": True, **out}

    def delete_remision(self, remision_id: int, file_name: str | None, actor: str):
        out = self.repository.delete_remision(remision_id=remision_id, dataset_name=file_name, actor=actor)
        return {"ok": True, **out}

    def update_remision(self, remision_id: int, payload: dict, file_name: str | None, actor: str):
        return self.repository.update_remision(
            remision_id=remision_id,
            data=payload,
            dataset_name=file_name,
            actor=actor,
        )
