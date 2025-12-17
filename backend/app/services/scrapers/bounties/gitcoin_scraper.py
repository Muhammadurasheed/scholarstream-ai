"""
Gitcoin Bounty Scraper - PRODUCTION
Web3 Bounties Platform with Official API
FAANG-Level: Uses Gitcoin's official API for Web3 opportunities
"""
from typing import List, Dict, Any
from datetime import datetime
import structlog
from ..base_scraper import BaseScraper

logger = structlog.get_logger()


class GitcoinScraper(BaseScraper):
    """Production scraper for Gitcoin bounties"""
    
    def get_source_name(self) -> str:
        return "gitcoin"
    
    def get_source_type(self) -> str:
        return "bounty"
    
    async def scrape(self) -> List[Dict[str, Any]]:
        """
        Scrape bounties from Gitcoin
        Uses Gitcoin API for Web3/crypto bounties
        """
        logger.info("Scraping Gitcoin bounties")
        
        opportunities = []
        
        try:
            # Gitcoin API endpoint
            url = 'https://gitcoin.co/api/v0.1/bounties/'
            params = {
                'network': 'mainnet',
                'order_by': '-web3_created',
                'idx_status': 'open',
                'limit': 100
            }
            
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            bounties = data if isinstance(data, list) else data.get('results', [])
            
            for bounty in bounties:
                try:
                    opportunity = self._parse_gitcoin_bounty(bounty)
                    if opportunity:
                        opportunity['url_validated'] = await self.validate_url(opportunity.get('url', ''))
                        normalized = self.normalize_opportunity(opportunity)
                        opportunities.append(normalized)
                except Exception as e:
                    logger.error(f"Error parsing Gitcoin bounty: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Gitcoin API error: {e}")
        
        logger.info(f"Scraped {len(opportunities)} bounties from Gitcoin")
        return opportunities
    
    def _parse_gitcoin_bounty(self, bounty: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Gitcoin bounty data"""
        name = bounty.get('title', 'Gitcoin Bounty')
        url = bounty.get('url', '') or bounty.get('github_url', '')
        description = bounty.get('issue_description', '')
        
        # Parse value (in USD or crypto)
        value_in_usdt = bounty.get('value_in_usdt', 0)
        value_in_token = bounty.get('value_in_token', 0)
        token_name = bounty.get('token_name', 'USD')
        
        amount = int(float(value_in_usdt)) if value_in_usdt else int(float(value_in_token))
        amount_display = f"${amount:,}" if value_in_usdt else f"{value_in_token} {token_name}"
        
        # Parse deadline
        expires_date = bounty.get('expires_date', '')
        
        # Keywords/tags
        keywords = bounty.get('keywords', [])
        tags = self._extract_tags(name, description, keywords)
        
        # Experience level
        experience_level = bounty.get('experience_level', 'Intermediate')
        
        return {
            'name': name,
            'organization': 'Gitcoin',
            'description': description or f"{name} - Web3 Bounty",
            'amount': amount,
            'amount_display': amount_display,
            'deadline': expires_date,
            'deadline_type': 'fixed' if expires_date else 'rolling',
            'url': url,
            'tags': tags,
            'eligibility': {
                'gpa_min': None,
                'grades_eligible': ['High School', 'Undergraduate', 'Graduate', 'Professional'],
                'majors': ['Computer Science', 'Engineering', 'Blockchain'],
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
                'other': ['GitHub account', 'Web3 wallet', 'Code submission']
            }
        }
    
    def _extract_tags(self, name: str, description: str, keywords: List[str]) -> List[str]:
        """Extract relevant tags"""
        tags = ['Bounty', 'Web3', 'Gitcoin']
        
        # Add keywords
        tags.extend(keywords[:5])  # Limit to 5
        
        text = (name + " " + description).lower()
        
        # Technology tags
        if any(word in text for word in ['solidity', 'smart contract', 'ethereum']):
            tags.append('Smart Contracts')
        if any(word in text for word in ['defi', 'decentralized finance']):
            tags.append('DeFi')
        if any(word in text for word in ['nft', 'non-fungible']):
            tags.append('NFT')
        if any(word in text for word in ['dao', 'governance']):
            tags.append('DAO')
        if 'frontend' in text or 'react' in text:
            tags.append('Frontend')
        if 'backend' in text or 'api' in text:
            tags.append('Backend')
        
        return list(set(tags))  # Remove duplicates
