"""
Niche.com Scholarship Scraper - PRODUCTION IMPLEMENTATION
Platform with 1M+ scholarships and detailed filtering
"""
from typing import List, Dict, Any
from datetime import datetime, timedelta
import structlog
from bs4 import BeautifulSoup
import re
import json
from ..base_scraper import BaseScraper

logger = structlog.get_logger()


class NicheScraper(BaseScraper):
    """Production scraper for Niche.com scholarships"""
    
    def get_source_name(self) -> str:
        return "niche"
    
    def get_source_type(self) -> str:
        return "scholarship"
    
    async def scrape(self) -> List[Dict[str, Any]]:
        """
        Scrape scholarships from Niche.com
        Niche has a well-structured scholarship directory
        """
        logger.info("Scraping Niche.com scholarships")
        
        opportunities = []
        
        # Niche scholarship directory URLs
        base_url = "https://www.niche.com/colleges/scholarships/"
        
        # Categories to scrape
        categories = [
            "no-essay-scholarships/",
            "easy-scholarships/",
            "scholarships-for-high-school-seniors/",
            "scholarships-for-college-students/",
            "scholarships-for-graduate-students/",
            "merit-scholarships/",
            "stem-scholarships/",
            "scholarships-for-women/",
            "minority-scholarships/",
        ]
        
        for category in categories:
            try:
                url = base_url + category
                response = await self.client.get(url)
                
                if response.status_code != 200:
                    logger.warning(f"Failed to fetch {url}: {response.status_code}")
                    continue
                
                soup = BeautifulSoup(response.text, 'lxml')
                
                # Niche uses structured data - look for scholarship cards
                scholarship_cards = soup.find_all('div', class_='scholarship') or \
                                  soup.find_all('article', {'data-entity-type': 'scholarship'}) or \
                                  soup.find_all('div', class_='search-result')
                
                for card in scholarship_cards[:15]:  # Limit per category
                    try:
                        scholarship = self._parse_niche_scholarship(card, url)
                        if scholarship:
                            # Validate URL
                            if scholarship.get('url'):
                                scholarship['url_validated'] = await self.validate_url(scholarship['url'])
                            
                            normalized = self.normalize_opportunity(scholarship)
                            opportunities.append(normalized)
                    except Exception as e:
                        logger.error(f"Error parsing Niche scholarship: {e}")
                        continue
                
                # Respectful delay
                await self._sleep(1.5)
                
            except Exception as e:
                logger.error(f"Error scraping Niche category {category}: {e}")
                continue
        
        logger.info(f"Scraped {len(opportunities)} scholarships from Niche.com")
        return opportunities
    
    def _parse_niche_scholarship(self, card, source_url: str) -> Dict[str, Any]:
        """Parse Niche scholarship card"""
        # Extract name
        name_elem = card.find('h2') or card.find('h3') or card.find('a', class_='scholarship__name')
        name = name_elem.get_text(strip=True) if name_elem else "Niche Scholarship"
        
        # Extract organization (often Niche itself or partner)
        org_elem = card.find('span', class_='scholarship__sponsor') or card.find('div', class_='provider')
        organization = org_elem.get_text(strip=True) if org_elem else "Niche.com"
        
        # Extract amount
        amount_elem = card.find('span', class_='scholarship__amount') or card.find('strong', class_='amount')
        amount_text = amount_elem.get_text(strip=True) if amount_elem else "$1,000"
        amount = self._parse_amount(amount_text)
        
        # Extract deadline
        deadline_elem = card.find('time') or card.find('span', class_='deadline')
        deadline_text = deadline_elem.get_text(strip=True) if deadline_elem else None
        deadline = self._parse_deadline(deadline_text)
        
        # Extract URL
        link_elem = card.find('a', href=True)
        url = link_elem['href'] if link_elem else source_url
        if url.startswith('/'):
            url = f"https://www.niche.com{url}"
        
        # Extract description
        desc_elem = card.find('p', class_='scholarship__description') or card.find('div', class_='description')
        description = desc_elem.get_text(strip=True) if desc_elem else f"{name} from {organization}"
        
        # Extract tags from badges/labels
        tags = []
        badge_elems = card.find_all('span', class_='badge') or card.find_all('span', class_='label')
        for badge in badge_elems:
            tag_text = badge.get_text(strip=True)
            if tag_text:
                tags.append(tag_text)
        
        if not tags:
            tags = self._extract_tags_from_text(name + " " + description)
        
        # Determine eligibility
        eligibility = self._parse_eligibility(card, name, description)
        
        # Determine requirements
        requirements = self._parse_requirements(card, description)
        
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
            'eligibility': eligibility,
            'requirements': requirements
        }
    
    def _parse_amount(self, amount_text: str) -> int:
        """Parse amount from text"""
        # Handle ranges like "$1,000-$5,000"
        numbers = re.findall(r'\$?\d[\d,]*', amount_text)
        if numbers:
            # Take first number
            amount_str = numbers[0].replace('$', '').replace(',', '')
            try:
                return int(amount_str)
            except:
                return 1000
        return 1000
    
    def _parse_deadline(self, deadline_text: str) -> str:
        """Parse deadline from various formats"""
        if not deadline_text:
            return None
        
        text_lower = deadline_text.lower()
        
        # Check for rolling/ongoing
        if 'rolling' in text_lower or 'ongoing' in text_lower or 'varies' in text_lower:
            return None
        
        # Try to parse date
        try:
            from dateutil import parser
            dt = parser.parse(deadline_text)
            return dt.isoformat()
        except:
            # If can't parse, return None (rolling)
            return None
    
    def _extract_tags_from_text(self, text: str) -> List[str]:
        """Extract tags from text"""
        tags = []
        text_lower = text.lower()
        
        tag_map = {
            'No Essay': ['no essay', 'no-essay'],
            'Easy': ['easy', 'simple', 'quick'],
            'STEM': ['stem', 'science', 'technology', 'engineering', 'math', 'computer'],
            'Women': ['women', 'female'],
            'Minority': ['minority', 'diversity', 'underrepresented', 'african american', 'hispanic', 'latino'],
            'Merit-Based': ['merit', 'academic', 'achievement', 'gpa'],
            'Need-Based': ['need', 'financial need', 'low-income'],
            'High School': ['high school', 'senior'],
            'Undergraduate': ['undergraduate', 'college student'],
            'Graduate': ['graduate', 'masters', 'phd', 'doctoral'],
        }
        
        for tag, keywords in tag_map.items():
            if any(kw in text_lower for kw in keywords):
                tags.append(tag)
        
        return tags if tags else ['General']
    
    def _parse_eligibility(self, card, name: str, description: str) -> Dict[str, Any]:
        """Parse eligibility requirements"""
        text = (name + " " + description).lower()
        
        # Grade levels
        grades = []
        if 'high school' in text or 'senior' in text:
            grades.append('High School Senior')
        if 'undergraduate' in text or 'college' in text:
            grades.append('Undergraduate')
        if 'graduate' in text or 'masters' in text or 'phd' in text:
            grades.append('Graduate')
        
        if not grades:
            grades = ['Undergraduate']
        
        # GPA requirement
        gpa_min = None
        gpa_patterns = [r'(\d\.\d+)\s*gpa', r'gpa\s*of\s*(\d\.\d+)', r'minimum\s*(\d\.\d+)']
        for pattern in gpa_patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    gpa_min = float(match.group(1))
                    break
                except:
                    pass
        
        # Gender
        gender = None
        if 'women' in text or 'female' in text:
            gender = 'Female'
        elif 'men' in text or 'male' in text:
            gender = 'Male'
        
        # Citizenship
        citizenship = None
        if 'us citizen' in text or 'american citizen' in text or 'united states' in text:
            citizenship = 'United States'
        elif 'international' in text:
            citizenship = 'International'
        
        # Backgrounds
        backgrounds = []
        if 'first-generation' in text or 'first generation' in text:
            backgrounds.append('First-generation')
        if 'minority' in text or 'underrepresented' in text:
            backgrounds.append('Minority')
        if 'low-income' in text or 'financial need' in text:
            backgrounds.append('Low-income')
        
        return {
            'gpa_min': gpa_min,
            'grades_eligible': grades,
            'majors': None,
            'gender': gender,
            'citizenship': citizenship,
            'backgrounds': backgrounds,
            'states': None
        }
    
    def _parse_requirements(self, card, description: str) -> Dict[str, Any]:
        """Parse application requirements"""
        text = description.lower()
        
        # Check for essay requirement
        essay_required = any(word in text for word in ['essay', 'write', 'statement', 'composition'])
        
        # Check for no-essay
        if 'no essay' in text or 'no-essay' in text:
            essay_required = False
        
        # Recommendation letters
        rec_count = 0
        if 'recommendation' in text or 'letter' in text:
            # Try to find number
            rec_match = re.search(r'(\d+)\s*recommendation', text)
            if rec_match:
                rec_count = int(rec_match.group(1))
            else:
                rec_count = 1
        
        return {
            'essay': essay_required,
            'essay_prompts': [],
            'recommendation_letters': rec_count,
            'transcript': 'transcript' in text,
            'resume': 'resume' in text or 'cv' in text,
            'other': []
        }
    
    async def _sleep(self, seconds: float):
        """Async sleep"""
        import asyncio
        await asyncio.sleep(seconds)
