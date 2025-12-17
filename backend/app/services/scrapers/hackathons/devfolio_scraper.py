"""
Devfolio Hackathon Scraper - PRODUCTION
India/Asia Hackathon Platform
FAANG-Level: Web scraping with comprehensive error handling
"""
from typing import List, Dict, Any
from datetime import datetime
import structlog
from bs4 import BeautifulSoup
from ..base_scraper import BaseScraper
from ..anti_scraping import anti_scraping_manager

logger = structlog.get_logger()


class DevfolioScraper(BaseScraper):
    """Production scraper for Devfolio hackathons"""
    
    def get_source_name(self) -> str:
        return "devfolio"
    
    def get_source_type(self) -> str:
        return "hackathon"
    
    async def scrape(self) -> List[Dict[str, Any]]:
        """
        Scrape hackathons from Devfolio
        Focus on India/Asia region
        """
        logger.info("Scraping Devfolio hackathons")
        
        opportunities = []
        
        try:
            url = 'https://devfolio.co/hackathons'
            
            # Rate limiting
            await anti_scraping_manager.wait_if_needed(url)
            headers = anti_scraping_manager.get_headers('devfolio.co')
            
            response = await self.client.get(url, headers=headers)
            
            if response.status_code == 403:
                anti_scraping_manager.mark_blocked('devfolio.co', 30)
                return []
            
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Find hackathon cards
            hackathon_cards = soup.find_all('div', class_='hackathon-card') or \
                            soup.find_all('article', class_='hackathon')
            
            for card in hackathon_cards[:25]:  # Limit to 25
                try:
                    opportunity = self._parse_devfolio_card(card)
                    if opportunity:
                        opportunity['url_validated'] = await self.validate_url(opportunity.get('url', ''))
                        normalized = self.normalize_opportunity(opportunity)
                        opportunities.append(normalized)
                except Exception as e:
                    logger.error(f"Error parsing Devfolio card: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Devfolio scraping error: {e}")
        
        logger.info(f"Scraped {len(opportunities)} hackathons from Devfolio")
        return opportunities
    
    def _parse_devfolio_card(self, card) -> Dict[str, Any]:
        """Parse Devfolio hackathon card"""
        # Extract name
        name_elem = card.find('h3') or card.find('h2') or card.find('a', class_='title')
        name = name_elem.get_text(strip=True) if name_elem else "Devfolio Hackathon"
        
        # Extract URL
        link = card.find('a', href=True)
        url = link['href'] if link else ''
        if url and not url.startswith('http'):
            url = f"https://devfolio.co{url}"
        
        # Extract description
        desc_elem = card.find('p', class_='description') or card.find('div', class_='summary')
        description = desc_elem.get_text(strip=True) if desc_elem else f"{name} on Devfolio"
        
        # Extract prize
        prize_elem = card.find('span', class_='prize') or card.find('div', class_='prize-pool')
        prize_text = prize_elem.get_text(strip=True) if prize_elem else "₹0"
        
        # Parse amount (handle INR)
        import re
        amounts = re.findall(r'[₹$]?[\d,]+', prize_text)
        prize_amount = 0
        if amounts:
            amount_str = amounts[0].replace('₹', '').replace('$', '').replace(',', '')
            try:
                prize_amount = int(amount_str)
                # Convert INR to USD (approximate)
                if '₹' in prize_text:
                    prize_amount = int(prize_amount / 83)  # Rough conversion
            except:
                pass
        
        # Extract deadline
        deadline_elem = card.find('time') or card.find('span', class_='deadline')
        deadline_text = deadline_elem.get_text(strip=True) if deadline_elem else None
        
        return {
            'name': name,
            'organization': 'Devfolio',
            'description': description,
            'amount': prize_amount,
            'amount_display': prize_text,
            'deadline': deadline_text,
            'deadline_type': 'fixed' if deadline_text else 'rolling',
            'url': url,
            'tags': ['Hackathon', 'Devfolio', 'India', 'Asia'],
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
                'other': ['Devfolio account', 'Team formation']
            }
        }
