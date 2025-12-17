"""
Devpost Hackathon Scraper - PRODUCTION
World's largest hackathon platform
FAANG-Level: API integration with fallback to web scraping
"""
from typing import List, Dict, Any
from datetime import datetime
import structlog
from bs4 import BeautifulSoup
from ..base_scraper import BaseScraper
from ..api_client import api_client_manager
from ..anti_scraping import anti_scraping_manager

logger = structlog.get_logger()


class DevpostScraper(BaseScraper):
    """Production scraper for Devpost hackathons"""
    
    def get_source_name(self) -> str:
        return "devpost"
    
    def get_source_type(self) -> str:
        return "hackathon"
    
    async def scrape(self) -> List[Dict[str, Any]]:
        """
        Scrape hackathons from Devpost
        Tries API first, falls back to web scraping
        """
        logger.info("Scraping Devpost hackathons")
        
        opportunities = []
        
        try:
            # Try API first
            hackathons = await api_client_manager.get_devpost_hackathons()
            
            if hackathons:
                for event in hackathons:
                    try:
                        opportunity = self._parse_api_event(event)
                        if opportunity:
                            opportunity['url_validated'] = await self.validate_url(opportunity.get('url', ''))
                            normalized = self.normalize_opportunity(opportunity)
                            opportunities.append(normalized)
                    except Exception as e:
                        logger.error(f"Error parsing Devpost API event: {e}")
                        continue
            else:
                # Fallback to web scraping
                opportunities = await self._scrape_web()
            
        except Exception as e:
            logger.error(f"Devpost scraping error: {e}")
            # Try web scraping as fallback
            opportunities = await self._scrape_web()
        
        logger.info(f"Scraped {len(opportunities)} hackathons from Devpost")
        return opportunities
    
    async def _scrape_web(self) -> List[Dict[str, Any]]:
        """Fallback web scraping"""
        opportunities = []
        
        try:
            url = 'https://devpost.com/hackathons'
            
            # Wait for rate limit
            await anti_scraping_manager.wait_if_needed(url)
            
            # Get headers
            headers = anti_scraping_manager.get_headers('devpost.com')
            
            response = await self.client.get(url, headers=headers)
            
            if response.status_code == 403:
                anti_scraping_manager.mark_blocked('devpost.com', 30)
                return []
            
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Find hackathon cards
            hackathon_cards = soup.find_all('div', class_='hackathon-tile') or \
                            soup.find_all('article', class_='hackathon')
            
            for card in hackathon_cards[:20]:  # Limit to 20
                try:
                    opportunity = self._parse_web_card(card)
                    if opportunity:
                        opportunity['url_validated'] = await self.validate_url(opportunity.get('url', ''))
                        normalized = self.normalize_opportunity(opportunity)
                        opportunities.append(normalized)
                except Exception as e:
                    logger.error(f"Error parsing Devpost card: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Devpost web scraping error: {e}")
        
        return opportunities
    
    def _parse_api_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Parse event from API"""
        name = event.get('title', 'Devpost Hackathon')
        url = event.get('url', '')
        description = event.get('tagline', '')
        
        # Parse prize
        prize_amount = event.get('prize_amount', 0)
        prize_display = f"${prize_amount:,}" if prize_amount else "Varies"
        
        # Parse deadline
        deadline = event.get('submission_period_dates', '')
        
        # Location
        location = event.get('location', 'Virtual')
        is_online = event.get('online', True)
        
        return {
            'name': name,
            'organization': 'Devpost',
            'description': description or f"{name} on Devpost",
            'amount': prize_amount,
            'amount_display': prize_display,
            'deadline': deadline,
            'deadline_type': 'fixed',
            'url': url,
            'tags': self._extract_tags(name, description, is_online),
            'eligibility': {
                'gpa_min': None,
                'grades_eligible': ['High School', 'Undergraduate', 'Graduate', 'Professional'],
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
                'other': ['Project submission', 'Demo video']
            }
        }
    
    def _parse_web_card(self, card) -> Dict[str, Any]:
        """Parse hackathon card from web"""
        # Extract name
        name_elem = card.find('h3') or card.find('h2') or card.find('a', class_='title')
        name = name_elem.get_text(strip=True) if name_elem else "Devpost Hackathon"
        
        # Extract URL
        link = card.find('a', href=True)
        url = link['href'] if link else ''
        if url and not url.startswith('http'):
            url = f"https://devpost.com{url}"
        
        # Extract description
        desc_elem = card.find('p', class_='tagline') or card.find('div', class_='description')
        description = desc_elem.get_text(strip=True) if desc_elem else f"{name} on Devpost"
        
        # Extract prize
        prize_elem = card.find('span', class_='prize') or card.find('div', class_='prize-amount')
        prize_text = prize_elem.get_text(strip=True) if prize_elem else "$0"
        
        import re
        amounts = re.findall(r'\d[\d,]*', prize_text)
        prize_amount = int(amounts[0].replace(',', '')) if amounts else 0
        
        return {
            'name': name,
            'organization': 'Devpost',
            'description': description,
            'amount': prize_amount,
            'amount_display': prize_text,
            'deadline': None,  # Would need to parse from card
            'deadline_type': 'rolling',
            'url': url,
            'tags': ['Hackathon', 'Devpost'],
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
                'other': []
            }
        }
    
    def _extract_tags(self, name: str, description: str, is_online: bool) -> List[str]:
        """Extract tags"""
        tags = ['Hackathon', 'Devpost']
        
        if is_online:
            tags.append('Virtual')
        
        text = (name + " " + description).lower()
        
        if 'ai' in text or 'ml' in text:
            tags.append('AI/ML')
        if 'web' in text:
            tags.append('Web')
        if 'mobile' in text:
            tags.append('Mobile')
        if 'blockchain' in text or 'web3' in text:
            tags.append('Blockchain')
        
        return tags
