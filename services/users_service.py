class UsersService:
    def __init__(self, repository):
        self.repository = repository

    def list_users(self):
        return {"ok": True, "users": self.repository.list_users()}

    def save_user(self, payload):
        return {"ok": True, "user": self.repository.save_user(payload)}

    def delete_user(self, user_id: int):
        success = self.repository.delete_user(user_id)
        if not success:
            raise FileNotFoundError("No se encontró el usuario")
        return {"ok": True, "message": "Usuario eliminado"}

    def reset_password(self, user_id: int, new_password: str):
        success = self.repository.reset_password(user_id, new_password)
        if not success:
            raise FileNotFoundError("No se encontró el usuario")
        return {"ok": True, "message": "Contraseña actualizada"}
