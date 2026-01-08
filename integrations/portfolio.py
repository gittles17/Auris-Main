"""
Portfolio Integration - Accesses Create Advertising's finished work.
"""

import os
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from datetime import datetime


class PortfolioIntegration:
    """Integrates with Create Advertising's website and social channels."""
    
    def __init__(self):
        self.website_url = os.getenv("CREATE_WEBSITE_URL", "https://createadvertising.com")
        self.portfolio_cache: List[Dict] = []
        self.last_fetched: Optional[datetime] = None
    
    def get_recent_work(self, limit: int = 20) -> List[Dict]:
        """Fetch recent work from the website."""
        try:
            return self._scrape_website()
        except Exception as e:
            print(f"Warning: Could not fetch portfolio: {e}")
            return []
    
    def _scrape_website(self) -> List[Dict]:
        """Scrape work from the Create website."""
        works = []
        
        try:
            response = requests.get(self.website_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            work_elements = soup.find_all(['article', 'div'], class_=lambda x: x and any(
                term in str(x).lower() for term in ['work', 'project', 'portfolio', 'case']
            ))
            
            for elem in work_elements[:20]:
                title = elem.find(['h1', 'h2', 'h3', 'h4'])
                link = elem.find('a')
                img = elem.find('img')
                
                work = {
                    "title": title.get_text(strip=True) if title else "Untitled",
                    "url": link.get('href', '') if link else "",
                    "thumbnail": img.get('src', '') if img else "",
                    "source": "website"
                }
                
                if work["title"] != "Untitled":
                    works.append(work)
            
            self.portfolio_cache = works
            self.last_fetched = datetime.now()
            
        except requests.RequestException as e:
            print(f"Could not fetch website: {e}")
        
        return works
    
    def search_work(self, query: str) -> List[Dict]:
        """Search portfolio for specific work."""
        if not self.portfolio_cache:
            self.get_recent_work()
        
        query_lower = query.lower()
        matching = []
        
        for work in self.portfolio_cache:
            title = work.get("title", "").lower()
            if query_lower in title:
                matching.append(work)
        
        return matching

