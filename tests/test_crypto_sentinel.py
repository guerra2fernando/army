"""
Crypto Sentinel Agent Tests
Comprehensive tests for market intelligence and signal generation.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

from app.agents.crypto_sentinel.models import (
    SignalType, Sentiment, MarketData, TechnicalIndicators,
    NewsItem, TradingSignal, MorningBrief
)
from app.agents.crypto_sentinel.data_fetcher import (
    MarketDataFetcher, symbol_to_coingecko_id
)
from app.agents.crypto_sentinel.news_fetcher import NewsFetcher, SentimentAnalyzer
from app.agents.crypto_sentinel.analyzer import TechnicalAnalyzer
from app.agents.crypto_sentinel.signal_generator import SignalGenerator
from app.agents.crypto_sentinel.agent import CryptoSentinelAgent


# =============================================================================
# MODEL TESTS
# =============================================================================

class TestModels:
    """Tests for data models."""
    
    def test_signal_type_enum(self):
        """Test SignalType enum values."""
        assert SignalType.BUY.value == "BUY"
        assert SignalType.SELL.value == "SELL"
        assert SignalType.HOLD.value == "HOLD"
    
    def test_sentiment_enum(self):
        """Test Sentiment enum values."""
        assert Sentiment.BULLISH.value == "BULLISH"
        assert Sentiment.BEARISH.value == "BEARISH"
        assert Sentiment.NEUTRAL.value == "NEUTRAL"
    
    def test_market_data_creation(self):
        """Test MarketData model creation."""
        data = MarketData(
            symbol="BTC",
            name="Bitcoin",
            price=97500.0,
            price_change_24h=2.5,
            volume_24h=45000000000.0,
            market_cap=1900000000000.0,
            rank=1
        )
        
        assert data.symbol == "BTC"
        assert data.name == "Bitcoin"
        assert data.price == 97500.0
        assert data.price_change_24h == 2.5
        assert data.rank == 1
    
    def test_market_data_defaults(self):
        """Test MarketData default values."""
        data = MarketData(symbol="ETH", name="Ethereum", price=3500.0)
        
        assert data.price_change_24h == 0.0
        assert data.price_change_7d is None
        assert data.volume_24h == 0.0
        assert data.rank == 999
    
    def test_technical_indicators_creation(self):
        """Test TechnicalIndicators model."""
        indicators = TechnicalIndicators(
            rsi_14=58.5,
            macd={"value": 150.0, "signal": 120.0, "histogram": 30.0},
            sma_20=95000.0,
            sma_50=90000.0
        )
        
        assert indicators.rsi_14 == 58.5
        assert indicators.macd["histogram"] == 30.0
        assert indicators.sma_200 is None
    
    def test_news_item_creation(self):
        """Test NewsItem model."""
        news = NewsItem(
            title="Bitcoin breaks $100K",
            source="CoinDesk",
            url="https://example.com/news",
            sentiment=Sentiment.BULLISH,
            mentioned_assets=["BTC"]
        )
        
        assert news.title == "Bitcoin breaks $100K"
        assert news.sentiment == Sentiment.BULLISH
        assert "BTC" in news.mentioned_assets
    
    def test_trading_signal_creation(self):
        """Test TradingSignal model."""
        signal = TradingSignal(
            signal_id=str(uuid4()),
            asset="SOL",
            signal_type=SignalType.BUY,
            confidence=80.0,
            entry_zone={"min": 140.0, "max": 148.0},
            targets=[{"price": 155.0, "probability": 70}],
            stop_loss=132.0,
            risk_reward=2.8
        )
        
        assert signal.asset == "SOL"
        assert signal.signal_type == SignalType.BUY
        assert signal.confidence == 80.0
        assert signal.stop_loss == 132.0
    
    def test_trading_signal_confidence_bounds(self):
        """Test TradingSignal confidence validation."""
        # Valid confidence
        signal = TradingSignal(
            signal_id="test",
            asset="BTC",
            signal_type=SignalType.HOLD,
            confidence=50.0
        )
        assert signal.confidence == 50.0
    
    def test_morning_brief_creation(self):
        """Test MorningBrief model."""
        brief = MorningBrief(
            date="2025-12-02",
            sentiment=Sentiment.BULLISH,
            market_summary={"total_market_cap": 3400000000000},
            top_movers=[],
            signals=[],
            news_highlights=[],
            risk_factors=["Market volatility"]
        )
        
        assert brief.date == "2025-12-02"
        assert brief.sentiment == Sentiment.BULLISH
        assert "Market volatility" in brief.risk_factors


# =============================================================================
# DATA FETCHER TESTS
# =============================================================================

class TestMarketDataFetcher:
    """Tests for market data fetching."""
    
    def test_symbol_to_coingecko_id(self):
        """Test symbol to CoinGecko ID mapping."""
        assert symbol_to_coingecko_id("BTC") == "bitcoin"
        assert symbol_to_coingecko_id("ETH") == "ethereum"
        assert symbol_to_coingecko_id("SOL") == "solana"
        assert symbol_to_coingecko_id("UNKNOWN") == "unknown"  # fallback
    
    def test_symbol_to_coingecko_id_case_insensitive(self):
        """Test symbol mapping is case insensitive."""
        assert symbol_to_coingecko_id("btc") == "bitcoin"
        assert symbol_to_coingecko_id("Eth") == "ethereum"
    
    @pytest.mark.asyncio
    async def test_market_data_fetcher_initialization(self):
        """Test fetcher initialization."""
        fetcher = MarketDataFetcher()
        assert fetcher.BASE_URL == "https://api.coingecko.com/api/v3"
        await fetcher.close()
    
    @pytest.mark.asyncio
    async def test_get_top_coins_mock(self):
        """Test get_top_coins with mocked response."""
        mock_response = [
            {
                "symbol": "btc",
                "name": "Bitcoin",
                "current_price": 97500.0,
                "price_change_percentage_24h": 2.5,
                "price_change_percentage_7d_in_currency": 5.0,
                "total_volume": 45000000000,
                "market_cap": 1900000000000,
                "market_cap_rank": 1
            },
            {
                "symbol": "eth",
                "name": "Ethereum",
                "current_price": 3500.0,
                "price_change_percentage_24h": 1.2,
                "price_change_percentage_7d_in_currency": 3.0,
                "total_volume": 25000000000,
                "market_cap": 420000000000,
                "market_cap_rank": 2
            }
        ]
        
        fetcher = MarketDataFetcher()
        
        with patch.object(fetcher.client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MagicMock(
                status_code=200,
                json=lambda: mock_response,
                raise_for_status=lambda: None
            )
            
            coins = await fetcher.get_top_coins(limit=2)
            
            assert len(coins) == 2
            assert coins[0].symbol == "BTC"
            assert coins[0].price == 97500.0
            assert coins[1].symbol == "ETH"
        
        await fetcher.close()
    
    @pytest.mark.asyncio
    async def test_get_global_data_mock(self):
        """Test get_global_data with mocked response."""
        mock_response = {
            "data": {
                "total_market_cap": {"usd": 3400000000000},
                "total_volume": {"usd": 150000000000},
                "market_cap_percentage": {"btc": 54.2, "eth": 12.5},
                "market_cap_change_percentage_24h_usd": 2.1,
                "active_cryptocurrencies": 10000
            }
        }
        
        fetcher = MarketDataFetcher()
        
        with patch.object(fetcher.client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MagicMock(
                status_code=200,
                json=lambda: mock_response,
                raise_for_status=lambda: None
            )
            
            global_data = await fetcher.get_global_data()
            
            assert global_data["total_market_cap"] == 3400000000000
            assert global_data["btc_dominance"] == 54.2
        
        await fetcher.close()
    
    @pytest.mark.asyncio
    async def test_get_ohlcv_mock(self):
        """Test get_ohlcv with mocked response."""
        # CoinGecko returns [timestamp, open, high, low, close]
        mock_response = [
            [1701388800000, 95000, 96000, 94500, 95500],
            [1701475200000, 95500, 97000, 95000, 96500],
            [1701561600000, 96500, 98000, 96000, 97500],
        ]
        
        fetcher = MarketDataFetcher()
        
        with patch.object(fetcher.client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MagicMock(
                status_code=200,
                json=lambda: mock_response,
                raise_for_status=lambda: None
            )
            
            ohlcv = await fetcher.get_ohlcv("bitcoin", days=3)
            
            assert len(ohlcv) == 3
            assert ohlcv[0]["open"] == 95000
            assert ohlcv[2]["close"] == 97500
        
        await fetcher.close()


# =============================================================================
# NEWS FETCHER TESTS
# =============================================================================

class TestNewsFetcher:
    """Tests for news fetching."""
    
    @pytest.mark.asyncio
    async def test_news_fetcher_initialization(self):
        """Test news fetcher initialization."""
        fetcher = NewsFetcher()
        assert fetcher.BASE_URL == "https://cryptopanic.com/api/v1"
        await fetcher.close()
    
    @pytest.mark.asyncio
    async def test_get_news_without_api_key(self):
        """Test get_news returns empty list without API key."""
        fetcher = NewsFetcher()
        fetcher.api_key = None
        
        news = await fetcher.get_news()
        
        assert news == []
        await fetcher.close()
    
    @pytest.mark.asyncio
    async def test_get_news_mock(self):
        """Test get_news with mocked response."""
        mock_response = {
            "results": [
                {
                    "title": "Bitcoin reaches new high",
                    "source": {"title": "CoinDesk"},
                    "url": "https://coindesk.com/news/1",
                    "published_at": "2025-12-02T08:00:00Z",
                    "votes": {"positive": 50, "negative": 5},
                    "currencies": [{"code": "BTC"}]
                },
                {
                    "title": "ETH staking update",
                    "source": {"title": "CryptoNews"},
                    "url": "https://cryptonews.com/news/1",
                    "published_at": "2025-12-02T07:00:00Z",
                    "votes": {"positive": 20, "negative": 20},
                    "currencies": [{"code": "ETH"}]
                }
            ]
        }
        
        fetcher = NewsFetcher()
        fetcher.api_key = "test-api-key"
        
        with patch.object(fetcher.client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MagicMock(
                status_code=200,
                json=lambda: mock_response,
                raise_for_status=lambda: None
            )
            
            news = await fetcher.get_news(limit=2)
            
            assert len(news) == 2
            assert news[0].title == "Bitcoin reaches new high"
            assert news[0].sentiment == Sentiment.BULLISH  # positive > negative*2
            assert news[1].sentiment == Sentiment.NEUTRAL  # equal votes
            assert "BTC" in news[0].mentioned_assets
        
        await fetcher.close()


class TestSentimentAnalyzer:
    """Tests for sentiment analysis."""
    
    def test_analyze_empty_news(self):
        """Test sentiment analysis with no news."""
        sentiment = SentimentAnalyzer.analyze_news_sentiment([])
        assert sentiment == Sentiment.NEUTRAL
    
    def test_analyze_bullish_news(self):
        """Test sentiment analysis with bullish news."""
        news = [
            NewsItem(title="Bull 1", sentiment=Sentiment.BULLISH),
            NewsItem(title="Bull 2", sentiment=Sentiment.BULLISH),
            NewsItem(title="Neutral", sentiment=Sentiment.NEUTRAL),
        ]
        
        sentiment = SentimentAnalyzer.analyze_news_sentiment(news)
        assert sentiment == Sentiment.BULLISH
    
    def test_analyze_bearish_news(self):
        """Test sentiment analysis with bearish news."""
        news = [
            NewsItem(title="Bear 1", sentiment=Sentiment.BEARISH),
            NewsItem(title="Bear 2", sentiment=Sentiment.BEARISH),
            NewsItem(title="Neutral", sentiment=Sentiment.NEUTRAL),
        ]
        
        sentiment = SentimentAnalyzer.analyze_news_sentiment(news)
        assert sentiment == Sentiment.BEARISH
    
    def test_analyze_mixed_news(self):
        """Test sentiment analysis with mixed news."""
        news = [
            NewsItem(title="Bull", sentiment=Sentiment.BULLISH),
            NewsItem(title="Bear", sentiment=Sentiment.BEARISH),
            NewsItem(title="Neutral", sentiment=Sentiment.NEUTRAL),
        ]
        
        sentiment = SentimentAnalyzer.analyze_news_sentiment(news)
        assert sentiment == Sentiment.NEUTRAL


# =============================================================================
# TECHNICAL ANALYZER TESTS
# =============================================================================

class TestTechnicalAnalyzer:
    """Tests for technical analysis."""
    
    def test_calculate_indicators_insufficient_data(self):
        """Test indicators with insufficient data."""
        ohlcv = [{"close": 100, "high": 101, "low": 99}] * 10  # Only 10 candles
        
        indicators = TechnicalAnalyzer.calculate_indicators(ohlcv)
        
        # Should return empty indicators with insufficient data
        assert indicators.rsi_14 is None or indicators.sma_50 is None
    
    def test_calculate_indicators_with_sufficient_data(self):
        """Test indicators calculation with sufficient data."""
        # Create 50+ candles of price data
        base_price = 100.0
        ohlcv = []
        for i in range(60):
            price = base_price + (i * 0.5)  # Uptrend
            ohlcv.append({
                "timestamp": 1701388800000 + (i * 86400000),
                "open": price - 0.5,
                "high": price + 1,
                "low": price - 1,
                "close": price
            })
        
        indicators = TechnicalAnalyzer.calculate_indicators(ohlcv)
        
        assert indicators.sma_20 is not None
        assert indicators.sma_50 is not None
        assert indicators.rsi_14 is not None
        assert indicators.macd is not None
        assert "value" in indicators.macd
        assert "signal" in indicators.macd
        assert "histogram" in indicators.macd
    
    def test_calculate_rsi(self):
        """Test RSI calculation."""
        # Create uptrending data (should have RSI > 50)
        prices = [100 + i for i in range(30)]  # Consistent uptrend
        import pandas as pd
        
        rsi = TechnicalAnalyzer._calculate_rsi(pd.Series(prices), 14)
        
        assert rsi is not None
        assert 0 <= rsi <= 100
        assert rsi > 50  # Should be bullish in uptrend
    
    def test_calculate_macd(self):
        """Test MACD calculation."""
        import pandas as pd
        prices = pd.Series([100 + i * 0.5 for i in range(50)])  # Uptrend
        
        macd = TechnicalAnalyzer._calculate_macd(prices)
        
        assert "value" in macd
        assert "signal" in macd
        assert "histogram" in macd
    
    def test_calculate_bollinger_bands(self):
        """Test Bollinger Bands calculation."""
        import pandas as pd
        prices = pd.Series([100 + i * 0.1 for i in range(30)])
        
        bb = TechnicalAnalyzer._calculate_bollinger(prices)
        
        assert "upper" in bb
        assert "middle" in bb
        assert "lower" in bb
        assert bb["upper"] > bb["middle"] > bb["lower"]
    
    def test_determine_trend_bullish(self):
        """Test bullish trend detection."""
        indicators = TechnicalIndicators(
            rsi_14=45.0,  # Not overbought
            macd={"value": 100, "signal": 80, "histogram": 20},  # Positive
            sma_50=95000.0
        )
        
        trend = TechnicalAnalyzer.determine_trend(indicators, 98000.0)  # Above SMA
        
        assert trend == "BULLISH"
    
    def test_determine_trend_bearish(self):
        """Test bearish trend detection."""
        indicators = TechnicalIndicators(
            rsi_14=75.0,  # Overbought
            macd={"value": -100, "signal": -80, "histogram": -20},  # Negative
            sma_50=100000.0
        )
        
        trend = TechnicalAnalyzer.determine_trend(indicators, 95000.0)  # Below SMA
        
        assert trend == "BEARISH"
    
    def test_determine_trend_neutral(self):
        """Test neutral trend detection."""
        indicators = TechnicalIndicators(
            rsi_14=50.0,  # Neutral
            macd={"value": 0, "signal": 0, "histogram": 0}
        )
        
        trend = TechnicalAnalyzer.determine_trend(indicators, 97000.0)
        
        assert trend == "NEUTRAL"


# =============================================================================
# SIGNAL GENERATOR TESTS
# =============================================================================

class TestSignalGenerator:
    """Tests for signal generation."""
    
    def test_signal_generator_initialization(self):
        """Test signal generator initialization."""
        generator = SignalGenerator()
        
        assert generator.MIN_CONFIDENCE == 60
        assert "price_action" in generator.WEIGHTS
        assert generator.WEIGHTS["price_action"] == 0.25
    
    def test_generate_buy_signal(self):
        """Test BUY signal generation."""
        generator = SignalGenerator()
        
        market_data = MarketData(
            symbol="SOL",
            name="Solana",
            price=142.50,
            price_change_24h=8.5  # Strong positive movement
        )
        
        indicators = TechnicalIndicators(
            rsi_14=45.0,  # Not overbought
            macd={"value": 10, "signal": 5, "histogram": 5}
        )
        
        news = [NewsItem(title="SOL partnership", sentiment=Sentiment.BULLISH)]
        
        signal = generator.generate_signal(
            market_data=market_data,
            indicators=indicators,
            news_items=news,
            news_sentiment=Sentiment.BULLISH
        )
        
        assert signal is not None
        assert signal.signal_type == SignalType.BUY
        assert signal.asset == "SOL"
        assert signal.confidence >= 60
        assert signal.stop_loss > 0
        assert len(signal.targets) > 0
    
    def test_generate_sell_signal(self):
        """Test SELL signal generation."""
        generator = SignalGenerator()
        
        market_data = MarketData(
            symbol="DOGE",
            name="Dogecoin",
            price=0.42,
            price_change_24h=-12.0  # Strong negative movement
        )
        
        indicators = TechnicalIndicators(
            rsi_14=78.0,  # Overbought
            macd={"value": -5, "signal": -2, "histogram": -3}
        )
        
        news = [NewsItem(title="DOGE crash", sentiment=Sentiment.BEARISH)]
        
        signal = generator.generate_signal(
            market_data=market_data,
            indicators=indicators,
            news_items=news,
            news_sentiment=Sentiment.BEARISH
        )
        
        assert signal is not None
        assert signal.signal_type == SignalType.SELL
        assert signal.asset == "DOGE"
        assert signal.confidence >= 60
    
    def test_generate_hold_signal(self):
        """Test HOLD signal generation for neutral conditions."""
        generator = SignalGenerator()
        
        market_data = MarketData(
            symbol="BTC",
            name="Bitcoin",
            price=97500.0,
            price_change_24h=0.5  # Minimal movement
        )
        
        indicators = TechnicalIndicators(
            rsi_14=50.0,  # Neutral
            macd={"value": 0, "signal": 0, "histogram": 0}
        )
        
        news = [NewsItem(title="BTC stable", sentiment=Sentiment.NEUTRAL)]
        
        signal = generator.generate_signal(
            market_data=market_data,
            indicators=indicators,
            news_items=news,
            news_sentiment=Sentiment.NEUTRAL
        )
        
        # Might return None if confidence too low, or HOLD signal
        if signal:
            assert signal.signal_type == SignalType.HOLD or signal.confidence < 60
    
    def test_no_signal_low_confidence(self):
        """Test that no signal is generated for low confidence scenarios."""
        generator = SignalGenerator()
        
        market_data = MarketData(
            symbol="XRP",
            name="XRP",
            price=1.50,
            price_change_24h=2.0  # Moderate movement
        )
        
        indicators = TechnicalIndicators()  # No indicators
        
        news = []  # No news
        
        signal = generator.generate_signal(
            market_data=market_data,
            indicators=indicators,
            news_items=news,
            news_sentiment=Sentiment.NEUTRAL
        )
        
        # Should either be None or have low confidence
        if signal and signal.signal_type != SignalType.HOLD:
            assert signal.confidence < 60
    
    def test_calculate_scores(self):
        """Test score calculation."""
        generator = SignalGenerator()
        
        market_data = MarketData(
            symbol="ETH",
            name="Ethereum",
            price=3500.0,
            price_change_24h=7.0
        )
        
        indicators = TechnicalIndicators(
            rsi_14=35.0,  # Slightly oversold - bullish
            macd={"value": 50, "signal": 30, "histogram": 20}
        )
        
        news = [NewsItem(title="ETH upgrade", sentiment=Sentiment.BULLISH)]
        
        scores = generator._calculate_scores(
            market_data, indicators, news, Sentiment.BULLISH
        )
        
        assert "price_action" in scores
        assert "news_sentiment" in scores
        assert "technical" in scores
        assert scores["price_action"] > 0  # Positive price change
        assert scores["news_sentiment"] > 0  # Bullish sentiment
    
    def test_risk_reward_calculation(self):
        """Test risk/reward ratio calculation."""
        generator = SignalGenerator()
        
        market_data = MarketData(
            symbol="AVAX",
            name="Avalanche",
            price=40.0,
            price_change_24h=10.0
        )
        
        indicators = TechnicalIndicators(
            rsi_14=40.0,
            macd={"value": 2, "signal": 1, "histogram": 1}
        )
        
        signal = generator.generate_signal(
            market_data=market_data,
            indicators=indicators,
            news_items=[],
            news_sentiment=Sentiment.BULLISH
        )
        
        if signal and signal.signal_type == SignalType.BUY:
            assert signal.risk_reward > 0


# =============================================================================
# AGENT TESTS
# =============================================================================

class TestCryptoSentinelAgent:
    """Tests for the main agent class."""
    
    @pytest.mark.asyncio
    async def test_agent_initialization(self):
        """Test agent initialization."""
        agent = CryptoSentinelAgent()
        
        assert agent.market_fetcher is not None
        assert agent.news_fetcher is not None
        assert agent.analyzer is not None
        assert agent.signal_generator is not None
        
        await agent.close()
    
    @pytest.mark.asyncio
    async def test_get_top_movers(self):
        """Test top movers identification."""
        agent = CryptoSentinelAgent()
        
        coins = [
            MarketData(symbol="SOL", name="Solana", price=142, price_change_24h=8.5),
            MarketData(symbol="BTC", name="Bitcoin", price=97500, price_change_24h=1.2),
            MarketData(symbol="ETH", name="Ethereum", price=3500, price_change_24h=-2.0),
            MarketData(symbol="DOGE", name="Dogecoin", price=0.4, price_change_24h=-6.5),
        ]
        
        movers = agent._get_top_movers(coins, min_change=5.0)
        
        assert len(movers) == 2  # SOL and DOGE
        assert movers[0].symbol == "SOL"  # Highest absolute change
        
        await agent.close()
    
    @pytest.mark.asyncio
    async def test_identify_risk_factors(self):
        """Test risk factor identification."""
        agent = CryptoSentinelAgent()
        
        # Scenario: Market-wide decline
        coins = [
            MarketData(symbol="BTC", name="Bitcoin", price=95000, price_change_24h=-7.0),
            MarketData(symbol="ETH", name="Ethereum", price=3200, price_change_24h=-5.0),
            MarketData(symbol="SOL", name="Solana", price=130, price_change_24h=-8.0),
        ]
        
        news = [
            NewsItem(title="Market crash", sentiment=Sentiment.BEARISH),
            NewsItem(title="FUD spreading", sentiment=Sentiment.BEARISH),
        ]
        
        risks = agent._identify_risk_factors(coins, news)
        
        assert len(risks) >= 1  # Should identify at least one risk
        
        await agent.close()
    
    @pytest.mark.asyncio
    async def test_generate_morning_brief_mock(self):
        """Test morning brief generation with mocked data."""
        agent = CryptoSentinelAgent()
        
        # Mock market data
        mock_coins = [
            MarketData(symbol="BTC", name="Bitcoin", price=97500, price_change_24h=2.0, rank=1),
            MarketData(symbol="ETH", name="Ethereum", price=3500, price_change_24h=1.5, rank=2),
            MarketData(symbol="SOL", name="Solana", price=142, price_change_24h=8.5, rank=5),
        ]
        
        mock_global = {
            "total_market_cap": 3400000000000,
            "total_volume": 150000000000,
            "btc_dominance": 54.2,
            "market_cap_change_24h": 2.1
        }
        
        mock_news = [
            NewsItem(title="BTC bullish", sentiment=Sentiment.BULLISH, mentioned_assets=["BTC"]),
            NewsItem(title="SOL partnership", sentiment=Sentiment.BULLISH, mentioned_assets=["SOL"]),
        ]
        
        # Mock the fetcher methods
        with patch.object(agent.market_fetcher, 'get_top_coins', new_callable=AsyncMock) as mock_get_coins, \
             patch.object(agent.market_fetcher, 'get_global_data', new_callable=AsyncMock) as mock_get_global, \
             patch.object(agent.market_fetcher, 'get_ohlcv', new_callable=AsyncMock) as mock_get_ohlcv, \
             patch.object(agent.news_fetcher, 'get_trending_news', new_callable=AsyncMock) as mock_get_news, \
             patch.object(agent, '_save_brief', new_callable=AsyncMock) as mock_save, \
             patch.object(agent, '_save_signal', new_callable=AsyncMock) as mock_save_signal:
            
            mock_get_coins.return_value = mock_coins
            mock_get_global.return_value = mock_global
            mock_get_news.return_value = mock_news
            mock_get_ohlcv.return_value = [
                {"timestamp": i, "open": 100+i, "high": 102+i, "low": 99+i, "close": 101+i}
                for i in range(50)
            ]
            
            brief = await agent.generate_morning_brief()
            
            assert brief is not None
            assert brief.date == datetime.utcnow().strftime("%Y-%m-%d")
            assert brief.sentiment in [Sentiment.BULLISH, Sentiment.BEARISH, Sentiment.NEUTRAL]
            assert "total_market_cap" in brief.market_summary
        
        await agent.close()
    
    @pytest.mark.asyncio
    async def test_analyze_asset_mock(self):
        """Test asset analysis with mocked data."""
        agent = CryptoSentinelAgent()
        
        mock_coin_data = {
            "name": "Bitcoin",
            "market_cap_rank": 1,
            "market_data": {
                "current_price": {"usd": 97500},
                "price_change_percentage_24h": 2.5,
                "price_change_percentage_7d": 5.0,
                "total_volume": {"usd": 45000000000},
                "market_cap": {"usd": 1900000000000}
            }
        }
        
        mock_ohlcv = [
            {"timestamp": i, "open": 95000+i*50, "high": 96000+i*50, "low": 94500+i*50, "close": 95500+i*50}
            for i in range(50)
        ]
        
        mock_news = [
            NewsItem(title="BTC news", sentiment=Sentiment.BULLISH, mentioned_assets=["BTC"])
        ]
        
        with patch.object(agent.market_fetcher, 'get_coin_data', new_callable=AsyncMock) as mock_get_coin, \
             patch.object(agent.market_fetcher, 'get_ohlcv', new_callable=AsyncMock) as mock_get_ohlcv, \
             patch.object(agent.news_fetcher, 'get_news_for_asset', new_callable=AsyncMock) as mock_get_news:
            
            mock_get_coin.return_value = mock_coin_data
            mock_get_ohlcv.return_value = mock_ohlcv
            mock_get_news.return_value = mock_news
            
            analysis = await agent.analyze_asset("BTC")
            
            assert analysis["symbol"] == "BTC"
            assert analysis["name"] == "Bitcoin"
            assert analysis["price"] == 97500
            assert "trend" in analysis
            assert "indicators" in analysis
            assert "analyzed_at" in analysis
        
        await agent.close()


# =============================================================================
# API ROUTE TESTS
# =============================================================================

class TestCryptoRoutes:
    """Tests for crypto API routes."""
    
    @pytest.mark.asyncio
    async def test_get_market_overview(self, client, auth_headers, test_user):
        """Test market overview endpoint."""
        from app.agents.crypto_sentinel.agent import get_crypto_sentinel
        
        agent = get_crypto_sentinel()
        
        mock_coins = [
            MarketData(symbol="BTC", name="Bitcoin", price=97500, price_change_24h=2.0, rank=1),
        ]
        
        mock_global = {
            "total_market_cap": 3400000000000,
            "total_volume": 150000000000,
            "btc_dominance": 54.2,
            "market_cap_change_24h": 2.1
        }
        
        with patch.object(agent.market_fetcher, 'get_top_coins', new_callable=AsyncMock) as mock_get_coins, \
             patch.object(agent.market_fetcher, 'get_global_data', new_callable=AsyncMock) as mock_get_global:
            
            mock_get_coins.return_value = mock_coins
            mock_get_global.return_value = mock_global
            
            response = await client.get("/api/v1/crypto/market", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert "global" in data
            assert "top_coins" in data
    
    @pytest.mark.asyncio
    async def test_analyze_asset_endpoint(self, client, auth_headers, test_user):
        """Test asset analysis endpoint."""
        from app.agents.crypto_sentinel.agent import get_crypto_sentinel
        
        agent = get_crypto_sentinel()
        
        mock_coin_data = {
            "name": "Bitcoin",
            "market_cap_rank": 1,
            "market_data": {
                "current_price": {"usd": 97500},
                "price_change_percentage_24h": 2.5,
                "price_change_percentage_7d": 5.0,
                "total_volume": {"usd": 45000000000},
                "market_cap": {"usd": 1900000000000}
            }
        }
        
        mock_ohlcv = [
            {"timestamp": i, "open": 95000+i*50, "high": 96000+i*50, "low": 94500+i*50, "close": 95500+i*50}
            for i in range(50)
        ]
        
        with patch.object(agent.market_fetcher, 'get_coin_data', new_callable=AsyncMock) as mock_get_coin, \
             patch.object(agent.market_fetcher, 'get_ohlcv', new_callable=AsyncMock) as mock_get_ohlcv, \
             patch.object(agent.news_fetcher, 'get_news_for_asset', new_callable=AsyncMock) as mock_get_news:
            
            mock_get_coin.return_value = mock_coin_data
            mock_get_ohlcv.return_value = mock_ohlcv
            mock_get_news.return_value = []
            
            response = await client.get("/api/v1/crypto/analyze/BTC", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert data["symbol"] == "BTC"
    
    @pytest.mark.asyncio
    async def test_get_signals_endpoint(self, client, auth_headers, test_user):
        """Test signals endpoint."""
        response = await client.get("/api/v1/crypto/signals", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "signals" in data
    
    @pytest.mark.asyncio
    async def test_crypto_routes_require_auth(self, client):
        """Test that crypto routes require authentication."""
        endpoints = [
            "/api/v1/crypto/market",
            "/api/v1/crypto/signals",
            "/api/v1/crypto/analyze/BTC",
        ]
        
        for endpoint in endpoints:
            response = await client.get(endpoint)
            assert response.status_code == 403 or response.status_code == 401

