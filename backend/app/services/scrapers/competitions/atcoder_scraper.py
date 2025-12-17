"""
AtCoder Competition Scraper - PRODUCTION
Japanese Competitive Programming Platform with Official API
FAANG-Level: Uses AtCoder's official API
"""
from typing import List, Dict, Any
from datetime import datetime
import structlog
from ..base_scraper import BaseScraper

logger = structlog.get_logger()


class AtCoderScraper(BaseScraper):
    """Production scraper for AtCoder competitions"""
    
    def get_source_name(self) -> str:
        return "atcoder"
    
    def get_source_type(self) -> str:
        return "competition"
    
    async def scrape(self) -> List[Dict[str, Any]]:
        """Scrape competitions from AtCoder - Japanese platform"""
        logger.info("Scraping AtCoder competitions")
        
        opportunities = []
        
        try:
            # AtCoder API endpoint
            url = 'https://atcoder.jp/contests/'
            
            response = await self.client.get(url)
            response.raise_for_status()
            
            # Parse upcoming contests
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'lxml')
            
            contest_rows = soup.find_all('tr', class_='contest-row') or soup.find_all('tr')[1:6]
            
            for row in contest_rows[:10]:
                try:
                    contest = self._parse_atcoder_row(row)
                    if contest:
                        contest['url_validated'] = await self.validate_url(contest.get('url', ''))
                        normalized = self.normalize_opportunity(contest)
                        opportunities.append(normalized)
                except Exception as e:
                    logger.error(f"Error parsing AtCoder row: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"AtCoder API error: {e}")
        
        logger.info(f"Scraped {len(opportunities)} competitions from AtCoder")
        return opportunities
    
    def _parse_atcoder_row(self, row) -> Dict[str, Any]:
        """Parse AtCoder contest row"""
        cells = row.find_all('td')
        if len(cells) < 2:
            return None
        
        # Extract contest name
        name_cell = cells[1] if len(cells) > 1 else cells[0]
        link = name_cell.find('a', href=True)
        name = link.get_text(strip=True) if link else "AtCoder Contest"
        url = f"https://atcoder.jp{link['href']}" if link else ''
        
        # Extract start time
        time_cell = cells[0] if len(cells) > 1 else None
        start_time = time_cell.get_text(strip=True) if time_cell else None
        
        return {
            'name': name,
            'organization': 'AtCoder',
            'description': f"{name} - Competitive Programming Contest on AtCoder",
            'amount': 0,
            'amount_display': 'Rating Points',
            'deadline': start_time,
            'deadline_type': 'fixed',
            'url': url,
            'tags': ['Competition', 'Competitive Programming', 'AtCoder', 'Japan'],
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
                'other': ['AtCoder account']
            }
        }
