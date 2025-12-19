"""Pytest fixtures for Termijob tests."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from termijob.models import Base, Job


@pytest.fixture
def temp_db_path(tmp_path):
    """Create a temporary database path."""
    return tmp_path / "test_jobs.db"


@pytest.fixture
def test_engine(temp_db_path):
    """Create a test database engine."""
    engine = create_engine(f"sqlite:///{temp_db_path}", echo=False)
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def test_session(test_engine):
    """Create a test database session."""
    Session = sessionmaker(bind=test_engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def mock_db(test_engine, temp_db_path):
    """Mock the database functions to use test database."""
    with patch("termijob.models.get_database_path", return_value=temp_db_path):
        with patch("termijob.models.get_engine", return_value=test_engine):
            Session = sessionmaker(bind=test_engine)
            with patch("termijob.models.get_session", return_value=Session()):
                yield


@pytest.fixture
def sample_job_data():
    """Sample job data for testing."""
    return {
        "title": "Python Web Scraper Developer",
        "category": "Web Scraping",
        "description": "Need a developer to build a web scraper for e-commerce sites.",
        "skills": "Python, BeautifulSoup, Selenium",
        "budget": "$200-400",
        "client_location": "United States",
        "experience_level": "Intermediate",
        "job_type": "Fixed",
        "raw_text": "Looking for a Python developer...",
    }


@pytest.fixture
def sample_job(test_session, sample_job_data):
    """Create a sample job in the test database."""
    job = Job(**sample_job_data)
    test_session.add(job)
    test_session.commit()
    test_session.refresh(job)
    return job
