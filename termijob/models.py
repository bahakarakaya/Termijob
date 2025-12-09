"""Database models for Termijob."""

from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker
from pathlib import Path

Base = declarative_base()


class Job(Base):
    """Job posting model."""
    
    __tablename__ = "jobs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500), nullable=False)
    category = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=False)
    skills = Column(Text, nullable=True)  # Comma-separated skills
    budget = Column(String(100), nullable=True)  # Budget as string (hourly/fixed)
    client_location = Column(String(200), nullable=True)
    experience_level = Column(String(50), nullable=True)
    job_type = Column(String(50), nullable=True)  # Fixed/Hourly
    raw_text = Column(Text, nullable=False)  # Original pasted text
    notes = Column(Text, nullable=True)  # User notes
    applied = Column(Boolean, default=False, nullable=False)  # Applied flag
    done = Column(Boolean, default=False, nullable=False)  # Done/completed flag
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Job(id={self.id}, title='{self.title[:30]}...', category='{self.category}')>"
    
    @property
    def skills_list(self) -> list[str]:
        """Return skills as a list."""
        if not self.skills:
            return []
        return [s.strip() for s in self.skills.split(",") if s.strip()]


def get_database_path() -> Path:
    """Get the database path in user's data directory."""
    data_dir = Path.home() / ".local" / "share" / "termijob"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "jobs.db"


def get_engine():
    """Create and return database engine."""
    db_path = get_database_path()
    return create_engine(f"sqlite:///{db_path}", echo=False)


def get_session():
    """Create and return a new database session."""
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()


def init_db():
    """Initialize the database and run migrations."""
    engine = get_engine()
    Base.metadata.create_all(engine)
    
    # Run migrations for existing databases
    _run_migrations(engine)


def _run_migrations(engine):
    """Run all database migrations."""
    from sqlalchemy import text, inspect
    
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns('jobs')]
    
    migrations = [
        ('notes', 'ALTER TABLE jobs ADD COLUMN notes TEXT'),
        ('applied', 'ALTER TABLE jobs ADD COLUMN applied BOOLEAN DEFAULT 0 NOT NULL'),
        ('done', 'ALTER TABLE jobs ADD COLUMN done BOOLEAN DEFAULT 0 NOT NULL'),
    ]
    
    with engine.connect() as conn:
        for column_name, sql in migrations:
            if column_name not in columns:
                conn.execute(text(sql))
        conn.commit()
