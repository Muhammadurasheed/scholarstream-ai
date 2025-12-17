"""
Topcoder Competition Scraper - PRODUCTION  
Algorithm and Design Competitions with Official API
FAANG-Level: Uses Topcoder's official API
"""
from typing import List, Dict, Any
from datetime import datetime
import structlog
from ..base_scraper import BaseScraper

logger = structlog.get_logger()


class TopcoderScraper(BaseScraper):
    """Production scraper for Topcoder competitions"""
    
    def get_source_name(self) -> str:
        return "topcoder"
    
    def get_source_type(self) -> str:
        return "competition"
    
    async def scrape(self) -> List[Dict[str, Any]]:
        """
        Scrape competitions from Topcoder
        Uses Topcoder API
        """
        logger.info("Scraping Topcoder competitions")
        
        opportunities = []
        
        try:
            # Topcoder API endpoint for challenges
            url = 'https://api.topcoder.com/v5/challenges'
            params = {
                'status': 'Active',
                'perPage': 50,
                'sortBy': 'prize',
                'sortOrder': 'desc'
            }
            
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            challenges = data if isinstance(data, list) else data.get('result', [])
            
            for challenge in challenges:
                try:
                    opportunity = self._parse_topcoder_challenge(challenge)
                    if opportunity:
                        opportunity['url_validated'] = await self.validate_url(opportunity.get('url', ''))
                        normalized = self.normalize_opportunity(opportunity)
                        opportunities.append(normalized)
                except Exception as e:
                    logger.error(f"Error parsing Topcoder challenge: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Topcoder API error: {e}")
        
        logger.info(f"Scraped {len(opportunities)} competitions from Topcoder")
        return opportunities
    
    def _parse_topcoder_challenge(self, challenge: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Topcoder challenge data"""
        name = challenge.get('name', 'Topcoder Challenge')
        challenge_id = challenge.get('id', '')
        url = f"https://www.topcoder.com/challenges/{challenge_id}"
        
        # Parse prize
        prizes = challenge.get('prizes', [])
        total_prize = sum(prizes) if prizes else 0
        prize_display = f"${total_prize:,}" if total_prize else "Points"
        
        # Parse deadline
        submission_end_date = challenge.get('submissionEndDate', '')
        
        # Track/type
        track = challenge.get('track', 'Development')
        challenge_type = challenge.get('type', 'Code')
        
        # Description
        description = challenge.get('overview', '') or challenge.get('description', '')
        
        # Tags
        tags = self._extract_tags(name, track, challenge_type)
        
        # Technologies
        technologies = challenge.get('technologies', [])
        
        return {
            'name': name,
            'organization': 'Topcoder',
            'description': description or f"{name} - {track} Challenge on Topcoder",
            'amount': total_prize,
            'amount_display': prize_display,
            'deadline': submission_end_date,
            'deadline_type': 'fixed',
            'url': url,
            'tags': tags,
            'eligibility': {
                'gpa_min': None,
                'grades_eligible': ['High School', 'Undergraduate', 'Graduate', 'Professional'],
                'majors': ['Computer Science', 'Design', 'Engineering'],
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
                'other': ['Topcoder account', 'Solution submission']
            }
        }
    
    def _extract_tags(self, name: str, track: str, challenge_type: str) -> List[str]:
        """Extract relevant tags"""
        tags = ['Competition', 'Topcoder']
        
        # Add track
        if track:
            tags.append(track)
        
        # Add type
        if challenge_type:
            tags.append(challenge_type)
        
        text = name.lower()
        
        # Technology tags
        if any(word in text for word in ['algorithm', 'algo']):
            tags.append('Algorithms')
        if any(word in text for word in ['design', 'ui', 'ux']):
            tags.append('Design')
        if any(word in text for word in ['data', 'ml', 'ai']):
            tags.append('Data Science')
        if any(word in text for word in ['web', 'frontend', 'backend']):
            tags.append('Web Development')
        if any(word in text for word in ['mobile', 'ios', 'android']):
            tags.append('Mobile')
        
        return tags
