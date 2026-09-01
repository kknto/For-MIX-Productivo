class FleetService:
    def __init__(self, repository):
        self.repository = repository

    def list_vehicles(self):
        return {"ok": True, "vehicles": self.repository.list_vehicles()}

    def save_vehicle(self, payload, actor: str):
        result = self.repository.save_vehicle(payload, actor=actor)
        return {"ok": True, **result, "vehicles": self.repository.list_vehicles()}

    def delete_vehicle(self, vehicle_id: int, actor: str):
        self.repository.delete_vehicle(vehicle_id, actor=actor)
        return {"ok": True, "vehicles": self.repository.list_vehicles()}

    def list_fuel(self, vehicle_id: int | None, limit: int, date_from: str, date_to: str):
        return {
            "ok": True,
            "records": self.repository.list_fuel(
                vehicle_id=vehicle_id,
                limit=limit,
                date_from=date_from,
                date_to=date_to,
            ),
        }

    def save_fuel(self, payload, actor: str):
        return {"ok": True, **self.repository.save_fuel(payload, actor=actor)}

    def edit_fuel(self, record_id: int, payload):
        return {"ok": True, **self.repository.edit_fuel(record_id, payload)}

    def delete_fuel(self, record_id: int):
        self.repository.delete_fuel(record_id)
        return {"ok": True}

    def summary(self):
        return {"ok": True, "summary": self.repository.summary()}

    def kpis(self):
        return {"ok": True, **self.repository.kpis()}

    def trend(self, vehicle_id: int):
        return {"ok": True, "trend": self.repository.trend(vehicle_id)}

    def list_maintenance(self, vehicle_id: int | None):
        return {"ok": True, "records": self.repository.list_maintenance(vehicle_id=vehicle_id)}

    def save_maintenance(self, payload, actor: str):
        return {"ok": True, **self.repository.save_maintenance(payload, actor=actor)}

    def delete_maintenance(self, record_id: int):
        self.repository.delete_maintenance(record_id)
        return {"ok": True}

    def alerts(self):
        return {"ok": True, "alerts": self.repository.alerts()}
