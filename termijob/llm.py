"""LLM integration for job parsing and categorization using Ollama."""

import json
from typing import Optional
from pydantic import BaseModel
import ollama


class ParsedJob(BaseModel):
    """Parsed job information from LLM."""
    
    title: str
    category: str
    description: str
    skills: list[str]
    budget: Optional[str] = None
    client_location: Optional[str] = None
    experience_level: Optional[str] = None
    job_type: Optional[str] = None  # Fixed/Hourly


# Predefined categories for job classification
CATEGORIES = [
    "Web Scraping",
    "Computer Vision",
    "Machine Learning",
    "Data Science",
    "Web Development",
    "Mobile Development",
    "API Development",
    "Automation",
    "Natural Language Processing",
    "Large Language Models",
    "Cloud Computing",
    "Agent Development",
    "Data Engineering",
    "DevOps",
    "Database",
    "Desktop Application",
    "Bot Development",
    "Other",
]


SYSTEM_PROMPT = f"""You are an expert at parsing Upwork job postings. Given a raw job posting text, extract the following information in JSON format:

1. title: The job title (create a concise one if not explicitly stated)
2. category: Classify the job into ONE of these categories: {', '.join(CATEGORIES)}
3. description: A brief summary of what the job requires (2-3 sentences)
4. skills: A list of required/preferred skills mentioned
5. budget: The budget information if mentioned (e.g., "$50-100", "$25/hr", "Fixed: $500")
6. client_location: The client's location if mentioned
7. experience_level: The required experience level if mentioned (Entry, Intermediate, Expert)
8. job_type: "Fixed" or "Hourly" based on the job posting

IMPORTANT: 
- Always respond with valid JSON only, no additional text
- Choose the most appropriate category based on the primary focus of the job
- If information is not available, use null for optional fields
- For skills, extract specific technologies, tools, and competencies mentioned

Example output:
{{
    "title": "Build Web Scraper for E-commerce Sites",
    "category": "Web Scraping",
    "description": "Need a Python developer to build a web scraper that extracts product data from multiple e-commerce websites.",
    "skills": ["Python", "BeautifulSoup", "Selenium", "Scrapy"],
    "budget": "$200-400",
    "client_location": "United States",
    "experience_level": "Intermediate",
    "job_type": "Fixed"
}}"""


class LLMParser:
    """Parser for job postings using local Llama model via Ollama."""
    
    def __init__(self, model: str = "llama3.1"):
        """Initialize the parser with specified model."""
        self.model = model
        self.client = ollama.Client()
    
    def parse_job(self, raw_text: str) -> ParsedJob:
        """Parse a raw job posting text and return structured data."""
        try:
            response = self.client.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Parse this job posting:\n\n{raw_text}"}
                ],
                options={
                    "temperature": 0.1,  # Low temperature for consistent parsing
                    "num_predict": 1000,
                }
            )
            
            content = response["message"]["content"]
            
            # Try to extract JSON from the response
            json_data = self._extract_json(content)
            
            return ParsedJob(**json_data)
            
        except Exception as e:
            # If parsing fails, return a basic parsed job with "Other" category
            return ParsedJob(
                title="Untitled Job",
                category="Other",
                description=raw_text[:500] if len(raw_text) > 500 else raw_text,
                skills=[],
                budget=None,
                client_location=None,
                experience_level=None,
                job_type=None,
            )
    
    def _extract_json(self, content: str) -> dict:
        """Extract JSON from LLM response."""
        # Try direct parsing first
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass
        
        # Try to find JSON block in the response
        start_markers = ["{", "```json\n{", "```\n{"]
        end_markers = ["}", "}```", "}\n```"]
        
        for start, end in zip(start_markers, end_markers):
            if start in content:
                try:
                    start_idx = content.find("{")
                    end_idx = content.rfind("}") + 1
                    if start_idx != -1 and end_idx > start_idx:
                        json_str = content[start_idx:end_idx]
                        return json.loads(json_str)
                except json.JSONDecodeError:
                    continue
        
        raise ValueError(f"Could not extract JSON from response: {content}")
    
    def check_model_available(self) -> bool:
        """Check if the Ollama model is available."""
        try:
            models = self.client.list()
            model_names = [m["name"] for m in models.get("models", [])]
            # Check if any model name starts with our model name (handles tags)
            return any(self.model in name or name.startswith(self.model.split(":")[0]) 
                      for name in model_names)
        except Exception:
            return False
    
    def get_available_models(self) -> list[str]:
        """Get list of available Ollama models."""
        try:
            models = self.client.list()
            return [m["name"] for m in models.get("models", [])]
        except Exception:
            return []
