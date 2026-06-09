"""
Technical Analysis Engine
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from loguru import logger
from .models import TechnicalIndicators


class TechnicalAnalyzer:
    """
    Performs technical analysis on price data.
    """
    
    @staticmethod
    def calculate_indicators(ohlcv_data: List[Dict]) -> TechnicalIndicators:
        """
        Calculate technical indicators from OHLCV data.
        
        Args:
            ohlcv_data: List of OHLCV candles
            
        Returns:
            TechnicalIndicators object
        """
        if len(ohlcv_data) < 20:
            return TechnicalIndicators()
        
        try:
            # Convert to DataFrame
            df = pd.DataFrame(ohlcv_data)
            df['close'] = pd.to_numeric(df['close'], errors='coerce')
            df['high'] = pd.to_numeric(df['high'], errors='coerce')
            df['low'] = pd.to_numeric(df['low'], errors='coerce')
            
            # Drop any NaN values
            df = df.dropna()
            
            if len(df) < 20:
                return TechnicalIndicators()
            
            indicators = TechnicalIndicators()
            
            # RSI (14 period)
            if len(df) >= 15:
                indicators.rsi_14 = TechnicalAnalyzer._calculate_rsi(df['close'], 14)
            
            # MACD (12, 26, 9)
            if len(df) >= 27:
                indicators.macd = TechnicalAnalyzer._calculate_macd(df['close'])
            
            # SMAs
            indicators.sma_20 = float(df['close'].rolling(window=20).mean().iloc[-1])
            
            if len(df) >= 50:
                indicators.sma_50 = float(df['close'].rolling(window=50).mean().iloc[-1])
            
            if len(df) >= 200:
                indicators.sma_200 = float(df['close'].rolling(window=200).mean().iloc[-1])
            
            # EMAs
            if len(df) >= 12:
                indicators.ema_12 = float(df['close'].ewm(span=12, adjust=False).mean().iloc[-1])
            
            if len(df) >= 26:
                indicators.ema_26 = float(df['close'].ewm(span=26, adjust=False).mean().iloc[-1])
            
            # Bollinger Bands
            indicators.bollinger_bands = TechnicalAnalyzer._calculate_bollinger(df['close'])
            
            return indicators
            
        except Exception as e:
            logger.error(f"Error calculating indicators: {e}")
            return TechnicalIndicators()
    
    @staticmethod
    def _calculate_rsi(prices: pd.Series, period: int = 14) -> Optional[float]:
        """Calculate RSI indicator."""
        try:
            delta = prices.diff()
            gain = delta.where(delta > 0, 0).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            
            # Avoid division by zero
            loss = loss.replace(0, 0.0001)
            
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            result = rsi.iloc[-1]
            return float(result) if not pd.isna(result) else None
            
        except Exception as e:
            logger.error(f"Error calculating RSI: {e}")
            return None
    
    @staticmethod
    def _calculate_macd(
        prices: pd.Series,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9
    ) -> Dict[str, float]:
        """Calculate MACD indicator."""
        try:
            ema_fast = prices.ewm(span=fast, adjust=False).mean()
            ema_slow = prices.ewm(span=slow, adjust=False).mean()
            
            macd_line = ema_fast - ema_slow
            signal_line = macd_line.ewm(span=signal, adjust=False).mean()
            histogram = macd_line - signal_line
            
            return {
                "value": float(macd_line.iloc[-1]),
                "signal": float(signal_line.iloc[-1]),
                "histogram": float(histogram.iloc[-1])
            }
            
        except Exception as e:
            logger.error(f"Error calculating MACD: {e}")
            return {"value": 0, "signal": 0, "histogram": 0}
    
    @staticmethod
    def _calculate_bollinger(
        prices: pd.Series,
        period: int = 20,
        std_dev: float = 2.0
    ) -> Dict[str, float]:
        """Calculate Bollinger Bands."""
        try:
            sma = prices.rolling(window=period).mean()
            std = prices.rolling(window=period).std()
            
            return {
                "upper": float(sma.iloc[-1] + std_dev * std.iloc[-1]),
                "middle": float(sma.iloc[-1]),
                "lower": float(sma.iloc[-1] - std_dev * std.iloc[-1])
            }
            
        except Exception as e:
            logger.error(f"Error calculating Bollinger Bands: {e}")
            return {"upper": 0, "middle": 0, "lower": 0}
    
    @staticmethod
    def determine_trend(indicators: TechnicalIndicators, current_price: float) -> str:
        """
        Determine trend based on indicators.
        
        Returns: "BULLISH", "BEARISH", or "NEUTRAL"
        """
        signals = []
        
        # RSI signals
        if indicators.rsi_14 is not None:
            if indicators.rsi_14 > 70:
                signals.append(-1)  # Overbought
            elif indicators.rsi_14 < 30:
                signals.append(1)   # Oversold
            else:
                # Neutral but slight bias based on RSI position
                signals.append((50 - indicators.rsi_14) / 50)
        
        # MACD signals
        if indicators.macd is not None:
            if indicators.macd["histogram"] > 0:
                signals.append(1)
            elif indicators.macd["histogram"] < 0:
                signals.append(-1)
            else:
                signals.append(0)
        
        # Price vs SMA signals
        if indicators.sma_50 is not None:
            if current_price > indicators.sma_50:
                signals.append(1)
            else:
                signals.append(-1)
        
        if not signals:
            return "NEUTRAL"
        
        avg_signal = sum(signals) / len(signals)
        
        if avg_signal > 0.3:
            return "BULLISH"
        elif avg_signal < -0.3:
            return "BEARISH"
        else:
            return "NEUTRAL"

