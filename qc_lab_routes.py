import os
import uuid

from flask import Blueprint, Response, current_app, jsonify, render_template, request
from werkzeug.utils import secure_filename

from core.rbac import LABORATORIO_ROLES, QC_LAB_WRITE_ROLES
from http_security import api_error_response
from repositories.qc_lab_repository import QcLabRepository
from services.qc_lab_service import QcLabService


ALLOWED_IMAGE_MIME = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def read_validated_qc_image(file, max_bytes: int):
    if not file or not file.filename:
        return "", None

    filename = secure_filename(file.filename)
    ext = os.path.splitext(filename)[1].lower()
    mimetype = (file.mimetype or "").lower()

    if mimetype not in ALLOWED_IMAGE_MIME or ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValueError("Formato de imagen no permitido. Use JPG, PNG o WEBP.")

    raw = file.stream.read(max_bytes + 1)
    if len(raw) > max_bytes:
        raise ValueError("La imagen excede el tamano maximo permitido.")
    if not raw:
        raise ValueError("La imagen esta vacia.")

    if mimetype == "image/jpeg" and not raw.startswith(b"\xff\xd8\xff"):
        raise ValueError("Imagen JPG invalida.")
    if mimetype == "image/png" and not raw.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("Imagen PNG invalida.")
    if mimetype == "image/webp" and not (raw.startswith(b"RIFF") and raw[8:12] == b"WEBP"):
        raise ValueError("Imagen WEBP invalida.")

    return ext, raw


def register_qc_lab_routes(app, store, login_required, require_roles):
    """
    Registers QC Lab-related API routes to the given Flask app via a Blueprint.
    """
    qc_bp = Blueprint("qc_lab", __name__, url_prefix="/api/qclab")
    qc_lab_service = QcLabService(QcLabRepository(store))

    @qc_bp.route("/samples", methods=["GET"])
    @require_roles(*LABORATORIO_ROLES)
    def api_list_samples():
        limit = request.args.get("limit", 100, type=int)
        try:
            return jsonify(qc_lab_service.list_samples(limit=limit))
        except Exception as exc:
            return api_error_response(exc, 500)

    @qc_bp.route("/samples/<int:sample_id>", methods=["GET"])
    @require_roles(*LABORATORIO_ROLES)
    def api_get_sample(sample_id):
        try:
            return jsonify(qc_lab_service.get_sample(sample_id))
        except FileNotFoundError as exc:
            return api_error_response(exc, 404)
        except Exception as exc:
            return api_error_response(exc, 500)

    @qc_bp.route("/samples/<int:sample_id>", methods=["DELETE"])
    @require_roles(*QC_LAB_WRITE_ROLES)
    def api_delete_sample(sample_id):
        try:
            return jsonify(qc_lab_service.delete_sample(sample_id))
        except FileNotFoundError as exc:
            return api_error_response(exc, 404)
        except Exception as exc:
            return api_error_response(exc, 500)

    @qc_bp.route("/lookup_remision/<remision_no>", methods=["GET"])
    @require_roles(*LABORATORIO_ROLES)
    def api_lookup_remision(remision_no):
        try:
            return jsonify(qc_lab_service.lookup_remision(remision_no))
        except FileNotFoundError as exc:
            return api_error_response(exc, 404)
        except Exception as exc:
            return api_error_response(exc, 500)

    @qc_bp.route("/samples", methods=["POST"])
    @require_roles(*QC_LAB_WRITE_ROLES)
    def api_save_sample():
        payload = request.json
        try:
            return jsonify(qc_lab_service.save_sample(payload, request.current_user["username"]))
        except Exception as exc:
            return api_error_response(exc, 500)

    @qc_bp.route("/cylinders", methods=["GET"])
    @require_roles(*LABORATORIO_ROLES)
    def api_get_all_cylinders():
        limit = request.args.get("limit", 500, type=int)
        pending_only = request.args.get("pending_only", "false") == "true"
        try:
            return jsonify(qc_lab_service.list_cylinders(pending_only=pending_only, limit=limit))
        except Exception as exc:
            return api_error_response(exc, 500)

    @qc_bp.route("/cylinders/<int:cylinder_id>/test", methods=["POST"])
    @require_roles(*QC_LAB_WRITE_ROLES)
    def api_save_cylinder_test(cylinder_id):
        try:
            file = request.files.get("image")
            image_path = ""
            image_data = None

            if file and file.filename:
                ext, image_data = read_validated_qc_image(file, int(app.config["MAX_CONTENT_LENGTH"]))
                if not store.is_postgres:
                    uploads_dir = app.config.get("QC_UPLOADS_DIR") or os.path.join(
                        app.config.get("BASE_DIR", "."),
                        "static",
                        "uploads",
                        "qc_images",
                    )
                    os.makedirs(uploads_dir, exist_ok=True)
                    unique_name = f"{uuid.uuid4().hex}{ext}"
                    full_path = os.path.join(uploads_dir, unique_name)
                    with open(full_path, "wb") as file_handle:
                        file_handle.write(image_data)
                    image_path = f"/static/uploads/qc_images/{unique_name}"

            payload = request.form.to_dict()
            return jsonify(
                qc_lab_service.test_cylinder(
                    cylinder_id,
                    payload,
                    image_path=image_path,
                    image_data=image_data,
                )
            )
        except Exception as exc:
            return api_error_response(exc, 500)

    @qc_bp.route("/cylinders/<int:cylinder_id>/image", methods=["GET"])
    @require_roles(*LABORATORIO_ROLES)
    def api_get_cylinder_image(cylinder_id):
        try:
            with store._conn() as conn:
                row = conn.execute(
                    "SELECT image_data, image_path FROM qc_cylinders WHERE id = ?",
                    (cylinder_id,),
                ).fetchone()
                if not row:
                    return jsonify({"ok": False, "error": "Cilindro no encontrado"}), 404

                if row.get("image_data"):
                    return Response(row["image_data"], mimetype="image/jpeg")

                if row.get("image_path"):
                    path = row["image_path"]
                    if path.startswith("/static/"):
                        rel_path = path[1:] if path.startswith("/") else path
                        full_path = os.path.join(current_app.root_path, rel_path)
                        if os.path.exists(full_path):
                            with open(full_path, "rb") as file_handle:
                                return Response(file_handle.read(), mimetype="image/jpeg")

                return jsonify({"ok": False, "error": "Imagen no encontrada"}), 404
        except Exception as exc:
            return api_error_response(exc, 500)

    @qc_bp.route("/stats/trends", methods=["GET"])
    @require_roles(*LABORATORIO_ROLES)
    def api_get_qc_trends():
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")

        try:
            with store._conn() as conn:
                sql = """
                    SELECT c.id, c.sample_id, c.target_age_days, c.expected_test_date, c.status,
                           c.strength_kgcm2, c.break_date,
                           s.sample_code, s.fc_expected, s.remision_id, s.cast_date,
                           r.formula
                    FROM qc_cylinders c
                    JOIN qc_samples s ON c.sample_id = s.id
                    LEFT JOIN remisiones r ON s.remision_id = r.remision_no
                    WHERE c.status = 'ensayado'
                """
                params = []
                if start_date:
                    sql += " AND s.cast_date >= ?"
                    params.append(f"{start_date} 00:00:00")
                if end_date:
                    sql += " AND s.cast_date <= ?"
                    params.append(f"{end_date} 23:59:59")

                sql += " ORDER BY s.cast_date DESC, c.target_age_days ASC LIMIT 500"
                cur = conn.execute(sql, tuple(params))
                tested = [dict(row) for row in cur.fetchall()]

            return jsonify({"ok": True, "data": tested})
        except Exception as exc:
            return api_error_response(exc, 500)

    @qc_bp.route("/reports/trends", methods=["GET"])
    @require_roles(*LABORATORIO_ROLES)
    def api_get_qc_trends_page():
        return render_template("qc_trends_report.html")

    app.register_blueprint(qc_bp)
