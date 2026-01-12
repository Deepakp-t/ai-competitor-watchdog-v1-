"""
Database initialization script
Run this to create the database schema
"""
from src.storage.database import init_database

if __name__ == '__main__':
    print("Initializing database...")
    init_database()
    print("Database initialization complete!")

