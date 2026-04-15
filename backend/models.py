from flask_login import UserMixin

from backend.roles import (
    DEFAULT_ROLE,
    can_access_user_management,
    can_add_users,
    can_delete_role,
    can_handle_chat_service,
    can_manage_schedule,
    can_post_news,
    get_role_label,
    is_staff_role,
    normalize_role,
)


class User(UserMixin):
    def __init__(self, document):
        self.document = document
        self.id = str(document["_id"])
        self.student_name = document.get("student_name", "")
        self.role = normalize_role(document.get("role", DEFAULT_ROLE))
        self.student_number = document.get("student_number", "")

    @classmethod
    def from_document(cls, document):
        if not document:
            return None
        return cls(document)

    def is_admin(self):
        return self.role == "admin"

    def is_staff(self):
        return is_staff_role(self.role)

    def get_role_label(self):
        return get_role_label(self.role)

    def can_access_user_management(self):
        return can_access_user_management(self.role)

    def can_add_users(self):
        return can_add_users(self.role)

    def can_delete_role(self, target_role):
        return can_delete_role(self.role, target_role)

    def can_manage_schedule(self):
        return can_manage_schedule(self.role)

    def can_post_news(self):
        return can_post_news(self.role)

    def can_handle_chat_service(self, service_type):
        return can_handle_chat_service(self.role, service_type)
