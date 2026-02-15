# Asset Allocation Policy v1.4.1

> **Операционная спецификация с counter-cyclical логикой**

**Status:** Production  
**Updated:** 2026-02-15  
**Previous:** v1.4

---

## Changelog v1.4 → v1.4.1

### Tuned from CFO Backtest Results

| Parameter | v1.4 | v1.4.1 | Reason |
|-----------|------|--------|--------|
| Panic momentum | < -0.70 | < -0.50 | Earlier detection |
| Panic vol_z | > 1.5 | > 1.5 OR > 1.0 | More sensitive |
| Deep drawdown | < -20% | < -25% | Fewer false positives |
| Big rally | > 30% | > 40% | Fewer false positives |

### Backtest Results

```
Metric              v1.3.1    v1.4.1    Improvement
───────────────────────────────────────────────────
Panic Sells           17         3        -82% ✅
Panic Holds            0        19        +19  ✅
```

---

## Counter-Cyclical Logic

### Detection Thresholds (v1.4.1)

```python
# Panic detection (MORE SENSITIVE than v1.4)
is_panic = (
    (momentum < -0.50 and vol_z > 1.5) or  # High vol + negative
    (momentum < -0.60 and vol_z > 1.0) or  # Strong negative
    (returns_30d < -0.30)                   # Deep drawdown alone
)

is_extreme_panic = momentum < -0.75 and vol_z > 2.0
is_deep_drawdown = returns_30d < -0.25

# Euphoria detection (unchanged)
is_euphoria = momentum > 0.70 and confidence > 0.60
is_extreme_euphoria = momentum > 0.80 and confidence > 0.70
is_big_rally = returns_30d > 0.40  # Raised from 0.30
```

### Rules

| # | Condition | Action | Size |
|---|-----------|--------|------|
| 1 | Extreme panic + deep drawdown | BUY | +10% BTC |
| 2 | Extreme euphoria + big rally | SELL | -15% BTC |
| 3 | Tail risk + panic | **HOLD** | 0 |
| 4 | Tail risk (no panic) | STRONG_SELL | -50% |
| 5 | BEAR + panic | **HOLD** | 0 |
| 6 | BEAR + oversold (RSI < 30) | **HOLD** | 0 |

---

## Position Sizes

| Action | BTC | ETH |
|--------|-----|-----|
| STRONG_BUY | +20% | N/A |
| BUY | +10% | +5% |
| HOLD | 0 | 0 |
| SELL | -15% | -20% |
| STRONG_SELL | -50% | -70% |

---

## Regime Logic

### BULL
```
if euphoria:
    HOLD (don't buy overbought)
elif confidence >= 0.70 and momentum > 0.50:
    STRONG_BUY
elif confidence >= 0.50 and momentum > 0:
    BUY
else:
    HOLD
```

### BEAR
```
if panic_block:
    HOLD (don't sell panic!)
elif confidence >= 0.60 and momentum < -0.50:
    SELL (reduced from STRONG_SELL)
elif confidence >= 0.50 and momentum < 0 and RSI > 30:
    SELL
else:
    HOLD
```

### TRANSITION
```
if momentum < -0.30 and confidence >= 0.50 and not panic:
    SELL
else:
    HOLD
```

### RANGE
```
if panic:
    BUY (mean reversion)
elif euphoria:
    SELL (mean reversion)
else:
    HOLD
```

---

## Cooldowns

| After | Wait |
|-------|------|
| BUY | 3 days |
| SELL | 7 days |
| STRONG_* | 14 days |

---

## Example Output

```
📉 DIRECTIONAL
   BTC: HOLD
   ETH: HOLD
   → COUNTER-CYCLICAL: Not selling into panic

Reasoning:
  • TAIL RISK detected, but PANIC conditions active
  • Momentum: -0.82, Vol_z: 2.3
  • Returns_30d: -28%
```

---

## Implementation

**File:** `asset_allocation.py`

```python
def compute_allocation(
    asset: str,
    regime: str,
    ...
    vol_z: float = 0,        # v1.4+
    returns_30d: float = 0,  # v1.4+
) -> AllocationPolicy:
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| v1.3.1 | 2026-02 | Conservative baseline |
| v1.4 | 2026-02-15 | Counter-cyclical logic |
| **v1.4.1** | **2026-02-15** | **Tuned thresholds from backtest** |
