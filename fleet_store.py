from fleet_fuel_store import FleetFuelMixin
from fleet_maintenance_store import FleetMaintenanceMixin
from fleet_vehicle_store import FleetVehicleMixin


class FleetStoreMixin(FleetVehicleMixin, FleetFuelMixin, FleetMaintenanceMixin):
    """Mixin providing fleet management methods. Expects `self._conn()` from host class."""

