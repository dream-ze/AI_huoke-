"""
Database initialization and migration helper
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.core.database import Base, engine
from app.models import BrowserPluginCollection, ContentAsset, Customer, PublishRecord, RewrittenContent, User


def init_db():
    """Initialize database - create all tables"""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✓ Database tables created successfully!")


def drop_db():
    """Drop all tables - WARNING: This will delete all data"""
    response = input("Are you sure you want to drop all tables? (yes/no): ")
    if response.lower() == "yes":
        print("Dropping all tables...")
        Base.metadata.drop_all(bind=engine)
        print("✓ All tables dropped!")
    else:
        print("Cancelled.")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "init":
            init_db()
        elif sys.argv[1] == "drop":
            drop_db()
        else:
            print("Usage: python init_db.py [init|drop]")
    else:
        init_db()
