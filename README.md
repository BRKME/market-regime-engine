# 📊 Market Regime Engine v3.4

Probabilistic crypto market regime detection with LP intelligence and asset allocation.

## Current Versions

| Component | Version | Status |
|-----------|---------|--------|
| Market Regime Engine | v3.4 | Production |
| LP Intelligence | v2.0.1 | Production |
| Asset Allocation | v1.4 | Production |

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run full analysis
python main.py

# Dry run (no Telegram)
python main.py --dry-run

# Backtest
python backtest.py
```

## Documentation

📚 All documentation is in the `/docs` folder:

- **[MARKET_REGIME_ENGINE_v3.4.md](docs/MARKET_REGIME_ENGINE_v3.4.md)** — Regime detection (latest)
- **[MARKET_REGIME_ENGINE_v3.3.md](docs/MARKET_REGIME_ENGINE_v3.3.md)** — Full specification
- **[LP_INTELLIGENCE_SYSTEM_v2.0.1.md](docs/LP_INTELLIGENCE_SYSTEM_v2.0.1.md)** — LP policy
- **[ASSET_ALLOCATION_POLICY_v1_4.md](docs/ASSET_ALLOCATION_POLICY_v1_4.md)** — Asset allocation with counter-cyclical logic

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    MARKET REGIME ENGINE                      │
│                         (v3.4)                               │
├─────────────────────────────────────────────────────────────┤
│  Inputs: BTC price, volume, funding, OI, macro, sentiment   │
│  Output: BULL | BEAR | RANGE | TRANSITION + probabilities   │
└──────────────────────────┬──────────────────────────────────┘
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  LP INTELLIGENCE │ │ ASSET ALLOCATION│ │   TELEGRAM      │
│     (v2.0.1)     │ │     (v1.4)      │ │    OUTPUT       │
├─────────────────┤ ├─────────────────┤ ├─────────────────┤
│ • Vol decompose │ │ • Counter-cyclic│ │ • Rich comments │
│ • Dual risk     │ │ • Don't sell    │ │ • Probabilities │
│ • LP regimes    │ │   panic         │ │ • LP matrix     │
│ • Fee/variance  │ │ • Buy fear      │ │                 │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

## Key Features (v3.4)

### Regime Detection
- 4 regimes: BULL, BEAR, RANGE, TRANSITION
- Probabilistic classification with confidence scoring
- Structural break detection

### Asset Allocation (v1.4 Counter-Cyclical)
- **Don't sell panic**: Blocks SELL when momentum < -0.70 AND vol_z > 1.5
- **Buy fear**: Accumulate on extreme panic + deep drawdown
- **Sell greed**: Take profit on euphoria + big rally
- **Mean reversion**: In RANGE regime

### LP Intelligence
- Volatility decomposition (trend/range/jump)
- Dual risk model (directional vs LP-specific)
- 8 LP regimes with specific policies

## Backtest Results

```
Metric              v1.3.1    v1.4    Improvement
─────────────────────────────────────────────────
Sells at bottom     39%       13%     -26% ✅
Sells at top        0%        14%     +14% ✅
Buys at bottom      3%        5%      +2%
```

## Output Example (v3.4)

```
🚨 ALERT: TAIL RISK
BTC $70,751

🔴 BEAR
   Phase: 8d mature · Confidence: 18%
   Tail risk: ACTIVE ↓

Probabilities:
   BULL       ░░░░░░░░░░░░ 0.04
   BEAR       ██████░░░░░░ 0.55
   RANGE      ░░░░░░░░░░░░ 0.03
   TRANSITION ████░░░░░░░░ 0.38

→ Паника на рынке. Возможно близко дно — не лучшее время продавать.

📉 DIRECTIONAL
   BTC: HOLD
   ETH: HOLD
   → COUNTER-CYCLICAL: Not selling into panic

💧 LP POLICY

          Dir Risk →
      ┌───────┬───────┐
  LP↑ │ Q3   │ Q1   │
      │ spot  │ ideal │
      ├───────┼───────┤
  LP↓ │ Q4   │[Q2]  │
      │ exit  │ LP    │
      └───────┴───────┘

   Dir: -0.82 · LP: +0.20 · F/V: 1.2x
   Exposure: 4% (max 20%)
   → LP opportunity есть, но капитал ограничен.

v3.4 · LP v2.0.1 · AA v1.4
```

## GitHub Actions Setup

### 1. Fork this repo

### 2. Set GitHub Secrets

Go to **Settings → Secrets and variables → Actions** and add:

| Secret | Description |
|--------|-------------|
| `TELEGRAM_BOT_TOKEN` | Bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | Your chat/group ID |
| `FRED_API_KEY` | FRED API key (optional, for macro data) |

### 3. Enable GitHub Actions

The engine runs at **07:00 UTC** and **19:00 UTC** daily.

## Data Sources (all free)

| Data | Source | Auth |
|------|--------|------|
| BTC price, volume | Yahoo Finance / Binance | None |
| Market cap, BTC.D | CoinGecko | None |
| Fear & Greed | alternative.me | None |
| Funding, OI | Binance | None |
| DXY, SPX, Gold | Yahoo Finance | None |
| US Treasury, M2 | FRED | Free key |

## License

MIT
