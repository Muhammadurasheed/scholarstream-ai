"""
Opportunity Scrapers Package
Production-grade scrapers for real-time opportunity discovery
"""

from .base_scraper import BaseScraper
from .devpost_scraper import DevpostScraper
from .gitcoin_scraper import GitcoinScraper
from .kaggle_scraper import KaggleScraper
from .mlh_scraper import MLHScraper
from .scholarships_scraper import ScholarshipsScraper

__all__ = [
    'BaseScraper',
    'DevpostScraper',
    'GitcoinScraper',
    'KaggleScraper',
    'MLHScraper',
    'ScholarshipsScraper'
]
