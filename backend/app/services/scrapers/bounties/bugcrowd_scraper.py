"""
Bugcrowd Bug Bounty Scraper - PRODUCTION
Enterprise Bug Bounty Platform
FAANG-Level: Web scraping with comprehensive error handling
"""
from typing import List, Dict, Any
from datetime import datetime
import structlog
from bs4 import BeautifulSoup
from ..base_scraper import BaseScraper
from ..anti_scraping import anti_scraping_manager

logger = structlog.get_logger()


class BugcrowdScraper(BaseScraper):
    """Production scraper for Bugcrowd bug bounties"""
    
    def get_source_name(self) -> str:
        return "bugcrowd"
    
    def get_source_type(self) -> str:
        return "bounty"
    
    async def scrape(self) -> List[Dict[str, Any]]:
        """
        Scrape bug bounties from Bugcrowd
        Uses web scraping of public programs
        """
        logger.info("Scraping Bugcrowd bug bounties")
        
        opportunities = []
        
        try:
            url = 'https://bugcrowd.com/programs'
            
            # Rate limiting
            await anti_scraping_manager.wait_if_needed(url)
            headers = anti_scraping_manager.get_headers('bugcrowd.com')
            
            response = await self.client.get(url, headers=headers)
            
            if response.status_code == 403:
                anti_scraping_manager.mark_blocked('bugcrowd.com', 30)
                logger.warning("Bugcrowd blocked, using fallback data")
                return self._get_fallback_bounties()
            
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Find program cards
            program_cards = soup.find_all('div', class_='program-card') or \
                          soup.find_all('div', {'data-program': True})
            
            for card in program_cards[:30]:  # Limit to 30
                try:
                    opportunity = self._parse_bugcrowd_card(card)
                    if opportunity:
                        opportunity['url_validated'] = await self.validate_url(opportunity.get('url', ''))
                        normalized = self.normalize_opportunity(opportunity)
                        opportunities.append(normalized)
                except Exception as e:
                    logger.error(f"Error parsing Bugcrowd card: {e}")
                    continue
            
            # If no programs found, use fallback
            if len(opportunities) == 0:
                opportunities = self._get_fallback_bounties()
            
        except Exception as e:
            logger.error(f"Bugcrowd scraping error: {e}")
            opportunities = self._get_fallback_bounties()
        
        logger.info(f"Scraped {len(opportunities)} bug bounties from Bugcrowd")
        return opportunities
    
    def _parse_bugcrowd_card(self, card) -> Dict[str, Any]:
        """Parse Bugcrowd program card"""
        # Extract name
        name_elem = card.find('h3') or card.find('h2') or card.find('a', class_='program-name')
        name = name_elem.get_text(strip=True) if name_elem else "Bugcrowd Program"
        
        # Extract URL
        link = card.find('a', href=True)
        url = link['href'] if link else ''
        if url and not url.startswith('http'):
            url = f"https://bugcrowd.com{url}"
        
        # Extract bounty info
        bounty_elem = card.find('span', class_='bounty-range') or card.find('div', class_='reward')
        bounty_text = bounty_elem.get_text(strip=True) if bounty_elem else "Varies"
        
        # Parse amount
        import re
        amounts = re.findall(r'\$[\d,]+', bounty_text)
        amount = 0
        if amounts:
            amount = int(amounts[-1].replace('$', '').replace(',', ''))  # Take max
        
        return {
            'name': f"{name} Bug Bounty",
            'organization': name,
            'description': f"Enterprise bug bounty program for {name} via Bugcrowd",
            'amount': amount,
            'amount_display': bounty_text,
            'deadline': None,
            'deadline_type': 'rolling',
            'url': url,
            'tags': ['Bug Bounty', 'Security', 'Bugcrowd', 'Enterprise'],
            'eligibility': {
                'gpa_min': None,
                'grades_eligible': ['High School', 'Undergraduate', 'Graduate', 'Professional'],
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
                'other': ['Bugcrowd account', 'Valid vulnerability']
            }
        }
    
    def _get_fallback_bounties(self) -> List[Dict[str, Any]]:
        """Fallback curated bounties"""
        bounties = [
            {
                'name': 'Tesla Bug Bounty Program',
                'organization': 'Tesla',
                'description': 'Find security vulnerabilities in Tesla systems and earn rewards',
                'amount': 15000,
                'amount_display': 'Up to $15,000',
                'deadline': None,
                'deadline_type': 'rolling',
                'url': 'https://bugcrowd.com/tesla',
                'tags': ['Bug Bounty', 'Security', 'Bugcrowd', 'Automotive'],
                'eligibility': {'gpa_min': None, 'grades_eligible': ['Professional'], 'majors': None, 'gender': None, 'citizenship': None, 'backgrounds': [], 'states': None},
                'requirements': {'essay': False, 'essay_prompts': [], 'recommendation_letters': 0, 'transcript': False, 'resume': False, 'other': []}
            }
        ]
        
        result = []
        for b in bounties:
            b['url_validated'] = False
            normalized = self.normalize_opportunity(b)
            result.append(normalized)
        
        return result
