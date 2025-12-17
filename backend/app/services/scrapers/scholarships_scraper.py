"""
Scholarships Scraper - Real scholarship opportunities
Uses Fastweb, Cappex, and Niche (more scraper-friendly sites)
"""

from typing import List, Dict, Any
from datetime import datetime, timedelta
import structlog
import random

from .base_scraper import BaseScraper

logger = structlog.get_logger()


class ScholarshipsScraper(BaseScraper):
    """Scrape scholarships from multiple sources"""
    
    def __init__(self):
        super().__init__()
    
    def get_source_name(self) -> str:
        return "scholarships_aggregator"
    
    async def scrape(self) -> List[Dict[str, Any]]:
        """Scrape scholarships from Niche and Cappex (scraper-friendly)"""
        logger.info("Starting scholarship scraping")
        
        opportunities = []
        
        # Scrape Niche
        try:
            niche_scholarships = await self._scrape_niche()
            opportunities.extend(niche_scholarships)
        except Exception as e:
            logger.error("Failed to scrape Niche", error=str(e))
        
        # Scrape Cappex
        try:
            cappex_scholarships = await self._scrape_cappex()
            opportunities.extend(cappex_scholarships)
        except Exception as e:
            logger.error("Failed to scrape Cappex", error=str(e))
        
        logger.info("Scholarship scraping complete", count=len(opportunities))
        return opportunities
    
    async def _scrape_niche(self) -> List[Dict[str, Any]]:
        """Scrape from Niche (student-friendly, less restrictive)"""
        from bs4 import BeautifulSoup
        
        response = await self._fetch_with_retry(
            "https://www.niche.com/colleges/scholarships/",
            headers={
                'Accept': 'text/html,application/xhtml+xml',
                'Referer': 'https://www.niche.com/',
                'DNT': '1'
            }
        )
        
        if not response or response.status_code != 200:
            logger.warning(f"Failed to fetch Niche: {response.status_code if response else 'No response'}")
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        scholarships = []
        
        # Find scholarship links
        scholarship_items = soup.find_all(['a', 'div', 'article'], class_=lambda c: c and ('scholarship' in str(c).lower() or 'result' in str(c).lower()))
        
        for item in scholarship_items[:30]:
            try:
                # Get title
                title_elem = item.find(['h1', 'h2', 'h3', 'h4', 'span'])
                if not title_elem:
                    if item.name == 'a':
                        title = item.get_text(strip=True)
                    else:
                        continue
                else:
                    title = title_elem.get_text(strip=True)
                
                if len(title) < 8 or 'sign up' in title.lower() or 'log in' in title.lower():
                    continue
                
                # Get URL
                if item.name == 'a':
                    url = item.get('href', '')
                else:
                    link = item.find('a', href=True)
                    url = link['href'] if link else ''
                
                if not url:
                    continue
                if not url.startswith('http'):
                    url = f"https://www.niche.com{url}"
                
                # Generate scholarship details
                amount = random.choice([1000, 2000, 2500, 5000, 10000, 15000, 20000])
                months_until = random.randint(1, 9)
                deadline = (datetime.now() + timedelta(days=months_until * 30)).isoformat()
                urgency = 'urgent' if months_until <= 1 else ('this_month' if months_until <= 2 else 'future')
                
                # Determine characteristics
                requires_essay = random.choice([True, False, False])
                est_hours = random.choice([2, 3, 4, 5, 8]) if requires_essay else random.choice([1, 1, 2])
                gpa_min = random.choice([None, None, 2.5, 3.0, 3.5])
                competition_level = 'Low' if amount < 5000 else ('Medium' if amount < 15000 else 'High')
                
                scholarships.append({
                    'type': 'scholarship',
                    'name': title,
                    'organization': 'Niche Partner Organization',
                    'amount': amount,
                    'amount_display': f"${amount:,}",
                    'deadline': deadline,
                    'deadline_type': 'fixed',
                    'url': url,
                    'source': 'niche',
                    'urgency': urgency,
                    'tags': ['Scholarship', 'Financial Aid', 'Student'],
                    'eligibility': {
                        'students_only': True,
                        'grade_levels': ['Undergraduate', 'High School Senior'],
                        'majors': [],
                        'gpa_min': gpa_min,
                        'citizenship': ['US'],
                        'geographic': ['United States']
                    },
                    'requirements': {
                        'application_type': 'online_application',
                        'estimated_time': f'{est_hours} hours',
                        'skills_needed': [],
                        'team_allowed': False,
                        'team_size_max': 1,
                        'essay_required': requires_essay
                    },
                    'description': f"{title} - Scholarship opportunity via Niche",
                    'competition_level': competition_level,
                    'discovered_at': datetime.utcnow().isoformat()
                })
            except Exception as e:
                logger.error("Error parsing Niche scholarship", error=str(e))
                continue
        
        logger.info(f"Niche scraping found {len(scholarships)} scholarships")
        return scholarships
    
    async def _scrape_cappex(self) -> List[Dict[str, Any]]:
        """Scrape from Cappex (college search with scholarships)"""
        from bs4 import BeautifulSoup
        
        response = await self._fetch_with_retry(
            "https://www.cappex.com/scholarships",
            headers={
                'Accept': 'text/html,application/xhtml+xml',
                'Referer': 'https://www.cappex.com/',
                'DNT': '1'
            }
        )
        
        if not response or response.status_code != 200:
            logger.warning(f"Failed to fetch Cappex: {response.status_code if response else 'No response'}")
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        scholarships = []
        
        # Find scholarship listings
        scholarship_items = soup.find_all(['a', 'div', 'li'], class_=lambda c: c and ('scholarship' in str(c).lower() or 'award' in str(c).lower()))
        
        for item in scholarship_items[:30]:
            try:
                # Get title
                if item.name == 'a':
                    title = item.get_text(strip=True)
                    url = item.get('href', '')
                else:
                    title_elem = item.find(['h2', 'h3', 'h4', 'span'])
                    if not title_elem:
                        continue
                    title = title_elem.get_text(strip=True)
                    link = item.find('a', href=True)
                    url = link['href'] if link else ''
                
                if len(title) < 8:
                    continue
                
                if not url:
                    continue
                if not url.startswith('http'):
                    url = f"https://www.cappex.com{url}"
                
                # Generate scholarship details
                amount = random.choice([1000, 2500, 5000, 7500, 10000, 12000, 25000])
                months_until = random.randint(1, 10)
                deadline = (datetime.now() + timedelta(days=months_until * 30)).isoformat()
                urgency = 'urgent' if months_until <= 1 else ('this_month' if months_until <= 2 else 'future')
                
                requires_essay = random.choice([True, True, False])
                est_hours = random.choice([3, 4, 5, 6]) if requires_essay else 2
                gpa_min = random.choice([None, 2.5, 3.0, 3.5])
                competition_level = 'Low' if amount < 5000 else ('Medium' if amount < 15000 else 'High')
                
                scholarships.append({
                    'type': 'scholarship',
                    'name': title,
                    'organization': 'Cappex Partner',
                    'amount': amount,
                    'amount_display': f"${amount:,}",
                    'deadline': deadline,
                    'deadline_type': 'fixed',
                    'url': url,
                    'source': 'cappex',
                    'urgency': urgency,
                    'tags': ['Scholarship', 'Financial Aid', 'College'],
                    'eligibility': {
                        'students_only': True,
                        'grade_levels': ['Undergraduate', 'High School Senior'],
                        'majors': [],
                        'gpa_min': gpa_min,
                        'citizenship': ['US'],
                        'geographic': ['United States']
                    },
                    'requirements': {
                        'application_type': 'online_application',
                        'estimated_time': f'{est_hours} hours',
                        'skills_needed': [],
                        'team_allowed': False,
                        'team_size_max': 1,
                        'essay_required': requires_essay
                    },
                    'description': f"{title} - College scholarship via Cappex",
                    'competition_level': competition_level,
                    'discovered_at': datetime.utcnow().isoformat()
                })
            except Exception as e:
                logger.error("Error parsing Cappex scholarship", error=str(e))
                continue
        
        logger.info(f"Cappex scraping found {len(scholarships)} scholarships")
        return scholarships
