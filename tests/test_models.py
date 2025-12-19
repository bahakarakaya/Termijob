"""Tests for database models."""

import pytest
from datetime import datetime

from termijob.models import Job


class TestJobModel:
    """Tests for the Job model."""

    def test_job_creation(self, test_session, sample_job_data):
        """Test creating a job."""
        job = Job(**sample_job_data)
        test_session.add(job)
        test_session.commit()
        
        assert job.id is not None
        assert job.title == sample_job_data["title"]
        assert job.category == sample_job_data["category"]
        assert job.description == sample_job_data["description"]

    def test_job_default_values(self, test_session, sample_job_data):
        """Test default values for job fields."""
        job = Job(**sample_job_data)
        test_session.add(job)
        test_session.commit()
        
        assert job.applied is False
        assert job.done is False
        assert job.notes is None
        assert job.created_at is not None

    def test_job_repr(self, sample_job):
        """Test job string representation."""
        repr_str = repr(sample_job)
        assert "Job" in repr_str
        assert str(sample_job.id) in repr_str
        assert sample_job.category in repr_str

    def test_skills_list_property(self, test_session, sample_job_data):
        """Test skills_list property returns list of skills."""
        job = Job(**sample_job_data)
        test_session.add(job)
        test_session.commit()
        
        skills = job.skills_list
        assert isinstance(skills, list)
        assert "Python" in skills
        assert "BeautifulSoup" in skills
        assert "Selenium" in skills

    def test_skills_list_empty(self, test_session, sample_job_data):
        """Test skills_list with no skills."""
        sample_job_data["skills"] = None
        job = Job(**sample_job_data)
        test_session.add(job)
        test_session.commit()
        
        assert job.skills_list == []

    def test_skills_list_with_whitespace(self, test_session, sample_job_data):
        """Test skills_list handles whitespace correctly."""
        sample_job_data["skills"] = "  Python  ,  JavaScript  ,  "
        job = Job(**sample_job_data)
        test_session.add(job)
        test_session.commit()
        
        skills = job.skills_list
        assert "Python" in skills
        assert "JavaScript" in skills
        assert "" not in skills  # Empty strings should be filtered

    def test_job_optional_fields(self, test_session):
        """Test job with only required fields."""
        job = Job(
            title="Minimal Job",
            category="Other",
            description="A minimal job posting",
            raw_text="Raw text here",
        )
        test_session.add(job)
        test_session.commit()
        
        assert job.id is not None
        assert job.budget is None
        assert job.client_location is None
        assert job.experience_level is None
        assert job.job_type is None

    def test_job_applied_flag(self, test_session, sample_job_data):
        """Test toggling applied flag."""
        job = Job(**sample_job_data)
        test_session.add(job)
        test_session.commit()
        
        assert job.applied is False
        job.applied = True
        test_session.commit()
        assert job.applied is True

    def test_job_done_flag(self, test_session, sample_job_data):
        """Test toggling done flag."""
        job = Job(**sample_job_data)
        test_session.add(job)
        test_session.commit()
        
        assert job.done is False
        job.done = True
        test_session.commit()
        assert job.done is True

    def test_job_notes(self, test_session, sample_job_data):
        """Test adding notes to a job."""
        job = Job(**sample_job_data)
        test_session.add(job)
        test_session.commit()
        
        job.notes = "This looks like a good opportunity!"
        test_session.commit()
        
        assert job.notes == "This looks like a good opportunity!"
