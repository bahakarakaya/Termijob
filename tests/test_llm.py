"""Tests for LLM parser."""

import pytest
from unittest.mock import patch, MagicMock

from termijob.llm import LLMParser, ParsedJob, CATEGORIES


class TestParsedJob:
    """Tests for ParsedJob model."""

    def test_parsed_job_creation(self):
        """Test creating a ParsedJob."""
        job = ParsedJob(
            title="Python Developer",
            category="Web Development",
            description="Build a web application",
            skills=["Python", "Django"],
        )
        
        assert job.title == "Python Developer"
        assert job.category == "Web Development"
        assert job.description == "Build a web application"
        assert job.skills == ["Python", "Django"]

    def test_parsed_job_optional_fields(self):
        """Test ParsedJob with optional fields."""
        job = ParsedJob(
            title="Developer",
            category="Other",
            description="A job",
            skills=[],
        )
        
        assert job.budget is None
        assert job.client_location is None
        assert job.experience_level is None
        assert job.job_type is None

    def test_parsed_job_all_fields(self):
        """Test ParsedJob with all fields."""
        job = ParsedJob(
            title="Senior Python Developer",
            category="Web Development",
            description="Build enterprise web applications",
            skills=["Python", "Django", "PostgreSQL"],
            budget="$50-100/hr",
            client_location="United States",
            experience_level="Expert",
            job_type="Hourly",
        )
        
        assert job.budget == "$50-100/hr"
        assert job.client_location == "United States"
        assert job.experience_level == "Expert"
        assert job.job_type == "Hourly"


class TestCategories:
    """Tests for job categories."""

    def test_categories_exist(self):
        """Test that categories are defined."""
        assert len(CATEGORIES) > 0

    def test_expected_categories_present(self):
        """Test expected categories are present."""
        expected = [
            "Web Scraping",
            "Computer Vision",
            "Machine Learning",
            "Web Development",
            "API Development",
            "Large Language Models",
            "Agent Development",
            "Other",
        ]
        for category in expected:
            assert category in CATEGORIES, f"Category '{category}' not found"


class TestLLMParser:
    """Tests for LLMParser class."""

    @pytest.fixture
    def mock_ollama_client(self):
        """Create a mock Ollama client."""
        with patch("termijob.llm.ollama.Client") as mock:
            yield mock

    @pytest.fixture
    def parser(self, mock_ollama_client):
        """Create an LLMParser with mocked client."""
        return LLMParser()

    def test_parser_initialization(self, mock_ollama_client):
        """Test parser initializes with default model."""
        parser = LLMParser()
        assert parser.model == "llama3.1"

    def test_parser_custom_model(self, mock_ollama_client):
        """Test parser with custom model."""
        parser = LLMParser(model="llama3.2")
        assert parser.model == "llama3.2"

    def test_parse_job_success(self, parser, mock_ollama_client):
        """Test successful job parsing."""
        mock_response = {
            "message": {
                "content": '''{
                    "title": "Web Scraper Developer",
                    "category": "Web Scraping",
                    "description": "Build a web scraper for e-commerce",
                    "skills": ["Python", "BeautifulSoup"],
                    "budget": "$300",
                    "client_location": "USA",
                    "experience_level": "Intermediate",
                    "job_type": "Fixed"
                }'''
            }
        }
        parser.client.chat.return_value = mock_response
        
        result = parser.parse_job("Looking for a Python developer to build web scraper...")
        
        assert isinstance(result, ParsedJob)
        assert result.title == "Web Scraper Developer"
        assert result.category == "Web Scraping"
        assert "Python" in result.skills

    def test_parse_job_with_markdown_json(self, parser, mock_ollama_client):
        """Test parsing when LLM returns JSON in markdown code block."""
        mock_response = {
            "message": {
                "content": '''Here is the parsed job:
```json
{
    "title": "ML Engineer",
    "category": "Machine Learning",
    "description": "Train ML models",
    "skills": ["Python", "TensorFlow"],
    "budget": null,
    "client_location": null,
    "experience_level": "Expert",
    "job_type": "Hourly"
}
```'''
            }
        }
        parser.client.chat.return_value = mock_response
        
        result = parser.parse_job("Need ML engineer...")
        
        assert result.title == "ML Engineer"
        assert result.category == "Machine Learning"

    def test_parse_job_fallback_on_error(self, parser, mock_ollama_client):
        """Test fallback when parsing fails."""
        parser.client.chat.side_effect = Exception("Connection error")
        
        result = parser.parse_job("Some job text that cannot be parsed")
        
        assert result.title == "Untitled Job"
        assert result.category == "Other"
        assert result.skills == []

    def test_parse_job_fallback_on_invalid_json(self, parser, mock_ollama_client):
        """Test fallback when LLM returns invalid JSON."""
        mock_response = {
            "message": {
                "content": "This is not valid JSON at all"
            }
        }
        parser.client.chat.return_value = mock_response
        
        result = parser.parse_job("Some job text")
        
        assert result.title == "Untitled Job"
        assert result.category == "Other"

    def test_check_model_available_true(self, parser, mock_ollama_client):
        """Test model availability check when model exists."""
        parser.client.list.return_value = {
            "models": [
                {"name": "llama3.1:latest"},
                {"name": "codellama:7b"},
            ]
        }
        
        assert parser.check_model_available() is True

    def test_check_model_available_false(self, parser, mock_ollama_client):
        """Test model availability check when model doesn't exist."""
        parser.client.list.return_value = {
            "models": [
                {"name": "codellama:7b"},
            ]
        }
        
        assert parser.check_model_available() is False

    def test_check_model_available_error(self, parser, mock_ollama_client):
        """Test model availability check on connection error."""
        parser.client.list.side_effect = Exception("Connection refused")
        
        assert parser.check_model_available() is False

    def test_get_available_models(self, parser, mock_ollama_client):
        """Test getting list of available models."""
        parser.client.list.return_value = {
            "models": [
                {"name": "llama3.1:latest"},
                {"name": "codellama:7b"},
                {"name": "mistral:latest"},
            ]
        }
        
        models = parser.get_available_models()
        
        assert len(models) == 3
        assert "llama3.1:latest" in models
        assert "codellama:7b" in models

    def test_get_available_models_error(self, parser, mock_ollama_client):
        """Test getting models on connection error."""
        parser.client.list.side_effect = Exception("Connection refused")
        
        models = parser.get_available_models()
        
        assert models == []

    def test_extract_json_direct(self, parser):
        """Test extracting JSON directly."""
        content = '{"title": "Test", "category": "Other", "description": "Desc", "skills": []}'
        
        result = parser._extract_json(content)
        
        assert result["title"] == "Test"

    def test_extract_json_with_text(self, parser):
        """Test extracting JSON from text with surrounding content."""
        content = '''Here is the result:
        {"title": "Test Job", "category": "Web Development", "description": "A job", "skills": ["Python"]}
        
        Let me know if you need anything else!'''
        
        result = parser._extract_json(content)
        
        assert result["title"] == "Test Job"
        assert result["category"] == "Web Development"

    def test_extract_json_failure(self, parser):
        """Test JSON extraction failure."""
        content = "This contains no valid JSON"
        
        with pytest.raises(ValueError):
            parser._extract_json(content)
