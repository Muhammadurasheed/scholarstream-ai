"""
HackQuest Hackathon Scraper - PRODUCTION
Web3 education and hackathon platform
"""
from typing import List, Dict, Any
from datetime import datetime
import structlog
import httpx
from bs4 import BeautifulSoup
from ..base_scraper import BaseScraper
from ..anti_scraping import anti_scraping_manager

logger = structlog.get_logger()


class HackQuestScraper(BaseScraper):
    """Production scraper for HackQuest hackathons"""
    
    BASE_URL = "https://www.hackquest.io"
    
    def get_source_name(self) -> str:
        return "hackquest"
    
    def get_source_type(self) -> str:
        return "hackathon"
    
    async def scrape(self) -> List[Dict[str, Any]]:
        """Scrape hackathons from HackQuest"""
        logger.info("Scraping HackQuest hackathons")
        
        opportunities = []
        
        try:
            # Try API first
            opportunities = await self._scrape_api()
            
            if not opportunities:
                opportunities = await self._scrape_web()
                
        except Exception as e:
            logger.error(f"HackQuest scraping error: {e}")
            opportunities = await self._scrape_web()
        
        logger.info(f"Scraped {len(opportunities)} hackathons from HackQuest")
        return opportunities
    
    async def _scrape_api(self) -> List[Dict[str, Any]]:
        """Try HackQuest API"""
        opportunities = []
        
        try:
            headers = anti_scraping_manager.get_headers('hackquest.io')
            headers['Accept'] = 'application/json'
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                # HackQuest hackathon API
                response = await client.get(
                    f"{self.BASE_URL}/api/hackathons",
                    headers=headers,
                    params={'status': 'ongoing', 'limit': 50}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    hackathons = data.get('data', []) or data.get('hackathons', []) or data
                    
                    if isinstance(hackathons, list):
                        for hack in hackathons[:30]:
                            try:
                                opp = self._parse_api_hackathon(hack)
                                if opp:
                                    opportunities.append(self.normalize_opportunity(opp))
                            except Exception as e:
                                logger.error(f"Error parsing HackQuest API event: {e}")
                                
        except Exception as e:
            logger.warning(f"HackQuest API failed: {e}")
            
        return opportunities
    
    async def _scrape_web(self) -> List[Dict[str, Any]]:
        """Fallback web scraping"""
        opportunities = []
        
        try:
            url = f"{self.BASE_URL}/hackathon"
            
            await anti_scraping_manager.wait_if_needed(url)
            headers = anti_scraping_manager.get_headers('hackquest.io')
            
            response = await self.client.get(url, headers=headers)
            
            if response.status_code == 403:
                anti_scraping_manager.mark_blocked('hackquest.io', 30)
                return []
            
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Find hackathon cards
            cards = soup.find_all('div', class_=lambda c: c and 'hackathon' in c.lower() if c else False) or \
                    soup.find_all('a', class_=lambda c: c and 'card' in c.lower() if c else False) or \
                    soup.find_all('article')
            
            for card in cards[:25]:
                try:
                    opp = self._parse_web_card(card)
                    if opp and opp.get('name'):
                        opportunities.append(self.normalize_opportunity(opp))
                except Exception as e:
                    logger.error(f"Error parsing HackQuest card: {e}")
                    
        except Exception as e:
            logger.error(f"HackQuest web scraping error: {e}")
            
        return opportunities
    
    def _parse_api_hackathon(self, hack: Dict[str, Any]) -> Dict[str, Any]:
        """Parse hackathon from API"""
        name = hack.get('name') or hack.get('title', 'HackQuest Hackathon')
        
        slug = hack.get('slug') or hack.get('id', '')
        url = f"{self.BASE_URL}/hackathon/{slug}" if slug else self.BASE_URL
        
        prize = hack.get('prize_pool') or hack.get('totalPrize') or 0
        if isinstance(prize, str):
            import re
            amounts = re.findall(r'[\d,]+', prize.replace(',', ''))
            prize = int(amounts[0]) if amounts else 0
        
        prize_display = f"${prize:,}" if prize else 'Varies'
        
        deadline = hack.get('end_time') or hack.get('deadline')
        description = hack.get('description') or hack.get('intro') or f"{name} on HackQuest"
        
        return {
            'name': name,
            'organization': 'HackQuest',
            'description': description[:500] if len(description) > 500 else description,
            'amount': prize if isinstance(prize, int) else 0,
            'amount_display': prize_display,
            'deadline': deadline,
            'deadline_type': 'fixed' if deadline else 'rolling',
            'url': url,
            'tags': self._extract_tags(hack, name, description),
            'eligibility': {
                'gpa_min': None,
                'grades_eligible': ['High School', 'Undergraduate', 'Graduate', 'Professional'],
                'majors': None,
                'gender': None,
                'citizenship': 'International',
                'backgrounds': [],
                'states': None
            },
            'requirements': {
                'essay': False,
                'essay_prompts': [],
                'recommendation_letters': 0,
                'transcript': False,
                'resume': False,
                'other': ['Project submission']
            }
        }
    
    def _parse_web_card(self, card) -> Dict[str, Any]:
        """Parse card from web"""
        name_elem = card.find('h2') or card.find('h3') or card.find('span', class_='title')
        name = name_elem.get_text(strip=True) if name_elem else None
        
        if not name:
            return None
        
        if card.name == 'a':
            url = card.get('href', '')
        else:
            link = card.find('a', href=True)
            url = link['href'] if link else ''
            
        if url and not url.startswith('http'):
            url = f"{self.BASE_URL}{url}"
        
        desc_elem = card.find('p')
        description = desc_elem.get_text(strip=True) if desc_elem else f"{name} on HackQuest"
        
        return {
            'name': name,
            'organization': 'HackQuest',
            'description': description,
            'amount': 0,
            'amount_display': 'Varies',
            'deadline': None,
            'deadline_type': 'rolling',
            'url': url,
            'tags': ['Hackathon', 'HackQuest', 'Web3', 'Learning'],
            'eligibility': {
                'gpa_min': None,
                'grades_eligible': ['High School', 'Undergraduate', 'Graduate', 'Professional'],
                'majors': None,
                'gender': None,
                'citizenship': 'International',
                'backgrounds': [],
                'states': None
            },
            'requirements': {
                'essay': False,
                'essay_prompts': [],
                'recommendation_letters': 0,
                'transcript': False,
                'resume': False,
                'other': []
            }
        }
    
    def _extract_tags(self, hack: Dict, name: str, description: str) -> List[str]:
        """Extract tags"""
        tags = ['Hackathon', 'HackQuest', 'Web3']
        
        api_tags = hack.get('tags', []) or hack.get('tracks', [])
        if api_tags:
            tags.extend([str(t) for t in api_tags[:5]])
        
        text = (name + " " + description).lower()
        
        if any(w in text for w in ['solidity', 'smart contract', 'ethereum']):
            tags.append('Solidity')
        if any(w in text for w in ['rust', 'solana']):
            tags.append('Solana')
        if any(w in text for w in ['move', 'sui', 'aptos']):
            tags.append('Move')
        if any(w in text for w in ['ai', 'ml', 'llm']):
            tags.append('AI/ML')
            
        return list(set(tags))
