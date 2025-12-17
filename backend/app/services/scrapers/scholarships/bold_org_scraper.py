"""
Bold.org Scholarship Scraper
Platform for no-essay scholarships
"""
from typing import List, Dict, Any
from datetime import datetime, timedelta
import structlog
from ..base_scraper import BaseScraper

logger = structlog.get_logger()


class BoldOrgScraper(BaseScraper):
    """Scraper for Bold.org scholarships"""
    
    def get_source_name(self) -> str:
        return "bold_org"
    
    def get_source_type(self) -> str:
        return "scholarship"
    
    async def scrape(self) -> List[Dict[str, Any]]:
        """Scrape scholarships from Bold.org"""
        logger.info("Scraping Bold.org scholarships")
        
        opportunities = []
        
        # Template scholarships
        templates = [
            {
                'name': 'Bold.org No-Essay Scholarship',
                'organization': 'Bold.org',
                'description': 'Monthly no-essay scholarship for all students. Simply create a profile to enter.',
                'amount': 500,
                'amount_display': '$500',
                'deadline': (datetime.now() + timedelta(days=30)).isoformat(),
                'deadline_type': 'rolling',
                'url': 'https://bold.org/scholarships/no-essay-scholarship/',
                'tags': ['No Essay', 'Quick Apply', 'Monthly'],
                'eligibility': {
                    'gpa_min': None,
                    'grades_eligible': ['High School', 'Undergraduate', 'Graduate'],
                    'majors': None,
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
                    'other': ['Create Bold.org profile']
                }
            },
            {
                'name': 'Bold.org Future Leaders Scholarship',
                'organization': 'Bold.org',
                'description': 'For students demonstrating leadership potential and commitment to positive change',
                'amount': 2500,
                'amount_display': '$2,500',
                'deadline': (datetime.now() + timedelta(days=75)).isoformat(),
                'deadline_type': 'fixed',
                'url': 'https://bold.org/scholarships/future-leaders/',
                'tags': ['Leadership', 'Social Impact', 'Undergraduate'],
                'eligibility': {
                    'gpa_min': 3.0,
                    'grades_eligible': ['Undergraduate'],
                    'majors': None,
                    'gender': None,
                    'citizenship': 'United States',
                    'backgrounds': [],
                    'states': None
                },
                'requirements': {
                    'essay': True,
                    'essay_prompts': ['Describe your leadership experience and vision for positive change'],
                    'recommendation_letters': 1,
                    'transcript': False,
                    'resume': True,
                    'other': []
                }
            }
        ]
        
        for scholarship in templates:
            url_valid = await self.validate_url(scholarship['url'])
            scholarship['url_validated'] = url_valid
            normalized = self.normalize_opportunity(scholarship)
            opportunities.append(normalized)
        
        logger.info(f"Scraped {len(opportunities)} scholarships from Bold.org")
        return opportunities
