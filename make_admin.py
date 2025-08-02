from src.database.database import SessionLocal
from src.database.models import User
db = SessionLocal()
user = db.query(User).filter(User.email == "admin@aura.test").first()
user.is_admin = True
db.commit()
print(f"✅ Success! User '{user.email}' is now an admin.")
db.close()
