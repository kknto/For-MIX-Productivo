class UsersRepository:
    def __init__(self, store):
        self.store = store

    def list_users(self):
        return self.store.list_users()

    def save_user(self, payload):
        return self.store.save_user(payload)

    def delete_user(self, user_id: int):
        return self.store.delete_user(user_id)

    def reset_password(self, user_id: int, new_password: str):
        return self.store.admin_reset_password(user_id, new_password)
