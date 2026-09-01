def build_store_schema_sql(store) -> str:
    id_type = "SERIAL PRIMARY KEY" if store.is_postgres else "INTEGER PRIMARY KEY AUTOINCREMENT"
    real_type = "DOUBLE PRECISION" if store.is_postgres else "REAL"
    blob_type = "BYTEA" if store.is_postgres else "BLOB"
    return f"""
        CREATE TABLE IF NOT EXISTS datasets(
          id {id_type},
          name TEXT NOT NULL UNIQUE,
          family_code TEXT NOT NULL DEFAULT '',
          headers_json TEXT NOT NULL,
          rows_json TEXT NOT NULL,
          encoding TEXT NOT NULL,
          delimiter TEXT NOT NULL,
          content_hash TEXT NOT NULL,
          row_count INTEGER NOT NULL DEFAULT 0,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          version INTEGER NOT NULL DEFAULT 1,
          deleted_at TEXT
        );
        CREATE TABLE IF NOT EXISTS dataset_revisions(
          id {id_type},
          dataset_id INTEGER NOT NULL REFERENCES datasets(id),
          headers_json TEXT NOT NULL,
          rows_json TEXT NOT NULL,
          content_hash TEXT NOT NULL,
          row_count INTEGER NOT NULL DEFAULT 0,
          note TEXT NOT NULL DEFAULT '',
          created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS app_state(
          key TEXT PRIMARY KEY,
          value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS upload_staging(
          token TEXT PRIMARY KEY,
          original_name TEXT NOT NULL,
          headers_json TEXT NOT NULL,
          rows_json TEXT NOT NULL,
          encoding TEXT NOT NULL,
          delimiter TEXT NOT NULL,
          content_hash TEXT NOT NULL,
          validation_json TEXT NOT NULL,
          created_at TEXT NOT NULL,
          expires_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS qc_profiles(
          dataset_id INTEGER PRIMARY KEY REFERENCES datasets(id),
          values_json TEXT NOT NULL,
          version INTEGER NOT NULL DEFAULT 1,
          updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS doser_profiles(
          dataset_id INTEGER PRIMARY KEY REFERENCES datasets(id),
          params_json TEXT NOT NULL,
          version INTEGER NOT NULL DEFAULT 1,
          updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS users(
          id {id_type},
          username TEXT NOT NULL UNIQUE,
          role TEXT NOT NULL,
          password_hash TEXT NOT NULL,
          is_active INTEGER NOT NULL DEFAULT 1,
          must_change_password INTEGER NOT NULL DEFAULT 0,
          password_updated_at TEXT,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          last_login_at TEXT
        );
        CREATE TABLE IF NOT EXISTS auth_locks(
          username TEXT PRIMARY KEY,
          failed_count INTEGER NOT NULL DEFAULT 0,
          locked_until TEXT,
          last_failed_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS remisiones(
          id {id_type},
          dataset_id INTEGER NOT NULL REFERENCES datasets(id),
          remision_no TEXT NOT NULL UNIQUE,
          cliente TEXT NOT NULL DEFAULT '',
          ubicacion TEXT NOT NULL DEFAULT '',
          formula TEXT NOT NULL DEFAULT '',
          fc TEXT NOT NULL DEFAULT '',
          edad TEXT NOT NULL DEFAULT '',
          tipo TEXT NOT NULL DEFAULT '',
          tma TEXT NOT NULL DEFAULT '',
          rev TEXT NOT NULL DEFAULT '',
          comp TEXT NOT NULL DEFAULT '',
          dosificacion_m3 {real_type} NOT NULL DEFAULT 0,
          peso_receta {real_type} NOT NULL DEFAULT 0,
          peso_teorico_total {real_type} NOT NULL DEFAULT 0,
          peso_real_total {real_type} NOT NULL DEFAULT 0,
          status TEXT NOT NULL DEFAULT 'abierta',
          snapshot_json TEXT NOT NULL,
          created_at TEXT NOT NULL,
          created_by TEXT NOT NULL DEFAULT '',
          updated_at TEXT NOT NULL,
          version INTEGER NOT NULL DEFAULT 1
        );
        CREATE INDEX IF NOT EXISTS idx_remisiones_dataset_created ON remisiones(dataset_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_remisiones_created ON remisiones(created_at DESC);
        CREATE TABLE IF NOT EXISTS audit_log(
          id {id_type},
          created_at TEXT NOT NULL,
          username TEXT NOT NULL DEFAULT '',
          action TEXT NOT NULL,
          entity TEXT NOT NULL DEFAULT '',
          entity_id TEXT NOT NULL DEFAULT '',
          dataset_id INTEGER,
          details_json TEXT NOT NULL DEFAULT '{{}}'
        );
        CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_log(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_audit_dataset_created ON audit_log(dataset_id, created_at DESC);
        CREATE TABLE IF NOT EXISTS materials(
          id {id_type},
          name TEXT NOT NULL UNIQUE,
          doser_alias TEXT NOT NULL DEFAULT '',
          unit TEXT NOT NULL DEFAULT 'kg',
          current_stock {real_type} NOT NULL DEFAULT 0,
          min_stock {real_type} NOT NULL DEFAULT 0,
          status TEXT NOT NULL DEFAULT 'activo',
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS inventory_transactions(
          id {id_type},
          material_id INTEGER NOT NULL REFERENCES materials(id),
          transaction_type TEXT NOT NULL,
          amount {real_type} NOT NULL DEFAULT 0,
          reference TEXT NOT NULL DEFAULT '',
          actor TEXT NOT NULL DEFAULT '',
          created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_inv_trx_created ON inventory_transactions(created_at DESC);
        CREATE TABLE IF NOT EXISTS qc_samples(
          id {id_type},
          sample_code TEXT NOT NULL UNIQUE,
          cast_date TEXT NOT NULL,
          remision_id TEXT NOT NULL DEFAULT '',
          fc_expected {real_type} NOT NULL DEFAULT 0,
          slump_cm {real_type} NOT NULL DEFAULT 0,
          temperature_c {real_type} NOT NULL DEFAULT 0,
          created_at TEXT NOT NULL,
          actor TEXT NOT NULL DEFAULT ''
        );
        CREATE INDEX IF NOT EXISTS idx_qc_samples_cast_date ON qc_samples(cast_date DESC);
        CREATE TABLE IF NOT EXISTS qc_cylinders(
          id {id_type},
          sample_id INTEGER NOT NULL REFERENCES qc_samples(id),
          target_age_days INTEGER NOT NULL DEFAULT 28,
          expected_test_date TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'pendiente',
          strength_kgcm2 {real_type} NOT NULL DEFAULT 0,
          break_date TEXT,
          image_path TEXT NOT NULL DEFAULT '',
          image_data {blob_type} DEFAULT NULL,
          notes TEXT NOT NULL DEFAULT '',
          failure_type TEXT NOT NULL DEFAULT ''
        );
        CREATE INDEX IF NOT EXISTS idx_qc_cyl_expected_date ON qc_cylinders(expected_test_date ASC);
        CREATE INDEX IF NOT EXISTS idx_qc_cyl_sample_id ON qc_cylinders(sample_id);
        CREATE TABLE IF NOT EXISTS vehicles(
          id {id_type},
          unit_number TEXT NOT NULL UNIQUE,
          phone TEXT NOT NULL DEFAULT '',
          year_model TEXT NOT NULL DEFAULT '',
          serial_number TEXT NOT NULL DEFAULT '',
          plate TEXT NOT NULL DEFAULT '',
          driver TEXT NOT NULL DEFAULT '',
          tank_capacity {real_type} NOT NULL DEFAULT 0,
          expected_kml {real_type} NOT NULL DEFAULT 0,
          status TEXT NOT NULL DEFAULT 'activo',
          notes TEXT NOT NULL DEFAULT '',
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS fuel_records(
          id {id_type},
          vehicle_id INTEGER NOT NULL REFERENCES vehicles(id),
          record_date TEXT NOT NULL,
          odometer_km {real_type} NOT NULL DEFAULT 0,
          liters {real_type} NOT NULL DEFAULT 0,
          total_cost {real_type} NOT NULL DEFAULT 0,
          price_per_liter {real_type} NOT NULL DEFAULT 0,
          driver TEXT NOT NULL DEFAULT '',
          station TEXT NOT NULL DEFAULT '',
          km_traveled {real_type} NOT NULL DEFAULT 0,
          kml_real {real_type} NOT NULL DEFAULT 0,
          cost_per_km {real_type} NOT NULL DEFAULT 0,
          notes TEXT NOT NULL DEFAULT '',
          created_by TEXT NOT NULL DEFAULT '',
          created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_fuel_vehicle_date ON fuel_records(vehicle_id, record_date DESC);
        CREATE TABLE IF NOT EXISTS maintenance_records(
          id {id_type},
          vehicle_id INTEGER NOT NULL REFERENCES vehicles(id),
          maintenance_type TEXT NOT NULL DEFAULT '',
          description TEXT NOT NULL DEFAULT '',
          cost {real_type} NOT NULL DEFAULT 0,
          odometer_km {real_type} NOT NULL DEFAULT 0,
          next_km {real_type} NOT NULL DEFAULT 0,
          record_date TEXT NOT NULL,
          provider TEXT NOT NULL DEFAULT '',
          notes TEXT NOT NULL DEFAULT '',
          created_by TEXT NOT NULL DEFAULT '',
          created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_maint_vehicle_date ON maintenance_records(vehicle_id, record_date DESC);
    """
