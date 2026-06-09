"""
News Fetcher
Aggregates cryptocurrency news from various sources.
"""
import httpx
from typing import List, Optional
from datetime import datetime
from loguru import logger
from app.config import get_settings
from .models import NewsItem, Sentiment

settings = get_settings()


class NewsFetcher:
    """
    Fetches cryptocurrency news from CryptoPanic.
    """

    BASE_URL = "https://cryptopanic.com/api/v1"
    
    def __init__(self):
        self.api_key = getattr(settings, 'cryptopanic_api_key', None)
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
    
    async def get_news(
        self,
        currencies: Optional[List[str]] = None,
        kind: str = "news",
        filter_type: str = "hot",
        limit: int = 20
    ) -> List[NewsItem]:
        """
        Get news from CryptoPanic.
        
        Args:
            currencies: Filter by currency symbols (e.g., ["BTC", "ETH"])
            kind: Type of content ("news", "media", "all")
            filter_type: Filter type ("rising", "hot", "bullish", "bearish")
            limit: Maximum number of items
            
        Returns:
            List of NewsItem objects
        """
        if not self.api_key:
            logger.warning("CryptoPanic API key not configured")
            return []
        
        try:
            params = {
                "auth_token": self.api_key,
                "kind": kind,
                "filter": filter_type,
                "public": "true",
                "limit": limit
            }
            
            if currencies:
                params["currencies"] = ",".join(currencies)
            
            response = await self.client.get(
                f"{self.BASE_URL}/posts/",
                params=params
            )
            response.raise_for_status()
            
            data = response.json()
            results = data.get("results", [])[:limit]
            
            news_items = []
            for item in results:
                # Determine sentiment from votes
                votes = item.get("votes", {})
                positive = votes.get("positive", 0)
                negative = votes.get("negative", 0)
                
                if positive > negative * 2:
                    sentiment = Sentiment.BULLISH
                elif negative > positive * 2:
                    sentiment = Sentiment.BEARISH
                else:
                    sentiment = Sentiment.NEUTRAL
                
                # Extract mentioned currencies
                currencies_mentioned = [
                    c["code"] for c in item.get("currencies", [])
                ]
                
                # Parse published_at
                published_str = item.get("published_at", "")
                try:
                    if published_str:
                        published_at = datetime.fromisoformat(
                            published_str.replace("Z", "+00:00")
                        )
                    else:
                        published_at = datetime.utcnow()
                except (ValueError, TypeError):
                    published_at = datetime.utcnow()
                
                news_items.append(NewsItem(
                    title=item.get("title", ""),
                    source=item.get("source", {}).get("title", "Unknown"),
                    url=item.get("url", ""),
                    published_at=published_at,
                    sentiment=sentiment,
                    relevance_score=float(positive + negative),  # Engagement as relevance
                    mentioned_assets=currencies_mentioned
                ))
            
            return news_items
            
        except httpx.HTTPError as e:
            logger.error(f"Error fetching news: {e}")
            return []
    
    async def get_trending_news(self, limit: int = 10) -> List[NewsItem]:
        """Get trending/hot news."""
        return await self.get_news(filter_type="hot", limit=limit)
    
    async def get_bullish_news(self, limit: int = 10) -> List[NewsItem]:
        """Get bullish sentiment news."""
        return await self.get_news(filter_type="bullish", limit=limit)
    
    async def get_bearish_news(self, limit: int = 10) -> List[NewsItem]:
        """Get bearish sentiment news."""
        return await self.get_news(filter_type="bearish", limit=limit)
    
    async def get_news_for_asset(
        self,
        symbol: str,
        limit: int = 10
    ) -> List[NewsItem]:
        """Get news for a specific asset."""
        return await self.get_news(currencies=[symbol], limit=limit)


class SentimentAnalyzer:
    """
    Analyzes overall market sentiment from news.
    """
    
    @staticmethod
    def analyze_news_sentiment(news_items: List[NewsItem]) -> Sentiment:
        """
        Determine overall sentiment from news items.
        
        Args:
            news_items: List of news items
            
        Returns:
            Overall sentiment
        """
        if not news_items:
            return Sentiment.NEUTRAL
        
        bullish_count = sum(1 for n in news_items if n.sentiment == Sentiment.BULLISH)
        bearish_count = sum(1 for n in news_items if n.sentiment == Sentiment.BEARISH)
        
        total = len(news_items)
        bullish_ratio = bullish_count / total
        bearish_ratio = bearish_count / total
        
        if bullish_ratio > 0.5:
            return Sentiment.BULLISH
        elif bearish_ratio > 0.5:
            return Sentiment.BEARISH
        else:
            return Sentiment.NEUTRAL

