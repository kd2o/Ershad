import os
from dotenv import load_dotenv
from backend import create_app, db

load_dotenv()

def ensure_admin():
    admin_name = os.getenv("ADMIN_NAME", "Admin").strip()
    admin_name_key = " ".join(admin_name.lower().split())
    admin_student_number = os.getenv("ADMIN_STUDENT_NUMBER", "0000").strip()

    app = create_app()
    with app.app_context():
        existing_user = db.db.users.find_one({"student_number": admin_student_number})
        
        if existing_user:
            print(f"Admin '{admin_name}' already exists.")
            return

        db.db.users.insert_one(
            {
                "student_name": admin_name,
                "student_name_key": admin_name_key,
                "student_number": admin_student_number,
                "role": "admin",
            }
        )
        print(f"Admin user '{admin_name}' added successfully.")

if __name__ == "__main__":
    ensure_admin()