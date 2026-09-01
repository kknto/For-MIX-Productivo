from doser_param_store import DoserParamStoreMixin
from qc_profile_store import QCProfileStoreMixin


class QCDoserStoreMixin(QCProfileStoreMixin, DoserParamStoreMixin):
    pass
