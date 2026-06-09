"""
Trading Signal Generator
"""
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from uuid import uuid4
from loguru import logger

from .models import (
    TradingSignal, SignalType, MarketData, 
    TechnicalIndicators, NewsItem, Sentiment
)


class SignalGenerator:
    """
    Generates trading signals based on multiple factors.
    """
    
    # Weighting factors
    WEIGHTS = {
        "price_action": 0.25,
        "volume": 0.20,
        "news_sentiment": 0.20,
        "technical": 0.20,
        "on_chain": 0.15
    }
    
    MIN_CONFIDENCE = 60  # Minimum confidence to generate signal
    
    def generate_signal(
        self,
        market_data: MarketData,
        indicators: TechnicalIndicators,
        news_items: List[NewsItem],
        news_sentiment: Sentiment
    ) -> Optional[TradingSignal]:
        """
        Generate a trading signal for an asset.
        
        Args:
            market_data: Current market data
            indicators: Technical indicators
            news_items: Recent news
            news_sentiment: Overall news sentiment
            
        Returns:
            TradingSignal if confidence >= threshold, else None
        """
        # Calculate component scores
        scores = self._calculate_scores(
            market_data, indicators, news_items, news_sentiment
        )
        
        # Calculate weighted total
        total_score = sum(
            scores[key] * self.WEIGHTS[key]
            for key in self.WEIGHTS
            if key in scores
        )
        
        # Determine signal type and confidence
        if total_score > 0.2:
            signal_type = SignalType.BUY
            confidence = min(50 + total_score * 50, 95)
        elif total_score < -0.2:
            signal_type = SignalType.SELL
            confidence = min(50 + abs(total_score) * 50, 95)
        else:
            signal_type = SignalType.HOLD
            confidence = 50 + (0.2 - abs(total_score)) * 100
        
        # Only return signal if confidence meets threshold for BUY/SELL
        if signal_type != SignalType.HOLD and confidence < self.MIN_CONFIDENCE:
            return None
        
        # Generate signal details
        signal = self._build_signal(
            market_data=market_data,
            signal_type=signal_type,
            confidence=confidence,
            scores=scores,
            indicators=indicators,
            news_sentiment=news_sentiment
        )
        
        return signal
    
    def _calculate_scores(
        self,
        market_data: MarketData,
        indicators: TechnicalIndicators,
        news_items: List[NewsItem],
        news_sentiment: Sentiment
    ) -> Dict[str, float]:
        """Calculate individual component scores (-1 to 1)."""
        scores = {}
        
        # Price Action Score
        price_change = market_data.price_change_24h
        if price_change > 10:
            scores["price_action"] = 0.8
        elif price_change > 5:
            scores["price_action"] = 0.5
        elif price_change > 0:
            scores["price_action"] = 0.2
        elif price_change > -5:
            scores["price_action"] = -0.2
        elif price_change > -10:
            scores["price_action"] = -0.5
        else:
            scores["price_action"] = -0.8
        
        # Volume Score (simplified - would need historical data for proper comparison)
        scores["volume"] = 0.0  # Neutral without historical data
        
        # News Sentiment Score
        if news_sentiment == Sentiment.BULLISH:
            scores["news_sentiment"] = 0.7
        elif news_sentiment == Sentiment.BEARISH:
            scores["news_sentiment"] = -0.7
        else:
            scores["news_sentiment"] = 0.0
        
        # Technical Score
        tech_score = 0.0
        factors = 0
        
        if indicators.rsi_14 is not None:
            factors += 1
            if indicators.rsi_14 < 30:
                tech_score += 0.8  # Oversold - bullish
            elif indicators.rsi_14 > 70:
                tech_score -= 0.8  # Overbought - bearish
            else:
                tech_score += (50 - indicators.rsi_14) / 100  # Slight bias
        
        if indicators.macd is not None:
            factors += 1
            if indicators.macd["histogram"] > 0:
                tech_score += 0.5
            else:
                tech_score -= 0.5
        
        if factors > 0:
            scores["technical"] = tech_score / factors
        else:
            scores["technical"] = 0.0
        
        # On-chain (placeholder - would need on-chain data source)
        scores["on_chain"] = 0.0
        
        return scores
    
    def _build_signal(
        self,
        market_data: MarketData,
        signal_type: SignalType,
        confidence: float,
        scores: Dict[str, float],
        indicators: TechnicalIndicators,
        news_sentiment: Sentiment
    ) -> TradingSignal:
        """Build the complete signal object."""
        current_price = market_data.price
        
        # Calculate entry zone (within 2% of current)
        if signal_type == SignalType.BUY:
            entry_zone = {
                "min": round(current_price * 0.98, 8),
                "max": round(current_price * 1.02, 8)
            }
            # Targets based on confidence
            targets = [
                {"price": round(current_price * 1.05, 8), "probability": 70},
                {"price": round(current_price * 1.10, 8), "probability": 45},
                {"price": round(current_price * 1.15, 8), "probability": 20},
            ]
            stop_loss = round(current_price * 0.93, 8)
        elif signal_type == SignalType.SELL:
            entry_zone = {
                "min": round(current_price * 0.98, 8),
                "max": round(current_price * 1.02, 8)
            }
            targets = [
                {"price": round(current_price * 0.95, 8), "probability": 70},
                {"price": round(current_price * 0.90, 8), "probability": 45},
            ]
            stop_loss = round(current_price * 1.07, 8)
        else:
            entry_zone = {"min": current_price, "max": current_price}
            targets = []
            stop_loss = current_price
        
        # Calculate risk/reward
        if targets and signal_type == SignalType.BUY:
            reward = targets[0]["price"] - current_price
            risk = current_price - stop_loss
            risk_reward = round(reward / risk, 2) if risk > 0 else 0
        elif targets and signal_type == SignalType.SELL:
            reward = current_price - targets[0]["price"]
            risk = stop_loss - current_price
            risk_reward = round(reward / risk, 2) if risk > 0 else 0
        else:
            risk_reward = 0
        
        # Build reasoning
        reasoning = {
            "price_action": f"{market_data.price_change_24h:+.1f}% in 24h",
            "technical": f"RSI: {indicators.rsi_14:.0f}" if indicators.rsi_14 else "N/A",
            "news_sentiment": news_sentiment.value,
            "confidence_factors": str(scores)
        }
        
        return TradingSignal(
            signal_id=str(uuid4()),
            asset=market_data.symbol,
            signal_type=signal_type,
            confidence=round(confidence, 1),
            entry_zone=entry_zone,
            targets=targets,
            stop_loss=round(stop_loss, 8),
            risk_reward=risk_reward,
            time_horizon="1-2 weeks",
            reasoning=reasoning,
            generated_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=7)
        )

