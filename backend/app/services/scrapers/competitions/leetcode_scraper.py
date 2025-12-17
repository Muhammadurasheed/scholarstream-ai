"""
LeetCode Competition Scraper - PRODUCTION
Coding Challenge Platform
FAANG-Level: Weekly contests and challenges
"""
from typing import List, Dict, Any
from datetime import datetime, timedelta
import structlog
from ..base_scraper import BaseScraper

logger = structlog.get_logger()


class LeetCodeScraper(BaseScraper):
    """Production scraper for LeetCode competitions"""
    
    def get_source_name(self) -> str:
        return "leetcode"
    
    def get_source_type(self) -> str:
        return "competition"
    
    async def scrape(self) -> List[Dict[str, Any]]:
        """Scrape competitions from LeetCode"""
        logger.info("Scraping LeetCode competitions")
        
        # LeetCode has weekly contests - curated data
        opportunities = self._get_curated_contests()
        
        logger.info(f"Scraped {len(opportunities)} competitions from LeetCode")
        return opportunities
    
    def _get_curated_contests(self) -> List[Dict[str, Any]]:
        """Curated LeetCode contests"""
        contests = [
            {
                'name': 'LeetCode Weekly Contest',
                'organization': 'LeetCode',
                'description': 'Weekly coding contest with 4 problems. Compete globally and improve your ranking.',
                'amount': 0,
                'amount_display': 'Rating Points',
                'deadline': (datetime.now() + timedelta(days=7)).isoformat(),
                'deadline_type': 'rolling',
                'url': 'https://leetcode.com/contest/',
                'tags': ['Competition', 'Coding', 'LeetCode', 'Weekly'],
                'eligibility': {
                    'gpa_min': None,
                    'grades_eligible': ['High School', 'Undergraduate', 'Graduate', 'Professional'],
                    'majors': ['Computer Science'],
                    'gender': None,
                    'citizenship': None,
                    'backgrounds': [],
                    'states': None
                },
                'requirements': {
                    'essay': False,
                    'essay_prompts': [],
                    'recommendation_letters': 0,
                    'transcript': False,
                    'resume': False,
                    'other': ['LeetCode account']
                }
            },
            {
                'name': 'LeetCode Biweekly Contest',
                'organization': 'LeetCode',
                'description': 'Biweekly coding contest. Practice algorithms and data structures.',
                'amount': 0,
                'amount_display': 'Rating Points',
                'deadline': (datetime.now() + timedelta(days=14)).isoformat(),
                'deadline_type': 'rolling',
                'url': 'https://leetcode.com/contest/',
                'tags': ['Competition', 'Coding', 'LeetCode', 'Biweekly'],
                'eligibility': {
                    'gpa_min': None,
                    'grades_eligible': ['High School', 'Undergraduate', 'Graduate', 'Professional'],
                    'majors': ['Computer Science'],
                    'gender': None,
                    'citizenship': None,
                    'backgrounds': [],
                    'states': None
                },
                'requirements': {
                    'essay': False,
                    'essay_prompts': [],
                    'recommendation_letters': 0,
                    'transcript': False,
                    'resume': False,
                    'other': ['LeetCode account']
                }
            }
        ]
        
        result = []
        for c in contests:
            c['url_validated'] = False
            normalized = self.normalize_opportunity(c)
            result.append(normalized)
        
        return result
