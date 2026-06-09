"""
Crypto Sentinel Agent
Main agent class for cryptocurrency market intelligence.
"""
import httpx
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from uuid import uuid4
from loguru import logger

from app.db import Database
from app.config import get_settings
from .data_fetcher import MarketDataFetcher, symbol_to_coingecko_id
from .news_fetcher import NewsFetcher, SentimentAnalyzer
from .analyzer import TechnicalAnalyzer
from .signal_generator import SignalGenerator
from .models import MorningBrief, Sentiment, TradingSignal, MarketData, NewsItem
from app.utils.data_contracts import contract_logger

settings = get_settings()


class CryptoSentinelAgent:
    """
    Crypto Sentinel - Market Intelligence Agent
    
    Responsibilities:
    - Generate morning briefs
    - Create trading signals
    - Monitor markets
    - Analyze specific assets
    """
    
    def __init__(self):
        self.logger = logger.bind(agent="CRYPTO_SENTINEL")
        self.market_fetcher = MarketDataFetcher()
        self.news_fetcher = NewsFetcher()
        self.analyzer = TechnicalAnalyzer()
        self.signal_generator = SignalGenerator()
    
    async def close(self):
        """Clean up resources."""
        await self.market_fetcher.close()
        await self.news_fetcher.close()
    
    # =========================================================================
    # Main Actions
    # =========================================================================
    
    async def generate_morning_brief(self) -> MorningBrief:
        """
        Generate the daily morning brief.
        
        Returns:
            MorningBrief with market summary and signals
        """
        self.logger.info("Generating morning brief...")
        
        # Fetch market data
        top_coins = await self.market_fetcher.get_top_coins(limit=50)
        global_data = await self.market_fetcher.get_global_data()
        
        # Fetch news
        news = await self.news_fetcher.get_trending_news(limit=20)
        news_sentiment = SentimentAnalyzer.analyze_news_sentiment(news)
        
        # Identify top movers
        top_movers = self._get_top_movers(top_coins)
        
        # Generate signals for top movers
        signals = []
        for mover in top_movers[:5]:
            signal = await self._generate_signal_for_asset(mover, news)
            if signal:
                signals.append(signal)

        # Identify risk factors
        risk_factors = self._identify_risk_factors(top_coins, news)

        # Build brief
        brief = MorningBrief(
            date=datetime.utcnow().strftime("%Y-%m-%d"),
            sentiment=news_sentiment,
            market_summary={
                "total_market_cap": global_data.get("total_market_cap", 0),
                "total_volume": global_data.get("total_volume", 0),
                "btc_dominance": global_data.get("btc_dominance", 0),
                "market_cap_change_24h": global_data.get("market_cap_change_24h", 0)
            },
            top_movers=[m.dict() for m in top_movers[:10]],
            signals=signals,
            news_highlights=news[:5],
            risk_factors=risk_factors,
            generated_at=datetime.utcnow()
        )

        # Save signals to database (for Active Signals display)
        await self._save_signals(signals)

        # Save to database
        await self._save_brief(brief)
        
        self.logger.info(f"Morning brief generated: {len(signals)} signals")
        
        return brief
    
    async def analyze_asset(self, symbol: str) -> Dict[str, Any]:
        """
        Perform detailed analysis on a specific asset.
        
        Args:
            symbol: Asset symbol (e.g., "BTC")
            
        Returns:
            Analysis results
        """
        self.logger.info(f"Analyzing asset: {symbol}")
        
        coin_id = symbol_to_coingecko_id(symbol)

        # Fetch data
        coin_data = await self.market_fetcher.get_coin_data(coin_id)

        # Try to get OHLCV data - handle missing data gracefully
        try:
            ohlcv = await self.market_fetcher.get_ohlcv(coin_id, days=30)
        except httpx.HTTPError as e:
            if e.response and e.response.status_code == 404:
                self.logger.warning(f"OHLCV data not available for {symbol} ({coin_id})")
                ohlcv = []
            else:
                raise

        news = await self.news_fetcher.get_news_for_asset(symbol, limit=10)
        
        # Calculate indicators
        indicators = self.analyzer.calculate_indicators(ohlcv)
        
        # Get market data
        market_data_info = coin_data.get("market_data", {})
        current_price = market_data_info.get("current_price", {}).get("usd", 0)
        
        # Determine trend
        trend = self.analyzer.determine_trend(indicators, current_price)
        
        # Build market data
        market_data = MarketData(
            symbol=symbol,
            name=coin_data.get("name", symbol),
            price=current_price,
            price_change_24h=market_data_info.get("price_change_percentage_24h") or 0,
            price_change_7d=market_data_info.get("price_change_percentage_7d"),
            volume_24h=market_data_info.get("total_volume", {}).get("usd", 0),
            market_cap=market_data_info.get("market_cap", {}).get("usd", 0),
            rank=coin_data.get("market_cap_rank", 999),
            last_updated=datetime.utcnow()
        )
        
        # Generate signal
        news_sentiment = SentimentAnalyzer.analyze_news_sentiment(news)
        signal = self.signal_generator.generate_signal(
            market_data, indicators, news, news_sentiment
        )
        
        return {
            "symbol": symbol,
            "name": coin_data.get("name", symbol),
            "price": current_price,
            "change_24h": market_data.price_change_24h,
            "change_7d": market_data.price_change_7d,
            "market_cap": market_data.market_cap,
            "volume_24h": market_data.volume_24h,
            "trend": trend,
            "indicators": indicators.dict() if indicators else {},
            "news_sentiment": news_sentiment.value,
            "recent_news": [n.dict() for n in news[:5]],
            "signal": signal.dict() if signal else None,
            "analyzed_at": datetime.utcnow().isoformat()
        }
    
    async def get_active_signals(self) -> List[TradingSignal]:
        """Get all active trading signals."""
        signals_col = Database.get_collection("crypto_signals")
        
        cursor = signals_col.find({
            "status": "ACTIVE",
            "expires_at": {"$gt": datetime.utcnow()}
        }).sort("confidence", -1)
        
        results = await cursor.to_list(length=20)
        
        # Convert to TradingSignal objects
        signals = []
        for s in results:
            try:
                # Remove MongoDB _id field
                s.pop("_id", None)
                # Convert string dates back to datetime if needed
                if isinstance(s.get("generated_at"), str):
                    s["generated_at"] = datetime.fromisoformat(s["generated_at"].replace("Z", "+00:00"))
                if isinstance(s.get("expires_at"), str):
                    s["expires_at"] = datetime.fromisoformat(s["expires_at"].replace("Z", "+00:00"))
                signals.append(TradingSignal(**s))
            except Exception as e:
                self.logger.error(f"Error parsing signal: {e}")
        
        return signals
    
    # =========================================================================
    # Helper Methods
    # =========================================================================
    
    def _get_top_movers(
        self,
        coins: List[MarketData],
        min_change: float = 5.0
    ) -> List[MarketData]:
        """Get top moving coins by 24h change."""
        movers = [c for c in coins if abs(c.price_change_24h) >= min_change]
        return sorted(movers, key=lambda x: abs(x.price_change_24h), reverse=True)
    
    async def _generate_signal_for_asset(
        self,
        market_data: MarketData,
        news: List[NewsItem]
    ) -> Optional[TradingSignal]:
        """Generate signal for a single asset."""
        try:
            coin_id = symbol_to_coingecko_id(market_data.symbol)

            # Try to get OHLCV data - skip if not available (common for small cap coins)
            try:
                ohlcv = await self.market_fetcher.get_ohlcv(coin_id, days=30)
            except httpx.HTTPError as e:
                if e.response and e.response.status_code == 404:
                    self.logger.debug(f"OHLCV data not available for {market_data.symbol} ({coin_id}) - skipping signal generation")
                    return None
                raise  # Re-raise other HTTP errors

            # Skip if no OHLCV data
            if not ohlcv:
                self.logger.debug(f"No OHLCV data available for {market_data.symbol} - skipping")
                return None

            indicators = self.analyzer.calculate_indicators(ohlcv)

            asset_news = [n for n in news if market_data.symbol in n.mentioned_assets]
            news_sentiment = SentimentAnalyzer.analyze_news_sentiment(asset_news)

            signal = self.signal_generator.generate_signal(
                market_data, indicators, asset_news, news_sentiment
            )

            if signal:
                await self._save_signal(signal)

            return signal

        except Exception as e:
            self.logger.error(f"Error generating signal for {market_data.symbol}: {e}")
            return None
    
    def _identify_risk_factors(
        self,
        coins: List[MarketData],
        news: List[NewsItem]
    ) -> List[str]:
        """Identify current risk factors."""
        risks = []
        
        if not coins:
            return risks
        
        # Check for market-wide decline
        declining = sum(1 for c in coins if c.price_change_24h < 0)
        if declining / len(coins) > 0.7:
            risks.append("Market-wide decline: >70% of assets down")
        
        # Check for bearish news
        if news:
            bearish_news = sum(1 for n in news if n.sentiment == Sentiment.BEARISH)
            if bearish_news / len(news) > 0.5:
                risks.append("Elevated bearish sentiment in news")
        
        # BTC-specific risks
        btc = next((c for c in coins if c.symbol == "BTC"), None)
        if btc and btc.price_change_24h < -5:
            risks.append(f"BTC showing weakness: {btc.price_change_24h:.1f}%")
        
        return risks
    
    async def _save_brief(self, brief: MorningBrief):
        """Save morning brief to database."""
        try:
            # Normalize crypto section per data contract
            top_movers = []
            for mover in brief.top_movers:
                coin = mover.get("symbol") or mover.get("name") or mover.get("asset") or ""
                change = mover.get("price_change_24h") or mover.get("change_pct") or 0
                top_movers.append(
                    {
                        "coin": coin,
                        "change": change,
                        "signal": mover.get("signal", "HOLD"),
                        "confidence": mover.get("confidence", 0),
                    }
                )

            crypto_section = {
                "sentiment": brief.sentiment.value if isinstance(brief.sentiment, Sentiment) else brief.sentiment,
                "top_movers": top_movers,
                "alerts": brief.risk_factors,
                "summary": (
                    f"Market cap ${brief.market_summary.get('total_market_cap', 0):,.0f}, "
                    f"BTC dom {brief.market_summary.get('btc_dominance', 0):.1f}%"
                ),
                "signals": [
                    signal.dict() if hasattr(signal, "dict") else signal for signal in brief.signals
                ],
                "news_highlights": [
                    news.dict() if hasattr(news, "dict") else news for news in brief.news_highlights
                ],
                "market_summary": brief.market_summary,
            }

            default_jobs = {
                "applications_sent": 0,
                "interviews_scheduled": 0,
                "matches_found": 0,
                "drafts_ready": 0,
                "summary": "Job updates not available for this brief",
            }
            default_projects = {
                "scaffolds_completed": 0,
                "active_workflows": 0,
                "code_generated_lines": 0,
                "summary": "Project metrics not captured in this brief",
            }
            default_system = {
                "health_score": 100,
                "agents_active": 0,
                "tasks_completed": 0,
                "errors_count": 0,
                "summary": "System metrics not captured in this brief",
            }

            await contract_logger.record_brief(
                date=brief.date,
                brief_sections={
                    "crypto": crypto_section,
                    "jobs": default_jobs,
                    "projects": default_projects,
                    "system": default_system,
                    "data_freshness": {"crypto": datetime.utcnow()},
                    "generated_at": brief.generated_at,
                },
            )

            await contract_logger.emit_event(
                event_type="BRIEF_GENERATED",
                title="Daily brief completed",
                priority="NORMAL",
                agent_name="CRYPTO_SENTINEL",
                payload={"date": brief.date, "type": "crypto"},
            )
        except Exception as e:
            self.logger.error(f"Error saving brief: {e}")
    
    async def _save_signals(self, signals: List[TradingSignal]):
        """Save multiple signals to database."""
        for signal in signals:
            await self._save_signal(signal)

    async def _save_signal(self, signal: TradingSignal):
        """Save signal to database and send notification."""
        try:
            signals_col = Database.get_collection("crypto_signals")
            signal_dict = signal.dict()

            # Convert datetime objects to strings
            if hasattr(signal_dict.get("generated_at"), "isoformat"):
                signal_dict["generated_at"] = signal_dict["generated_at"].isoformat()
            if hasattr(signal_dict.get("expires_at"), "isoformat"):
                signal_dict["expires_at"] = signal_dict["expires_at"].isoformat()

            await signals_col.insert_one(signal_dict)

            # Send notification for actionable signals (BUY/SELL)
            if signal.signal_type.value in ("BUY", "SELL") and signal.confidence >= 70:
                await self._notify_signal(signal)

        except Exception as e:
            self.logger.error(f"Error saving signal: {e}")
    
    async def _notify_signal(self, signal: TradingSignal):
        """Send notification for a trading signal."""
        try:
            from app.notifications.service import get_notification_service
            service = get_notification_service()
            
            # Get entry price from entry_zone
            entry_price = signal.entry_zone.get("min", 0) if signal.entry_zone else 0
            
            # Format reasoning as string if it's a dict
            reasoning = signal.reasoning
            if isinstance(reasoning, dict):
                reasoning = "; ".join(f"{k}: {v}" for k, v in reasoning.items())
            
            await service.notify_crypto_signal(
                coin=signal.asset,
                signal=signal.signal_type.value,
                confidence=signal.confidence,
                price=entry_price,
                change_24h=0,  # Would need to pass this from market data
                reason=reasoning
            )
        except Exception as e:
            self.logger.error(f"Error sending signal notification: {e}")


# Singleton
_agent: Optional[CryptoSentinelAgent] = None


def get_crypto_sentinel() -> CryptoSentinelAgent:
    """Get or create the Crypto Sentinel agent instance."""
    global _agent
    if _agent is None:
        _agent = CryptoSentinelAgent()
    return _agent

