def register_feature_routes(app, store, feature_enabled, login_required, require_roles):
    if feature_enabled("dosificador"):
        from doser_routes import register_doser_routes

        register_doser_routes(app, store, require_roles)

    if feature_enabled("remisiones") or feature_enabled("dosificador"):
        from remision_routes import register_remision_routes

        register_remision_routes(app, store, require_roles)

    if feature_enabled("editor") or feature_enabled("consulta") or feature_enabled("dosificador"):
        from editor_routes import register_editor_routes

        register_editor_routes(app, store, require_roles)

    if feature_enabled("flotilla"):
        from fleet_routes import register_fleet_routes

        register_fleet_routes(app, store, login_required, require_roles)

    if feature_enabled("inventario"):
        from inventory_routes import register_inventory_routes

        register_inventory_routes(app, store, login_required, require_roles)

    if feature_enabled("laboratorio"):
        from qc_lab_routes import register_qc_lab_routes

        register_qc_lab_routes(app, store, login_required, require_roles)

    if feature_enabled("usuarios"):
        from user_routes import register_user_routes

        users_bp = register_user_routes(store, require_roles)
        app.register_blueprint(users_bp)
