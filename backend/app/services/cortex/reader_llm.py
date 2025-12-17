
import structlog
import google.generativeai as genai
from typing import Optional, Dict, Any
from app.config import settings
from app.models import OpportunitySchema
import json

logger = structlog.get_logger()

# Configure Gemini
if settings.gemini_api_key:
    genai.configure(api_key=settings.gemini_api_key)

class ReaderLLM:
    """
    The 'Reader': Turns Raw HTML/Text into Structured JSON.
    Optimized for Gemini Flash (Fast/Cheap).
    """
    
    MODEL_NAME = "gemini-1.5-flash" # Use Flash for speed/cost

    async def parse_opportunity(self, raw_text: str, source_url: str) -> Optional[OpportunitySchema]:
        """
        Extracts opportunity details from raw text.
        """
        if not settings.gemini_api_key:
            return None

        # Truncate text to avoid token limits (Flash has large context but efficiency matters)
        truncated_text = raw_text[:50000]

        prompt = f"""
        You are a Data Extraction Specialist. Extract one scholarship, hackathon, grant, or bounty opportunity from the text below.
        
        Return pure JSON matching this schema:
        {{
            "title": "String",
            "organization": "String",
            "amount": Number (0 if unknown),
            "amount_display": "String (e.g. $5,000)",
            "deadline": "ISO 8601 Date String (YYYY-MM-DD)",
            "deadline_timestamp": Number (Unix Timestamp),
            "geo_tags": ["String", "String"] (e.g. ["Global", "Nigeria", "Remote"]),
            "type_tags": ["String"] (e.g. ["Grant", "Hackathon"]),
            "description": "Short summary",
            "eligibility_text": "Requirements snippet"
        }}

        Rules:
        1. If deadline is missing, estimate logic or null.
        2. Geo Tags: Detect country/region requirements. If "Remote" or "Online", add "Global".
        3. Type Tags: Detect if it's a "Hackathon", "Grant", "Bounty", or "Scholarship".
        
        Source URL: {source_url}
        
        Text Content:
        {truncated_text}
        """

        try:
            model = genai.GenerativeModel(self.MODEL_NAME)
            response = await model.generate_content_async(prompt, generation_config={"response_mime_type": "application/json"})
            
            data = json.loads(response.text)
            
            # Post-processing / Validation
            data['source_url'] = source_url
            # Generate ID hash
            from hashlib import md5
            data['id'] = md5(source_url.encode()).hexdigest()
            
            # Pydantic Validation
            return OpportunitySchema(**data)

        except Exception as e:
            logger.error("Reader LLM extraction failed", url=source_url, error=str(e))
            return None

reader_llm = ReaderLLM()
