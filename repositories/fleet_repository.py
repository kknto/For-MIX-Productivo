class FleetRepository:
    def __init__(self, store):
        self.store = store

    def list_vehicles(self):
        return self.store.list_vehicles()

    def save_vehicle(self, data, actor: str):
        return self.store.save_vehicle(data, actor=actor)

    def delete_vehicle(self, vehicle_id: int, actor: str):
        return self.store.delete_vehicle(vehicle_id, actor=actor)

    def list_fuel(self, vehicle_id: int | None = None, limit: int = 200, date_from: str = "", date_to: str = ""):
        return self.store.list_fuel_records(vehicle_id=vehicle_id, limit=limit, date_from=date_from, date_to=date_to)

    def save_fuel(self, data, actor: str):
        return self.store.save_fuel_record(data, actor=actor)

    def edit_fuel(self, record_id: int, data):
        return self.store.edit_fuel_record(record_id, data)

    def delete_fuel(self, record_id: int):
        return self.store.delete_fuel_record(record_id)

    def summary(self):
        return self.store.fleet_summary()

    def kpis(self):
        return self.store.fleet_kpi_stats()

    def trend(self, vehicle_id: int):
        return self.store.fuel_trend(vehicle_id)

    def list_maintenance(self, vehicle_id: int | None = None):
        return self.store.list_maintenance(vehicle_id=vehicle_id)

    def save_maintenance(self, data, actor: str):
        return self.store.save_maintenance(data, actor=actor)

    def delete_maintenance(self, record_id: int):
        return self.store.delete_maintenance(record_id)

    def alerts(self):
        return self.store.maintenance_alerts()
