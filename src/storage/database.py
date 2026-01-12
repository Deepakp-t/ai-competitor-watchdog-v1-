"""
Database connection and session management
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from dotenv import load_dotenv
from .models import Base

load_dotenv()


def get_database_url() -> str:
    """Get database URL from environment or default to SQLite"""
    db_url = os.getenv('DATABASE_URL', 'sqlite:///watchdog.db')
    # Ensure SQLite URLs use absolute path
    if db_url.startswith('sqlite:///'):
        db_path = db_url.replace('sqlite:///', '')
        if not os.path.isabs(db_path):
            # Make path relative to project root
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            db_path = os.path.join(project_root, db_path)
        db_url = f'sqlite:///{db_path}'
    return db_url


def create_engine_instance():
    """Create SQLAlchemy engine"""
    db_url = get_database_url()
    # SQLite-specific configuration
    if db_url.startswith('sqlite'):
        engine = create_engine(
            db_url,
            connect_args={'check_same_thread': False},  # SQLite-specific
            echo=False  # Set to True for SQL query logging
        )
    else:
        engine = create_engine(db_url, echo=False)
    return engine


def init_database():
    """Initialize database schema (create all tables)"""
    engine = create_engine_instance()
    Base.metadata.create_all(engine)
    print(f"Database initialized at: {get_database_url()}")


def get_session() -> Session:
    """Get database session"""
    engine = create_engine_instance()
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


# Context manager for database sessions
class DatabaseSession:
    """Context manager for database sessions"""
    
    def __init__(self):
        self.engine = create_engine_instance()
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.session = None
    
    def __enter__(self):
        self.session = self.SessionLocal()
        return self.session
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.session.rollback()
        else:
            self.session.commit()
        self.session.close()

