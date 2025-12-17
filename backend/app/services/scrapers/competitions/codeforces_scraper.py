"""
Codeforces Competition Scraper - PRODUCTION
Competitive Programming Platform with Official API
FAANG-Level: Uses Codeforces official API
"""
from typing import List, Dict, Any
from datetime import datetime, timedelta
import structlog
from ..base_scraper import BaseScraper

logger = structlog.get_logger()


class CodeforcesScraper(BaseScraper):
    """Production scraper for Codeforces competitions"""
    
    def get_source_name(self) -> str:
        return "codeforces"
    
    def get_source_type(self) -> str:
        return "competition"
    
    async def scrape(self) -> List[Dict[str, Any]]:
        """
        Scrape competitions from Codeforces
        Uses official Codeforces API
        """
        logger.info("Scraping Codeforces competitions")
        
        opportunities = []
        
        try:
            # Codeforces API endpoint
            url = 'https://codeforces.com/api/contest.list'
            
            response = await self.client.get(url)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('status') != 'OK':
                logger.error(f"Codeforces API error: {data.get('comment')}")
                return []
            
            contests = data.get('result', [])
            
            # Filter for upcoming and running contests
            for contest in contests:
                if contest.get('phase') in ['BEFORE', 'CODING']:
                    try:
                        opportunity = self._parse_codeforces_contest(contest)
                        if opportunity:
                            opportunity['url_validated'] = await self.validate_url(opportunity.get('url', ''))
                            normalized = self.normalize_opportunity(opportunity)
                            opportunities.append(normalized)
                    except Exception as e:
                        logger.error(f"Error parsing Codeforces contest: {e}")
                        continue
            
        except Exception as e:
            logger.error(f"Codeforces API error: {e}")
        
        logger.info(f"Scraped {len(opportunities)} competitions from Codeforces")
        return opportunities
    
    def _parse_codeforces_contest(self, contest: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Codeforces contest data"""
        name = contest.get('name', 'Codeforces Contest')
        contest_id = contest.get('id', '')
        url = f"https://codeforces.com/contest/{contest_id}"
        
        # Parse start time
        start_time_seconds = contest.get('startTimeSeconds', 0)
        duration_seconds = contest.get('durationSeconds', 0)
        
        if start_time_seconds:
            start_time = datetime.fromtimestamp(start_time_seconds)
            end_time = start_time + timedelta(seconds=duration_seconds)
            deadline = end_time.isoformat()
        else:
            deadline = None
        
        # Contest type
        contest_type = contest.get('type', 'CF')
        
        # Tags
        tags = self._extract_tags(name, contest_type)
        
        return {
            'name': name,
            'organization': 'Codeforces',
            'description': f"{name} - Competitive Programming Contest on Codeforces",
            'amount': 0,  # Most Codeforces contests are for rating, not prizes
            'amount_display': 'Rating Points',
            'deadline': deadline,
            'deadline_type': 'fixed',
            'url': url,
            'tags': tags,
            'eligibility': {
                'gpa_min': None,
                'grades_eligible': ['High School', 'Undergraduate', 'Graduate', 'Professional'],
                'majors': ['Computer Science', 'Mathematics', 'Engineering'],
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
                'other': ['Codeforces account', 'Programming skills']
            }
        }
    
    def _extract_tags(self, name: str, contest_type: str) -> List[str]:
        """Extract relevant tags"""
        tags = ['Competition', 'Competitive Programming', 'Codeforces']
        
        # Add contest type
        if contest_type == 'CF':
            tags.append('Codeforces Round')
        elif contest_type == 'ICPC':
            tags.append('ICPC Style')
        elif contest_type == 'IOI':
            tags.append('IOI Style')
        
        # Add difficulty level from name
        if 'div. 1' in name.lower() or 'div.1' in name.lower():
            tags.append('Advanced')
        elif 'div. 2' in name.lower() or 'div.2' in name.lower():
            tags.append('Intermediate')
        elif 'div. 3' in name.lower() or 'div.3' in name.lower():
            tags.append('Beginner')
        elif 'div. 4' in name.lower() or 'div.4' in name.lower():
            tags.append('Beginner Friendly')
        
        # Add special contest types
        if 'educational' in name.lower():
            tags.append('Educational')
        if 'global' in name.lower():
            tags.append('Global Round')
        
        return tags
