"""
Market Data Fetcher
Fetches cryptocurrency market data from APIs.
"""
import httpx
from typing import List, Dict, Optional
from datetime import datetime
from loguru import logger
from app.config import get_settings
from .models import MarketData

settings = get_settings()


class MarketDataFetcher:
    """
    Fetches market data from CoinGecko API.
    """
    
    BASE_URL = "https://api.coingecko.com/api/v3"
    
    def __init__(self):
        self.api_key = getattr(settings, 'coingecko_api_key', None)
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
    
    async def get_top_coins(self, limit: int = 50) -> List[MarketData]:
        """
        Get top coins by market cap.
        
        Args:
            limit: Number of coins to fetch
            
        Returns:
            List of MarketData objects
        """
        try:
            params = {
                "vs_currency": "usd",
                "order": "market_cap_desc",
                "per_page": limit,
                "page": 1,
                "sparkline": False,
                "price_change_percentage": "24h,7d"
            }
            
            if self.api_key:
                params["x_cg_demo_api_key"] = self.api_key
            
            response = await self.client.get(
                f"{self.BASE_URL}/coins/markets",
                params=params
            )
            response.raise_for_status()
            
            data = response.json()
            
            return [
                MarketData(
                    symbol=coin["symbol"].upper(),
                    name=coin["name"],
                    price=coin["current_price"] or 0,
                    price_change_24h=coin.get("price_change_percentage_24h") or 0,
                    price_change_7d=coin.get("price_change_percentage_7d_in_currency"),
                    volume_24h=coin.get("total_volume") or 0,
                    market_cap=coin.get("market_cap") or 0,
                    rank=coin.get("market_cap_rank") or 999,
                    last_updated=datetime.utcnow()
                )
                for coin in data
            ]
            
        except httpx.HTTPError as e:
            logger.error(f"Error fetching market data: {e}")
            raise
    
    async def get_coin_data(self, coin_id: str) -> Dict:
        """
        Get detailed data for a specific coin.
        
        Args:
            coin_id: CoinGecko coin ID (e.g., "bitcoin")
            
        Returns:
            Detailed coin data
        """
        try:
            params = {}
            if self.api_key:
                params["x_cg_demo_api_key"] = self.api_key
            
            response = await self.client.get(
                f"{self.BASE_URL}/coins/{coin_id}",
                params={
                    **params,
                    "localization": False,
                    "tickers": False,
                    "community_data": False,
                    "developer_data": False
                }
            )
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPError as e:
            logger.error(f"Error fetching coin data for {coin_id}: {e}")
            raise
    
    async def get_ohlcv(
        self,
        coin_id: str,
        days: int = 30
    ) -> List[Dict]:
        """
        Get OHLCV data for technical analysis.
        
        Args:
            coin_id: CoinGecko coin ID
            days: Number of days of history
            
        Returns:
            List of OHLCV candles
        """
        try:
            params = {
                "vs_currency": "usd",
                "days": days
            }
            if self.api_key:
                params["x_cg_demo_api_key"] = self.api_key
            
            response = await self.client.get(
                f"{self.BASE_URL}/coins/{coin_id}/ohlc",
                params=params
            )
            response.raise_for_status()
            
            data = response.json()
            
            return [
                {
                    "timestamp": candle[0],
                    "open": candle[1],
                    "high": candle[2],
                    "low": candle[3],
                    "close": candle[4]
                }
                for candle in data
            ]
            
        except httpx.HTTPError as e:
            logger.error(f"Error fetching OHLCV for {coin_id}: {e}")
            raise
    
    async def get_global_data(self) -> Dict:
        """Get global cryptocurrency market data."""
        try:
            params = {}
            if self.api_key:
                params["x_cg_demo_api_key"] = self.api_key
            
            response = await self.client.get(
                f"{self.BASE_URL}/global",
                params=params
            )
            response.raise_for_status()
            
            data = response.json()["data"]
            
            return {
                "total_market_cap": data["total_market_cap"]["usd"],
                "total_volume": data["total_volume"]["usd"],
                "btc_dominance": data["market_cap_percentage"]["btc"],
                "eth_dominance": data["market_cap_percentage"]["eth"],
                "market_cap_change_24h": data["market_cap_change_percentage_24h_usd"],
                "active_cryptocurrencies": data["active_cryptocurrencies"]
            }
            
        except httpx.HTTPError as e:
            logger.error(f"Error fetching global data: {e}")
            raise


# Symbol to CoinGecko ID mapping
# Note: Some coins like CC (unclear what it is) and HYPE (Hyperliquid) may not have
# OHLCV data available on CoinGecko's free tier - they'll be skipped gracefully
SYMBOL_TO_ID = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "AVAX": "avalanche-2",
    "DOGE": "dogecoin",
    "XRP": "ripple",
    "ADA": "cardano",
    "DOT": "polkadot",
    "MATIC": "matic-network",
    "POL": "matic-network",  # Polygon rebranded
    "LINK": "chainlink",
    "UNI": "uniswap",
    "ATOM": "cosmos",
    "LTC": "litecoin",
    "BCH": "bitcoin-cash",
    "NEAR": "near",
    "APT": "aptos",
    "ARB": "arbitrum",
    "OP": "optimism",
    "SUI": "sui",
    "SEI": "sei-network",
    "ZEC": "zcash",
    "TAO": "bittensor",
    "BNB": "binancecoin",
    "TRX": "tron",
    "SHIB": "shiba-inu",
    "TON": "the-open-network",
    "PEPE": "pepe",
    "HBAR": "hedera-hashgraph",
    "STX": "stacks",
    "IMX": "immutable-x",
    "INJ": "injective-protocol",
    "FIL": "filecoin",
    "RENDER": "render-token",
    "VET": "vechain",
    "MKR": "maker",
    "AAVE": "aave",
    "GRT": "the-graph",
    "FTM": "fantom",
    "THETA": "theta-token",
    "RUNE": "thorchain",
    "ALGO": "algorand",
    "FLOW": "flow",
    "XLM": "stellar",
    "EOS": "eos",
    "SAND": "the-sandbox",
    "MANA": "decentraland",
    "AXS": "axie-infinity",
    "CRV": "curve-dao-token",
    "LDO": "lido-dao",
    "HYPE": "hyperliquid",  # May not have OHLCV data
    "WIF": "dogwifcoin",
    "BONK": "bonk",
    "JUP": "jupiter-exchange-solana",
    "PYTH": "pyth-network",
    "JTO": "jito-governance-token",
}


def symbol_to_coingecko_id(symbol: str) -> str:
    """Convert trading symbol to CoinGecko ID."""
    return SYMBOL_TO_ID.get(symbol.upper(), symbol.lower())

