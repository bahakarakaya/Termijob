"""Database operations for Termijob."""

from typing import Optional
from sqlalchemy import func
from .models import Job, get_session, init_db


class JobRepository:
    """Repository for job CRUD operations."""
    
    def __init__(self):
        """Initialize the repository and ensure database exists."""
        init_db()
    
    def add_job(self, job_data: dict) -> Job:
        """Add a new job to the database."""
        session = get_session()
        try:
            job = Job(**job_data)
            session.add(job)
            session.commit()
            session.refresh(job)
            return job
        finally:
            session.close()
    
    def get_job(self, job_id: int) -> Optional[Job]:
        """Get a job by ID."""
        session = get_session()
        try:
            return session.query(Job).filter(Job.id == job_id).first()
        finally:
            session.close()
    
    def get_all_jobs(self) -> list[Job]:
        """Get all jobs."""
        session = get_session()
        try:
            return session.query(Job).order_by(Job.created_at.desc()).all()
        finally:
            session.close()
    
    def get_jobs_by_category(self, category: str) -> list[Job]:
        """Get all jobs in a specific category."""
        session = get_session()
        try:
            return session.query(Job).filter(
                Job.category == category
            ).order_by(Job.created_at.desc()).all()
        finally:
            session.close()
    
    def search_jobs(self, query: str) -> list[Job]:
        """Search jobs by title or description."""
        session = get_session()
        try:
            search_pattern = f"%{query}%"
            return session.query(Job).filter(
                (Job.title.ilike(search_pattern)) | 
                (Job.description.ilike(search_pattern)) |
                (Job.skills.ilike(search_pattern))
            ).order_by(Job.created_at.desc()).all()
        finally:
            session.close()
    
    def delete_job(self, job_id: int) -> bool:
        """Delete a job by ID."""
        session = get_session()
        try:
            job = session.query(Job).filter(Job.id == job_id).first()
            if job:
                session.delete(job)
                session.commit()
                return True
            return False
        finally:
            session.close()
    
    def get_categories_with_counts(self) -> list[tuple[str, int]]:
        """Get all categories with their job counts."""
        session = get_session()
        try:
            results = session.query(
                Job.category, 
                func.count(Job.id)
            ).group_by(Job.category).order_by(func.count(Job.id).desc()).all()
            return results
        finally:
            session.close()
    
    def get_job_count(self) -> int:
        """Get total job count."""
        session = get_session()
        try:
            return session.query(Job).count()
        finally:
            session.close()
    
    def get_recent_jobs(self, limit: int = 5) -> list[Job]:
        """Get the most recent jobs."""
        session = get_session()
        try:
            return session.query(Job).order_by(Job.created_at.desc()).limit(limit).all()
        finally:
            session.close()
