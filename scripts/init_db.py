#!/usr/bin/env python3
"""Database initialization script."""
import sys
import os

# Add the parent directory to Python path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.models.database import DatabaseManager


def main():
    """Initialize the database."""
    print(f"Initializing database at: {settings.database_url}")
    
    try:
        db_manager = DatabaseManager(settings.database_url)
        print("Database initialized successfully!")
        print("Tables created if they didn't exist.")
        
        # Test the connection
        with db_manager.get_session() as session:
            result = session.execute("SELECT COUNT(*) FROM tasks").fetchone()
            print(f"Current tasks in database: {result[0]}")
            
    except Exception as e:
        print(f"Failed to initialize database: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
