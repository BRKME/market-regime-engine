# Asset Allocation Policy Layer v1.4

> **Это операционная спецификация, не концепция.**

---

## MODEL IDENTITY

```
┌─────────────────────────────────────────────────────────────┐
│  Это:     CONSERVATIVE CAPITAL PRESERVATION POLICY          │
│  + NEW:   COUNTER-CYCLICAL LOGIC                            │
│  Не это:  ALPHA GENERATION SYSTEM                          │
│  Не это:  CAPITAL OPTIMIZER                                │
│  Не это:  TACTICAL TRADING STRATEGY                        │
└─────────────────────────────────────────────────────────────┘
```

---

## v1.4 CHANGES: COUNTER-CYCLICAL LOGIC

### Problem (v1.3.1)
```
Backtest показал:
- Sells at bottom: 39% (ПЛОХО)
- Buys at bottom: 3% (ПЛОХО)
- Model продаёт на дне и покупает на вершине
```

### Solution (v1.4)
```
1. DON'T SELL PANIC
   - Блокировать SELL/STRONG_SELL когда:
   - momentum < -0.70 AND vol_z > 1.5
   
2. ACCUMULATE ON FEAR
   - Покупать когда:
   - momentum < -0.80 AND vol_z > 2.0 AND returns_30d < -20%
   
3. TAKE PROFIT ON GREED
   - Продавать когда:
   - momentum > 0.70 AND confidence > 0.60 AND returns_30d > 30%

4. MEAN REVERSION IN RANGE
   - Panic in RANGE → BUY
   - Euphoria in RANGE → SELL
```

### Backtest Results
```
Metric              v1.3.1    v1.4    Improvement
─────────────────────────────────────────────────
Sells at bottom     39%       13%     -26% ✅
Sells at top        0%        14%     +14% ✅
Buys at bottom      3%        5%      +2%
```

---

## EXPLICIT TRADE-OFFS (READ BEFORE USE)

| # | Trade-off | What You Get | What You Lose |
|---|-----------|--------------|---------------|
| 1 | **TRANSITION = don't play** | Avoids false breakouts | Misses early trends |
| 2 | **Confidence as single scalar** | Simple gates | No regime vs direction nuance |
| 3 | **Counter-cyclical blocks** | Doesn't sell bottoms | May hold through further decline |
| 4 | **Discrete position sizing** | Executable rules | No edge-proportional sizing |
| 5 | **ETH ≤ BTC always** | Risk hierarchy | ETH never leads |
| 6 | **No EV calculation** | Rule-based simplicity | No payoff optimization |

**If these trade-offs don't fit your strategy — this model is not for you.**

---

## 1. Counter-Cyclical Conditions

### Panic Detection (proxy for RSI < 25)
```python
is_panic = momentum < -0.70 and vol_z > 1.5
is_extreme_panic = momentum < -0.80 and vol_z > 2.0
is_deep_drawdown = returns_30d < -0.20
```

### Euphoria Detection (proxy for RSI > 75)
```python
is_euphoria = momentum > 0.70 and confidence > 0.60
is_extreme_euphoria = momentum > 0.80 and confidence > 0.70
is_big_rally = returns_30d > 0.30
```

---

## 2. Actions

| Action | BTC Size | ETH Size | When Allowed |
|--------|----------|----------|--------------|
| STRONG_BUY | +20% portfolio | ❌ Never | conf ≥ 0.70, BULL, mom > 0.50, NOT euphoria |
| BUY | +10% portfolio | +5% portfolio | conf ≥ 0.50, BULL, mom > 0, NOT euphoria |
| HOLD | 0% | 0% | Always |
| SELL | −15% position | −20% position | conf ≥ 0.50, BEAR, mom < 0, NOT panic |
| STRONG_SELL | −50% position | −70% position | conf ≥ 0.60, NOT panic |

---

## 3. Confidence Gates (unchanged)

| Confidence | Allowed Actions |
|------------|-----------------|
| < 0.40 | HOLD only |
| 0.40 – 0.49 | HOLD only |
| 0.50 – 0.59 | BUY, SELL, HOLD |
| 0.60 – 0.69 | BUY, SELL, STRONG_SELL, HOLD |
| ≥ 0.70 | All actions |

---

## 4. Regime Gates (v1.4 updated)

| Regime | Allowed Actions | v1.4 Changes |
|--------|-----------------|--------------|
| BULL | STRONG_BUY, BUY, HOLD | Blocked if euphoria |
| BEAR | STRONG_SELL, SELL, HOLD | Blocked if panic |
| RANGE | HOLD, BUY, SELL | Mean reversion added |
| TRANSITION | HOLD, SELL, STRONG_SELL | Unchanged |

---

## 5. Decision Algorithm (v1.4)

```python
def compute(regime, conf, risk, mom, tail_risk, tail_pol, asset, btc_action, 
            last_action, last_date, history, vol_z, returns_30d):
    
    # ══════════════════════════════════════════════════════
    # v1.4 COUNTER-CYCLICAL DETECTION
    # ══════════════════════════════════════════════════════
    is_panic = mom < -0.70 and vol_z > 1.5
    is_extreme_panic = mom < -0.80 and vol_z > 2.0
    is_deep_drawdown = returns_30d < -0.20
    
    is_euphoria = mom > 0.70 and conf > 0.60
    is_extreme_euphoria = mom > 0.80 and conf > 0.70
    is_big_rally = returns_30d > 0.30
    
    panic_block_sell = is_panic or is_extreme_panic
    
    # ══════════════════════════════════════════════════════
    # RULE 1: Accumulate on fear
    # ══════════════════════════════════════════════════════
    if is_extreme_panic and is_deep_drawdown and asset == "BTC":
        return "BUY"  # Counter-cyclical accumulation
    
    # ══════════════════════════════════════════════════════
    # RULE 2: Take profit on greed
    # ══════════════════════════════════════════════════════
    if is_extreme_euphoria and is_big_rally and asset == "BTC":
        return "SELL"  # Counter-cyclical profit taking
    
    # ══════════════════════════════════════════════════════
    # RULE 3: Tail risk (modified)
    # ══════════════════════════════════════════════════════
    if tail_risk and tail_pol == "downside":
        if panic_block_sell:
            return "HOLD"  # Don't sell into panic
        else:
            return "STRONG_SELL"
    
    if tail_risk and tail_pol == "upside":
        return "SELL"  # Take profit
    
    # ══════════════════════════════════════════════════════
    # Standard logic with counter-cyclical blocks
    # ══════════════════════════════════════════════════════
    
    if conf < 0.40:
        return "HOLD"
    
    if regime == "BULL":
        if is_euphoria:
            return "HOLD"  # Don't buy euphoria
        elif conf >= 0.70 and mom > 0.50:
            return "STRONG_BUY"
        elif conf >= 0.50 and mom > 0:
            return "BUY"
        else:
            return "HOLD"
    
    elif regime == "BEAR":
        if panic_block_sell:
            return "HOLD"  # Don't sell panic
        elif conf >= 0.60 and mom < -0.50:
            return "STRONG_SELL"
        elif conf >= 0.50 and mom < 0:
            return "SELL"
        else:
            return "HOLD"
    
    elif regime == "RANGE":
        # Mean reversion
        if is_panic and asset == "BTC":
            return "BUY"
        elif is_euphoria and asset == "BTC":
            return "SELL"
        else:
            return "HOLD"
    
    else:  # TRANSITION
        if risk < -0.30 and conf >= 0.50 and not panic_block_sell:
            return "SELL"
        else:
            return "HOLD"
```

---

## 6. Rule Table (v1.4)

| # | Condition | Action | BTC | ETH |
|---|-----------|--------|-----|-----|
| **NEW** | extreme_panic + deep_drawdown | BUY | +10% | ❌ |
| **NEW** | extreme_euphoria + big_rally | SELL | −15% | −20% |
| 1 | tail_risk (down) + NOT panic | STRONG_SELL | −50% | −70% |
| **NEW** | tail_risk (down) + panic | HOLD | 0% | 0% |
| **NEW** | tail_risk (up) | SELL | −15% | −20% |
| 2 | conf < 0.40 | HOLD | 0% | 0% |
| 3 | churn ≥ 3/30d | HOLD | 0% | 0% |
| 4 | cooldown active | HOLD | 0% | 0% |
| 5 | BULL + conf ≥ 0.70 + mom > 0.50 + NOT euphoria | STRONG_BUY | +20% | ❌ |
| 6 | BULL + conf ≥ 0.50 + mom > 0 + NOT euphoria | BUY | +10% | +5% |
| **NEW** | BULL + euphoria | HOLD | 0% | 0% |
| **NEW** | RANGE + panic | BUY | +10% | ❌ |
| **NEW** | RANGE + euphoria | SELL | −15% | −20% |
| 7 | RANGE (normal) | HOLD | 0% | 0% |
| 8 | TRANSITION (no warning) | HOLD | 0% | 0% |
| 9 | TRANSITION + risk < −0.30 + NOT panic | SELL | −15% | −20% |
| 10 | BEAR + conf ≥ 0.60 + mom < −0.50 + NOT panic | STRONG_SELL | −50% | −70% |
| 11 | BEAR + conf ≥ 0.50 + mom < 0 + NOT panic | SELL | −15% | −20% |
| **NEW** | BEAR + panic | HOLD | 0% | 0% |

---

## 7. Quick Reference

```
┌─────────────────────────────────────────────────────────────┐
│           ASSET ALLOCATION v1.4                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  THIS MODEL:                                                │
│    ✅ Preserves capital                                     │
│    ✅ Avoids false breakouts                                │
│    ✅ Has executable rules                                  │
│    ✅ NEW: Doesn't sell bottoms                             │
│    ✅ NEW: Takes profit on euphoria                         │
│    ✅ NEW: Mean reversion in RANGE                          │
│                                                             │
│  THIS MODEL DOES NOT:                                       │
│    ❌ Catch early trends                                    │
│    ❌ Optimize expected value                               │
│    ❌ Lead with ETH                                         │
│    ❌ Trade TRANSITION actively                             │
│                                                             │
│  COUNTER-CYCLICAL THRESHOLDS:                               │
│    Panic: mom < -0.70 AND vol_z > 1.5                      │
│    Euphoria: mom > 0.70 AND conf > 0.60                    │
│    Extreme panic: mom < -0.80 AND vol_z > 2.0              │
│    Extreme euphoria: mom > 0.80 AND conf > 0.70            │
│                                                             │
│  GATES:                                                     │
│    conf < 0.40 → HOLD                                      │
│    conf ≥ 0.50 → BUY/SELL (if not blocked)                 │
│    conf ≥ 0.70 → STRONG_BUY (if not euphoria)              │
│                                                             │
│  SIZES:                                                     │
│    STRONG_BUY: +20% (BTC only)                             │
│    BUY: +10% BTC, +5% ETH                                  │
│    SELL: −15% BTC, −20% ETH                                │
│    STRONG_SELL: −50% BTC, −70% ETH                         │
│                                                             │
│  ANTI-CHURN:                                                │
│    Max 3 actions / 30d                                     │
│    Cooldowns: 7d / 3d / 14d                                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## VERSION HISTORY

| Ver | Changes |
|-----|---------|
| 1.0 | Initial |
| 1.1 | Persistence, polarity |
| 1.2 | Gradations |
| 1.2.1 | Intent, sizing |
| 1.3 | Hard rules |
| 1.3.1 | Documented limitations |
| **1.4** | **Counter-cyclical logic: don't sell panic, buy fear, sell greed** |

---

## STATUS: PRODUCTION

**Спецификация обновлена. Counter-cyclical logic внедрён. Backtest подтверждает улучшение.**
