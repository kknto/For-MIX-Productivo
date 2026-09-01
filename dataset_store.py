from dataset_backup_store import DatasetBackupMixin
from dataset_catalog_store import DatasetCatalogMixin
from dataset_core_store import DatasetCoreMixin
from dataset_history_store import DatasetHistoryMixin
from dataset_mutation_store import DatasetMutationMixin
from dataset_upload_store import DatasetUploadMixin


class DatasetStoreMixin(
    DatasetBackupMixin,
    DatasetUploadMixin,
    DatasetHistoryMixin,
    DatasetCatalogMixin,
    DatasetMutationMixin,
    DatasetCoreMixin,
):
    pass
