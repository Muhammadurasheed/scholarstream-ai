"""
HackerEarth Hackathon Scraper - PRODUCTION
Global Hackathon Platform with Public API
FAANG-Level: Uses HackerEarth's public API
"""
from typing import List, Dict, Any
from datetime import datetime
import structlog
from ..base_scraper import BaseScraper
from ..anti_scraping import anti_scraping_manager

logger = structlog.get_logger()


class HackerEarthScraper(BaseScraper):
    """Production scraper for HackerEarth hackathons"""
    
    def get_source_name(self) -> str:
        return "hackerearth"
    
    def get_source_type(self) -> str:
        return "hackathon"
    
    async def scrape(self) -> List[Dict[str, Any]]:
        """
        Scrape hackathons from HackerEarth
        Uses public API
        """
        logger.info("Scraping HackerEarth hackathons")
        
        opportunities = []
        
        try:
            # HackerEarth API endpoint
            url = 'https://api.hackerearth.com/v4/events/'
            
            # Rate limiting
            await anti_scraping_manager.wait_if_needed(url)
            headers = anti_scraping_manager.get_headers('hackerearth.com')
            
            response = await self.client.get(url, headers=headers)
            
            if response.status_code == 403:
                anti_scraping_manager.mark_blocked('hackerearth.com', 30)
                return []
            
            response.raise_for_status()
            
            data = response.json()
            events = data.get('events', []) if isinstance(data, dict) else data
            
            for event in events[:30]:  # Limit to 30
                try:
                    opportunity = self._parse_hackerearth_event(event)
                    if opportunity:
                        opportunity['url_validated'] = await self.validate_url(opportunity.get('url', ''))
                        normalized = self.normalize_opportunity(opportunity)
                        opportunities.append(normalized)
                except Exception as e:
                    logger.error(f"Error parsing HackerEarth event: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"HackerEarth API error: {e}")
        
        logger.info(f"Scraped {len(opportunities)} hackathons from HackerEarth")
        return opportunities
    
    def _parse_hackerearth_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Parse HackerEarth event data"""
        name = event.get('title', 'HackerEarth Hackathon')
        url = event.get('url', '')
        description = event.get('description', '')
        
        # Parse prize
        prize_amount = event.get('prize_amount', 0)
        prize_display = f"${prize_amount:,}" if prize_amount else "Varies"
        
        # Parse dates
        start_date = event.get('start_date', '')
        end_date = event.get('end_date', '')
        
        # Location
        location = event.get('location', 'Online')
        is_online = location.lower() in ['online', 'virtual', 'remote']
        
        # Tags
        tags = self._extract_tags(name, description, is_online)
        
        return {
            'name': name,
            'organization': 'HackerEarth',
            'description': description or f"{name} on HackerEarth",
            'amount': prize_amount,
            'amount_display': prize_display,
            'deadline': end_date,
            'deadline_type': 'fixed',
            'url': url,
            'tags': tags,
            'eligibility': {
                'gpa_min': None,
                'grades_eligible': ['High School', 'Undergraduate', 'Graduate', 'Professional'],
                'majors': None,
                'gender': None,
                'citizenship': None,  # Global
                'backgrounds': [],
                'states': None
            },
            'requirements': {
                'essay': False,
                'essay_prompts': [],
                'recommendation_letters': 0,
                'transcript': False,
                'resume': False,
                'other': ['HackerEarth account', 'Team registration', 'Project submission']
            }
        }
    
    def _extract_tags(self, name: str, description: str, is_online: bool) -> List[str]:
        """Extract relevant tags"""
        tags = ['Hackathon', 'HackerEarth']
        
        if is_online:
            tags.append('Virtual')
        else:
            tags.append('In-Person')
        
        text = (name + " " + description).lower()
        
        # Technology tags
        if any(word in text for word in ['ai', 'ml', 'machine learning']):
            tags.append('AI/ML')
        if any(word in text for word in ['web', 'frontend', 'backend']):
            tags.append('Web Development')
        if any(word in text for word in ['mobile', 'android', 'ios']):
            tags.append('Mobile')
        if any(word in text for word in ['blockchain', 'web3']):
            tags.append('Blockchain')
        if any(word in text for word in ['iot', 'hardware']):
            tags.append('IoT')
        
        return tags
