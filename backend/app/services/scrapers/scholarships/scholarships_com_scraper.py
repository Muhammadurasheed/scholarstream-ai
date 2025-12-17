"""
Scholarships.com Scraper - PRODUCTION IMPLEMENTATION (FIXED)
One of the largest scholarship databases with 3.7M+ scholarships
"""
from typing import List, Dict, Any
from datetime import datetime
import structlog
from bs4 import BeautifulSoup
import re
import asyncio
from ..base_scraper import BaseScraper

logger = structlog.get_logger()


class ScholarshipsDotComScraper(BaseScraper):
    """Production scraper for Scholarships.com"""
    
    def get_source_name(self) -> str:
        return "scholarships_com"
    
    def get_source_type(self) -> str:
        return "scholarship"
    
    async def scrape(self) -> List[Dict[str, Any]]:
        """
        Scrape scholarships from Scholarships.com
        Uses their browse/search pages to find opportunities
        """
        logger.info("Scraping Scholarships.com")
        
        opportunities = []
        
        # Scholarships.com browse URLs by category
        browse_urls = [
            'https://www.scholarships.com/financial-aid/college-scholarships/scholarships-by-type/merit-scholarships/',
            'https://www.scholarships.com/financial-aid/college-scholarships/scholarships-by-type/athletic-scholarships/',
            'https://www.scholarships.com/financial-aid/college-scholarships/scholarships-by-type/scholarships-for-women/',
            'https://www.scholarships.com/financial-aid/college-scholarships/scholarships-by-major/computer-science-scholarships/',
            'https://www.scholarships.com/financial-aid/college-scholarships/scholarships-by-major/engineering-scholarships/',
            'https://www.scholarships.com/financial-aid/college-scholarships/scholarships-by-state/',
        ]
        
        for url in browse_urls:
            try:
                # ✅ FIX: Use BaseScraper's _fetch_with_retry instead of undefined self.client
                response = await self._fetch_with_retry(url)
                
                if not response or response.status_code != 200:
                    logger.warning(f"Failed to fetch {url}: {response.status_code if response else 'No response'}")
                    continue
                
                soup = BeautifulSoup(response.text, 'lxml')
                
                # Find scholarship listings
                scholarship_cards = soup.find_all('div', class_='scholarship-item') or \
                                  soup.find_all('article', class_='scholarship') or \
                                  soup.find_all('div', {'data-scholarship-id': True})
                
                for card in scholarship_cards[:10]:  # Limit per category
                    try:
                        scholarship = self._parse_scholarship_card(card, url)
                        if scholarship:
                            # Add required fields
                            scholarship['type'] = 'scholarship'
                            scholarship['source'] = 'scholarships_com'
                            scholarship['discovered_at'] = datetime.utcnow().isoformat()
                            opportunities.append(scholarship)
                    except Exception as e:
                        logger.error(f"Error parsing scholarship card: {e}")
                        continue
                
                # Be respectful - pause between requests
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error scraping {url}: {e}")
                continue
        
        logger.info(f"Scraped {len(opportunities)} scholarships from Scholarships.com")
        return opportunities
    
    def _parse_scholarship_card(self, card, source_url: str) -> Dict[str, Any]:
        """Parse individual scholarship card"""
        # Extract name
        name_elem = card.find('h3') or card.find('h2') or card.find('a', class_='title')
        name = name_elem.get_text(strip=True) if name_elem else "Unknown Scholarship"
        
        # Extract organization
        org_elem = card.find('span', class_='provider') or card.find('div', class_='organization')
        organization = org_elem.get_text(strip=True) if org_elem else "Scholarships.com"
        
        # Extract amount
        amount_elem = card.find('span', class_='amount') or card.find('div', class_='award')
        amount_text = amount_elem.get_text(strip=True) if amount_elem else "$0"
        amount = self._parse_amount(amount_text)
        
        # Extract deadline
        deadline_elem = card.find('span', class_='deadline') or card.find('time')
        deadline = self._parse_deadline(deadline_elem.get_text(strip=True) if deadline_elem else None)
        
        # Extract URL
        link_elem = card.find('a', href=True)
        url = link_elem['href'] if link_elem else source_url
        if url.startswith('/'):
            url = f"https://www.scholarships.com{url}"
        
        # Extract description
        desc_elem = card.find('p', class_='description') or card.find('div', class_='summary')
        description = desc_elem.get_text(strip=True) if desc_elem else f"Scholarship opportunity from {organization}"
        
        # Determine tags from description and name
        tags = self._extract_tags(name + " " + description)
        
        return {
            'name': name,
            'organization': organization,
            'description': description,
            'amount': amount,
            'amount_display': amount_text,
            'deadline': deadline,
            'deadline_type': 'fixed' if deadline else 'rolling',
            'url': url,
            'tags': tags,
            'eligibility': self._infer_eligibility(name, description),
            'requirements': self._infer_requirements(description)
        }
    
    def _parse_amount(self, amount_text: str) -> int:
        """Parse amount from text like '$5,000' or '$1,000-$5,000'"""
        # Remove non-numeric except digits and comma
        numbers = re.findall(r'\d[\d,]*', amount_text)
        if numbers:
            # Take first number (or average if range)
            amount_str = numbers[0].replace(',', '')
            return int(amount_str)
        return 0
    
    def _parse_deadline(self, deadline_text: str) -> str:
        """Parse deadline from various formats"""
        if not deadline_text:
            return None
        
        # Common patterns: "December 31, 2024", "12/31/2024", "Rolling"
        if 'rolling' in deadline_text.lower():
            return None
        
        try:
            # Try to parse with dateutil if available
            from dateutil import parser
            dt = parser.parse(deadline_text)
            return dt.isoformat()
        except:
            # Return None if can't parse
            return None
    
    def _extract_tags(self, text: str) -> List[str]:
        """Extract relevant tags from text"""
        tags = []
        text_lower = text.lower()
        
        tag_keywords = {
            'STEM': ['stem', 'science', 'technology', 'engineering', 'math'],
            'Merit-Based': ['merit', 'academic', 'gpa', 'achievement'],
            'Need-Based': ['need', 'financial need', 'low-income'],
            'Women': ['women', 'female'],
            'Minority': ['minority', 'diversity', 'underrepresented'],
            'Leadership': ['leadership', 'leader'],
            'Community Service': ['community service', 'volunteer'],
            'Athletic': ['athletic', 'sports', 'athlete'],
        }
        
        for tag, keywords in tag_keywords.items():
            if any(kw in text_lower for kw in keywords):
                tags.append(tag)
        
        return tags or ['General']
    
    def _infer_eligibility(self, name: str, description: str) -> Dict[str, Any]:
        """Infer eligibility from name and description"""
        text = (name + " " + description).lower()
        
        # Infer grade levels
        grades = []
        if 'high school' in text:
            grades.append('High School Senior')
        if 'undergraduate' in text or 'college' in text:
            grades.append('Undergraduate')
        if 'graduate' in text or 'masters' in text or 'phd' in text:
            grades.append('Graduate')
        
        if not grades:
            grades = ['Undergraduate']  # Default
        
        # Infer GPA requirement
        gpa_min = None
        gpa_match = re.search(r'(\d\.\d+)\s*gpa', text)
        if gpa_match:
            gpa_min = float(gpa_match.group(1))
        
        return {
            'gpa_min': gpa_min,
            'grades_eligible': grades,
            'majors': None,
            'gender': 'Female' if 'women' in text else None,
            'citizenship': 'United States' if 'us' in text or 'american' in text else None,
            'backgrounds': [],
            'states': None
        }
    
    def _infer_requirements(self, description: str) -> Dict[str, Any]:
        """Infer requirements from description"""
        text = description.lower()
        
        return {
            'essay': 'essay' in text or 'write' in text or 'statement' in text,
            'essay_prompts': [],
            'recommendation_letters': 1 if 'recommendation' in text or 'letter' in text else 0,
            'transcript': 'transcript' in text,
            'resume': 'resume' in text or 'cv' in text,
            'other': []
        }
