# AGENT: CRYPTO SENTINEL
## Real-Time Market Intelligence & Signal Generation

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║   ░█████╗░██████╗░██╗░░░██╗██████╗░████████╗░█████╗░                         ║
║   ██╔══██╗██╔══██╗╚██╗░██╔╝██╔══██╗╚══██╔══╝██╔══██╗                         ║
║   ██║░░╚═╝██████╔╝░╚████╔╝░██████╔╝░░░██║░░░██║░░██║                         ║
║   ██║░░██╗██╔══██╗░░╚██╔╝░░██╔═══╝░░░░██║░░░██║░░██║                         ║
║   ╚█████╔╝██║░░██║░░░██║░░░██║░░░░░░░░██║░░░╚█████╔╝                         ║
║   ░╚════╝░╚═╝░░╚═╝░░░╚═╝░░░╚═╝░░░░░░░░╚═╝░░░░╚════╝░                         ║
║                                                                               ║
║   ░██████╗███████╗███╗░░██╗████████╗██╗███╗░░██╗███████╗██╗░░░░░             ║
║   ██╔════╝██╔════╝████╗░██║╚══██╔══╝██║████╗░██║██╔════╝██║░░░░░             ║
║   ╚█████╗░█████╗░░██╔██╗██║░░░██║░░░██║██╔██╗██║█████╗░░██║░░░░░             ║
║   ░╚═══██╗██╔══╝░░██║╚████║░░░██║░░░██║██║╚████║██╔══╝░░██║░░░░░             ║
║   ██████╔╝███████╗██║░╚███║░░░██║░░░██║██║░╚███║███████╗███████╗             ║
║   ╚═════╝░╚══════╝╚═╝░░╚══╝░░░╚═╝░░░╚═╝╚═╝░░╚══╝╚══════╝╚══════╝             ║
║                                                                               ║
║                    MARKET INTELLIGENCE AGENT                                  ║
║                         Version 2.0                                           ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

**Agent ID:** `CRYPTO_SENTINEL`  
**Location:** Cloud (DigitalOcean)  
**Primary Trigger:** Cron (08:00 AM Local Time)  
**Secondary Triggers:** On-demand, Event-based  

---

## TABLE OF CONTENTS

1. [Mission Statement](#1-mission-statement)
2. [Core Capabilities](#2-core-capabilities)
3. [Data Sources](#3-data-sources)
4. [Analysis Engine](#4-analysis-engine)
5. [Signal Generation](#5-signal-generation)
6. [Alert System](#6-alert-system)
7. [Portfolio Intelligence](#7-portfolio-intelligence)
8. [Learning System](#8-learning-system)
9. [Technical Specification](#9-technical-specification)
10. [Output Formats](#10-output-formats)

---

# 1. MISSION STATEMENT

The Crypto Sentinel is the **market intelligence arm** of ArmLenQuant. It monitors cryptocurrency markets 24/7, analyzes price movements, correlates news events, and generates actionable trading signals.

### Core Principles

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│   🔍 OBSERVE     →    Never miss a significant market move     │
│   🧠 ANALYZE     →    Understand WHY prices are moving         │
│   📊 QUANTIFY    →    Assign confidence levels to signals      │
│   🚨 ALERT       →    Notify before opportunities expire       │
│   📈 LEARN       →    Improve from historical accuracy         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Non-Execution Policy

**CRITICAL:** The Crypto Sentinel **DOES NOT** execute trades automatically.  
It generates signals and recommendations. The user makes final decisions.

---

# 2. CORE CAPABILITIES

## 2.1 Market Scanning

| Capability | Description |
|------------|-------------|
| **Price Monitoring** | Track top 50 cryptocurrencies by market cap |
| **Volume Analysis** | Detect unusual trading volume spikes |
| **Correlation Detection** | Identify coins moving together |
| **Divergence Alerts** | Spot when coins break from correlation |

## 2.2 News Intelligence

| Capability | Description |
|------------|-------------|
| **Real-Time News** | Aggregate from CryptoPanic, Twitter/X, RSS |
| **Sentiment Analysis** | Score news as bullish/bearish/neutral |
| **Event Correlation** | Link price moves to specific news events |
| **Rumor Detection** | Flag unverified but trending claims |

## 2.3 Technical Analysis

| Capability | Description |
|------------|-------------|
| **Trend Detection** | Identify uptrends, downtrends, consolidation |
| **Support/Resistance** | Calculate key price levels |
| **Momentum Indicators** | RSI, MACD, Stochastic analysis |
| **Pattern Recognition** | Detect chart patterns (double top, breakout, etc.) |

## 2.4 On-Chain Analysis

| Capability | Description |
|------------|-------------|
| **Whale Watching** | Track large wallet movements |
| **Exchange Flows** | Monitor deposits/withdrawals from exchanges |
| **Network Activity** | Analyze transaction counts, active addresses |
| **Smart Money Tracking** | Follow known successful wallets |

---

# 3. DATA SOURCES

## Primary APIs

```yaml
market_data:
  - name: CoinGecko
    endpoint: https://api.coingecko.com/api/v3
    rate_limit: 50/min
    data: prices, volumes, market_caps
  
  - name: CCXT (Multi-Exchange)
    exchanges: [binance, coinbase, kraken]
    data: order_books, trades, OHLCV

news_data:
  - name: CryptoPanic
    endpoint: https://cryptopanic.com/api/v1
    data: news, sentiment_votes
  
  - name: Twitter/X API
    data: trending_topics, influencer_posts

on_chain:
  - name: Glassnode (optional)
    data: whale_alerts, exchange_flows
  
  - name: Blockchain Explorers
    chains: [ethereum, solana, bitcoin]
    data: large_transactions
```

## Data Refresh Rates

| Data Type | Refresh Rate |
|-----------|--------------|
| Price/Volume | Every 1 minute |
| News | Every 5 minutes |
| On-Chain | Every 15 minutes |
| Technical Indicators | Every 5 minutes |

---

# 4. ANALYSIS ENGINE

## 4.1 The Morning Brief Protocol

Executed daily at 08:00 AM:

```
┌─────────────────────────────────────────────────────────────────┐
│                    MORNING BRIEF PIPELINE                       │
└─────────────────────────────────────────────────────────────────┘

    ┌───────────────────┐
    │ 1. MARKET SCAN    │
    │                   │
    │ • Fetch top 50    │
    │ • 24h changes     │
    │ • Volume spikes   │
    └────────┬──────────┘
             │
    ┌────────▼──────────┐
    │ 2. OUTLIER        │
    │    DETECTION      │
    │                   │
    │ • >5% movers      │
    │ • Volume >2x avg  │
    │ • New ATH/ATL     │
    └────────┬──────────┘
             │
    ┌────────▼──────────┐
    │ 3. NEWS           │
    │    CORRELATION    │
    │                   │
    │ • Match news to   │
    │   price moves     │
    │ • Sentiment score │
    └────────┬──────────┘
             │
    ┌────────▼──────────┐
    │ 4. TECHNICAL      │
    │    OVERLAY        │
    │                   │
    │ • Trend analysis  │
    │ • Support/resist  │
    │ • Momentum        │
    └────────┬──────────┘
             │
    ┌────────▼──────────┐
    │ 5. SIGNAL         │
    │    GENERATION     │
    │                   │
    │ • BUY/SELL/HOLD   │
    │ • Confidence %    │
    │ • Risk level      │
    └────────┬──────────┘
             │
    ┌────────▼──────────┐
    │ 6. BRIEF          │
    │    COMPILATION    │
    │                   │
    │ • Push to daily_  │
    │   brief collection│
    │ • Dashboard update│
    └───────────────────┘
```

## 4.2 Real-Time Monitoring (Background)

Runs continuously, triggers alerts on:

| Condition | Threshold | Action |
|-----------|-----------|--------|
| Flash Crash | >10% drop in 1h | Immediate alert |
| Pump Detection | >15% rise in 1h | Immediate alert |
| Volume Spike | >5x average | Add to watch list |
| Whale Move | >$10M transfer | Log + analyze |
| News Event | High impact | Correlate + alert |

## 4.3 Multi-Factor Scoring

Each potential signal is scored across multiple dimensions:

```
SIGNAL SCORE = (
    (Price_Action × 0.25) +
    (Volume_Confirmation × 0.20) +
    (News_Sentiment × 0.20) +
    (Technical_Indicators × 0.20) +
    (On_Chain_Data × 0.15)
) × Market_Regime_Modifier
```

**Market Regime Modifier:**
- Bull Market: 1.1x for BUY signals
- Bear Market: 1.1x for SELL signals
- Sideways: 0.9x for all signals (higher bar)

---

# 5. SIGNAL GENERATION

## 5.1 Signal Types

### BUY Signal

```javascript
{
  signal_type: "BUY",
  asset: "SOL",
  confidence: 80,  // 0-100
  reasoning: {
    price_action: "Broke above $140 resistance with volume",
    news_catalyst: "Solana announces Visa partnership",
    technical: "RSI at 45, MACD bullish crossover",
    on_chain: "Exchange outflows increasing"
  },
  entry_zone: {
    ideal: 142.50,
    max: 148.00
  },
  targets: [
    { price: 155.00, probability: 70 },
    { price: 170.00, probability: 45 },
    { price: 200.00, probability: 20 }
  ],
  stop_loss: 132.00,
  risk_reward: 2.8,
  time_horizon: "1-2 weeks",
  position_size_suggestion: "2-3% of portfolio"
}
```

### SELL Signal

```javascript
{
  signal_type: "SELL",
  asset: "DOGE",
  confidence: 75,
  reasoning: {
    price_action: "Double top pattern at $0.45",
    news_catalyst: "Elon Musk silent for 2 weeks",
    technical: "RSI overbought at 78, bearish divergence",
    on_chain: "Large wallets distributing"
  },
  exit_zones: [
    { price: 0.42, percentage: 50 },
    { price: 0.38, percentage: 50 }
  ],
  invalidation: 0.48
}
```

### HOLD/NEUTRAL Signal

```javascript
{
  signal_type: "HOLD",
  asset: "BTC",
  confidence: 65,
  reasoning: "Consolidating between $95K-$100K. No clear direction. Wait for breakout.",
  key_levels: {
    resistance: 100000,
    support: 95000
  },
  watch_for: [
    "Break above $100K with volume → BUY signal",
    "Break below $95K → SELL signal"
  ]
}
```

## 5.2 Confidence Calibration

| Confidence | Meaning | Historical Accuracy Target |
|------------|---------|---------------------------|
| 90-100% | Extremely high conviction | 85%+ |
| 75-89% | High conviction | 70-85% |
| 60-74% | Moderate conviction | 55-70% |
| Below 60% | Low conviction (no signal) | — |

Signals below 60% confidence are logged but **not** pushed to dashboard.

---

# 6. ALERT SYSTEM

## 6.1 Alert Priority Levels

| Level | Name | Description | Delivery |
|-------|------|-------------|----------|
| 🔴 | CRITICAL | Flash crash, >20% move | Push + Sound + Dashboard |
| 🟠 | HIGH | New signal >80% confidence | Push + Dashboard |
| 🟡 | MEDIUM | New signal 60-80% | Dashboard only |
| 🟢 | LOW | Watchlist update | Log only |

## 6.2 Alert Content

```
┌─────────────────────────────────────────────────────────────────┐
│ 🟠 HIGH PRIORITY ALERT                                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  SOL — BUY SIGNAL                                               │
│  Confidence: 80%                                                │
│                                                                 │
│  Price: $142.50 (+8.2% 24h)                                     │
│  Volume: 3.2x average                                           │
│                                                                 │
│  Catalyst: Visa partnership announcement                        │
│                                                                 │
│  Entry: $140-148 | Target: $155 | Stop: $132                    │
│  Risk/Reward: 2.8                                               │
│                                                                 │
│  [View Full Analysis]  [Add to Watchlist]  [Dismiss]            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

# 7. PORTFOLIO INTELLIGENCE

## 7.1 Portfolio Tracking (Optional Feature)

If user provides holdings, the Sentinel can:

| Feature | Description |
|---------|-------------|
| **PnL Tracking** | Real-time profit/loss on positions |
| **Risk Analysis** | Portfolio concentration, correlation risk |
| **Rebalancing Alerts** | Suggest when to rebalance |
| **Tax Lot Tracking** | Track cost basis for tax purposes |

## 7.2 Personalized Signals

With portfolio context, signals become personalized:

```javascript
{
  signal_type: "BUY",
  asset: "ETH",
  confidence: 78,
  portfolio_context: {
    current_allocation: "15%",
    suggestion: "Increase to 20%",
    reasoning: "Underweight relative to signal strength"
  }
}
```

---

# 8. LEARNING SYSTEM

## 8.1 Signal Tracking

Every signal is tracked to expiration:

```javascript
{
  signal_id: "uuid",
  asset: "SOL",
  signal_type: "BUY",
  confidence: 80,
  entry_price: 142.50,
  generated_at: ISODate,
  
  // Filled in later
  outcome: "WIN" | "LOSS" | "EXPIRED",
  exit_price: 158.00,
  return_percentage: 10.9,
  time_to_target: "8 days",
  
  // Post-mortem
  accuracy_contribution: 1,  // 1 = correct, 0 = wrong
  notes: "Hit first target, news catalyst played out as expected"
}
```

## 8.2 Performance Metrics

Dashboard displays:

| Metric | Calculation |
|--------|-------------|
| **Win Rate** | Winning signals / Total signals |
| **Avg Return** | Mean return on winning signals |
| **Avg Loss** | Mean loss on losing signals |
| **Sharpe Ratio** | Risk-adjusted return |
| **Max Drawdown** | Largest peak-to-trough loss |

## 8.3 Self-Improvement Loop

```
┌─────────────────────────────────────────────────────────────────┐
│                    LEARNING LOOP                                │
└─────────────────────────────────────────────────────────────────┘

     Weekly Analysis:
     
     1. Review all signals from past 7 days
     2. Calculate accuracy by:
        - Signal type (BUY vs SELL)
        - Asset class (BTC, alts, memes)
        - Confidence level
        - News-driven vs technical-driven
     
     3. Identify patterns:
        - "High confidence SOL signals: 90% accuracy"
        - "News-driven meme coin signals: 45% accuracy"
     
     4. Adjust weights:
        - Increase weight on high-performing factors
        - Decrease weight on low-performing factors
     
     5. Update system prompt with learnings
```

---

# 9. TECHNICAL SPECIFICATION

## 9.1 Agent Configuration

```yaml
agent:
  id: "CRYPTO_SENTINEL"
  version: "2.0.0"
  location: "CLOUD"
  
triggers:
  - type: "CRON"
    schedule: "0 8 * * *"  # 08:00 daily
    action: "morning_brief"
  
  - type: "CRON"
    schedule: "*/5 * * * *"  # Every 5 minutes
    action: "price_monitor"
  
  - type: "EVENT"
    event: "FLASH_CRASH"
    action: "emergency_analysis"
  
  - type: "MANUAL"
    action: "analyze_asset"

resources:
  cpu_limit: "500m"
  memory_limit: "512Mi"
  
dependencies:
  - ccxt
  - pandas
  - numpy
  - openai
  - requests
```

## 9.2 Database Collections

### `crypto_signals`

```javascript
{
  signal_id: "uuid",
  asset: "SOL",
  signal_type: "BUY",
  confidence: 80,
  entry_zone: { min: 140, max: 148 },
  targets: [...],
  stop_loss: 132,
  reasoning: {...},
  generated_at: ISODate,
  expires_at: ISODate,
  status: "ACTIVE" | "HIT_TARGET" | "STOPPED_OUT" | "EXPIRED"
}
```

### `crypto_watchlist`

```javascript
{
  asset: "AVAX",
  added_at: ISODate,
  reason: "Approaching key support at $35",
  alert_conditions: [
    { type: "PRICE_BELOW", value: 35, triggered: false },
    { type: "VOLUME_SPIKE", threshold: 3, triggered: false }
  ]
}
```

### `crypto_market_data`

```javascript
{
  timestamp: ISODate,
  asset: "BTC",
  price: 97500,
  volume_24h: 45000000000,
  market_cap: 1900000000000,
  change_24h: 2.3,
  technical: {
    rsi_14: 58,
    macd: { value: 150, signal: 120, histogram: 30 },
    sma_50: 94000,
    sma_200: 78000
  }
}
```

## 9.3 System Prompt

```
You are the Crypto Sentinel, the market intelligence agent for Project ArmLenQuant.

Your mission: Analyze cryptocurrency markets and generate actionable trading signals.

CORE RULES:
1. NEVER recommend trades you wouldn't make yourself
2. ALWAYS include stop-loss levels
3. NEVER chase pumps — wait for pullbacks
4. ALWAYS correlate price action with news/events
5. CONFIDENCE must be justified — don't inflate

ANALYSIS FRAMEWORK:
1. What is the price doing? (Trend, levels, volume)
2. Why is it doing that? (News, on-chain, macro)
3. What happens next? (Scenarios with probabilities)
4. What's the trade? (Entry, target, stop, R:R)
5. How confident am I? (0-100, justified)

OUTPUT FORMAT:
- Be concise but complete
- Lead with the signal
- Support with evidence
- Include risk parameters

PERSONALITY:
- Analytical, not emotional
- Cautious, not reckless
- Honest about uncertainty
- Learning from mistakes
```

---

# 10. OUTPUT FORMATS

## 10.1 Morning Brief (Daily)

```markdown
# CRYPTO MORNING BRIEF — December 2, 2025

## 🌡️ MARKET SENTIMENT: BULLISH

Total Market Cap: $3.4T (+2.1%)
Fear & Greed Index: 72 (Greed)
BTC Dominance: 54.2%

---

## 📊 TOP MOVERS (24h)

| Asset | Price | Change | Volume | Signal |
|-------|-------|--------|--------|--------|
| SOL | $142.50 | +8.2% | 3.2x | 🟢 BUY |
| AVAX | $42.30 | +5.1% | 1.8x | 🟡 WATCH |
| DOGE | $0.41 | +4.8% | 2.1x | ⚪ NEUTRAL |
| BTC | $97,500 | +1.2% | 1.0x | ⚪ NEUTRAL |

---

## 🎯 ACTIVE SIGNALS

### SOL — BUY (80% Confidence)
Entry: $140-148 | Target: $155 | Stop: $132
Catalyst: Visa partnership, strong momentum

---

## 📰 KEY NEWS

1. **Solana x Visa** — Partnership for USDC payments
2. **BTC ETF Flows** — $500M inflows yesterday
3. **Fed Watch** — Rate cut probability rising

---

## ⚠️ RISK FACTORS

- Macro: Fed meeting next week
- Technical: BTC at resistance ($100K)
- On-Chain: Some whale distribution detected
```

## 10.2 Signal Card (Real-Time)

```json
{
  "type": "SIGNAL_CARD",
  "priority": "HIGH",
  "asset": "SOL",
  "signal": "BUY",
  "confidence": 80,
  "price_current": 142.50,
  "price_change_24h": 8.2,
  "headline": "Visa partnership drives breakout",
  "entry": "140-148",
  "target": "155",
  "stop": "132",
  "risk_reward": 2.8,
  "time_horizon": "1-2 weeks"
}
```

## 10.3 Alert Message

```
🟠 CRYPTO SENTINEL ALERT

SOL BUY SIGNAL — 80% Confidence

Price: $142.50 (+8.2%)
Catalyst: Visa partnership

Entry: $140-148
Target: $155 (+9%)
Stop: $132 (-7%)
R:R: 2.8

Open ArmLenQuant for full analysis →
```

---

# APPENDIX: FUTURE ENHANCEMENTS

## Phase 2 Capabilities (Planned)

| Feature | Description |
|---------|-------------|
| **Derivatives Analysis** | Funding rates, open interest, liquidation levels |
| **DeFi Integration** | Yield farming opportunities, protocol TVL tracking |
| **Arbitrage Detection** | Cross-exchange price differences |
| **AI Narrative Tracking** | Track emerging crypto narratives (AI coins, RWA, etc.) |
| **Voice Alerts** | Audio summaries via TTS |

## Phase 3 Capabilities (Future)

| Feature | Description |
|---------|-------------|
| **Auto-Trading Mode** | Execute signals automatically (opt-in) |
| **Multi-Portfolio** | Manage multiple strategies |
| **Social Sentiment** | Reddit, Discord, Telegram analysis |
| **Whale Alert Integration** | Real-time large transaction tracking |

---

**END OF CRYPTO SENTINEL DOCUMENTATION**

*Agent Version: 2.0*  
*Last Updated: December 2025*

