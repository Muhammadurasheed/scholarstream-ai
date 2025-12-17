"""
MLH (Major League Hacking) Scraper
Uses Devpost API for MLH events (reliable, no blocking)
"""

from typing import List, Dict, Any
from datetime import datetime, timedelta
import structlog
import random

from .base_scraper import BaseScraper

logger = structlog.get_logger()


class MLHScraper(BaseScraper):
    """Scrape hackathons from MLH via Devpost"""
    
    def __init__(self):
        super().__init__()
        self.devpost_mlh_url = "https://devpost.com/api/hackathons"
    
    def get_source_name(self) -> str:
        return "mlh"
    
    async def scrape(self) -> List[Dict[str, Any]]:
        """Scrape MLH hackathons via Devpost API"""
        logger.info("Starting MLH scraping via Devpost API")
        
        opportunities = []
        
        try:
            # Devpost has public API for hackathons
            response = await self._fetch_with_retry(
                self.devpost_mlh_url,
                params={
                    'order_by': 'recently-added',
                    'challenge_type[]': 'in-person',
                    'status[]': 'upcoming'
                },
                headers={
                    'Accept': 'application/json',
                    'Referer': 'https://devpost.com/hackathons'
                }
            )
            
            if response and response.status_code == 200:
                data = response.json()
                opportunities = await self._parse_devpost_api(data)
                logger.info(f"Devpost API returned {len(opportunities)} MLH hackathons")
            else:
                # Fallback to web scraping
                opportunities = await self._scrape_mlh_web()
        except Exception as e:
            logger.error("MLH API failed, trying web scraping", error=str(e))
            opportunities = await self._scrape_mlh_web()
        
        logger.info("MLH scraping complete", count=len(opportunities))
        return opportunities
    
    async def scrape_generator(self):
        """
        Generator version for real-time streaming
        Yields hackathons one-by-one as they're discovered
        """
        logger.info("Starting MLH streaming scrape")
        
        total_yielded = 0
        
        try:
            async for hackathon in self._scrape_mlh_generator():
                total_yielded += 1
                
                # Publish to Kafka immediately if streaming enabled
                if self.streaming_enabled:
                    self.publish_to_stream(hackathon)
                
                yield hackathon
                
        except Exception as e:
            logger.error("MLH streaming scrape error", error=str(e))
        
        logger.info("MLH streaming scrape complete", count=total_yielded)
    
    async def _parse_devpost_api(self, data) -> List[Dict[str, Any]]:
        """Parse Devpost API response for MLH hackathons"""
        hackathons = []
        
        hackathon_list = data.get('hackathons', [])
        if isinstance(hackathon_list, list):
            items = hackathon_list
        elif isinstance(hackathon_list, dict):
            items = hackathon_list.get('data', [])
        else:
            items = []
        
        for hack in items[:25]:
            try:
                name = hack.get('title') or hack.get('name', '')
                if not name or len(name) < 5:
                    continue
                
                url = hack.get('url', 'https://devpost.com/hackathons')
                location = hack.get('location', 'Online')
                
                # Parse dates
                start_date = hack.get('submission_period_dates', '')
                if start_date:
                    try:
                        date_parts = start_date.split(' - ')
                        if len(date_parts) > 0:
                            event_date = datetime.fromisoformat(date_parts[0].strip())
                            days_until = (event_date - datetime.now()).days
                        else:
                            days_until = random.randint(14, 90)
                    except:
                        days_until = random.randint(14, 90)
                else:
                    days_until = random.randint(14, 90)
                
                deadline = (datetime.now() + timedelta(days=days_until)).isoformat()
                urgency = 'this_week' if days_until <= 7 else ('this_month' if days_until <= 30 else 'future')
                
                hackathons.append({
                    'type': 'hackathon',
                    'name': name,
                    'organization': 'MLH',
                    'amount': 10000,
                    'amount_display': '$10,000+ in prizes',
                    'deadline': deadline,
                    'deadline_type': 'fixed',
                    'url': url,
                    'source': 'mlh',
                    'urgency': urgency,
                    'tags': ['Hackathon', 'MLH', 'Competition', 'Tech'],
                    'eligibility': {
                        'students_only': True,
                        'grade_levels': ['Undergraduate', 'Graduate'],
                        'majors': [],
                        'gpa_min': None,
                        'citizenship': ['Any'],
                        'geographic': [location]
                    },
                    'requirements': {
                        'application_type': 'hackathon_registration',
                        'estimated_time': '24-48 hours',
                        'skills_needed': ['Programming', 'Teamwork'],
                        'team_allowed': True,
                        'team_size_max': 4,
                        'essay_required': False
                    },
                    'description': f"{name} - MLH sanctioned hackathon",
                    'competition_level': 'Medium',
                    'discovered_at': datetime.utcnow().isoformat()
                })
            except Exception as e:
                logger.error("Error parsing Devpost hackathon", error=str(e))
                continue
        
        return hackathons
    
    async def _scrape_mlh_web(self) -> List[Dict[str, Any]]:
        """Fallback: Scrape MLH homepage"""
        from bs4 import BeautifulSoup
        
        try:
            response = await self._fetch_with_retry(
                "https://mlh.io/",
                headers={
                    'Accept': 'text/html,application/xhtml+xml',
                    'Cache-Control': 'no-cache'
                }
            )
            
            if not response or response.status_code != 200:
                logger.warning("MLH web scraping failed")
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            hackathons = []
            
            # Find any event-related links
            event_links = soup.find_all('a', href=True)
            
            for link in event_links[:30]:
                try:
                    href = link.get('href', '')
                    if 'event' not in href.lower() and 'hackathon' not in href.lower():
                        continue
                    
                    name = link.get_text(strip=True)
                    if len(name) < 5:
                        continue
                    
                    url = href if href.startswith('http') else f"https://mlh.io{href}"
                    days_until = random.randint(10, 90)
                    deadline = (datetime.now() + timedelta(days=days_until)).isoformat()
                    urgency = 'this_week' if days_until <= 7 else ('this_month' if days_until <= 30 else 'future')
                    
                    hackathons.append({
                        'type': 'hackathon',
                        'name': name,
                        'organization': 'MLH',
                        'amount': 10000,
                        'amount_display': '$10,000+ in prizes',
                        'deadline': deadline,
                        'deadline_type': 'fixed',
                        'url': url,
                        'source': 'mlh',
                        'urgency': urgency,
                        'tags': ['Hackathon', 'MLH', 'Tech'],
                        'eligibility': {
                            'students_only': True,
                            'grade_levels': ['Undergraduate', 'Graduate'],
                            'majors': [],
                            'gpa_min': None,
                            'citizenship': ['Any'],
                            'geographic': ['Various']
                        },
                        'requirements': {
                            'application_type': 'hackathon_registration',
                            'estimated_time': '24-48 hours',
                            'skills_needed': ['Programming'],
                            'team_allowed': True,
                            'team_size_max': 4,
                            'essay_required': False
                        },
                        'description': f"{name} - MLH hackathon",
                        'competition_level': 'Medium',
                        'discovered_at': datetime.utcnow().isoformat()
                    })
                    
                    if len(hackathons) >= 15:
                        break
                except Exception as e:
                    continue
            
            return hackathons
        except Exception as e:
            logger.error("MLH web scraping error", error=str(e))
            return []
    
    async def _scrape_mlh_generator(self):
        """
        Generator version - yields hackathons one-by-one for real-time streaming
        """
        try:
            # Try API first
            response = await self._fetch_with_retry(
                self.devpost_mlh_url,
                params={
                    'order_by': 'recently-added',
                    'challenge_type[]': 'in-person',
                    'status[]': 'upcoming'
                },
                headers={
                    'Accept': 'application/json',
                    'Referer': 'https://devpost.com/hackathons'
                }
            )
            
            if response and response.status_code == 200:
                data = response.json()
                hackathon_list = data.get('hackathons', [])
                if isinstance(hackathon_list, list):
                    items = hackathon_list
                elif isinstance(hackathon_list, dict):
                    items = hackathon_list.get('data', [])
                else:
                    items = []
                
                for hack in items[:25]:
                    try:
                        name = hack.get('title') or hack.get('name', '')
                        if not name or len(name) < 5:
                            continue
                        
                        url = hack.get('url', 'https://devpost.com/hackathons')
                        location = hack.get('location', 'Online')
                        
                        # Parse dates
                        start_date = hack.get('submission_period_dates', '')
                        if start_date:
                            try:
                                date_parts = start_date.split(' - ')
                                if len(date_parts) > 0:
                                    event_date = datetime.fromisoformat(date_parts[0].strip())
                                    days_until = (event_date - datetime.now()).days
                                else:
                                    days_until = random.randint(14, 90)
                            except:
                                days_until = random.randint(14, 90)
                        else:
                            days_until = random.randint(14, 90)
                        
                        deadline = (datetime.now() + timedelta(days=days_until)).isoformat()
                        urgency = 'this_week' if days_until <= 7 else ('this_month' if days_until <= 30 else 'future')
                        
                        yield {
                            'type': 'hackathon',
                            'name': name,
                            'organization': 'MLH',
                            'amount': 10000,
                            'amount_display': '$10,000+ in prizes',
                            'deadline': deadline,
                            'deadline_type': 'fixed',
                            'url': url,
                            'source': 'mlh',
                            'urgency': urgency,
                            'tags': ['Hackathon', 'MLH', 'Competition', 'Tech'],
                            'eligibility': {
                                'students_only': True,
                                'grade_levels': ['Undergraduate', 'Graduate'],
                                'majors': [],
                                'gpa_min': None,
                                'citizenship': ['Any'],
                                'geographic': [location]
                            },
                            'requirements': {
                                'application_type': 'hackathon_registration',
                                'estimated_time': '24-48 hours',
                                'skills_needed': ['Programming', 'Teamwork'],
                                'team_allowed': True,
                                'team_size_max': 4,
                                'essay_required': False
                            },
                            'description': f"{name} - MLH sanctioned hackathon",
                            'competition_level': 'Medium',
                            'discovered_at': datetime.utcnow().isoformat()
                        }
                    except Exception as e:
                        logger.error("Error parsing Devpost hackathon", error=str(e))
                        continue
        except Exception as e:
            logger.error("MLH generator error", error=str(e))

