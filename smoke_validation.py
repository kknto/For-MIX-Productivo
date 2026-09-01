import io
import os
import shutil
import unittest
from datetime import timedelta
from uuid import uuid4
from pathlib import Path

from app import create_app


class SmokeValidationTests(unittest.TestCase):
    def setUp(self):
        self.repo_dir = Path(__file__).resolve().parent
        self.tmp_root = self.repo_dir / ".tmp_smoke"
        self.tmp_root.mkdir(exist_ok=True)
        self.base_dir = self.tmp_root / uuid4().hex
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.old_env = {
            "APP_SECRET_KEY": os.getenv("APP_SECRET_KEY"),
            "DATABASE_URL": os.getenv("DATABASE_URL"),
            "APP_TIMEZONE": os.getenv("APP_TIMEZONE"),
            "SESSION_COOKIE_SECURE": os.getenv("SESSION_COOKIE_SECURE"),
            "FORMIX_ALLOW_DEFAULT_USERS": os.getenv("FORMIX_ALLOW_DEFAULT_USERS"),
            "FORMIX_BOOTSTRAP_ADMIN_USERNAME": os.getenv("FORMIX_BOOTSTRAP_ADMIN_USERNAME"),
            "FORMIX_BOOTSTRAP_ADMIN_PASSWORD": os.getenv("FORMIX_BOOTSTRAP_ADMIN_PASSWORD"),
        }

        os.environ["APP_SECRET_KEY"] = "smoke-validation-secret"
        os.environ.pop("DATABASE_URL", None)
        os.environ["APP_TIMEZONE"] = "America/Cancun"
        os.environ["SESSION_COOKIE_SECURE"] = "0"
        os.environ["FORMIX_ALLOW_DEFAULT_USERS"] = "1"
        os.environ.pop("FORMIX_BOOTSTRAP_ADMIN_USERNAME", None)
        os.environ.pop("FORMIX_BOOTSTRAP_ADMIN_PASSWORD", None)

        self.csv_name = "bootstrap.csv"
        (self.base_dir / self.csv_name).write_text(
            "Formula;COD;f'c;Edad;Tipo;TMA;Rev;Comp\nA1;A1-001;250;28;Bombeable;20;10;Base\n",
            encoding="utf-8",
        )

        self.app = create_app(base_dir=self.base_dir, csv_file=self.csv_name)
        self.app.testing = True
        self.client = self.app.test_client()
        self.store = self.app.extensions["formix_store"]
        self._set_password("admin", "Admin#2026!", "Admin#2026!X")
        self._set_password("dosificador", "Dosi#2026!", "Dosi#2026!X")
        self._set_password("presupuestador", "Presu#2026!", "Presu#2026!X")
        self._set_password("laboratorista", "Lab#2026!", "Lab#2026!X")

    def tearDown(self):
        shutil.rmtree(self.base_dir, ignore_errors=True)
        for key, value in self.old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def _set_password(self, username: str, old_password: str, new_password: str):
        self.store.auth_change_password(username, old_password, new_password)

    def _login(self, username: str, password: str):
        response = self.client.get("/login")
        self.assertEqual(response.status_code, 200)
        with self.client.session_transaction() as session:
            csrf = session.get("_csrf_token")
        self.assertTrue(csrf)
        response = self.client.post(
            "/login",
            data={
                "username": username,
                "password": password,
                "_csrf_token": csrf,
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)
        return response

    def _csrf_token(self) -> str:
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        with self.client.session_transaction() as session:
            token = session.get("_csrf_token")
        self.assertTrue(token)
        return token

    def _api_json(self, method: str, path: str, payload: dict | None = None):
        method = method.upper()
        headers = {}
        json_payload = payload
        if method in {"POST", "PUT", "PATCH", "DELETE"}:
            csrf = self._csrf_token()
            headers["X-CSRF-Token"] = csrf
            if payload is not None:
                json_payload = {**payload, "_csrf_token": csrf}
        return self.client.open(path, method=method, json=json_payload, headers=headers)

    def test_security_handlers_sanitize_errors_and_trace_requests(self):
        self.app.config["PROPAGATE_EXCEPTIONS"] = False

        @self.app.get("/api/_smoke/private_error")
        def _smoke_private_error():
            raise RuntimeError("postgres://secret")

        @self.app.get("/api/_smoke/value_error")
        def _smoke_value_error():
            raise ValueError("Campo requerido")

        response = self.client.get("/login")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.headers.get("X-Request-ID"))
        self.assertEqual(response.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(response.headers.get("X-Frame-Options"), "DENY")

        private_resp = self.client.get("/api/_smoke/private_error")
        self.assertEqual(private_resp.status_code, 500)
        private_payload = private_resp.get_json()
        self.assertFalse(private_payload["ok"])
        self.assertEqual(private_payload["error"], "Error interno del servidor.")
        self.assertTrue(private_payload["request_id"])
        self.assertNotIn("postgres://secret", private_resp.get_data(as_text=True))

        value_resp = self.client.get("/api/_smoke/value_error")
        self.assertEqual(value_resp.status_code, 400)
        value_payload = value_resp.get_json()
        self.assertFalse(value_payload["ok"])
        self.assertEqual(value_payload["error"], "Campo requerido")
        self.assertTrue(value_payload["request_id"])

        origin_resp = self.client.post(
            "/login",
            data={"username": "admin", "password": "Admin#2026!X"},
            headers={"Origin": "https://evil.example"},
        )
        self.assertEqual(origin_resp.status_code, 403)
        self.assertEqual(origin_resp.get_json()["error"], "Origen no autorizado.")

    def _build_remision_snapshot(self, material_id: int, *, real_weight: float = 250.0):
        return {
            "formula": "A1",
            "fc": "250",
            "edad": "28",
            "tipo": "Bombeable",
            "tma": "20",
            "rev": "10",
            "comp": "Base",
            "dose": 1.0,
            "recipeWeight": real_weight,
            "theoreticalWeight": real_weight,
            "realWeight": real_weight,
            "realRows": [
                {
                    "name": "Fino 1",
                    "material_id": material_id,
                    "real": real_weight,
                }
            ],
        }

    def test_admin_session_and_editor_endpoints(self):
        self._login("admin", "Admin#2026!X")
        response = self.client.get("/api/session")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["ok"])
        self.assertIn("editor", payload["allowed_views"])

        data_resp = self.client.get("/api/data")
        self.assertEqual(data_resp.status_code, 200)

        self.assertEqual(self.app.config["BASE_DIR"], str(self.base_dir.resolve()))
        self.assertTrue(Path(self.app.config["QC_UPLOADS_DIR"]).exists())

    def test_bootstrap_admin_is_created_for_empty_preprod_instance(self):
        bootstrap_base = self.tmp_root / f"{uuid4().hex}_bootstrap_admin"
        bootstrap_base.mkdir(parents=True, exist_ok=True)
        os.environ["FORMIX_ALLOW_DEFAULT_USERS"] = "0"
        os.environ["FORMIX_BOOTSTRAP_ADMIN_USERNAME"] = "admin"
        os.environ["FORMIX_BOOTSTRAP_ADMIN_PASSWORD"] = "Preprod#2026X"
        app = create_app(base_dir=bootstrap_base)
        app.testing = True
        client = app.test_client()
        store = app.extensions["formix_store"]

        with store._conn() as conn:
            rows = conn.execute(
                "SELECT username,role,must_change_password FROM users ORDER BY id"
            ).fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["username"], "admin")
        self.assertEqual(rows[0]["role"], "administrador")
        self.assertEqual(int(rows[0]["must_change_password"]), 1)

        response = client.get("/login")
        self.assertEqual(response.status_code, 200)
        with client.session_transaction() as session:
            csrf = session.get("_csrf_token")
        self.assertTrue(csrf)
        login_resp = client.post(
            "/login",
            data={
                "username": "admin",
                "password": "Preprod#2026X",
                "_csrf_token": csrf,
            },
            follow_redirects=False,
        )
        self.assertEqual(login_resp.status_code, 302)
        self.assertIn("/change-password", login_resp.headers.get("Location", ""))
        shutil.rmtree(bootstrap_base, ignore_errors=True)

    def test_presupuestador_is_blocked_from_non_consulta_modules(self):
        self._login("presupuestador", "Presu#2026!X")
        self.assertEqual(self.client.get("/api/inventory/materials").status_code, 403)
        self.assertEqual(self.client.get("/api/fleet/vehicles").status_code, 403)
        self.assertEqual(self.client.get("/api/qclab/samples").status_code, 403)
        self.assertEqual(self.client.get("/api/doser/recipes_global").status_code, 403)
        self.assertEqual(self.client.get("/api/remisiones").status_code, 200)

    def test_presupuestador_can_view_remisiones_but_cannot_delete(self):
        self._login("admin", "Admin#2026!X")
        create_resp = self._api_json(
            "POST",
            "/api/remisiones/save",
            {
                "file": self.csv_name,
                "remision_no": "PRE-001",
                "snapshot": self._build_remision_snapshot(None, real_weight=100.0),
            },
        )
        self.assertEqual(create_resp.status_code, 200)
        remision_id = create_resp.get_json()["id"]

        logout_resp = self.client.post(
            "/logout",
            data={"_csrf_token": self._csrf_token()},
            follow_redirects=False,
        )
        self.assertEqual(logout_resp.status_code, 302)
        self._login("presupuestador", "Presu#2026!X")

        list_resp = self.client.get("/api/remisiones")
        self.assertEqual(list_resp.status_code, 200)
        self.assertTrue(any(item["id"] == remision_id for item in list_resp.get_json()["items"]))

        get_resp = self.client.get(f"/api/remisiones/{remision_id}")
        self.assertEqual(get_resp.status_code, 200)
        self.assertTrue(get_resp.get_json()["ok"])

        delete_resp = self.client.open(
            f"/api/remisiones/{remision_id}",
            method="DELETE",
            headers={"X-CSRF-Token": self._csrf_token()},
        )
        self.assertEqual(delete_resp.status_code, 403)

    def test_dosificador_can_access_operational_modules_but_not_lab(self):
        self._login("dosificador", "Dosi#2026!X")
        self.assertEqual(self.client.get("/api/inventory/materials").status_code, 200)
        self.assertEqual(self.client.get("/api/fleet/vehicles").status_code, 200)
        self.assertEqual(self.client.get("/api/qclab/samples").status_code, 403)
        self.assertEqual(self.client.get("/api/doser/recipes_global").status_code, 200)
        self.assertEqual(self.client.get("/api/doser/params").status_code, 200)

    def test_admin_can_save_qc_and_doser_params(self):
        self._login("admin", "Admin#2026!X")

        qc_before = self.client.get(f"/api/qc?file={self.csv_name}")
        self.assertEqual(qc_before.status_code, 200)
        qc_payload = qc_before.get_json()
        self.assertTrue(qc_payload["ok"])

        qc_values = qc_payload["values"]
        qc_values["Grueso 1"]["pvs"] = 1550.0
        qc_values["Grueso 1"]["pvc"] = 1500.0

        qc_save = self.client.post(
            "/api/qc/save",
            json={
                "file": self.csv_name,
                "version": qc_payload["version"],
                "values": qc_values,
                "_csrf_token": self._csrf_token(),
            },
        )
        self.assertEqual(qc_save.status_code, 200)
        qc_save_payload = qc_save.get_json()
        self.assertTrue(qc_save_payload["ok"])
        self.assertEqual(qc_save_payload["values"]["Grueso 1"]["pvs"], 1550.0)

        params_before = self.client.get(f"/api/doser/params?file={self.csv_name}")
        self.assertEqual(params_before.status_code, 200)
        params_payload = params_before.get_json()
        self.assertTrue(params_payload["ok"])

        params_values = dict(params_payload["values"])
        params_values["aire_pct"] = 2.75
        params_values["cemento_pesp"] = 3.12

        params_save = self.client.post(
            "/api/doser/params/save",
            json={
                "file": self.csv_name,
                "version": params_payload["version"],
                "values": params_values,
                "_csrf_token": self._csrf_token(),
            },
        )
        self.assertEqual(params_save.status_code, 200)
        params_save_payload = params_save.get_json()
        self.assertTrue(params_save_payload["ok"])
        self.assertEqual(params_save_payload["values"]["aire_pct"], 2.75)
        self.assertEqual(params_save_payload["values"]["cemento_pesp"], 3.12)

    def test_dosificador_cannot_save_qc_or_doser_params(self):
        self._login("dosificador", "Dosi#2026!X")

        qc_before = self.client.get(f"/api/qc?file={self.csv_name}")
        self.assertEqual(qc_before.status_code, 200)
        qc_payload = qc_before.get_json()

        denied_qc = self.client.post(
            "/api/qc/save",
            json={
                "file": self.csv_name,
                "version": qc_payload["version"],
                "values": qc_payload["values"],
                "_csrf_token": self._csrf_token(),
            },
        )
        self.assertEqual(denied_qc.status_code, 403)

        params_before = self.client.get(f"/api/doser/params?file={self.csv_name}")
        self.assertEqual(params_before.status_code, 200)
        params_payload = params_before.get_json()

        denied_params = self.client.post(
            "/api/doser/params/save",
            json={
                "file": self.csv_name,
                "version": params_payload["version"],
                "values": params_payload["values"],
                "_csrf_token": self._csrf_token(),
            },
        )
        self.assertEqual(denied_params.status_code, 403)

    def test_admin_inventory_and_fleet_workflows(self):
        self._login("admin", "Admin#2026!X")

        material_resp = self._api_json(
            "POST",
            "/api/inventory/materials",
            {
                "name": "Arena Prueba",
                "doser_alias": "Fino 1",
                "unit": "m3",
                "min_stock": 5,
            },
        )
        self.assertEqual(material_resp.status_code, 200)
        material_payload = material_resp.get_json()
        self.assertTrue(material_payload["ok"])
        material_id = material_payload["id"]

        trx_resp = self._api_json(
            "POST",
            "/api/inventory/transactions",
            {
                "material_id": material_id,
                "transaction_type": "ENTRADA",
                "amount": 12.5,
                "reference": "SMOKE-ENTRY",
            },
        )
        self.assertEqual(trx_resp.status_code, 200)
        trx_payload = trx_resp.get_json()
        self.assertTrue(trx_payload["ok"])
        self.assertEqual(trx_payload["new_stock"], 12.5)

        list_trx = self.client.get("/api/inventory/transactions?limit=20")
        self.assertEqual(list_trx.status_code, 200)
        trx_items = list_trx.get_json()["transactions"]
        self.assertTrue(any(item["reference"] == "SMOKE-ENTRY" for item in trx_items))

        summary_date = self.store.get_now().strftime("%Y-%m-%d")
        daily_summary = self.client.get(f"/api/inventory/daily_summary?date={summary_date}")
        self.assertEqual(daily_summary.status_code, 200)
        summary_payload = daily_summary.get_json()
        self.assertTrue(summary_payload["ok"])
        self.assertTrue(any(item["name"] == "Arena Prueba" for item in summary_payload["summary"]["current_inventory"]))

        vehicle_resp = self._api_json(
            "POST",
            "/api/fleet/vehicles",
            {
                "unit_number": "SMK-01",
                "driver": "Chofer Demo",
                "plate": "TST1234",
                "tank_capacity": 120,
                "expected_kml": 2.8,
            },
        )
        self.assertEqual(vehicle_resp.status_code, 200)
        vehicle_payload = vehicle_resp.get_json()
        self.assertTrue(vehicle_payload["ok"])
        vehicle_id = vehicle_payload["id"]

        fuel_resp = self._api_json(
            "POST",
            "/api/fleet/fuel",
            {
                "vehicle_id": vehicle_id,
                "record_date": f"{summary_date} 08:00:00",
                "odometer_km": 1000,
                "liters": 40,
                "total_cost": 960,
                "driver": "Chofer Demo",
                "station": "SMOKE",
            },
        )
        self.assertEqual(fuel_resp.status_code, 200)
        fuel_payload = fuel_resp.get_json()
        self.assertTrue(fuel_payload["ok"])

        fleet_summary = self.client.get("/api/fleet/summary")
        self.assertEqual(fleet_summary.status_code, 200)
        fleet_summary_payload = fleet_summary.get_json()
        self.assertTrue(fleet_summary_payload["ok"])
        self.assertTrue(any(item["unit_number"] == "SMK-01" for item in fleet_summary_payload["summary"]))

        fleet_kpis = self.client.get("/api/fleet/kpis")
        self.assertEqual(fleet_kpis.status_code, 200)
        self.assertTrue(fleet_kpis.get_json()["ok"])

    def test_admin_can_manage_fleet_maintenance_and_trends(self):
        self._login("admin", "Admin#2026!X")

        today = self.store.get_now().strftime("%Y-%m-%d")
        vehicle_resp = self._api_json(
            "POST",
            "/api/fleet/vehicles",
            {
                "unit_number": "SMK-02",
                "driver": "Chofer KPI",
                "plate": "KPI2026",
                "tank_capacity": 150,
                "expected_kml": 3.1,
            },
        )
        self.assertEqual(vehicle_resp.status_code, 200)
        vehicle_id = vehicle_resp.get_json()["id"]

        first_fuel = self._api_json(
            "POST",
            "/api/fleet/fuel",
            {
                "vehicle_id": vehicle_id,
                "record_date": f"{today} 07:00:00",
                "odometer_km": 1000,
                "liters": 50,
                "total_cost": 1200,
                "driver": "Chofer KPI",
                "station": "BASE",
            },
        )
        self.assertEqual(first_fuel.status_code, 200)
        self.assertTrue(first_fuel.get_json()["ok"])

        second_fuel = self._api_json(
            "POST",
            "/api/fleet/fuel",
            {
                "vehicle_id": vehicle_id,
                "record_date": f"{today} 12:00:00",
                "odometer_km": 1250,
                "liters": 40,
                "total_cost": 1000,
                "driver": "Chofer KPI",
                "station": "RUTA",
            },
        )
        self.assertEqual(second_fuel.status_code, 200)
        second_payload = second_fuel.get_json()
        self.assertTrue(second_payload["ok"])
        self.assertGreater(second_payload["km_traveled"], 0)

        fuel_list = self.client.get(f"/api/fleet/fuel?vehicle_id={vehicle_id}&limit=10")
        self.assertEqual(fuel_list.status_code, 200)
        fuel_records = fuel_list.get_json()["records"]
        self.assertEqual(len(fuel_records), 2)
        editable_record_id = fuel_records[0]["id"]

        edit_resp = self._api_json(
            "PUT",
            f"/api/fleet/fuel/{editable_record_id}",
            {
                "record_date": f"{today} 12:30:00",
                "odometer_km": 1250,
                "liters": 42,
                "total_cost": 1092,
                "driver": "Chofer KPI",
                "station": "RUTA-EDIT",
                "notes": "ajuste smoke",
            },
        )
        self.assertEqual(edit_resp.status_code, 200)
        self.assertTrue(edit_resp.get_json()["ok"])

        trend_resp = self.client.get(f"/api/fleet/trend/{vehicle_id}")
        self.assertEqual(trend_resp.status_code, 200)
        trend_payload = trend_resp.get_json()
        self.assertTrue(trend_payload["ok"])
        self.assertTrue(trend_payload["trend"])

        maintenance_resp = self._api_json(
            "POST",
            "/api/fleet/maintenance",
            {
                "vehicle_id": vehicle_id,
                "maintenance_type": "Cambio de aceite",
                "description": "Servicio programado",
                "cost": 1500,
                "odometer_km": 1250,
                "next_km": 1700,
                "record_date": f"{today} 13:00:00",
                "provider": "Taller Smoke",
            },
        )
        self.assertEqual(maintenance_resp.status_code, 200)
        self.assertTrue(maintenance_resp.get_json()["ok"])

        maintenance_list = self.client.get(f"/api/fleet/maintenance?vehicle_id={vehicle_id}")
        self.assertEqual(maintenance_list.status_code, 200)
        maintenance_payload = maintenance_list.get_json()
        self.assertTrue(maintenance_payload["ok"])
        self.assertEqual(len(maintenance_payload["records"]), 1)
        maintenance_id = maintenance_payload["records"][0]["id"]

        alerts_resp = self.client.get("/api/fleet/alerts")
        self.assertEqual(alerts_resp.status_code, 200)
        alerts_payload = alerts_resp.get_json()
        self.assertTrue(alerts_payload["ok"])
        self.assertTrue(any(item["vehicle_id"] == vehicle_id for item in alerts_payload["alerts"]))

        delete_maintenance = self.client.open(
            f"/api/fleet/maintenance/{maintenance_id}",
            method="DELETE",
            headers={"X-CSRF-Token": self._csrf_token()},
        )
        self.assertEqual(delete_maintenance.status_code, 200)
        self.assertTrue(delete_maintenance.get_json()["ok"])

    def test_admin_can_manage_users(self):
        self._login("admin", "Admin#2026!X")

        create_resp = self._api_json(
            "POST",
            "/api/users",
            {
                "username": "smokeuser",
                "password": "Smoke#2026!",
                "role": "operador",
                "is_active": 1,
            },
        )
        self.assertEqual(create_resp.status_code, 200)
        create_payload = create_resp.get_json()
        self.assertTrue(create_payload["ok"])
        user_id = create_payload["user"]["id"]

        list_resp = self.client.get("/api/users")
        self.assertEqual(list_resp.status_code, 200)
        list_payload = list_resp.get_json()
        self.assertTrue(any(user["username"] == "smokeuser" for user in list_payload["users"]))

        reset_resp = self._api_json(
            "POST",
            f"/api/users/{user_id}/reset_password",
            {"new_password": "Reset#2026!"},
        )
        self.assertEqual(reset_resp.status_code, 200)
        self.assertTrue(reset_resp.get_json()["ok"])

        delete_resp = self.client.open(
            f"/api/users/{user_id}",
            method="DELETE",
            headers={"X-CSRF-Token": self._csrf_token()},
        )
        self.assertEqual(delete_resp.status_code, 200)
        self.assertTrue(delete_resp.get_json()["ok"])

    def test_admin_can_manage_remisiones_and_sync_inventory(self):
        self._login("admin", "Admin#2026!X")
        remision_date = (self.store.get_now().date() - timedelta(days=1)).strftime("%Y-%m-%d")

        material_resp = self._api_json(
            "POST",
            "/api/inventory/materials",
            {
                "name": "Arena Remision",
                "doser_alias": "Fino 1",
                "unit": "kg",
                "min_stock": 0,
            },
        )
        self.assertEqual(material_resp.status_code, 200)
        material_id = material_resp.get_json()["id"]

        stock_resp = self._api_json(
            "POST",
            "/api/inventory/transactions",
            {
                "material_id": material_id,
                "transaction_type": "ENTRADA",
                "amount": 500,
                "reference": "SMOKE-REMISION-STOCK",
            },
        )
        self.assertEqual(stock_resp.status_code, 200)
        self.assertEqual(stock_resp.get_json()["new_stock"], 500)

        save_resp = self._api_json(
            "POST",
            "/api/remisiones/save",
            {
                "file": self.csv_name,
                "remision_no": " R-001 ",
                "remision_date": remision_date,
                "snapshot": self._build_remision_snapshot(material_id, real_weight=250.0),
            },
        )
        self.assertEqual(save_resp.status_code, 200)
        save_payload = save_resp.get_json()
        self.assertTrue(save_payload["ok"])
        remision_id = save_payload["id"]
        self.assertEqual(save_payload["remision_no"], "R-001")
        self.assertTrue(save_payload["created_at"].startswith(remision_date))

        list_resp = self.client.get(f"/api/remisiones?date={remision_date}")
        self.assertEqual(list_resp.status_code, 200)
        list_payload = list_resp.get_json()
        self.assertTrue(any(item["id"] == remision_id for item in list_payload["items"]))

        get_resp = self.client.get(f"/api/remisiones/{remision_id}")
        self.assertEqual(get_resp.status_code, 200)
        get_payload = get_resp.get_json()
        self.assertTrue(get_payload["ok"])
        self.assertEqual(get_payload["snapshot"]["remisionNo"], "R-001")
        self.assertEqual(get_payload["file"], self.csv_name)
        self.assertEqual(get_payload["snapshot"]["timestamp"], save_payload["created_at"])

        trx_resp = self.client.get("/api/inventory/transactions?limit=20")
        self.assertEqual(trx_resp.status_code, 200)
        remision_trx = next(
            item for item in trx_resp.get_json()["transactions"] if item["reference"] == "Remision #R-001"
        )
        self.assertEqual(remision_trx["transaction_type"], "SALIDA")
        self.assertEqual(float(remision_trx["amount"]), 250.0)
        self.assertTrue(remision_trx["created_at"].startswith(remision_date))

        materials_resp = self.client.get("/api/inventory/materials")
        self.assertEqual(materials_resp.status_code, 200)
        arena = next(item for item in materials_resp.get_json()["materials"] if item["id"] == material_id)
        self.assertEqual(float(arena["current_stock"]), 250.0)

        updated_date = "2026-03-19 06:45:00"
        update_resp = self._api_json(
            "PUT",
            f"/api/remisiones/{remision_id}",
            {
                "file": self.csv_name,
                "remision_no": "R-001",
                "formula": "A1-ACT",
                "dosificacion_m3": 1.5,
                "peso_real_total": 245.0,
                "cliente": "Cliente Smoke",
                "ubicacion": "Obra Norte",
                "created_at": updated_date,
            },
        )
        self.assertEqual(update_resp.status_code, 200)
        self.assertTrue(update_resp.get_json()["ok"])

        updated_remision = self.client.get(f"/api/remisiones/{remision_id}")
        self.assertEqual(updated_remision.status_code, 200)
        updated_payload = updated_remision.get_json()
        self.assertEqual(updated_payload["formula"], "A1-ACT")
        self.assertEqual(updated_payload["snapshot"]["cliente"], "Cliente Smoke")
        self.assertEqual(updated_payload["snapshot"]["ubicacion"], "Obra Norte")
        self.assertEqual(updated_payload["snapshot"]["timestamp"], updated_date)

        trx_after_update = self.client.get("/api/inventory/transactions?limit=20")
        updated_trx = next(
            item
            for item in trx_after_update.get_json()["transactions"]
            if item["reference"] == "Remision #R-001"
        )
        self.assertEqual(updated_trx["created_at"], updated_date)

        summary_resp = self.client.get("/api/inventory/daily_summary?date=2026-03-19")
        self.assertEqual(summary_resp.status_code, 200)
        summary_payload = summary_resp.get_json()
        self.assertTrue(summary_payload["ok"])
        self.assertEqual(summary_payload["summary"]["production"]["total_remisiones"], 1)
        self.assertTrue(
            any(item["remision_no"] == "R-001" for item in summary_payload["summary"]["remisiones"])
        )

        paged_resp = self.client.get(
            f"/api/remisiones?cliente=Cliente%20Smoke&source_file={self.csv_name}&date_from=2026-03-19&date_to=2026-03-19&page=1&page_size=1"
        )
        self.assertEqual(paged_resp.status_code, 200)
        paged_payload = paged_resp.get_json()
        self.assertTrue(paged_payload["ok"])
        self.assertEqual(paged_payload["total"], 1)
        self.assertEqual(paged_payload["total_pages"], 1)
        self.assertEqual(paged_payload["page"], 1)
        self.assertEqual(len(paged_payload["items"]), 1)
        self.assertEqual(paged_payload["items"][0]["cliente"], "Cliente Smoke")
        self.assertEqual(paged_payload["items"][0]["source_file"], self.csv_name)

        delete_resp = self.client.open(
            f"/api/remisiones/{remision_id}",
            method="DELETE",
            headers={"X-CSRF-Token": self._csrf_token()},
        )
        self.assertEqual(delete_resp.status_code, 200)
        self.assertTrue(delete_resp.get_json()["ok"])

        missing_resp = self.client.get(f"/api/remisiones/{remision_id}")
        self.assertEqual(missing_resp.status_code, 404)

    def test_remision_save_rejects_invalid_and_future_dates(self):
        self._login("admin", "Admin#2026!X")

        invalid_resp = self._api_json(
            "POST",
            "/api/remisiones/save",
            {
                "file": self.csv_name,
                "remision_no": "BAD-DATE-001",
                "remision_date": "2026/03/20",
                "snapshot": self._build_remision_snapshot(None, real_weight=100.0),
            },
        )
        self.assertEqual(invalid_resp.status_code, 400)
        self.assertIn("YYYY-MM-DD", invalid_resp.get_json()["error"])

        future_date = (self.store.get_now().date() + timedelta(days=1)).strftime("%Y-%m-%d")
        future_resp = self._api_json(
            "POST",
            "/api/remisiones/save",
            {
                "file": self.csv_name,
                "remision_no": "BAD-DATE-002",
                "remision_date": future_date,
                "snapshot": self._build_remision_snapshot(None, real_weight=100.0),
            },
        )
        self.assertEqual(future_resp.status_code, 400)
        self.assertIn("no puede ser futura", future_resp.get_json()["error"])

    def test_editor_history_can_restore_previous_revision(self):
        self._login("admin", "Admin#2026!X")

        original_resp = self.client.get("/api/data")
        self.assertEqual(original_resp.status_code, 200)
        original_payload = original_resp.get_json()
        original_headers = list(original_payload["headers"])
        original_rows = [list(row) for row in original_payload["rows"]]
        original_version = int(original_payload["version"])

        mutated_rows = [list(row) for row in original_rows]
        mutated_rows[0][0] = "A1-EDITADA"

        save_resp = self._api_json(
            "POST",
            "/api/save",
            {
                "headers": original_headers,
                "rows": mutated_rows,
                "version": original_version,
            },
        )
        self.assertEqual(save_resp.status_code, 200)
        save_payload = save_resp.get_json()
        self.assertTrue(save_payload["ok"])
        changed_version = int(save_payload["version"])
        self.assertGreater(changed_version, original_version)

        changed_resp = self.client.get("/api/data")
        self.assertEqual(changed_resp.status_code, 200)
        changed_payload = changed_resp.get_json()
        self.assertEqual(changed_payload["rows"][0][0], "A1-EDITADA")

        history_resp = self.client.get(f"/api/history?file={self.csv_name}")
        self.assertEqual(history_resp.status_code, 200)
        history_payload = history_resp.get_json()
        self.assertTrue(history_payload["ok"])
        self.assertTrue(history_payload["revisions"])
        revision_id = int(history_payload["revisions"][0]["id"])

        restore_resp = self._api_json(
            "POST",
            "/api/history/restore",
            {
                "file": self.csv_name,
                "revision_id": revision_id,
                "version": changed_version,
            },
        )
        self.assertEqual(restore_resp.status_code, 200)
        restore_payload = restore_resp.get_json()
        self.assertTrue(restore_payload["ok"])
        self.assertGreater(int(restore_payload["version"]), changed_version)

        restored_resp = self.client.get("/api/data")
        self.assertEqual(restored_resp.status_code, 200)
        restored_payload = restored_resp.get_json()
        self.assertEqual(restored_payload["rows"], original_rows)
        self.assertEqual(restored_payload["headers"], original_headers)

    def test_editor_upload_preview_and_commit_new_dataset(self):
        self._login("admin", "Admin#2026!X")

        upload_name = "pilot_upload.csv"
        upload_bytes = (
            "Formula;COD;f'c;Edad;Tipo;TMA;Rev;Comp\n"
            "B2;B2-101;300;28;Bombeable;20;11;Piloto\n"
        ).encode("utf-8")

        preview_resp = self.client.post(
            "/api/upload/preview",
            data={
                "file": (io.BytesIO(upload_bytes), upload_name),
                "_csrf_token": self._csrf_token(),
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(preview_resp.status_code, 200)
        preview_payload = preview_resp.get_json()
        self.assertTrue(preview_payload["ok"])
        self.assertEqual(preview_payload["file"], upload_name)
        self.assertEqual(preview_payload["suggested_mode"], "new")
        self.assertIsNone(preview_payload["duplicate_of"])
        self.assertIn("token", preview_payload)

        commit_resp = self._api_json(
            "POST",
            "/api/upload/commit",
            {
                "token": preview_payload["token"],
                "mode": "new",
                "family_code": "PILOTO",
            },
        )
        self.assertEqual(commit_resp.status_code, 200)
        commit_payload = commit_resp.get_json()
        self.assertTrue(commit_payload["ok"])
        self.assertEqual(commit_payload["file"], upload_name)
        self.assertEqual(commit_payload["family"], "PILOTO")
        self.assertIn(upload_name, commit_payload["files"])

        data_resp = self.client.get("/api/data")
        self.assertEqual(data_resp.status_code, 200)
        data_payload = data_resp.get_json()
        self.assertEqual(data_payload["file"], upload_name)
        self.assertEqual(data_payload["family"], "PILOTO")
        self.assertEqual(data_payload["rows"][0][0], "B2")
        self.assertEqual(data_payload["rows"][0][1], "B2-101")

        history_resp = self.client.get(f"/api/history?file={upload_name}")
        self.assertEqual(history_resp.status_code, 200)
        history_payload = history_resp.get_json()
        self.assertTrue(history_payload["ok"])
        self.assertEqual(history_payload["file"], upload_name)

        summary_resp = self.client.get("/api/families/summary")
        self.assertEqual(summary_resp.status_code, 200)
        summary_payload = summary_resp.get_json()
        self.assertTrue(summary_payload["ok"])
        self.assertTrue(any(item["family"] == "PILOTO" for item in summary_payload["summary"]))

    def test_editor_upload_commit_replace_updates_active_dataset(self):
        self._login("admin", "Admin#2026!X")

        upload_name = "replace_source.csv"
        upload_bytes = (
            "Formula;COD;f'c;Edad;Tipo;TMA;Rev;Comp\n"
            "A9;A9-909;350;14;Tremie;40;22;Reemplazo\n"
        ).encode("utf-8")

        preview_resp = self.client.post(
            "/api/upload/preview",
            data={
                "file": (io.BytesIO(upload_bytes), upload_name),
                "_csrf_token": self._csrf_token(),
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(preview_resp.status_code, 200)
        preview_payload = preview_resp.get_json()
        self.assertTrue(preview_payload["ok"])

        commit_resp = self._api_json(
            "POST",
            "/api/upload/commit",
            {
                "token": preview_payload["token"],
                "mode": "replace",
                "target_file": self.csv_name,
                "family_code": "REPLAZO",
            },
        )
        self.assertEqual(commit_resp.status_code, 200)
        commit_payload = commit_resp.get_json()
        self.assertTrue(commit_payload["ok"])
        self.assertEqual(commit_payload["file"], self.csv_name)
        self.assertEqual(commit_payload["family"], "REPLAZO")
        self.assertEqual(commit_payload["replaced"], 1)

        data_resp = self.client.get("/api/data")
        self.assertEqual(data_resp.status_code, 200)
        data_payload = data_resp.get_json()
        self.assertEqual(data_payload["file"], self.csv_name)
        self.assertEqual(data_payload["family"], "REPLAZO")
        self.assertEqual(data_payload["rows"][0][0], "A9")
        self.assertEqual(data_payload["rows"][0][1], "A9-909")

    def test_editor_upload_commit_merge_updates_and_inserts_rows(self):
        self._login("admin", "Admin#2026!X")

        upload_name = "merge_source.csv"
        upload_bytes = (
            "Formula;COD;f'c;Edad;Tipo;TMA;Rev;Comp\n"
            "A1;A1-001;250;28;Bombeable;20;10;Base\n"
            "A2;A2-001;300;14;Tiro directo;40;03;Nueva\n"
        ).encode("utf-8")

        preview_resp = self.client.post(
            "/api/upload/preview",
            data={
                "file": (io.BytesIO(upload_bytes), upload_name),
                "_csrf_token": self._csrf_token(),
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(preview_resp.status_code, 200)
        preview_payload = preview_resp.get_json()
        self.assertTrue(preview_payload["ok"])

        commit_resp = self._api_json(
            "POST",
            "/api/upload/commit",
            {
                "token": preview_payload["token"],
                "mode": "merge",
                "target_file": self.csv_name,
            },
        )
        self.assertEqual(commit_resp.status_code, 200)
        commit_payload = commit_resp.get_json()
        self.assertTrue(commit_payload["ok"])
        self.assertEqual(commit_payload["file"], self.csv_name)
        self.assertEqual(commit_payload["inserted"], 1)
        self.assertEqual(commit_payload["updated"], 1)
        self.assertEqual(commit_payload["rows"], 2)

        data_resp = self.client.get("/api/data")
        self.assertEqual(data_resp.status_code, 200)
        data_payload = data_resp.get_json()
        self.assertEqual(data_payload["file"], self.csv_name)
        self.assertEqual(len(data_payload["rows"]), 2)
        self.assertEqual(data_payload["rows"][0][1], "A1-001")
        self.assertTrue(any(row[0] == "A2" and row[1] == "A2-001" for row in data_payload["rows"]))

    def test_admin_can_create_and_restore_backup(self):
        self._login("admin", "Admin#2026!X")

        original_resp = self.client.get("/api/data")
        self.assertEqual(original_resp.status_code, 200)
        original_payload = original_resp.get_json()
        original_headers = list(original_payload["headers"])
        original_rows = [list(row) for row in original_payload["rows"]]
        original_version = int(original_payload["version"])

        backup_create = self._api_json("POST", "/api/backups/create", {"reason": "smoke_restore"})
        self.assertEqual(backup_create.status_code, 200)
        backup_payload = backup_create.get_json()
        self.assertTrue(backup_payload["ok"])
        backup_file = backup_payload["backup"]["file"]
        self.assertTrue(backup_file.endswith(".sqlite3"))

        changed_rows = [list(row) for row in original_rows]
        changed_rows[0][1] = "A1-RESTORE-TEST"
        save_resp = self._api_json(
            "POST",
            "/api/save",
            {
                "headers": original_headers,
                "rows": changed_rows,
                "version": original_version,
            },
        )
        self.assertEqual(save_resp.status_code, 200)
        self.assertTrue(save_resp.get_json()["ok"])

        changed_resp = self.client.get("/api/data")
        self.assertEqual(changed_resp.status_code, 200)
        self.assertEqual(changed_resp.get_json()["rows"][0][1], "A1-RESTORE-TEST")

        restore_resp = self._api_json(
            "POST",
            "/api/backups/restore",
            {"file": backup_file},
        )
        self.assertEqual(restore_resp.status_code, 200)
        restore_payload = restore_resp.get_json()
        self.assertTrue(restore_payload["ok"])
        self.assertEqual(restore_payload["backup"], backup_file)
        self.assertEqual(restore_payload["active_file"], self.csv_name)

        restored_resp = self.client.get("/api/data")
        self.assertEqual(restored_resp.status_code, 200)
        restored_payload = restored_resp.get_json()
        self.assertEqual(restored_payload["headers"], original_headers)
        self.assertEqual(restored_payload["rows"], original_rows)

    def test_laboratorista_can_manage_lab_but_not_admin_users(self):
        self._login("laboratorista", "Lab#2026!X")
        self.assertEqual(self.client.get("/api/users").status_code, 403)
        self.assertEqual(self.client.get("/api/inventory/materials").status_code, 403)

        today = self.store.get_now().strftime("%Y-%m-%d")
        sample_resp = self._api_json(
            "POST",
            "/api/qclab/samples",
            {
                "sample_code": "LAB-SMOKE-01",
                "cast_date": today,
                "fc_expected": 250,
                "slump_cm": 10,
                "cylinder_ages": [7, 28],
            },
        )
        self.assertEqual(sample_resp.status_code, 200)
        sample_payload = sample_resp.get_json()
        self.assertTrue(sample_payload["ok"])
        sample_id = sample_payload["sample"]["id"]

        get_sample = self.client.get(f"/api/qclab/samples/{sample_id}")
        self.assertEqual(get_sample.status_code, 200)
        sample_detail = get_sample.get_json()
        self.assertTrue(sample_detail["ok"])
        self.assertEqual(len(sample_detail["sample"]["cylinders"]), 2)

        cylinders_resp = self.client.get("/api/qclab/cylinders?pending_only=false")
        self.assertEqual(cylinders_resp.status_code, 200)
        cylinders_payload = cylinders_resp.get_json()
        self.assertTrue(any(cyl["sample_id"] == sample_id for cyl in cylinders_payload["cylinders"]))

        delete_sample = self.client.open(
            f"/api/qclab/samples/{sample_id}",
            method="DELETE",
            headers={"X-CSRF-Token": self._csrf_token()},
        )
        self.assertEqual(delete_sample.status_code, 200)
        self.assertTrue(delete_sample.get_json()["ok"])

    def test_laboratorista_can_test_cylinders_and_lookup_remision(self):
        self._login("admin", "Admin#2026!X")

        material_resp = self._api_json(
            "POST",
            "/api/inventory/materials",
            {
                "name": "Arena Lab",
                "doser_alias": "Fino 1",
                "unit": "kg",
                "min_stock": 0,
            },
        )
        self.assertEqual(material_resp.status_code, 200)
        material_id = material_resp.get_json()["id"]

        stock_resp = self._api_json(
            "POST",
            "/api/inventory/transactions",
            {
                "material_id": material_id,
                "transaction_type": "ENTRADA",
                "amount": 300,
                "reference": "SMOKE-LAB-STOCK",
            },
        )
        self.assertEqual(stock_resp.status_code, 200)

        remision_resp = self._api_json(
            "POST",
            "/api/remisiones/save",
            {
                "file": self.csv_name,
                "remision_no": "LAB-001",
                "snapshot": self._build_remision_snapshot(material_id, real_weight=120.0),
            },
        )
        self.assertEqual(remision_resp.status_code, 200)
        self.assertTrue(remision_resp.get_json()["ok"])

        logout_resp = self.client.post(
            "/logout",
            data={"_csrf_token": self._csrf_token()},
            follow_redirects=False,
        )
        self.assertEqual(logout_resp.status_code, 302)
        self._login("laboratorista", "Lab#2026!X")

        lookup_resp = self.client.get("/api/qclab/lookup_remision/LAB-001")
        self.assertEqual(lookup_resp.status_code, 200)
        lookup_payload = lookup_resp.get_json()
        self.assertTrue(lookup_payload["ok"])
        self.assertEqual(lookup_payload["remision"]["remision_no"], "LAB-001")

        today = self.store.get_now().strftime("%Y-%m-%d")
        sample_resp = self._api_json(
            "POST",
            "/api/qclab/samples",
            {
                "sample_code": "LAB-SMOKE-02",
                "cast_date": today,
                "remision_id": "LAB-001",
                "fc_expected": 250,
                "slump_cm": 12,
                "cylinder_ages": [7],
            },
        )
        self.assertEqual(sample_resp.status_code, 200)
        sample_payload = sample_resp.get_json()
        self.assertTrue(sample_payload["ok"])
        sample = sample_payload["sample"]
        cylinder_id = sample["cylinders"][0]["id"]

        invalid_upload_resp = self.client.post(
            f"/api/qclab/cylinders/{cylinder_id}/test",
            data={
                "status": "ensayado",
                "strength_kgcm2": "285.5",
                "break_date": f"{today} 09:00:00",
                "notes": "resultado smoke",
                "_csrf_token": self._csrf_token(),
                "image": (io.BytesIO(b"not an image"), "evidence.txt"),
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(invalid_upload_resp.status_code, 400)
        self.assertIn("Formato de imagen no permitido", invalid_upload_resp.get_json()["error"])

        test_resp = self.client.post(
            f"/api/qclab/cylinders/{cylinder_id}/test",
            data={
                "status": "ensayado",
                "strength_kgcm2": "285.5",
                "break_date": f"{today} 09:00:00",
                "notes": "resultado smoke",
                "_csrf_token": self._csrf_token(),
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(test_resp.status_code, 200)
        test_payload = test_resp.get_json()
        self.assertTrue(test_payload["ok"])
        tested_cylinder = test_payload["sample"]["cylinders"][0]
        self.assertEqual(tested_cylinder["status"], "ensayado")
        self.assertEqual(float(tested_cylinder["strength_kgcm2"]), 285.5)

        trends_resp = self.client.get("/api/qclab/stats/trends")
        self.assertEqual(trends_resp.status_code, 200)
        trends_payload = trends_resp.get_json()
        self.assertTrue(trends_payload["ok"])
        self.assertTrue(any(item["sample_code"] == "LAB-SMOKE-02" for item in trends_payload["data"]))

    def test_instance_feature_toggles_disable_modules(self):
        feature_base = self.tmp_root / f"{uuid4().hex}_features"
        feature_base.mkdir(parents=True, exist_ok=True)
        (feature_base / self.csv_name).write_text(
            "Formula;COD;f'c;Edad;Tipo;TMA;Rev;Comp\nB1;B1-001;300;28;Bombeable;20;12;Base\n",
            encoding="utf-8",
        )
        (feature_base / "instance.toml").write_text(
            """
[instance]
brand_name = "Piloto"
plant_name = "Planta Demo"

[features]
editor = true
consulta = true
dosificador = false
remisiones = false
inventario = false
laboratorio = false
flotilla = false
usuarios = false
""".strip(),
            encoding="utf-8",
        )

        feature_app = create_app(base_dir=feature_base, csv_file=self.csv_name)
        feature_app.testing = True
        feature_client = feature_app.test_client()
        feature_store = feature_app.extensions["formix_store"]
        feature_store.auth_change_password("admin", "Admin#2026!", "Admin#2026!Y")

        login_page = feature_client.get("/login")
        self.assertEqual(login_page.status_code, 200)
        with feature_client.session_transaction() as feature_session:
            feature_csrf = feature_session.get("_csrf_token")
        self.assertTrue(feature_csrf)

        login_resp = feature_client.post(
            "/login",
            data={
                "username": "admin",
                "password": "Admin#2026!Y",
                "_csrf_token": feature_csrf,
            },
            follow_redirects=False,
        )
        self.assertEqual(login_resp.status_code, 302)

        session_resp = feature_client.get("/api/session")
        self.assertEqual(session_resp.status_code, 200)
        session_payload = session_resp.get_json()
        self.assertEqual(session_payload["allowed_views"], ["consulta", "editor"])
        self.assertFalse(session_payload["enabled_features"]["dosificador"])
        self.assertFalse(session_payload["enabled_features"]["remisiones"])
        self.assertFalse(session_payload["enabled_features"]["inventario"])

        self.assertEqual(feature_client.get("/api/data").status_code, 200)
        self.assertEqual(feature_client.get("/api/families/summary").status_code, 200)
        self.assertEqual(feature_client.get("/api/doser/recipes_global").status_code, 404)
        self.assertEqual(feature_client.get("/api/remisiones").status_code, 404)
        self.assertEqual(feature_client.get("/api/inventory/materials").status_code, 404)
        self.assertEqual(feature_client.get("/api/fleet/vehicles").status_code, 404)
        self.assertEqual(feature_client.get("/api/qclab/samples").status_code, 404)
        self.assertEqual(feature_client.get("/api/users").status_code, 404)

        shutil.rmtree(feature_base, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
