"""
Industry Intelligence - Fetches news and data from entertainment industry sources.
"""

import os
import requests
import feedparser
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from datetime import datetime, timedelta


class IndustryIntelligence:
    """Fetches and processes entertainment industry news and data."""
    
    def __init__(self):
        self.cache: Dict[str, Dict] = {}
        self.cache_duration = timedelta(hours=1)
        
        self.rss_feeds = {
            "variety": "https://variety.com/feed/",
            "deadline": "https://deadline.com/feed/",
            "hollywood_reporter": "https://www.hollywoodreporter.com/feed/",
        }
        
        self.boxofficemojo_url = "https://www.boxofficemojo.com"
    
    def get_latest_news(self, source: str = "all", limit: int = 10) -> List[Dict]:
        """Fetch latest news from industry sources."""
        articles = []
        
        if source == "all":
            sources = list(self.rss_feeds.keys())
        else:
            sources = [source] if source in self.rss_feeds else []
        
        for src in sources:
            try:
                feed_articles = self._fetch_rss(src)
                articles.extend(feed_articles)
            except Exception as e:
                print(f"Warning: Could not fetch {src}: {e}")
        
        articles.sort(key=lambda x: x.get("published", ""), reverse=True)
        return articles[:limit]
    
    def _fetch_rss(self, source: str) -> List[Dict]:
        """Fetch articles from an RSS feed."""
        cache_key = f"rss_{source}"
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if datetime.now() - cached["timestamp"] < self.cache_duration:
                return cached["data"]
        
        url = self.rss_feeds.get(source)
        if not url:
            return []
        
        feed = feedparser.parse(url)
        articles = []
        
        for entry in feed.entries[:20]:
            article = {
                "source": source,
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "summary": entry.get("summary", "")[:500],
                "published": entry.get("published", ""),
                "tags": [t.get("term", "") for t in entry.get("tags", [])]
            }
            articles.append(article)
        
        self.cache[cache_key] = {
            "timestamp": datetime.now(),
            "data": articles
        }
        
        return articles
    
    def search_news(self, query: str, limit: int = 10) -> List[Dict]:
        """Search for news articles matching a query."""
        all_articles = self.get_latest_news("all", limit=50)
        
        query_lower = query.lower()
        matching = []
        
        for article in all_articles:
            title = article.get("title", "").lower()
            summary = article.get("summary", "").lower()
            tags = " ".join(article.get("tags", [])).lower()
            
            if query_lower in title or query_lower in summary or query_lower in tags:
                matching.append(article)
        
        return matching[:limit]
    
    def get_project_buzz(self, project_name: str) -> Dict:
        """Get industry buzz/sentiment around a specific project."""
        articles = self.search_news(project_name, limit=10)
        
        return {
            "project": project_name,
            "article_count": len(articles),
            "articles": articles,
            "summary": f"Found {len(articles)} recent articles mentioning {project_name}"
        }

