"""
Devpost Scraper - PRODUCTION API VERSION
Uses hidden internal API for reliable data access
"""

from typing import List, Dict, Any
from datetime import datetime, timedelta
import structlog
import re

from .base_scraper import BaseScraper

logger = structlog.get_logger()


class DevpostScraper(BaseScraper):
    """Scrape hackathons from Devpost using internal API"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://devpost.com"
        # The API endpoint discovered in JS source
        self.api_url = "https://devpost.com/api/hackathons"
    
    def get_source_name(self) -> str:
        return "devpost"
    
    async def scrape(self) -> List[Dict[str, Any]]:
        """
        Scrape active and upcoming hackathons from Devpost API
        """
        logger.info("Starting Devpost scraping via API")
        
        opportunities = []
        
        # Scrape multiple status pages
        statuses = ['open', 'upcoming']
        
        for status in statuses:
            try:
                page_opps = await self._fetch_from_api(status)
                opportunities.extend(page_opps)
            except Exception as e:
                logger.error(f"Failed to scrape {status} page", error=str(e))
        
        # Deduplicate
        unique_opps = {opp['url']: opp for opp in opportunities}.values()
        
        logger.info("Devpost scraping complete", count=len(unique_opps))
        return list(unique_opps)
    
    async def _fetch_from_api(self, status: str) -> List[Dict[str, Any]]:
        """Fetch hackathons from API for a specific status"""
        
        # Fetch first 2 pages (approx 60 hackathons)
        all_hackathons = []
        
        for page in range(1, 4):
            params = {
                'status[]': status,
                'order': 'submission_period',
                'page': page,
                'per_page': 20  # Appears to be default
            }
            
            # API expects standard browser headers
            headers = {
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': f'https://devpost.com/hackathons?status[]={status}'
            }
            
            response = await self._fetch_with_retry(self.api_url, params=params, headers=headers)
            
            if not response or response.status_code != 200:
                logger.warning(f"Failed to fetch Devpost API page {page}: {response.status_code if response else 'No response'}")
                break
                
            try:
                data = response.json()
                
                # Check for hackathons in response
                if 'hackathons' not in data or not data['hackathons']:
                    break
                
                for item in data['hackathons']:
                    opp = self._parse_api_item(item, status)
                    if opp:
                        all_hackathons.append(opp)
                        
                # Check if we have more pages
                meta = data.get('meta', {})
                if meta.get('current_page') >= meta.get('total_pages', 1):
                    break
                    
            except Exception as e:
                logger.error(f"Error parsing Devpost API response: {e}")
                break
        
        return all_hackathons
    
    def _parse_api_item(self, item: Dict[str, Any], status: str) -> Dict[str, Any]:
        """Parse single API hackathon item"""
        
        try:
            title = item.get('title', 'Unknown Hackathon')
            url = item.get('url', '')
            if url and not url.startswith('http'):
                url = self.base_url + url
                
            # Extract organization
            organization = "Unknown"
            if item.get('organization'):
                organization = item.get('organization', {}).get('name', 'Unknown')
            elif item.get('displayed_host'):
                 organization = item.get('displayed_host')
            
            # Extract prize info
            prize_amount = item.get('prize_amount', '$0')
            amount, amount_display = self._parse_prize(prize_amount)
            
            # Extract dates
            submission_period_dates = item.get('submission_period_dates', '')
            
            # Estimate deadline
            deadline_str = None
            urgency = 'future'
            
            if submission_period_dates and 'until' in submission_period_dates:
                 # Format: "Sep 25 - Nov 15, 2024" or similar
                 # For now, let's just use a reasonable default based on status
                 # Parsing "Nov 15, 2024" is possible but format varies
                 pass
            
            # Fallback deadline logic
            time_left = item.get('time_left_to_submission', '')
            if time_left:
                deadline, _, urgency = self._parse_deadline(time_left)
            else:
                 deadline = (datetime.now() + timedelta(days=45)).isoformat()
                 urgency = 'future'
            
            # Locations
            locations = []
            if item.get('displayed_location', {}).get('location'):
                locations.append(item.get('displayed_location').get('location'))
            else:
                locations.append("Online")
                
            return {
                'type': 'hackathon',
                'name': title,
                'organization': organization,
                'amount': amount,
                'amount_display': amount_display,
                'deadline': deadline,
                'deadline_type': 'fixed',
                'url': url,
                'source_url': url,  # Frontend expects source_url
                'source_type': 'devpost',  # Proper source type enum
                'source': 'devpost',
                'urgency': urgency,
                'tags': item.get('themes', []) + ['Hackathon'],
                # Logo extraction - Devpost API provides thumbnail
                'logo_url': item.get('thumbnail_url') or item.get('organization', {}).get('logo_url', ''),
                # Participants count from API
                'participants_count': item.get('registrations_count', 0),
                'eligibility': {
                    'students_only': False,
                    'grade_levels': [],
                    'majors': ['Computer Science'],
                    'gpa_min': None,
                    'citizenship': ['Any'],
                    'geographic': locations
                },
                'requirements': {
                    'application_type': 'submission',
                    'estimated_time': '48 hours',
                    'skills_needed': ['Coding'],
                    'team_allowed': True,
                    'team_size_max': item.get('max_team_size', 4),
                    'essay_required': False
                },
                'description': item.get('tagline', '') or f"{title} - {organization}. {submission_period_dates}",
                'competition_level': 'Medium',
                'discovered_at': datetime.utcnow().isoformat() + 'Z',
                'last_verified': datetime.utcnow().isoformat() + 'Z'  # Set current time as verified
            }
        except Exception as e:
            logger.error(f"Error parsing API item: {e}", item_title=item.get('title'))
            return None
            
    def _parse_prize(self, prize_text: str) -> tuple:
        """Parse prize amount from text"""
        if not prize_text:
            return 0, "$0"
        
        # Extract numbers
        numbers = re.findall(r'\d+[,\d]*', str(prize_text))
        if numbers:
            amount_str = numbers[0].replace(',', '')
            try:
                amount = int(amount_str)
                return amount, prize_text
            except:
                pass
        
        return 0, prize_text
    
    def _parse_deadline(self, deadline_text: str) -> tuple:
        """Parse deadline from time left text"""
        # "14 days left" or "about 1 month left"
        if not deadline_text:
             return (datetime.now() + timedelta(days=30)).isoformat(), 'fixed', 'future'
             
        days_match = re.search(r'(\d+)\s*days?', deadline_text)
        hours_match = re.search(r'(\d+)\s*hours?', deadline_text)
        
        days_left = 30
        urgency = 'future'
        
        if days_match:
            days_left = int(days_match.group(1))
        elif hours_match:
            days_left = 0 # < 1 day
            
        deadline = (datetime.now() + timedelta(days=days_left)).isoformat()
        
        if days_left <= 7:
            urgency = 'urgent'
        elif days_left <= 30:
            urgency = 'this_month'
            
        return deadline, 'fixed', urgency
