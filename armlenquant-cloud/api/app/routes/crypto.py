"""
Crypto API Routes
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, Dict, Any
from loguru import logger

from app.utils.auth import get_current_user
from app.agents.crypto_sentinel.agent import get_crypto_sentinel
from app.agents.crypto_sentinel.models import TradingSignal

router = APIRouter(prefix="/crypto", tags=["Crypto"])


def transform_signal_for_frontend(signal: TradingSignal) -> Dict[str, Any]:
    """Transform TradingSignal to match frontend expected format."""
    signal_dict = signal.dict()
    
    # Map backend fields to frontend expected fields
    return {
        "signal_id": signal_dict.get("signal_id"),
        "symbol": signal_dict.get("asset"),  # asset -> symbol
        "signal_type": signal_dict.get("signal_type"),
        "confidence": signal_dict.get("confidence"),
        "entry_price": signal_dict.get("entry_zone", {}).get("min", 0),  # entry_zone.min -> entry_price
        "target_price": signal_dict.get("targets", [{}])[0].get("price") if signal_dict.get("targets") else None,  # first target
        "stop_loss": signal_dict.get("stop_loss"),
        "reasoning": signal_dict.get("reasoning"),  # Keep as-is, frontend handles both string and object
        "created_at": signal_dict.get("generated_at"),  # generated_at -> created_at
        "expires_at": signal_dict.get("expires_at"),
        "status": signal_dict.get("status", "ACTIVE"),
    }


@router.get("/market")
async def get_market_overview(current_user: dict = Depends(get_current_user)):
    """Get market overview."""
    agent = get_crypto_sentinel()
    
    top_coins = await agent.market_fetcher.get_top_coins(limit=20)
    global_data = await agent.market_fetcher.get_global_data()
    
    # Transform to match frontend expected format
    return {
        "global": {
            "total_market_cap": global_data.get("total_market_cap", 0),
            "total_volume_24h": global_data.get("total_volume", 0),
            "btc_dominance": global_data.get("btc_dominance", 0),
            "active_cryptocurrencies": global_data.get("active_cryptocurrencies", 0),
            "market_cap_change_24h": global_data.get("market_cap_change_24h", 0),
        },
        "top_coins": [
            {
                "id": c.symbol.lower(),
                "symbol": c.symbol,
                "name": c.name,
                "current_price": c.price,
                "market_cap": c.market_cap,
                "market_cap_rank": c.rank,
                "price_change_percentage_24h": c.price_change_24h,
                "price_change_percentage_7d": c.price_change_7d,
                "total_volume": c.volume_24h,
                "high_24h": c.price * 1.02,  # Approximate if not available
                "low_24h": c.price * 0.98,   # Approximate if not available
            }
            for c in top_coins
        ]
    }


@router.get("/brief")
async def get_morning_brief(
    date: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get the morning brief for today or a specific date."""
    from app.db import Database
    from datetime import datetime
    
    briefs = Database.get_collection("daily_brief")
    
    query_date = date or datetime.utcnow().strftime("%Y-%m-%d")
    brief = await briefs.find_one({"date": query_date})
    
    if not brief:
        raise HTTPException(status_code=404, detail="Brief not found")
    
    brief.pop("_id", None)
    crypto_section = brief.get("crypto", {})
    top_movers = [
        {
            "coin": mover.get("coin") or mover.get("symbol") or mover.get("name", ""),
            "change": mover.get("change") or mover.get("price_change_24h", 0),
        }
        for mover in crypto_section.get("top_movers", [])
    ]
    signals = crypto_section.get("signals", [])
    
    return {
        "date": brief.get("date"),
        "market_sentiment": crypto_section.get("sentiment"),
        "summary": crypto_section.get("summary")
        or f"Market cap ${crypto_section.get('market_summary', {}).get('total_market_cap', 0) / 1e12:.2f}T. BTC dominance {crypto_section.get('market_summary', {}).get('btc_dominance', 0):.1f}%.",
        "top_movers": top_movers[:5],
        "signals": [
            transform_signal_for_frontend(TradingSignal(**s)) for s in signals if s
        ],
        "news_highlights": [
            n.get("title", "") if isinstance(n, dict) else str(n)
            for n in crypto_section.get("news_highlights", [])
        ],
        "created_at": brief.get("generated_at"),
    }


@router.post("/brief/generate")
async def generate_brief(current_user: dict = Depends(get_current_user)):
    """Manually trigger morning brief generation."""
    agent = get_crypto_sentinel()
    brief = await agent.generate_morning_brief()
    return brief.dict()


@router.get("/analyze/{symbol}")
async def analyze_asset(
    symbol: str,
    current_user: dict = Depends(get_current_user)
):
    """Analyze a specific cryptocurrency."""
    agent = get_crypto_sentinel()
    analysis = await agent.analyze_asset(symbol.upper())
    
    # Transform analysis to match frontend expected format
    return {
        "symbol": analysis.get("symbol"),
        "name": analysis.get("name"),
        "price": analysis.get("price"),
        "change_24h": analysis.get("change_24h"),
        "change_7d": analysis.get("change_7d"),
        "market_cap": analysis.get("market_cap"),
        "volume_24h": analysis.get("volume_24h"),
        "sentiment": analysis.get("news_sentiment"),
        "indicators": {
            "rsi": analysis.get("indicators", {}).get("rsi_14"),
            "macd": analysis.get("indicators", {}).get("macd"),
            "sma_20": analysis.get("indicators", {}).get("sma_20"),
            "sma_50": analysis.get("indicators", {}).get("sma_50"),
            "bollinger": analysis.get("indicators", {}).get("bollinger_bands"),
        },
        "signal": transform_signal_for_frontend(TradingSignal(**analysis["signal"])) if analysis.get("signal") else None,
        "summary": f"{analysis.get('trend', 'NEUTRAL')} trend. {analysis.get('news_sentiment', 'NEUTRAL')} news sentiment.",
        "analyzed_at": analysis.get("analyzed_at"),
    }


@router.get("/signals")
async def get_signals(current_user: dict = Depends(get_current_user)):
    """Get active trading signals."""
    agent = get_crypto_sentinel()
    signals = await agent.get_active_signals()
    # Transform signals to match frontend expected format
    return {"signals": [transform_signal_for_frontend(s) for s in signals]}


@router.get("/signals/{signal_id}")
async def get_signal(
    signal_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific signal by ID."""
    from app.db import Database
    
    signals = Database.get_collection("crypto_signals")
    signal = await signals.find_one({"signal_id": signal_id})
    
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
    
    signal.pop("_id", None)
    return signal

