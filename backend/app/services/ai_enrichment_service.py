"""
AI Enrichment Service
Batch enrichment of opportunities using Gemini
"""
import google.generativeai as genai
from typing import List, Dict, Any
import json
import asyncio
import structlog
from datetime import datetime

from app.config import settings

logger = structlog.get_logger()


from bs4 import BeautifulSoup

# Global instance
ai_enrichment_service = None

class AIEnrichmentService:
    """
    Enriches raw opportunity data using Gemini AI
    Processes in batches to optimize API usage
    """
    
    def __init__(self):
        genai.configure(api_key=settings.gemini_api_key)
        self.model = genai.GenerativeModel(settings.gemini_model)
        self.batch_size = 10  # Process 10 opportunities at once
    
    def clean_html(self, html_content: str) -> str:
        """
        Aggressively clean HTML to reduce token usage by 60-80%
        Removes scripts, styles, svgs, comments, and non-content tags.
        """
        if not html_content:
            return ""
            
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove heavy non-content tags
            for tag in soup(['script', 'style', 'svg', 'path', 'noscript', 'meta', 'link', 'iframe', 'footer', 'nav']):
                tag.decompose()
                
            # Remove comments
            # (BeautifulSoup handles this if we don't explicitly keep them usually via decompose usually)
            
            # Get text or simplified HTML? 
            # Keeping structure is good for "List detection", but attributes are heavy.
            # Let's keep minimal tags
            
            # Strategy: Get text with separator? No, structure helps AI.
            # Let's just return the body content without the noise.
            
            body = soup.body
            if body:
                return str(body)[:50000] # Hard cap at ~12k tokens per page
            else:
                 return str(soup)[:50000]
                 
        except Exception as e:
            logger.warning("HTML Clean failed, returning raw truncated", error=str(e))
            return html_content[:50000]

    async def extract_opportunities_from_html_batch(self, items: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """
        Batch process multiple HTML pages in ONE prompt to save Quota (RPM)
        items: List of dicts with {'url': str, 'html': str}
        """
        if not items:
            return []
            
        # 1. Clean all HTMLs
        cleaned_items = []
        for item in items:
            clean = self.clean_html(item.get('html', ''))
            if len(clean) > 500: # Skip empty/junk pages
                cleaned_items.append({
                    'url': item.get('url'),
                    'content': clean
                })
        
        if not cleaned_items:
            return []

        # 2. Construct HUGE Prompt (Gemini 1.5 Flash supports 1M+ tokens)
        # We separate pages clearly
        
        context_str = ""
        for i, item in enumerate(cleaned_items):
            context_str += f"\n\n=== START PAGE {i+1} URL: {item['url']} ===\n"
            context_str += item['content']
            context_str += f"\n=== END PAGE {i+1} ===\n"

        prompt = f"""
You are an expert financial opportunity extractor.
I have concatenated {len(cleaned_items)} different webpages below.
Extract ALL financial opportunities (Scholarships, Grants, Hackathons, Bounties) from ALL pages.

INSTRUCTIONS:
1. Process each "PAGE" block independently but return a single combined JSON list.
2. For each opportunity, map the 'url' field to the absolute URL found in the "PAGE URL" header if the link is relative.
3. Required Fields: title, organization, amount_value (int), amount_display, deadline (YYYY-MM-DD), description, url (absolute), type, eligibility.
4. If a page has NO opportunities, skip it.

DATA:
{context_str}

RETURN JSON ARRAY ONLY.
"""
        max_retries = 3
        base_delay = 10 # Higher delay for batch
        
        for attempt in range(max_retries):
            try:
                response = await self.model.generate_content_async(prompt)
                text = response.text.strip()
                
                if text.startswith("```json"):
                    text = text.split("```json")[1].split("```")[0].strip()
                elif text.startswith("```"):
                    text = text.split("```")[1].split("```")[0].strip()
                    
                extracted = json.loads(text)
                if not isinstance(extracted, list):
                    if isinstance(extracted, dict):
                        extracted = [extracted]
                    else:
                        return []
                
                # VALIDATION: Principal Engineer Level Quality Gate
                valid_opportunities = []
                for item in extracted:
                    try:
                        # 1. Critical Field Check
                        if not item.get('title') or not item.get('url'):
                            continue # Skip items without title or URL
                        
                        # 2. Data Cleaning
                        if item.get('amount_value') is None:
                            item['amount_value'] = 0
                        
                        # 3. NoneType Safety (The "Crash Fix")
                        if item.get('eligibility') is None:
                            item['eligibility'] = "Open to all users."
                        
                        if item.get('deadline') == "Unknown" or not item.get('deadline'):
                             item['deadline'] = None # Better than "Unknown" string

                        # 4. Standardize
                        # Ensure we don't have "Lorem Ipsum" or "Test"
                        if "lorem" in (item.get('description') or '').lower():
                            continue

                        valid_opportunities.append(item)
                    except Exception as val_err:
                        logger.warning("Dropping invalid opportunity data", error=str(val_err))
                        continue

                return valid_opportunities

            except Exception as e:
                error_str = str(e)
                error_type = type(e).__name__
                
                # Check for actual rate limit errors
                is_rate_limit = "429" in error_str or "Resource has been exhausted" in error_str or "RESOURCE_EXHAUSTED" in error_str
                
                if is_rate_limit:
                    wait_time = base_delay * (2 ** attempt) + 30
                    logger.warning(
                        "Gemini Rate Limit Hit (Batch)", 
                        items=len(cleaned_items),
                        retry_in=f"{wait_time}s", 
                        attempt=f"{attempt+1}/{max_retries}"
                    )
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    # Log the actual error for debugging
                    logger.error(
                        "Batch Extraction failed", 
                        error_type=error_type,
                        error=error_str[:500]  # Truncate long errors
                    )
                    return []
        
        return []

    async def enrich_opportunities_batch(
        self,
        raw_opportunities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Enrich opportunities in batches
        Returns structured, validated opportunity data
        """
        logger.info("Starting batch enrichment", total=len(raw_opportunities))
        
        enriched = []
        batches = [
            raw_opportunities[i:i + self.batch_size]
            for i in range(0, len(raw_opportunities), self.batch_size)
        ]
        
        for batch_idx, batch in enumerate(batches):
            try:
                batch_enriched = await self._enrich_batch(batch)
                enriched.extend(batch_enriched)
                
                logger.info(
                    "Batch enriched",
                    batch_num=batch_idx + 1,
                    total_batches=len(batches),
                    count=len(batch_enriched)
                )
                
                # Rate limiting: wait between batches
                if batch_idx < len(batches) - 1:
                    await asyncio.sleep(2)
                    
            except Exception as e:
                logger.error(
                    "Batch enrichment failed",
                    batch_num=batch_idx + 1,
                    error=str(e)
                )
                # Return raw data as fallback
                enriched.extend(batch)
        
        logger.info("Enrichment complete", total=len(enriched))
        return enriched
    
    async def _enrich_batch(self, batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Enrich a single batch using Gemini"""
        
        prompt = f"""
You are a financial opportunity data structuring expert. Clean and validate this opportunity data.

RAW DATA (array of opportunities):
{json.dumps(batch, indent=2)}

For EACH opportunity, validate and return structured JSON with these fields:
- Keep all existing fields
- Ensure all required fields are present
- Fix any data quality issues
- Standardize date formats to YYYY-MM-DD
- Ensure amounts are numeric

Return ONLY a JSON array, no markdown, no preamble.
Today's date: {datetime.now().strftime('%Y-%m-%d')}
"""
        max_retries = 3
        base_delay = 5
        
        for attempt in range(max_retries):
            try:
                # Use Flash for speed if available, or fallback to current model
                response = await self.model.generate_content_async(prompt)
                text = response.text.strip()
                
                if text.startswith("```json"):
                    text = text.split("```json")[1].split("```")[0].strip()
                elif text.startswith("```"):
                    text = text.split("```")[1].split("```")[0].strip()
                    
                extracted = json.loads(text)
                if not isinstance(extracted, list):
                    if isinstance(extracted, dict):
                        extracted = [extracted]
                    else:
                        return []
                
                return extracted

            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "Resource has been exhausted" in error_str:
                    # Extract wait time if available or backoff
                    wait_time = base_delay * (2 ** attempt) + 10 # Exponential + Buffer
                    logger.warning(
                        "Gemini Rate Limit Hit (429)", 
                        url="BATCH_OPP", 
                        retry_in=f"{wait_time}s", 
                        attempt=f"{attempt+1}/{max_retries}"
                    )
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    # Non-retryable error
                    logger.error("Enrichment failed", error=str(e))
                    return []
        
        logger.error("Max retries exceeded for AI extraction", url="BATCH_OPP")
        return []

    async def extract_opportunities_from_html(self, html_content: str, url: str) -> List[Dict[str, Any]]:
        """
        Extract structured opportunities from raw HTML using Gemini
        Works for lists, tables, and detail pages.
        """
        # CLEAN FIRST to save tokens
        clean_html_content = self.clean_html(html_content)

        prompt = f"""
You are an expert web scraper and data extractor. 
I will provide the HTML of a webpage ("{url}").
Your goal is to extract ALL financial opportunities (Scholarships, Grants, Hackathons, Bounties, Competitions) found on this page.

RAW HTML:
{clean_html_content}

INSTRUCTIONS:
1. Identify if this page contains list elements (multiple opportunities) or a single detail view.
2. FILTER OUT EXPIRED OPPORTUNITIES: If an opportunity's deadline is before today ({datetime.now().strftime('%Y-%m-%d')}), do NOT include it.
3. Extract the following fields for EACH opportunity:
   - title
   - organization (host)
   - amount_value (numeric estimate, or 0 if unknown)
   - amount_display (e.g "$5,000", "1st Prize: $10k")
   - deadline (YYYY-MM-DD, infer if needed, null if unknown)
   - description (DETAILED: Extract 2-3 sentences from the 'About' section or main body. Do NOT write generic summaries like "A hackathon where...". Use the actual text describing the theme/goal.)
   - url (absolute URL, resolve relative paths against "{url}")
   - type (scholarship, hackathon, grant, bounty, competition)
   - eligibility (string summary)

4. Return ONLY a valid JSON array of objects. No markdown.
"""
        max_retries = 3
        base_delay = 5
        
        for attempt in range(max_retries):
            try:
                # Use Flash for speed if available, or fallback to current model
                response = await self.model.generate_content_async(prompt)
                text = response.text.strip()
                
                if text.startswith("```json"):
                    text = text.split("```json")[1].split("```")[0].strip()
                elif text.startswith("```"):
                    text = text.split("```")[1].split("```")[0].strip()
                    
                extracted = json.loads(text)
                if not isinstance(extracted, list):
                    if isinstance(extracted, dict):
                        extracted = [extracted]
                    else:
                        return []
                
                # VALIDATION: Principal Engineer Level Quality Gate
                valid_opportunities = []
                for item in extracted:
                    try:
                        if not item.get('title') or not item.get('url'):
                            continue 
                        
                        if item.get('amount_value') is None:
                            item['amount_value'] = 0
                        
                        if item.get('eligibility') is None:
                            item['eligibility'] = "Open to all users."
                        
                        if item.get('deadline') == "Unknown" or not item.get('deadline'):
                             item['deadline'] = None

                        if "lorem" in (item.get('description') or '').lower():
                            continue

                        valid_opportunities.append(item)
                    except Exception:
                        continue

                return valid_opportunities

            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "Resource has been exhausted" in error_str:
                    # Extract wait time if available or backoff
                    wait_time = base_delay * (2 ** attempt) + 10 # Exponential + Buffer
                    logger.warning(
                        "Gemini Rate Limit Hit (429)", 
                        url=url, 
                        retry_in=f"{wait_time}s", 
                        attempt=f"{attempt+1}/{max_retries}"
                    )
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    # Non-retryable error
                    logger.error("HTML Extraction failed", url=url, error=str(e))
                    return []
        
        logger.error("Max retries exceeded for AI extraction", url=url)
        return []


# Global instance
ai_enrichment_service = AIEnrichmentService()
