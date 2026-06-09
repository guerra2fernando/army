"""
Crypto Sentinel Data Models
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class SignalType(str, Enum):
    """Trading signal types."""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class Sentiment(str, Enum):
    """Market sentiment types."""
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


class MarketData(BaseModel):
    """Market data for a single asset."""
    symbol: str
    name: str
    price: float
    price_change_24h: float = 0.0
    price_change_7d: Optional[float] = None
    volume_24h: float = 0.0
    market_cap: float = 0.0
    rank: int = 999
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TechnicalIndicators(BaseModel):
    """Technical analysis indicators."""
    rsi_14: Optional[float] = None
    macd: Optional[Dict[str, float]] = None  # value, signal, histogram
    sma_20: Optional[float] = None
    sma_50: Optional[float] = None
    sma_200: Optional[float] = None
    ema_12: Optional[float] = None
    ema_26: Optional[float] = None
    bollinger_bands: Optional[Dict[str, float]] = None  # upper, middle, lower
    volume_sma_20: Optional[float] = None
    volume_ratio: Optional[float] = None  # current vs average
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class NewsItem(BaseModel):
    """News article."""
    title: str
    source: str = "Unknown"
    url: str = ""
    published_at: datetime = Field(default_factory=datetime.utcnow)
    sentiment: Optional[Sentiment] = None
    relevance_score: float = 0.0
    mentioned_assets: List[str] = Field(default_factory=list)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TradingSignal(BaseModel):
    """Trading signal."""
    signal_id: str
    asset: str
    signal_type: SignalType
    confidence: float = Field(..., ge=0, le=100)  # 0-100
    entry_zone: Dict[str, float] = Field(default_factory=dict)  # min, max
    targets: List[Dict[str, float]] = Field(default_factory=list)  # price, probability
    stop_loss: float = 0.0
    risk_reward: float = 0.0
    time_horizon: str = "1-2 weeks"
    reasoning: Dict[str, str] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = "ACTIVE"
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class MorningBrief(BaseModel):
    """Daily morning brief."""
    date: str
    sentiment: Sentiment
    market_summary: Dict[str, Any] = Field(default_factory=dict)  # total_cap, btc_dominance, etc.
    top_movers: List[Dict[str, Any]] = Field(default_factory=list)
    signals: List[TradingSignal] = Field(default_factory=list)
    news_highlights: List[NewsItem] = Field(default_factory=list)
    risk_factors: List[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

