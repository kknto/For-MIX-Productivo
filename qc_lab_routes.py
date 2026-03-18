import os
import uuid
import io
from flask import Blueprint, jsonify, request, current_app, Response

def register_qc_lab_routes(app, store, login_required):
    """
    Registers QC Lab-related API routes to the given Flask app via a Blueprint.
    """
    qc_bp = Blueprint("qc_lab", __name__, url_prefix="/api/qclab")

    @qc_bp.route("/samples", methods=["GET"])
    @login_required
    def api_list_samples():
        limit = request.args.get("limit", 100, type=int)
        try:
            return jsonify({"ok": True, "samples": store.list_qc_samples(limit=limit)})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @qc_bp.route("/samples/<int:sample_id>", methods=["GET"])
    @login_required
    def api_get_sample(sample_id):
        try:
            sample = store.get_qc_sample(sample_id)
            if not sample:
                return jsonify({"ok": False, "error": "Muestra no encontrada"}), 404
            return jsonify({"ok": True, "sample": sample})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @qc_bp.route("/samples/<int:sample_id>", methods=["DELETE"])
    @login_required
    def api_delete_sample(sample_id):
        try:
            success = store.delete_qc_sample(sample_id)
            if not success:
                return jsonify({"ok": False, "error": "Muestra no encontrada"}), 404
            return jsonify({"ok": True})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @qc_bp.route("/lookup_remision/<remision_no>", methods=["GET"])
    @login_required
    def api_lookup_remision(remision_no):
        try:
            remision = store.get_remision_by_no(remision_no)
            if not remision:
                return jsonify({"ok": False, "error": "Remision no encontrada"}), 404
            return jsonify({"ok": True, "remision": remision})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @qc_bp.route("/samples", methods=["POST"])
    @login_required
    def api_save_sample():
        payload = request.json
        try:
            saved = store.save_qc_sample(payload, request.current_user["username"])
            return jsonify({"ok": True, "sample": saved})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @qc_bp.route("/cylinders", methods=["GET"])
    @login_required
    def api_get_all_cylinders():
        limit = request.args.get("limit", 500, type=int)
        pending_only = request.args.get("pending_only", "false") == "true"
        try:
            cylinders = store.list_qc_cylinders(pending_only=pending_only, limit=limit)
            return jsonify({"ok": True, "cylinders": cylinders})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @qc_bp.route("/cylinders/<int:cylinder_id>/test", methods=["POST"])
    @login_required
    def api_save_cylinder_test(cylinder_id):
        file = request.files.get("image")
        image_path = ""
        image_data = None
        
        if file and file.filename:
            # Still save to disk for local cache/preview if desired, 
            # but primary storage will be DB now.
            uploads_dir = os.path.join(app.config.get("BASE_DIR", "."), "static", "uploads", "qc_images")
            os.makedirs(uploads_dir, exist_ok=True)
            
            ext = os.path.splitext(file.filename)[1]
            unique_name = f"{uuid.uuid4().hex}{ext}"
            full_path = os.path.join(uploads_dir, unique_name)
            
            # Read bytes for DB storage
            image_data = file.read()
            file.seek(0) # Reset pointer to save to disk too
            file.save(full_path)
            
            image_path = f"/static/uploads/qc_images/{unique_name}"
        
        try:
            payload = request.form.to_dict()
            updated_sample = store.test_qc_cylinder(cylinder_id, payload, image_path, image_data)
            return jsonify({"ok": True, "sample": updated_sample})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @qc_bp.route("/cylinders/<int:cylinder_id>/image", methods=["GET"])
    @login_required
    def api_get_cylinder_image(cylinder_id):
        try:
            with store._conn() as conn:
                row = conn.execute("SELECT image_data, image_path FROM qc_cylinders WHERE id = ?", (cylinder_id,)).fetchone()
                if not row:
                    return jsonify({"ok": False, "error": "Cilindro no encontrado"}), 404
                
                # 1. Prioridad: image_data (binario en DB)
                if row.get("image_data"):
                    return Response(row["image_data"], mimetype='image/jpeg')
                
                # 2. Fallback: image_path (archivo en disco)
                if row.get("image_path"):
                    path = row["image_path"]
                    if path.startswith("/static/"):
                        # Quitar el primer slash para os.path.join
                        rel_path = path[1:] if path.startswith("/") else path
                        full_path = os.path.join(current_app.root_path, rel_path)
                        if os.path.exists(full_path):
                            with open(full_path, "rb") as f:
                                return Response(f.read(), mimetype='image/jpeg')
                
                return jsonify({"ok": False, "error": "Imagen no encontrada"}), 404
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @qc_bp.route("/stats/trends", methods=["GET"])
    @login_required
    def api_get_qc_trends():
        try:
            # Fetch last 200 cylinders with sample info
            # We use a larger limit to have enough data for a meaningful trend
            cylinders = store.list_qc_cylinders(limit=250)
            # Filter only tested ones for the charts
            tested = [c for c in cylinders if c.get("status") == "ensayado"]
            return jsonify({"ok": True, "data": tested})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    app.register_blueprint(qc_bp)
