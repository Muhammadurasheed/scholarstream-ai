"""
AngelHack Hackathon Scraper - PRODUCTION
Premier global hackathon organizer with corporate partnerships
"""
from typing import List, Dict, Any
from datetime import datetime
import structlog
from bs4 import BeautifulSoup
from ..base_scraper import BaseScraper
from ..anti_scraping import anti_scraping_manager

logger = structlog.get_logger()


class AngelHackScraper(BaseScraper):
    """Production scraper for AngelHack hackathons"""
    
    BASE_URL = "https://angelhack.com"
    
    def get_source_name(self) -> str:
        return "angelhack"
    
    def get_source_type(self) -> str:
        return "hackathon"
    
    async def scrape(self) -> List[Dict[str, Any]]:
        """Scrape hackathons from AngelHack"""
        logger.info("Scraping AngelHack hackathons")
        
        opportunities = []
        
        try:
            # AngelHack events page
            events_urls = [
                f"{self.BASE_URL}/events",
                f"{self.BASE_URL}/hackathons",
            ]
            
            for url in events_urls:
                try:
                    page_opps = await self._scrape_page(url)
                    opportunities.extend(page_opps)
                except Exception as e:
                    logger.warning(f"Failed to scrape {url}: {e}")
                    
        except Exception as e:
            logger.error(f"AngelHack scraping error: {e}")
        
        # Deduplicate by URL
        seen_urls = set()
        unique_opps = []
        for opp in opportunities:
            if opp.get('url') not in seen_urls:
                seen_urls.add(opp.get('url'))
                unique_opps.append(opp)
        
        logger.info(f"Scraped {len(unique_opps)} hackathons from AngelHack")
        return unique_opps
    
    async def _scrape_page(self, url: str) -> List[Dict[str, Any]]:
        """Scrape a single page"""
        opportunities = []
        
        await anti_scraping_manager.wait_if_needed(url)
        headers = anti_scraping_manager.get_headers('angelhack.com')
        
        response = await self.client.get(url, headers=headers)
        
        if response.status_code == 403:
            anti_scraping_manager.mark_blocked('angelhack.com', 30)
            return []
        
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'lxml')
        
        # Find event cards - AngelHack typically uses article or div with event classes
        cards = soup.find_all('article', class_=lambda c: c and 'event' in c.lower() if c else False) or \
                soup.find_all('div', class_=lambda c: c and 'hackathon' in c.lower() if c else False) or \
                soup.find_all('div', class_='event-card') or \
                soup.find_all('a', class_='event-link')
        
        # Also try generic card patterns
        if not cards:
            cards = soup.find_all('div', class_='card') or soup.find_all('article')
        
        for card in cards[:20]:
            try:
                opp = self._parse_card(card)
                if opp and opp.get('name'):
                    opportunities.append(self.normalize_opportunity(opp))
            except Exception as e:
                logger.error(f"Error parsing AngelHack card: {e}")
                
        return opportunities
    
    def _parse_card(self, card) -> Dict[str, Any]:
        """Parse event card"""
        # Extract name
        name_elem = card.find('h2') or card.find('h3') or card.find('h4') or card.find('span', class_='title')
        name = name_elem.get_text(strip=True) if name_elem else None
        
        if not name:
            return None
        
        # Extract URL
        if card.name == 'a':
            url = card.get('href', '')
        else:
            link = card.find('a', href=True)
            url = link['href'] if link else ''
            
        if url and not url.startswith('http'):
            url = f"{self.BASE_URL}{url}"
        
        # Extract description
        desc_elem = card.find('p') or card.find('div', class_='description')
        description = desc_elem.get_text(strip=True) if desc_elem else f"{name} - AngelHack Event"
        
        # Extract date
        date_elem = card.find('time') or card.find('span', class_='date')
        deadline = date_elem.get('datetime') or date_elem.get_text(strip=True) if date_elem else None
        
        # Extract location
        location_elem = card.find('span', class_='location') or card.find('div', class_='venue')
        location = location_elem.get_text(strip=True) if location_elem else 'Virtual'
        
        is_virtual = 'virtual' in location.lower() or 'online' in location.lower()
        
        return {
            'name': name,
            'organization': 'AngelHack',
            'description': description[:500] if len(description) > 500 else description,
            'amount': 0,  # AngelHack prizes vary
            'amount_display': 'Varies',
            'deadline': deadline,
            'deadline_type': 'fixed' if deadline else 'rolling',
            'url': url,
            'tags': self._extract_tags(name, description, is_virtual),
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
                'other': ['Team registration', 'Project submission']
            }
        }
    
    def _extract_tags(self, name: str, description: str, is_virtual: bool) -> List[str]:
        """Extract tags"""
        tags = ['Hackathon', 'AngelHack']
        
        if is_virtual:
            tags.append('Virtual')
        
        text = (name + " " + description).lower()
        
        if any(w in text for w in ['ai', 'ml', 'machine learning']):
            tags.append('AI/ML')
        if any(w in text for w in ['fintech', 'finance', 'banking']):
            tags.append('FinTech')
        if any(w in text for w in ['health', 'medical', 'biotech']):
            tags.append('HealthTech')
        if any(w in text for w in ['blockchain', 'web3', 'crypto']):
            tags.append('Web3')
        if any(w in text for w in ['climate', 'sustainability', 'green']):
            tags.append('CleanTech')
            
        return list(set(tags))
