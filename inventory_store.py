from inventory_material_store import InventoryMaterialMixin
from inventory_transaction_store import InventoryTransactionMixin


class InventoryStoreMixin(InventoryMaterialMixin, InventoryTransactionMixin):
    """
    Handles operations for the Inventory module.
    Expects self._conn() to be available from AppStore context.
    """

