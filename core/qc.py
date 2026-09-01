QC_AGGREGATES = ("Fino 1", "Fino 2", "Grueso 1", "Grueso 2")
QC_FIELDS = ("pvs", "pvc", "densidad", "absorcion", "humedad")


def default_qc_values() -> dict:
    return {
        agg: {"pvs": 0.0, "pvc": 0.0, "densidad": 0.0, "absorcion": 0.0, "humedad": 0.0}
        for agg in QC_AGGREGATES
    }
