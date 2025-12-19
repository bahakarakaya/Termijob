"""Tests for JobRepository."""

import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from termijob.models import Base, Job
from termijob.repository import JobRepository


class TestJobRepository:
    """Tests for the JobRepository class."""

    @pytest.fixture
    def repo_with_mock_db(self, test_engine, temp_db_path):
        """Create a repository with mocked database."""
        Session = sessionmaker(bind=test_engine)
        
        with patch("termijob.repository.init_db"):
            with patch("termijob.models.get_database_path", return_value=temp_db_path):
                with patch("termijob.models.get_engine", return_value=test_engine):
                    with patch("termijob.models.get_session", side_effect=lambda: Session()):
                        with patch("termijob.repository.get_session", side_effect=lambda: Session()):
                            repo = JobRepository()
                            yield repo

    def test_add_job(self, repo_with_mock_db, sample_job_data):
        """Test adding a job."""
        job = repo_with_mock_db.add_job(sample_job_data)
        
        assert job.id is not None
        assert job.title == sample_job_data["title"]
        assert job.category == sample_job_data["category"]

    def test_get_job(self, repo_with_mock_db, sample_job_data):
        """Test getting a job by ID."""
        created_job = repo_with_mock_db.add_job(sample_job_data)
        
        retrieved_job = repo_with_mock_db.get_job(created_job.id)
        
        assert retrieved_job is not None
        assert retrieved_job.id == created_job.id
        assert retrieved_job.title == sample_job_data["title"]

    def test_get_job_not_found(self, repo_with_mock_db):
        """Test getting a non-existent job."""
        job = repo_with_mock_db.get_job(99999)
        assert job is None

    def test_get_all_jobs(self, repo_with_mock_db, sample_job_data):
        """Test getting all jobs."""
        repo_with_mock_db.add_job(sample_job_data)
        sample_job_data["title"] = "Another Job"
        repo_with_mock_db.add_job(sample_job_data)
        
        jobs = repo_with_mock_db.get_all_jobs()
        
        assert len(jobs) == 2

    def test_get_jobs_by_category(self, repo_with_mock_db, sample_job_data):
        """Test filtering jobs by category."""
        repo_with_mock_db.add_job(sample_job_data)
        
        sample_job_data["title"] = "ML Job"
        sample_job_data["category"] = "Machine Learning"
        repo_with_mock_db.add_job(sample_job_data)
        
        web_jobs = repo_with_mock_db.get_jobs_by_category("Web Scraping")
        ml_jobs = repo_with_mock_db.get_jobs_by_category("Machine Learning")
        
        assert len(web_jobs) == 1
        assert len(ml_jobs) == 1
        assert web_jobs[0].category == "Web Scraping"

    def test_search_jobs_by_title(self, repo_with_mock_db, sample_job_data):
        """Test searching jobs by title."""
        repo_with_mock_db.add_job(sample_job_data)
        
        results = repo_with_mock_db.search_jobs("Python")
        
        assert len(results) == 1
        assert "Python" in results[0].title

    def test_search_jobs_by_description(self, repo_with_mock_db, sample_job_data):
        """Test searching jobs by description."""
        repo_with_mock_db.add_job(sample_job_data)
        
        results = repo_with_mock_db.search_jobs("e-commerce")
        
        assert len(results) == 1

    def test_search_jobs_by_skills(self, repo_with_mock_db, sample_job_data):
        """Test searching jobs by skills."""
        repo_with_mock_db.add_job(sample_job_data)
        
        results = repo_with_mock_db.search_jobs("Selenium")
        
        assert len(results) == 1

    def test_search_jobs_no_results(self, repo_with_mock_db, sample_job_data):
        """Test search with no matching results."""
        repo_with_mock_db.add_job(sample_job_data)
        
        results = repo_with_mock_db.search_jobs("NonexistentTerm")
        
        assert len(results) == 0

    def test_delete_job(self, repo_with_mock_db, sample_job_data):
        """Test deleting a job."""
        job = repo_with_mock_db.add_job(sample_job_data)
        
        result = repo_with_mock_db.delete_job(job.id)
        
        assert result is True
        assert repo_with_mock_db.get_job(job.id) is None

    def test_delete_job_not_found(self, repo_with_mock_db):
        """Test deleting a non-existent job."""
        result = repo_with_mock_db.delete_job(99999)
        assert result is False

    def test_get_categories_with_counts(self, repo_with_mock_db, sample_job_data):
        """Test getting category counts."""
        repo_with_mock_db.add_job(sample_job_data)
        sample_job_data["title"] = "Another Scraper"
        repo_with_mock_db.add_job(sample_job_data)
        
        sample_job_data["title"] = "ML Project"
        sample_job_data["category"] = "Machine Learning"
        repo_with_mock_db.add_job(sample_job_data)
        
        categories = repo_with_mock_db.get_categories_with_counts()
        
        assert len(categories) == 2
        # Web Scraping should have 2 jobs
        web_scraping = next((c for c in categories if c[0] == "Web Scraping"), None)
        assert web_scraping is not None
        assert web_scraping[1] == 2

    def test_get_job_count(self, repo_with_mock_db, sample_job_data):
        """Test getting total job count."""
        assert repo_with_mock_db.get_job_count() == 0
        
        repo_with_mock_db.add_job(sample_job_data)
        assert repo_with_mock_db.get_job_count() == 1
        
        sample_job_data["title"] = "Another Job"
        repo_with_mock_db.add_job(sample_job_data)
        assert repo_with_mock_db.get_job_count() == 2

    def test_get_recent_jobs(self, repo_with_mock_db, sample_job_data):
        """Test getting recent jobs."""
        for i in range(10):
            sample_job_data["title"] = f"Job {i}"
            repo_with_mock_db.add_job(sample_job_data)
        
        recent = repo_with_mock_db.get_recent_jobs(limit=5)
        
        assert len(recent) == 5

    def test_update_job_notes(self, repo_with_mock_db, sample_job_data):
        """Test updating job notes."""
        job = repo_with_mock_db.add_job(sample_job_data)
        
        result = repo_with_mock_db.update_job_notes(job.id, "Great opportunity!")
        
        assert result is True
        updated_job = repo_with_mock_db.get_job(job.id)
        assert updated_job.notes == "Great opportunity!"

    def test_update_job_notes_not_found(self, repo_with_mock_db):
        """Test updating notes for non-existent job."""
        result = repo_with_mock_db.update_job_notes(99999, "Some notes")
        assert result is False

    def test_toggle_job_applied(self, repo_with_mock_db, sample_job_data):
        """Test toggling applied flag."""
        job = repo_with_mock_db.add_job(sample_job_data)
        assert repo_with_mock_db.get_job(job.id).applied is False
        
        result = repo_with_mock_db.toggle_job_applied(job.id)
        assert result is True
        assert repo_with_mock_db.get_job(job.id).applied is True
        
        result = repo_with_mock_db.toggle_job_applied(job.id)
        assert result is False
        assert repo_with_mock_db.get_job(job.id).applied is False

    def test_toggle_job_applied_not_found(self, repo_with_mock_db):
        """Test toggling applied for non-existent job."""
        result = repo_with_mock_db.toggle_job_applied(99999)
        assert result is None

    def test_toggle_job_done(self, repo_with_mock_db, sample_job_data):
        """Test toggling done flag."""
        job = repo_with_mock_db.add_job(sample_job_data)
        assert repo_with_mock_db.get_job(job.id).done is False
        
        result = repo_with_mock_db.toggle_job_done(job.id)
        assert result is True
        assert repo_with_mock_db.get_job(job.id).done is True

    def test_toggle_job_done_not_found(self, repo_with_mock_db):
        """Test toggling done for non-existent job."""
        result = repo_with_mock_db.toggle_job_done(99999)
        assert result is None

    def test_set_job_applied(self, repo_with_mock_db, sample_job_data):
        """Test setting applied flag."""
        job = repo_with_mock_db.add_job(sample_job_data)
        
        result = repo_with_mock_db.set_job_applied(job.id, True)
        assert result is True
        assert repo_with_mock_db.get_job(job.id).applied is True
        
        result = repo_with_mock_db.set_job_applied(job.id, False)
        assert result is True
        assert repo_with_mock_db.get_job(job.id).applied is False

    def test_set_job_done(self, repo_with_mock_db, sample_job_data):
        """Test setting done flag."""
        job = repo_with_mock_db.add_job(sample_job_data)
        
        result = repo_with_mock_db.set_job_done(job.id, True)
        assert result is True
        assert repo_with_mock_db.get_job(job.id).done is True
