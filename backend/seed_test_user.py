#!/usr/bin/env python
"""Create a test user for development and write credentials to file."""

from app.db.session import SessionLocal
from app.models.user import User
from app.core.security import get_password_hash
import os

def main():
    db = SessionLocal()
    with open("TEST_USER_CREDENTIALS.txt", "w") as f:
        try:
            # Check existing users
            users = db.query(User).all()
            f.write(f"Current users: {len(users)}\n")
            
            for u in users:
                f.write(f"  - {u.email}\n")
            
            # Create test user if none exist
            if len(users) == 0:
                email = "owner@bharat.com"
                password = "Owner@123456"
                
                test_user = User(
                    email=email,
                    hashed_password=get_password_hash(password)
                )
                db.add(test_user)
                db.commit()
                
                f.write("\n✅ TEST USER CREATED\n")
                f.write(f"Email: {email}\n")
                f.write(f"Password: {password}\n")
            else:
                f.write("\n✓ Users already exist\n")
        finally:
            db.close()

if __name__ == "__main__":
    main()
