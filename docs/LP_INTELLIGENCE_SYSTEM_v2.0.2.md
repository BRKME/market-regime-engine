# LP Intelligence System v2.0.2

> **"Volatility as Opportunity" — Conservative Trend Management**

**Status:** Production  
**Updated:** 2026-02-15  
**Previous:** v2.0.1

---

## Changelog v2.0.1 → v2.0.2

### CFO Backtest Results

```
Metric              v2.0.1    v2.0.2    Improvement
───────────────────────────────────────────────────
Return               -8.0%     +6.5%    +14.5% ✅
IL Suffered         $3,272    $1,914      -42% ✅
vs Spot             -12.9%     +1.6%    +14.5% ✅
```

### Parameter Changes

| Regime | v2.0.1 | v2.0.2 | Change |
|--------|--------|--------|--------|
| HARVEST | 0.90 | 0.80 | -11% |
| MEAN_REVERT | 0.70 | 0.60 | -14% |
| VOLATILE_CHOP | 0.80 | 0.50 | -38% |
| **TRENDING** | 0.30 | **0.10** | **-67%** |
| **BREAKOUT** | 0.40 | **0.20** | **-50%** |
| GAP_RISK | 0.50 | 0.25 | -50% |
| CHURN | 0.10 | 0.05 | -50% |

### Persistence Thresholds

| Threshold | v2.0.1 | v2.0.2 | Effect |
|-----------|--------|--------|--------|
| CHOPPY | 0.20 | 0.25 | Earlier range detection |
| MODERATE | 0.40 | 0.35 | Earlier caution |
| TRENDING | 0.50 | 0.45 | Earlier trend detection |

---

## Core Principle

```
┌────────────────────────────────────────────────────────────┐
│  v2.0.2 KEY INSIGHT: BE MORE AGGRESSIVE ABOUT AVOIDING    │
│  TRENDS. THE COST OF MISSING LP FEES IS LESS THAN THE     │
│  COST OF SUFFERING IL IN A TRENDING MARKET.               │
└────────────────────────────────────────────────────────────┘
```

---

## LP Regime Parameters (v2.0.2)

```python
LP_REGIME_PARAMS = {
    "HARVEST":       {"notional": 0.80, "range": "tight",     "rebalance": "aggressive"},
    "MEAN_REVERT":   {"notional": 0.60, "range": "standard",  "rebalance": "normal"},
    "VOLATILE_CHOP": {"notional": 0.50, "range": "moderate",  "rebalance": "active"},
    "TRENDING":      {"notional": 0.10, "range": "wide",      "rebalance": "minimal"},
    "BREAKOUT":      {"notional": 0.20, "range": "wide",      "rebalance": "cautious"},
    "CHURN":         {"notional": 0.05, "range": "very_wide", "rebalance": "disabled"},
    "GAP_RISK":      {"notional": 0.25, "range": "wide",      "rebalance": "cautious"},
    "AVOID":         {"notional": 0.00, "range": "n/a",       "rebalance": "disabled"},
}
```

---

## Trend Detection (v2.0.2)

```python
# Earlier trend detection
LP_PERSISTENCE_CHOPPY = 0.25    # Was 0.20 - detect range sooner
LP_PERSISTENCE_MODERATE = 0.35  # Was 0.40 - caution sooner
LP_PERSISTENCE_TRENDING = 0.45  # Was 0.50 - detect trend sooner
```

### Exposure Logic

```python
def compute_exposure(row):
    persistence = row['persistence']
    momentum = abs(row['momentum'])
    returns_7d = abs(row['returns_7d'])
    
    # Strong trend = MINIMAL exposure
    is_strong_trend = (
        persistence > 0.45 or 
        momentum > 0.5 or 
        returns_7d > 0.05
    )
    
    is_weak_trend = (
        persistence > 0.35 or 
        momentum > 0.3
    )
    
    if regime == "RANGE" and not is_weak_trend:
        return 0.60  # Good for LP
    elif regime == "RANGE" and is_weak_trend:
        return 0.30  # Cautious
    elif is_strong_trend:
        return 0.10  # MINIMAL - avoid IL
    elif is_weak_trend:
        return 0.20  # Low
    else:
        return 0.40  # Default
```

---

## Risk Quadrant Matrix

```
         Dir Risk →
     ┌───────┬───────┐
 LP↑ │ Q3    │ Q1    │
     │ spot  │ ideal │
     ├───────┼───────┤
 LP↓ │ Q4    │ Q2    │
     │ exit  │ LP    │
     └───────┴───────┘

Q1: dir+, lp+ → Full deployment
Q2: dir-, lp+ → LP opportunity (key insight!)
Q3: dir+, lp- → Hold spot, reduce LP
Q4: dir-, lp- → Minimize / exit
```

---

## Vol Structure Classification

| Classification | Range Share | LP Implication |
|----------------|-------------|----------------|
| RANGE_DOMINANT | > 50% | ✅ High fee opportunity |
| TREND_DOMINANT | > 50% | ⚠️ High IL risk |
| JUMP_ELEVATED | > 20% | 🚨 Gap risk |
| BALANCED | else | Standard |

---

## Fee/Variance Ratio

```
Ratio > 3.0  → Maximize allocation
Ratio 2-3    → Standard allocation
Ratio 1-2    → Cautious
Ratio < 1.0  → AVOID / EXIT
```

---

## Example Output (v2.0.2)

```
💧 LP POLICY

          Dir Risk →
      ┌───────┬───────┐
  LP↑ │ Q3   │ Q1   │
      │ spot  │ ideal │
      ├───────┼───────┤
  LP↓ │[Q4]  │ Q2   │
      │ exit  │ LP    │
      └───────┴───────┘

   Dir: -0.82 · LP: -0.30 · F/V: 0.8x
   Exposure: 10% (max 20%)
   Range: wide
   Hedge: REQUIRED
   
   Signals:
   • High trend persistence → IL risk
   • Trend-dominant volatility
   • Fee/Var 0.8x → unprofitable

v3.4 · LP v2.0.2 · AA v1.4.1
```

---

## Implementation

**Files:**
- `lp_policy_engine.py` — Main logic
- `settings.py` — Parameters (LP_REGIME_PARAMS, LP_PERSISTENCE_*)

---

## Combined System Results

When combined with AA v1.4.1:

```
Full System (AA + LP) vs Buy & Hold:
- Return:  +14.0% vs +8.2%  (alpha: +5.8%)
- Max DD:  25.0% vs 65.0%   (-40% improvement)
- Sharpe:  0.51 vs 0.46
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| v2.0 | 2026-02 | Vol decomposition, dual risk |
| v2.0.1 | 2026-02 | Trend persistence, uncertainty inversion |
| **v2.0.2** | **2026-02-15** | **Conservative trends, -67% TRENDING exposure** |
