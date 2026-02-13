#!/usr/bin/env python
"""Create a test user for development."""

from app.db.session import SessionLocal
from app.models.user import User
from app.core.security import get_password_hash

def main():
    db = SessionLocal()
    try:
        # Check existing users
        users = db.query(User).all()
        print(f"\n{'='*60}")
        print(f"Current users in database: {len(users)}")
        print(f"{'='*60}")
        
        for u in users:
            print(f"  ✓ ID: {u.id} | Email: {u.email}")
        
        # Create test user if none exist
        if len(users) == 0:
            print(f"\n{'='*60}")
            print("CREATING TEST USER")
            print(f"{'='*60}")
            
            email = "owner@bharat.com"
            password = "Owner@123456"
            
            test_user = User(
                email=email,
                hashed_password=get_password_hash(password)
            )
            db.add(test_user)
            db.commit()
            
            print(f"\n✅ Test user created successfully!")
            print(f"{'='*60}")
            print(f"Email:    {email}")
            print(f"Password: {password}")
            print(f"{'='*60}\n")
        else:
            print("\n✓ Users already exist in database\n")
    
    finally:
        db.close()

if __name__ == "__main__":
    main()
