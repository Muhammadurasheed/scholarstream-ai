"""
MLH (Major League Hacking) Scraper - PRODUCTION
Official hackathon platform with public API
FAANG-Level: Uses official API, comprehensive error handling
"""
from typing import List, Dict, Any
from datetime import datetime
import structlog
from ..base_scraper import BaseScraper
from ..api_client import api_client_manager

logger = structlog.get_logger()


class MLHScraper(BaseScraper):
    """Production scraper for MLH hackathons"""
    
    def get_source_name(self) -> str:
        return "mlh"
    
    def get_source_type(self) -> str:
        return "hackathon"
    
    async def scrape(self) -> List[Dict[str, Any]]:
        """
        Scrape hackathons from MLH
        Uses official API - highly reliable
        """
        logger.info("Scraping MLH hackathons")
        
        opportunities = []
        
        try:
            # Get hackathons from API
            hackathons = await api_client_manager.get_mlh_hackathons('current')
            
            for event in hackathons:
                try:
                    opportunity = self._parse_mlh_event(event)
                    if opportunity:
                        opportunity['url_validated'] = await self.validate_url(opportunity.get('url', ''))
                        normalized = self.normalize_opportunity(opportunity)
                        opportunities.append(normalized)
                except Exception as e:
                    logger.error(f"Error parsing MLH event: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"MLH scraping error: {e}")
        
        logger.info(f"Scraped {len(opportunities)} hackathons from MLH")
        return opportunities
    
    def _parse_mlh_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Parse MLH event data"""
        name = event.get('name', 'MLH Hackathon')
        url = event.get('url', '')
        
        # Parse dates
        start_date = event.get('start_date', '')
        end_date = event.get('end_date', '')
        
        # MLH events are typically free or have prizes
        prize_amount = 0
        prize_display = 'Varies'
        
        # Check for prize info in description
        description = event.get('description', '')
        if 'prize' in description.lower():
            # Try to extract prize amount
            import re
            amounts = re.findall(r'\$[\d,]+', description)
            if amounts:
                prize_display = amounts[0]
                prize_amount = int(amounts[0].replace('$', '').replace(',', ''))
        
        # Location
        location = event.get('location', 'Virtual')
        is_virtual = 'virtual' in location.lower() or 'online' in location.lower()
        
        return {
            'name': name,
            'organization': 'Major League Hacking',
            'description': description or f"{name} - MLH Official Hackathon",
            'amount': prize_amount,
            'amount_display': prize_display,
            'deadline': end_date,
            'deadline_type': 'fixed',
            'url': url,
            'tags': self._extract_tags(name, description, is_virtual),
            'eligibility': {
                'gpa_min': None,
                'grades_eligible': ['High School', 'Undergraduate', 'Graduate'],
                'majors': ['Computer Science', 'Engineering', 'Design', 'Business'],
                'gender': None,
                'citizenship': None,  # MLH is international
                'backgrounds': [],
                'states': None
            },
            'requirements': {
                'essay': False,
                'essay_prompts': [],
                'recommendation_letters': 0,
                'transcript': False,
                'resume': False,
                'other': ['Team formation', 'Project submission']
            }
        }
    
    def _extract_tags(self, name: str, description: str, is_virtual: bool) -> List[str]:
        """Extract relevant tags"""
        tags = ['Hackathon', 'MLH Official']
        
        text = (name + " " + description).lower()
        
        if is_virtual:
            tags.append('Virtual')
        else:
            tags.append('In-Person')
        
        # Technology tags
        if any(word in text for word in ['ai', 'ml', 'machine learning', 'artificial intelligence']):
            tags.append('AI/ML')
        if any(word in text for word in ['web', 'frontend', 'backend']):
            tags.append('Web Development')
        if any(word in text for word in ['mobile', 'ios', 'android']):
            tags.append('Mobile')
        if any(word in text for word in ['blockchain', 'web3', 'crypto']):
            tags.append('Blockchain')
        if any(word in text for word in ['game', 'gaming']):
            tags.append('Game Development')
        
        return tags
