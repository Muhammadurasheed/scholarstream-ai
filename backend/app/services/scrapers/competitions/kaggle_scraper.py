"""
Kaggle Competition Scraper - PRODUCTION
Official API - Highly Reliable
FAANG-Level: Uses Kaggle's official API with comprehensive error handling
"""
from typing import List, Dict, Any
from datetime import datetime
import structlog
from ..base_scraper import BaseScraper
from ..api_client import api_client_manager

logger = structlog.get_logger()


class KaggleScraper(BaseScraper):
    """Production scraper for Kaggle competitions"""
    
    def get_source_name(self) -> str:
        return "kaggle"
    
    def get_source_type(self) -> str:
        return "competition"
    
    async def scrape(self) -> List[Dict[str, Any]]:
        """
        Scrape competitions from Kaggle
        Uses official Kaggle API - gold standard reliability
        """
        logger.info("Scraping Kaggle competitions")
        
        opportunities = []
        
        try:
            # Get competitions from official API
            competitions = await api_client_manager.get_kaggle_competitions()
            
            for comp in competitions:
                try:
                    opportunity = self._parse_kaggle_competition(comp)
                    if opportunity:
                        opportunity['url_validated'] = await self.validate_url(opportunity.get('url', ''))
                        normalized = self.normalize_opportunity(opportunity)
                        opportunities.append(normalized)
                except Exception as e:
                    logger.error(f"Error parsing Kaggle competition: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Kaggle API error: {e}")
        
        logger.info(f"Scraped {len(opportunities)} competitions from Kaggle")
        return opportunities
    
    def _parse_kaggle_competition(self, comp: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Kaggle competition data"""
        name = comp.get('title', 'Kaggle Competition')
        url = f"https://www.kaggle.com/c/{comp.get('ref', '')}"
        description = comp.get('description', '')
        
        # Parse prize
        reward = comp.get('reward', '')
        prize_amount = self._parse_prize(reward)
        prize_display = reward if reward else 'Knowledge Points'
        
        # Parse deadline
        deadline = comp.get('deadline', '')
        
        # Category/tags
        category = comp.get('category', 'General')
        tags = self._extract_tags(name, description, category)
        
        return {
            'name': name,
            'organization': 'Kaggle',
            'description': description or f"{name} - Data Science Competition",
            'amount': prize_amount,
            'amount_display': prize_display,
            'deadline': deadline,
            'deadline_type': 'fixed',
            'url': url,
            'tags': tags,
            'eligibility': {
                'gpa_min': None,
                'grades_eligible': ['High School', 'Undergraduate', 'Graduate', 'Professional'],
                'majors': ['Data Science', 'Computer Science', 'Statistics', 'Mathematics'],
                'gender': None,
                'citizenship': None,  # Kaggle is international
                'backgrounds': [],
                'states': None
            },
            'requirements': {
                'essay': False,
                'essay_prompts': [],
                'recommendation_letters': 0,
                'transcript': False,
                'resume': False,
                'other': ['Kaggle account', 'Model submission', 'Code notebook']
            }
        }
    
    def _parse_prize(self, reward: str) -> int:
        """Parse prize amount from reward string"""
        if not reward:
            return 0
        
        import re
        # Extract numbers like $100,000 or 100000
        amounts = re.findall(r'\$?[\d,]+', reward)
        if amounts:
            amount_str = amounts[0].replace('$', '').replace(',', '')
            try:
                return int(amount_str)
            except:
                return 0
        return 0
    
    def _extract_tags(self, name: str, description: str, category: str) -> List[str]:
        """Extract relevant tags"""
        tags = ['Competition', 'Data Science', 'Kaggle']
        
        # Add category
        if category:
            tags.append(category)
        
        text = (name + " " + description).lower()
        
        # Technology tags
        if any(word in text for word in ['nlp', 'natural language', 'text']):
            tags.append('NLP')
        if any(word in text for word in ['computer vision', 'image', 'cv']):
            tags.append('Computer Vision')
        if any(word in text for word in ['time series', 'forecasting', 'prediction']):
            tags.append('Time Series')
        if any(word in text for word in ['tabular', 'structured']):
            tags.append('Tabular Data')
        if any(word in text for word in ['deep learning', 'neural']):
            tags.append('Deep Learning')
        
        return tags
