# 📊 Market Regime Engine v3.3

Probabilistic crypto market regime detection system.  
Runs on GitHub Actions. Sends Telegram alerts twice daily.

```
REGIME ∈ { BULL, BEAR, RANGE, TRANSITION }
```

## Architecture

```
Data Sources (free APIs)
    │
    ▼
┌──────────────┐     ┌────────────┐     ┌──────────────┐
│  Binance     │     │  CoinGecko │     │  FRED / YF   │
│  price/fund  │     │  MCap/BTC.D│     │  macro data  │
└──────┬───────┘     └─────┬──────┘     └──────┬───────┘
       │                   │                   │
       └───────────┬───────┘───────────────────┘
                   ▼
          ┌────────────────┐
          │  Data Pipeline │
          │  normalize +   │
          │  break detect  │
          └───────┬────────┘
                  ▼
          ┌────────────────┐
          │  5 Buckets     │
          │  M S R Sent Mac│
          └───────┬────────┘
                  ▼
          ┌────────────────┐
          │  Logits →      │
          │  Softmax →     │
          │  EMA → Switch  │
          └───────┬────────┘
                  ▼
          ┌────────────────┐
          │  Confidence +  │
          │  Churn + Health│
          └───────┬────────┘
                  ▼
          ┌────────────────┐
          │  Telegram Bot  │
          │  2x daily      │
          └────────────────┘
```

## Quick Start

### 1. Fork this repo

### 2. Set GitHub Secrets

Go to **Settings → Secrets and variables → Actions** and add:

| Secret | Description | Source |
|--------|-------------|--------|
| `TELEGRAM_BOT_TOKEN` | Bot token from @BotFather | [Create bot](https://t.me/BotFather) |
| `TELEGRAM_CHAT_ID` | Your chat/group ID | Send msg to bot, check `https://api.telegram.org/bot<TOKEN>/getUpdates` |
| `FRED_API_KEY` | FRED API key (macro data) | [Register free](https://fred.stlouisfed.org/docs/api/api_key.html) |

### 3. Enable GitHub Actions

Actions tab → Enable workflows.  
The engine runs at **07:00 UTC** and **19:00 UTC** daily.

### 4. Manual trigger

Actions tab → `Regime Check` → `Run workflow`

## Local Development

```bash
git clone https://github.com/YOUR_USER/market-regime-engine.git
cd market-regime-engine

python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env with your API keys

# Run
python main.py
```

## Data Sources (all free)

| Data | Source | Auth |
|------|--------|------|
| BTC price, volume, OHLC | Binance public API | None |
| Total market cap, BTC.D | CoinGecko free API | None |
| Fear & Greed Index | alternative.me | None |
| Funding rate, OI | Binance public API | None |
| DXY, SPX, Gold | Yahoo Finance (yfinance) | None |
| US Treasury yields, M2 | FRED API | Free key |

## Output Example

```
══════════════════════════════════
  REGIME ENGINE v3.3 — 2026-02-07
══════════════════════════════════
  
  🟢 Active Regime: BULL
  📊 Confidence: 0.68
  📅 Days in Regime: 6
  
  Probabilities:
    BULL  ████████████░  0.58
    BEAR  ██░░░░░░░░░░  0.10
    RANGE ████░░░░░░░░  0.20
    TRANS ███░░░░░░░░░  0.12
  
  Buckets:
    Momentum:  +0.45
    Stability: +0.30
    Rotation:  -0.15
    Sentiment: +0.35
    Macro:     +0.20
  
  💡 Hint: directional / wide_range
  ⚠️ Flags: none
══════════════════════════════════
```

## Model Specification

Full methodology: see `docs/MARKET_REGIME_ENGINE_v3_3.md`

## License

MIT
