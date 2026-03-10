from flask_login import UserMixin


class User(UserMixin):
    def __init__(self, document):
        self.document = document
        self.id = str(document["_id"])
        self.student_name = document.get("student_name", "")
        self.role = document.get("role", "user")
        self.student_number = document.get("student_number", "")

    @classmethod
    def from_document(cls, document):
        if not document:
            return None
        return cls(document)

    def is_admin(self):
        return self.role == "admin"
