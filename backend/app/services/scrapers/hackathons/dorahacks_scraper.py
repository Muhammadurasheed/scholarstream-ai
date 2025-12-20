"""
DoraHacks Hackathon Scraper - PRODUCTION
Major Web3 & AI hackathon platform with massive prizes
"""
from typing import List, Dict, Any
from datetime import datetime
import structlog
import httpx
from bs4 import BeautifulSoup
from ..base_scraper import BaseScraper
from ..anti_scraping import anti_scraping_manager

logger = structlog.get_logger()


class DoraHacksScraper(BaseScraper):
    """Production scraper for DoraHacks hackathons & bounties"""
    
    BASE_URL = "https://dorahacks.io"
    API_URL = "https://dorahacks.io/api/hackathon/list"
    
    def get_source_name(self) -> str:
        return "dorahacks"
    
    def get_source_type(self) -> str:
        return "hackathon"
    
    async def scrape(self) -> List[Dict[str, Any]]:
        """
        Scrape hackathons from DoraHacks
        Uses their API with web scraping fallback
        """
        logger.info("Scraping DoraHacks hackathons")
        
        opportunities = []
        
        try:
            # Try API first (DoraHacks has a public API)
            opportunities = await self._scrape_api()
            
            if not opportunities:
                # Fallback to web scraping
                opportunities = await self._scrape_web()
            
        except Exception as e:
            logger.error(f"DoraHacks scraping error: {e}")
            opportunities = await self._scrape_web()
        
        logger.info(f"Scraped {len(opportunities)} hackathons from DoraHacks")
        return opportunities
    
    async def _scrape_api(self) -> List[Dict[str, Any]]:
        """Try to use DoraHacks API"""
        opportunities = []
        
        try:
            headers = anti_scraping_manager.get_headers('dorahacks.io')
            headers['Accept'] = 'application/json'
            
            # DoraHacks API endpoint for hackathons
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.BASE_URL}/api/hackathon/buidl/list",
                    headers=headers,
                    params={'page': 1, 'limit': 50, 'status': 'ongoing'}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    hackathons = data.get('data', {}).get('list', []) or data.get('result', [])
                    
                    for hack in hackathons[:30]:
                        try:
                            opp = self._parse_api_hackathon(hack)
                            if opp:
                                opportunities.append(self.normalize_opportunity(opp))
                        except Exception as e:
                            logger.error(f"Error parsing DoraHacks API event: {e}")
                            
        except Exception as e:
            logger.warning(f"DoraHacks API failed, will try web: {e}")
            
        return opportunities
    
    async def _scrape_web(self) -> List[Dict[str, Any]]:
        """Fallback web scraping"""
        opportunities = []
        
        try:
            url = f"{self.BASE_URL}/hackathon"
            
            await anti_scraping_manager.wait_if_needed(url)
            headers = anti_scraping_manager.get_headers('dorahacks.io')
            
            response = await self.client.get(url, headers=headers)
            
            if response.status_code == 403:
                anti_scraping_manager.mark_blocked('dorahacks.io', 30)
                return []
            
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Find hackathon cards - DoraHacks uses various card structures
            cards = soup.find_all('div', class_='hackathon-card') or \
                    soup.find_all('a', class_='buidl-card') or \
                    soup.find_all('div', attrs={'data-hackathon': True})
            
            for card in cards[:25]:
                try:
                    opp = self._parse_web_card(card)
                    if opp:
                        opportunities.append(self.normalize_opportunity(opp))
                except Exception as e:
                    logger.error(f"Error parsing DoraHacks card: {e}")
                    
        except Exception as e:
            logger.error(f"DoraHacks web scraping error: {e}")
            
        return opportunities
    
    def _parse_api_hackathon(self, hack: Dict[str, Any]) -> Dict[str, Any]:
        """Parse hackathon from API response"""
        name = hack.get('name') or hack.get('title', 'DoraHacks Hackathon')
        
        # Build URL
        slug = hack.get('slug') or hack.get('id', '')
        url = f"{self.BASE_URL}/hackathon/{slug}" if slug else self.BASE_URL
        
        # Parse prize pool
        prize = hack.get('prize_pool') or hack.get('totalPrize') or 0
        if isinstance(prize, str):
            import re
            amounts = re.findall(r'[\d,]+', prize.replace(',', ''))
            prize = int(amounts[0]) if amounts else 0
        
        prize_display = f"${prize:,}" if prize else hack.get('prize_display', 'Varies')
        
        # Parse dates
        end_date = hack.get('end_time') or hack.get('deadline') or hack.get('submission_deadline')
        
        # Description
        description = hack.get('description') or hack.get('tagline') or f"{name} on DoraHacks"
        if len(description) > 500:
            description = description[:500] + "..."
        
        return {
            'name': name,
            'organization': 'DoraHacks',
            'description': description,
            'amount': prize if isinstance(prize, int) else 0,
            'amount_display': prize_display,
            'deadline': end_date,
            'deadline_type': 'fixed',
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
                'other': ['Project submission', 'Demo/Video']
            }
        }
    
    def _parse_web_card(self, card) -> Dict[str, Any]:
        """Parse hackathon card from web"""
        # Extract name
        name_elem = card.find('h3') or card.find('h2') or card.find('span', class_='title')
        name = name_elem.get_text(strip=True) if name_elem else "DoraHacks Hackathon"
        
        # Extract URL
        if card.name == 'a':
            url = card.get('href', '')
        else:
            link = card.find('a', href=True)
            url = link['href'] if link else ''
            
        if url and not url.startswith('http'):
            url = f"{self.BASE_URL}{url}"
        
        # Extract prize
        prize_elem = card.find('span', class_='prize') or card.find('div', class_='prize-pool')
        prize_text = prize_elem.get_text(strip=True) if prize_elem else "$0"
        
        import re
        amounts = re.findall(r'[\d,]+', prize_text.replace(',', ''))
        prize_amount = int(amounts[0]) if amounts else 0
        
        return {
            'name': name,
            'organization': 'DoraHacks',
            'description': f"{name} - Web3/AI hackathon on DoraHacks",
            'amount': prize_amount,
            'amount_display': prize_text,
            'deadline': None,
            'deadline_type': 'rolling',
            'url': url,
            'tags': ['Hackathon', 'DoraHacks', 'Web3', 'Blockchain'],
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
        """Extract tags from hackathon data"""
        tags = ['Hackathon', 'DoraHacks']
        
        # Add explicit tags from API
        api_tags = hack.get('tags', []) or hack.get('tracks', [])
        if api_tags:
            tags.extend([str(t) for t in api_tags[:5]])
        
        # Infer from content
        text = (name + " " + description).lower()
        
        if any(w in text for w in ['web3', 'blockchain', 'crypto', 'defi']):
            tags.append('Web3')
        if any(w in text for w in ['ai', 'ml', 'machine learning', 'gpt', 'llm']):
            tags.append('AI/ML')
        if 'nft' in text:
            tags.append('NFT')
        if any(w in text for w in ['dao', 'governance']):
            tags.append('DAO')
        if 'zk' in text or 'zero knowledge' in text:
            tags.append('ZK')
            
        return list(set(tags))
