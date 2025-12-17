"""
DrivenData Competition Scraper - PRODUCTION
Data Science for Social Impact Competitions
FAANG-Level: Web scraping with comprehensive error handling
"""
from typing import List, Dict, Any
from datetime import datetime
import structlog
from bs4 import BeautifulSoup
from ..base_scraper import BaseScraper
from ..anti_scraping import anti_scraping_manager

logger = structlog.get_logger()


class DrivenDataScraper(BaseScraper):
    """Production scraper for DrivenData competitions"""
    
    def get_source_name(self) -> str:
        return "drivendata"
    
    def get_source_type(self) -> str:
        return "competition"
    
    async def scrape(self) -> List[Dict[str, Any]]:
        """
        Scrape competitions from DrivenData
        Social impact data science competitions
        """
        logger.info("Scraping DrivenData competitions")
        
        opportunities = []
        
        try:
            url = 'https://www.drivendata.org/competitions/'
            
            # Rate limiting
            await anti_scraping_manager.wait_if_needed(url)
            headers = anti_scraping_manager.get_headers('drivendata.org')
            
            response = await self.client.get(url, headers=headers)
            
            if response.status_code == 403:
                anti_scraping_manager.mark_blocked('drivendata.org', 30)
                return []
            
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Find competition cards
            comp_cards = soup.find_all('div', class_='competition-tile') or \
                        soup.find_all('div', class_='competition-card')
            
            for card in comp_cards[:20]:  # Limit to 20
                try:
                    opportunity = self._parse_drivendata_card(card)
                    if opportunity:
                        opportunity['url_validated'] = await self.validate_url(opportunity.get('url', ''))
                        normalized = self.normalize_opportunity(opportunity)
                        opportunities.append(normalized)
                except Exception as e:
                    logger.error(f"Error parsing DrivenData card: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"DrivenData scraping error: {e}")
        
        logger.info(f"Scraped {len(opportunities)} competitions from DrivenData")
        return opportunities
    
    def _parse_drivendata_card(self, card) -> Dict[str, Any]:
        """Parse DrivenData competition card"""
        # Extract name
        name_elem = card.find('h3') or card.find('h2') or card.find('a', class_='title')
        name = name_elem.get_text(strip=True) if name_elem else "DrivenData Competition"
        
        # Extract URL
        link = card.find('a', href=True)
        url = link['href'] if link else ''
        if url and not url.startswith('http'):
            url = f"https://www.drivendata.org{url}"
        
        # Extract description
        desc_elem = card.find('p', class_='description') or card.find('div', class_='summary')
        description = desc_elem.get_text(strip=True) if desc_elem else f"{name} - Data Science for Social Impact"
        
        # Extract prize
        prize_elem = card.find('span', class_='prize') or card.find('div', class_='prize-amount')
        prize_text = prize_elem.get_text(strip=True) if prize_elem else "$0"
        
        import re
        amounts = re.findall(r'\$[\d,]+', prize_text)
        prize_amount = 0
        if amounts:
            prize_amount = int(amounts[0].replace('$', '').replace(',', ''))
        
        # Extract deadline
        deadline_elem = card.find('time') or card.find('span', class_='deadline')
        deadline_text = deadline_elem.get_text(strip=True) if deadline_elem else None
        
        return {
            'name': name,
            'organization': 'DrivenData',
            'description': description,
            'amount': prize_amount,
            'amount_display': prize_text,
            'deadline': deadline_text,
            'deadline_type': 'fixed' if deadline_text else 'rolling',
            'url': url,
            'tags': ['Competition', 'Data Science', 'Social Impact', 'DrivenData'],
            'eligibility': {
                'gpa_min': None,
                'grades_eligible': ['Undergraduate', 'Graduate', 'Professional'],
                'majors': ['Data Science', 'Computer Science', 'Statistics'],
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
                'other': ['DrivenData account', 'Model submission']
            }
        }
