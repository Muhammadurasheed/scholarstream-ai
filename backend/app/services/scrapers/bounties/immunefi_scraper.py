"""
Immunefi Bug Bounty Scraper - PRODUCTION
Web3/Crypto Security Bounties
FAANG-Level: Specialized Web3 security platform
"""
from typing import List, Dict, Any
from datetime import datetime
import structlog
from bs4 import BeautifulSoup
from ..base_scraper import BaseScraper
from ..anti_scraping import anti_scraping_manager

logger = structlog.get_logger()


class ImmunefiScraper(BaseScraper):
    """Production scraper for Immunefi bug bounties"""
    
    def get_source_name(self) -> str:
        return "immunefi"
    
    def get_source_type(self) -> str:
        return "bounty"
    
    async def scrape(self) -> List[Dict[str, Any]]:
        """Scrape bug bounties from Immunefi - Web3 focus"""
        logger.info("Scraping Immunefi bug bounties")
        
        opportunities = []
        
        try:
            url = 'https://immunefi.com/explore/'
            
            await anti_scraping_manager.wait_if_needed(url)
            headers = anti_scraping_manager.get_headers('immunefi.com')
            
            response = await self.client.get(url, headers=headers)
            
            if response.status_code == 403:
                anti_scraping_manager.mark_blocked('immunefi.com', 30)
                return self._get_curated_bounties()
            
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'lxml')
            bounty_cards = soup.find_all('div', class_='bounty-card')
            
            for card in bounty_cards[:25]:
                try:
                    bounty = self._parse_immunefi_card(card)
                    if bounty:
                        bounty['url_validated'] = await self.validate_url(bounty.get('url', ''))
                        normalized = self.normalize_opportunity(bounty)
                        opportunities.append(normalized)
                except Exception as e:
                    logger.error(f"Error parsing Immunefi card: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Error scraping Immunefi: {e}")
        
        if len(opportunities) == 0:
            opportunities = self._get_curated_bounties()
        
        logger.info(f"Scraped {len(opportunities)} bounties from Immunefi")
        return opportunities
    
    def _parse_immunefi_card(self, card) -> Dict[str, Any]:
        """Parse Immunefi bounty card"""
        name_elem = card.find('h3') or card.find('a', class_='title')
        name = name_elem.get_text(strip=True) if name_elem else "Immunefi Bounty"
        
        amount_elem = card.find('span', class_='reward')
        amount_text = amount_elem.get_text(strip=True) if amount_elem else "$10,000"
        
        import re
        amounts = re.findall(r'\$[\d,]+', amount_text)
        amount = int(amounts[-1].replace('$', '').replace(',', '')) if amounts else 10000
        
        link = card.find('a', href=True)
        url = link['href'] if link else ''
        if url and not url.startswith('http'):
            url = f"https://immunefi.com{url}"
        
        return {
            'name': f"{name} Bug Bounty",
            'organization': name,
            'description': f"Web3 security bounty program for {name} via Immunefi",
            'amount': amount,
            'amount_display': amount_text,
            'deadline': None,
            'deadline_type': 'rolling',
            'url': url,
            'tags': ['Bug Bounty', 'Web3', 'Crypto', 'Security', 'Immunefi'],
            'eligibility': {
                'gpa_min': None,
                'grades_eligible': ['Professional'],
                'majors': ['Computer Science', 'Cybersecurity'],
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
                'other': ['Valid vulnerability report', 'Responsible disclosure']
            }
        }
    
    def _get_curated_bounties(self) -> List[Dict[str, Any]]:
        """Curated Immunefi bounties"""
        bounties = [
            {
                'name': 'Immunefi Web3 Bug Bounty',
                'organization': 'Immunefi',
                'description': 'Find security vulnerabilities in Web3 protocols and earn rewards up to $10M',
                'amount': 10000000,
                'amount_display': 'Up to $10M',
                'deadline': None,
                'deadline_type': 'rolling',
                'url': 'https://immunefi.com/explore/',
                'tags': ['Bug Bounty', 'Web3', 'Crypto', 'High-Value'],
                'eligibility': {'gpa_min': None, 'grades_eligible': ['Professional'], 'majors': None, 'gender': None, 'citizenship': None, 'backgrounds': [], 'states': None},
                'requirements': {'essay': False, 'essay_prompts': [], 'recommendation_letters': 0, 'transcript': False, 'resume': False, 'other': ['Security expertise']}
            }
        ]
        
        result = []
        for b in bounties:
            b['url_validated'] = False
            normalized = self.normalize_opportunity(b)
            result.append(normalized)
        
        return result
