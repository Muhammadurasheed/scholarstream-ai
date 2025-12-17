"""
HackerOne Bug Bounty Scraper - PRODUCTION
Leading Bug Bounty Platform with Public API
FAANG-Level: Uses HackerOne's public directory API
"""
from typing import List, Dict, Any
from datetime import datetime
import structlog
from ..base_scraper import BaseScraper
from ..anti_scraping import anti_scraping_manager

logger = structlog.get_logger()


class HackerOneScraper(BaseScraper):
    """Production scraper for HackerOne bug bounties"""
    
    def get_source_name(self) -> str:
        return "hackerone"
    
    def get_source_type(self) -> str:
        return "bounty"
    
    async def scrape(self) -> List[Dict[str, Any]]:
        """
        Scrape bug bounties from HackerOne
        Uses public directory API
        """
        logger.info("Scraping HackerOne bug bounties")
        
        opportunities = []
        
        try:
            # HackerOne public directory API
            url = 'https://hackerone.com/directory/programs.json'
            
            # Rate limiting
            await anti_scraping_manager.wait_if_needed(url)
            headers = anti_scraping_manager.get_headers('hackerone.com')
            
            response = await self.client.get(url, headers=headers)
            
            if response.status_code == 403:
                anti_scraping_manager.mark_blocked('hackerone.com', 30)
                return []
            
            response.raise_for_status()
            
            data = response.json()
            programs = data.get('data', [])
            
            for program in programs[:50]:  # Limit to top 50
                try:
                    opportunity = self._parse_hackerone_program(program)
                    if opportunity:
                        opportunity['url_validated'] = await self.validate_url(opportunity.get('url', ''))
                        normalized = self.normalize_opportunity(opportunity)
                        opportunities.append(normalized)
                except Exception as e:
                    logger.error(f"Error parsing HackerOne program: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"HackerOne API error: {e}")
        
        logger.info(f"Scraped {len(opportunities)} bug bounties from HackerOne")
        return opportunities
    
    def _parse_hackerone_program(self, program: Dict[str, Any]) -> Dict[str, Any]:
        """Parse HackerOne program data"""
        attributes = program.get('attributes', {})
        
        name = attributes.get('name', 'HackerOne Bug Bounty')
        handle = attributes.get('handle', '')
        url = f"https://hackerone.com/{handle}" if handle else ''
        
        # Bounty info
        offers_bounties = attributes.get('offers_bounties', False)
        if not offers_bounties:
            return None  # Skip programs without bounties
        
        # Parse bounty range
        bounty_min = attributes.get('base_bounty', 0)
        bounty_max = attributes.get('max_bounty', 0)
        
        amount = bounty_max if bounty_max else bounty_min
        if bounty_min and bounty_max:
            amount_display = f"${bounty_min:,} - ${bounty_max:,}"
        elif amount:
            amount_display = f"Up to ${amount:,}"
        else:
            amount_display = "Varies"
        
        # Description
        submission_state = attributes.get('submission_state', 'open')
        if submission_state != 'open':
            return None  # Skip closed programs
        
        # Tags
        tags = self._extract_tags(name, attributes)
        
        return {
            'name': f"{name} Bug Bounty Program",
            'organization': name,
            'description': f"Bug bounty program for {name}. Find security vulnerabilities and earn rewards.",
            'amount': amount,
            'amount_display': amount_display,
            'deadline': None,  # Bug bounties are ongoing
            'deadline_type': 'rolling',
            'url': url,
            'tags': tags,
            'eligibility': {
                'gpa_min': None,
                'grades_eligible': ['High School', 'Undergraduate', 'Graduate', 'Professional'],
                'majors': ['Computer Science', 'Cybersecurity', 'Engineering'],
                'gender': None,
                'citizenship': None,  # Global
                'backgrounds': [],
                'states': None
            },
            'requirements': {
                'essay': False,
                'essay_prompts': [],
                'recommendation_letters': 0,
                'transcript': False,
                'resume': False,
                'other': ['HackerOne account', 'Valid vulnerability report', 'Responsible disclosure']
            }
        }
    
    def _extract_tags(self, name: str, attributes: Dict[str, Any]) -> List[str]:
        """Extract relevant tags"""
        tags = ['Bug Bounty', 'Security', 'HackerOne']
        
        # Add industry
        industry = attributes.get('industry', '')
        if industry:
            tags.append(industry)
        
        # Add company type
        if any(word in name.lower() for word in ['crypto', 'blockchain', 'defi']):
            tags.append('Cryptocurrency')
        if any(word in name.lower() for word in ['fintech', 'bank', 'payment']):
            tags.append('Fintech')
        if any(word in name.lower() for word in ['social', 'media']):
            tags.append('Social Media')
        if any(word in name.lower() for word in ['cloud', 'saas']):
            tags.append('Cloud/SaaS')
        
        return tags
