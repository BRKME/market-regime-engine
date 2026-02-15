# LP Intelligence System v2.0.1 — FINAL

## "Volatility as Opportunity"

**Status: Ready for Analyst Review**

---

## Executive Summary

```
┌────────────────────────────────────────────────────────────┐
│                 PARADIGM SHIFT                             │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  v1.x: "How to not lose money in LP"                       │
│        Volatility = Risk                                   │
│        Uncertainty = Danger                                │
│        Goal = Capital Preservation                         │
│                                                            │
│  v2.0.1: "How to profit from LP intelligently"             │
│        Volatility = Structure (decomposed)                 │
│        Uncertainty = Fuel for LP (inverted signal)         │
│        Goal = Risk-Adjusted Fee Capture                    │
│                                                            │
│  KEY INNOVATIONS:                                          │
│  • Dual Risk Model (directional vs LP-specific)            │
│  • Volatility Decomposition (trend/range/jump)             │
│  • Trend Persistence (stability matters, not sign)         │
│  • Uncertainty Inversion (low clarity = LP opportunity)    │
│  • Fee/Variance Ratio (expected LP payoff)                 │
│  • LP Regime Taxonomy (HARVEST/TRENDING/etc)               │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

---

## Changelog

| Version | Focus |
|---------|-------|
| v1.0-1.2 | Risk Governor (capital preservation) |
| v2.0 | LP Intelligence (vol decomposition, dual risk, TRANSITION subtypes) |
| **v2.0.1** | **Complete LP Framework** (trend persistence, uncertainty inversion, fee/variance ratio, LP regime taxonomy) |

---

## Analyst Critique Resolution Matrix

| # | Critique | Resolution in v2.0.1 |
|---|----------|---------------------|
| 1 | Market risk ≠ LP risk | ✅ Dual Risk Model (risk_directional + risk_lp) |
| 2 | TRANSITION = плохо (неверно) | ✅ TRANSITION Subtypes (POST_TREND = opportunity) |
| 3 | Volatility односторонняя | ✅ Vol Decomposition (RANGE_DOMINANT = good) |
| 4 | Momentum sign vs persistence | ✅ **Trend Persistence metric** |
| 5 | Uncertainty инвертирована | ✅ **Explicit Uncertainty Inversion** |
| 6 | Structural break = exit | ✅ LP-aware break assessment |
| 7 | Бинарная policy | ✅ Condition Rules, Adaptive De-risking |
| 8 | Fee/Risk отсутствует | ✅ **Fee/Variance Ratio** |
| 9 | LP-specific regime | ✅ **LP Regime Taxonomy** |

---

## Part I: Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                 LP INTELLIGENCE SYSTEM v2.0.1                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ╔═══════════════════════════════════════════════════════════╗ │
│  ║  LAYER 1: MARKET STRUCTURE ANALYSIS                       ║ │
│  ╠═══════════════════════════════════════════════════════════╣ │
│  ║  • Volatility Decomposition (σ_trend, σ_range, σ_jump)    ║ │
│  ║  • Trend Persistence (NEW v2.0.1)                         ║ │
│  ║  • TRANSITION Subtype Classifier                          ║ │
│  ║  • Fee Regime Detector                                    ║ │
│  ╚═══════════════════════════════════════════════════════════╝ │
│                              ▼                                  │
│  ╔═══════════════════════════════════════════════════════════╗ │
│  ║  LAYER 2: LP-SPECIFIC METRICS (NEW v2.0.1)                ║ │
│  ╠═══════════════════════════════════════════════════════════╣ │
│  ║  • Uncertainty Value (inverted from clarity)              ║ │
│  ║  • Fee/Variance Ratio (expected LP payoff)                ║ │
│  ║  • LP Regime Classification                               ║ │
│  ╚═══════════════════════════════════════════════════════════╝ │
│                              ▼                                  │
│  ╔═══════════════════════════════════════════════════════════╗ │
│  ║  LAYER 3: DUAL RISK MODEL                                 ║ │
│  ╠═══════════════════════════════════════════════════════════╣ │
│  ║  • risk_directional (market direction risk)               ║ │
│  ║  • risk_lp (LP-specific opportunity/risk)                 ║ │
│  ║  • Risk Quadrant Classification                           ║ │
│  ╚═══════════════════════════════════════════════════════════╝ │
│                              ▼                                  │
│  ╔═══════════════════════════════════════════════════════════╗ │
│  ║  LAYER 4: DECISION ENGINE                                 ║ │
│  ╠═══════════════════════════════════════════════════════════╣ │
│  ║  • LP Regime → Action Mapping                             ║ │
│  ║  • Condition-Based Rules                                  ║ │
│  ║  • Opportunity Cost Balancer                              ║ │
│  ║  • Adaptive De-risking                                    ║ │
│  ╚═══════════════════════════════════════════════════════════╝ │
│                              ▼                                  │
│  ╔═══════════════════════════════════════════════════════════╗ │
│  ║  LAYER 5: EXECUTION                                       ║ │
│  ╠═══════════════════════════════════════════════════════════╣ │
│  ║  • Position Sizing                                        ║ │
│  ║  • Range Optimization                                     ║ │
│  ║  • Rebalance Scheduling                                   ║ │
│  ╚═══════════════════════════════════════════════════════════╝ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Part II: Volatility Decomposition

### 2.1 Core Concept

```
σ_total² = σ_trend² + σ_range² + σ_jump²

Where:
  σ_trend = Directional drift (BAD for LP → IL accumulation)
  σ_range = Mean-reverting oscillation (GOOD for LP → fee capture)
  σ_jump  = Discontinuous gaps (VERY BAD for LP → gap risk)
```

### 2.2 Implementation

```python
def decompose_volatility(
    prices: np.ndarray,
    window: int = 30,
) -> dict:
    """
    Decompose total volatility into LP-relevant components.
    """
    returns = np.diff(np.log(prices))
    
    # Total volatility (annualized)
    sigma_total = np.std(returns) * np.sqrt(365)
    
    # ═══════════════════════════════════════════════════════
    # TREND COMPONENT: volatility of the smoothed price path
    # ═══════════════════════════════════════════════════════
    rolling_mean = pd.Series(prices).rolling(window).mean()
    trend_returns = np.diff(np.log(rolling_mean.dropna()))
    sigma_trend = np.std(trend_returns) * np.sqrt(365) if len(trend_returns) > 0 else 0
    
    # ═══════════════════════════════════════════════════════
    # JUMP COMPONENT: extreme returns (> 3σ)
    # ═══════════════════════════════════════════════════════
    threshold = 3 * np.std(returns)
    jumps = returns[np.abs(returns) > threshold]
    if len(jumps) > 0:
        jump_contribution = np.sum(jumps**2)
        total_contribution = np.sum(returns**2)
        jump_share = jump_contribution / total_contribution if total_contribution > 0 else 0
        sigma_jump = sigma_total * np.sqrt(jump_share)
    else:
        sigma_jump = 0
        jump_share = 0
    
    # ═══════════════════════════════════════════════════════
    # RANGE COMPONENT: residual (mean-reverting oscillation)
    # ═══════════════════════════════════════════════════════
    sigma_range_sq = max(0, sigma_total**2 - sigma_trend**2 - sigma_jump**2)
    sigma_range = np.sqrt(sigma_range_sq)
    
    # Shares of total variance
    total_var = sigma_total**2 if sigma_total > 0 else 1
    trend_share = (sigma_trend**2) / total_var
    range_share = (sigma_range**2) / total_var
    jump_share = (sigma_jump**2) / total_var
    
    return {
        "sigma_total": round(sigma_total, 4),
        "sigma_trend": round(sigma_trend, 4),
        "sigma_range": round(sigma_range, 4),
        "sigma_jump": round(sigma_jump, 4),
        "trend_share": round(trend_share, 3),
        "range_share": round(range_share, 3),
        "jump_share": round(jump_share, 3),
    }
```

### 2.3 Volatility Structure Classification

```python
def classify_vol_structure(decomposition: dict) -> dict:
    """
    Classify volatility structure for LP decision-making.
    """
    trend = decomposition["trend_share"]
    range_ = decomposition["range_share"]
    jump = decomposition["jump_share"]
    total = decomposition["sigma_total"]
    
    # Classification logic
    if total < 0.25:
        classification = "LOW_VOL"
        lp_implication = "LOW_FEES"
        action = "TIGHTEN_RANGE_OR_REDEPLOY"
    elif jump > 0.20:
        classification = "JUMP_ELEVATED"
        lp_implication = "GAP_RISK"
        action = "WIDEN_RANGE_MAINTAIN_NOTIONAL"
    elif trend > 0.50:
        classification = "TREND_DOMINANT"
        lp_implication = "HIGH_IL_RISK"
        action = "REDUCE_NOTIONAL_WIDEN_RANGE"
    elif range_ > 0.50:
        classification = "RANGE_DOMINANT"
        lp_implication = "HIGH_FEE_OPPORTUNITY"
        action = "INCREASE_NOTIONAL_OPTIMIZE_RANGE"
    else:
        classification = "BALANCED"
        lp_implication = "NEUTRAL"
        action = "STANDARD_ALLOCATION"
    
    return {
        "classification": classification,
        "lp_implication": lp_implication,
        "recommended_action": action,
        "components": decomposition,
    }
```

### 2.4 Vol Structure Decision Table

```
┌───────────────────┬────────────────┬─────────────────────────────────┐
│ Vol Structure     │ LP Implication │ Action                          │
├───────────────────┼────────────────┼─────────────────────────────────┤
│ RANGE_DOMINANT    │ FEE OPPORTUNITY│ Increase notional, tighten range│
│ TREND_DOMINANT    │ IL RISK        │ Reduce notional, widen range    │
│ JUMP_ELEVATED     │ GAP RISK       │ Widen range, maintain notional  │
│ BALANCED          │ NEUTRAL        │ Standard allocation             │
│ LOW_VOL           │ LOW FEES       │ Tighten range or redeploy       │
└───────────────────┴────────────────┴─────────────────────────────────┘
```

---

## Part III: Trend Persistence (NEW in v2.0.1)

### 3.1 Why Trend Persistence Matters

```
┌────────────────────────────────────────────────────────────┐
│         MOMENTUM SIGN vs TREND PERSISTENCE                 │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  v1.x ERROR:                                               │
│    Momentum = -0.9 → Risk-Off → LP exit                    │
│    Momentum = +0.9 → Risk-On → LP ok                       │
│                                                            │
│  REALITY FOR LP:                                           │
│    The SIGN of momentum doesn't matter.                    │
│    The PERSISTENCE of momentum matters.                    │
│                                                            │
│    Momentum = -0.9, persistent → TRENDING DOWN → BAD for LP│
│    Momentum = +0.9, persistent → TRENDING UP → BAD for LP  │
│    Momentum = ±0.3, unstable → CHOPPY → GOOD for LP        │
│                                                            │
│  KEY INSIGHT:                                              │
│    High |momentum| + high persistence = trending = IL      │
│    Any momentum + low persistence = choppy = fees          │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### 3.2 Trend Persistence Implementation

```python
def compute_trend_persistence(
    prices: np.ndarray,
    returns: np.ndarray = None,
    window: int = 14,
) -> dict:
    """
    Compute trend persistence metrics.
    
    For LP:
      High persistence = trending = BAD (IL accumulates)
      Low persistence = choppy = GOOD (fees accumulate)
    
    Key insight: We don't care about direction (+ or -),
    we care about STABILITY of direction.
    """
    if returns is None:
        returns = np.diff(np.log(prices))
    
    # ═══════════════════════════════════════════════════════
    # METRIC 1: Return Autocorrelation
    # High autocorr = returns predict next returns = trending
    # ═══════════════════════════════════════════════════════
    if len(returns) > 2:
        autocorr = np.corrcoef(returns[:-1], returns[1:])[0, 1]
        autocorr = 0 if np.isnan(autocorr) else autocorr
    else:
        autocorr = 0
    
    # ═══════════════════════════════════════════════════════
    # METRIC 2: Direction Consistency
    # How often does direction persist?
    # 1.0 = always same direction = trending
    # 0.0 = random direction = choppy
    # ═══════════════════════════════════════════════════════
    signs = np.sign(returns)
    # Rolling direction agreement
    direction_changes = np.sum(np.diff(signs) != 0)
    direction_consistency = 1 - (direction_changes / (len(signs) - 1)) if len(signs) > 1 else 0
    
    # ═══════════════════════════════════════════════════════
    # METRIC 3: Mean Reversion Strength
    # How quickly does price return to mean?
    # High MR = good for LP
    # ═══════════════════════════════════════════════════════
    price_series = pd.Series(prices)
    ma = price_series.rolling(window).mean()
    deviations = (price_series - ma) / ma
    deviations = deviations.dropna()
    
    if len(deviations) > 1:
        # Negative autocorr of deviations = mean-reverting
        dev_autocorr = np.corrcoef(deviations.values[:-1], deviations.values[1:])[0, 1]
        dev_autocorr = 0 if np.isnan(dev_autocorr) else dev_autocorr
        mean_reversion_strength = -dev_autocorr  # Invert: positive = mean-reverting
    else:
        mean_reversion_strength = 0
    
    # ═══════════════════════════════════════════════════════
    # COMPOSITE: Trend Persistence Score
    # 0.0 = no trend persistence (choppy, good for LP)
    # 1.0 = high trend persistence (trending, bad for LP)
    # ═══════════════════════════════════════════════════════
    persistence_score = (
        max(0, autocorr) * 0.4 +           # positive autocorr = trending
        direction_consistency * 0.4 +       # consistent direction = trending
        max(0, -mean_reversion_strength) * 0.2  # negative MR = trending
    )
    persistence_score = max(0, min(1, persistence_score))
    
    # LP implication
    if persistence_score > 0.6:
        lp_implication = "TRENDING"
        lp_action = "REDUCE_EXPOSURE"
    elif persistence_score > 0.4:
        lp_implication = "MODERATE_TREND"
        lp_action = "CAUTIOUS"
    elif persistence_score > 0.2:
        lp_implication = "NEUTRAL"
        lp_action = "STANDARD"
    else:
        lp_implication = "CHOPPY"
        lp_action = "INCREASE_EXPOSURE"
    
    return {
        "autocorrelation": round(autocorr, 3),
        "direction_consistency": round(direction_consistency, 3),
        "mean_reversion_strength": round(mean_reversion_strength, 3),
        "persistence_score": round(persistence_score, 3),
        "lp_implication": lp_implication,
        "lp_action": lp_action,
    }
```

### 3.3 Trend Persistence Decision Table

```
┌─────────────────────┬───────────────┬─────────────────────────────────┐
│ Persistence Score   │ LP Implication│ Action                          │
├─────────────────────┼───────────────┼─────────────────────────────────┤
│ > 0.6 (TRENDING)    │ HIGH IL RISK  │ Reduce exposure, widen ranges   │
│ 0.4 - 0.6 (MODERATE)│ CAUTION       │ Standard allocation, monitor    │
│ 0.2 - 0.4 (NEUTRAL) │ NEUTRAL       │ Standard allocation             │
│ < 0.2 (CHOPPY)      │ FEE HARVEST   │ Increase exposure, tighten range│
└─────────────────────┴───────────────┴─────────────────────────────────┘
```

---

## Part IV: Uncertainty Inversion (NEW in v2.0.1)

### 4.1 The Fundamental Insight

```
┌────────────────────────────────────────────────────────────┐
│           UNCERTAINTY: INVERTED SIGNAL FOR LP              │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  FOR DIRECTIONAL TRADING:                                  │
│    Low certainty → Don't trade → Wait for clarity          │
│    High certainty → Trade → Profit from direction          │
│                                                            │
│  FOR LP (INVERTED):                                        │
│    Low certainty → No clear trend → LP harvests vol        │
│    High certainty → Clear trend → LP gets IL               │
│                                                            │
│  THEREFORE:                                                │
│    uncertainty_value_for_lp = 1 - model_clarity            │
│                                                            │
│  MODEL SAYS:       LP HEARS:                               │
│  "I'm uncertain"   "Great, deploy!"                        │
│  "I'm confident"   "Careful, trend forming"                │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### 4.2 Uncertainty Value Implementation

```python
def compute_uncertainty_value_for_lp(
    model_clarity: float,
    regime: str,
    trend_persistence: float,
) -> dict:
    """
    Compute LP value of model uncertainty.
    
    KEY INSIGHT:
    Low model clarity = market doesn't know where it's going
                      = no clear trend
                      = LP can harvest volatility
    
    This INVERTS the directional trading signal.
    """
    # Base uncertainty value (inverted clarity)
    base_uncertainty_value = 1.0 - model_clarity
    
    # Adjust by regime
    # TRANSITION uncertainty is especially valuable for LP
    regime_multiplier = {
        "BULL": 0.8,        # Trending, uncertainty less valuable
        "BEAR": 0.8,        # Trending, uncertainty less valuable
        "RANGE": 1.0,       # Neutral
        "TRANSITION": 1.2,  # Uncertainty is premium for LP
    }.get(regime, 1.0)
    
    # Adjust by trend persistence
    # Low persistence + low clarity = maximum LP opportunity
    persistence_bonus = (1 - trend_persistence) * 0.2
    
    # Final uncertainty value for LP
    lp_uncertainty_value = min(1.0, base_uncertainty_value * regime_multiplier + persistence_bonus)
    
    # Interpretation
    if lp_uncertainty_value > 0.7:
        interpretation = "HIGH_LP_OPPORTUNITY"
        action_hint = "Market directionless, harvest volatility"
    elif lp_uncertainty_value > 0.4:
        interpretation = "MODERATE_LP_OPPORTUNITY"
        action_hint = "Some uncertainty, standard LP"
    else:
        interpretation = "LOW_LP_OPPORTUNITY"
        action_hint = "High clarity suggests trend, be cautious"
    
    return {
        "model_clarity": round(model_clarity, 2),
        "base_uncertainty": round(base_uncertainty_value, 2),
        "regime_multiplier": regime_multiplier,
        "persistence_bonus": round(persistence_bonus, 2),
        "lp_uncertainty_value": round(lp_uncertainty_value, 2),
        "interpretation": interpretation,
        "action_hint": action_hint,
    }
```

### 4.3 Uncertainty Inversion Example

```
SCENARIO: Low Model Clarity

Model says:
  regime = TRANSITION
  model_clarity = 0.25 (LOW)
  "I don't know where market is going"

v1.x interpretation:
  LOW clarity → HIGH uncertainty → RISK OFF
  Action: Reduce LP, wait for clarity

v2.0.1 interpretation:
  LOW clarity → HIGH uncertainty value for LP
  lp_uncertainty_value = 1 - 0.25 = 0.75
  + TRANSITION bonus = 0.75 * 1.2 = 0.90
  
  Action: DEPLOY LP (market directionless = harvest vol)
```

---

## Part V: Fee/Variance Ratio (NEW in v2.0.1)

### 5.1 Why Fee/Variance Ratio is Critical

```
┌────────────────────────────────────────────────────────────┐
│              THE MISSING LP METRIC                         │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  v1.x DECISION:                                            │
│    Risk is high → Exit LP                                  │
│    (No consideration of fees!)                             │
│                                                            │
│  REALITY:                                                  │
│    LP P&L = Fees - IL - Costs                              │
│    Need to compare BOTH sides                              │
│                                                            │
│  FEE/VARIANCE RATIO:                                       │
│    = Expected Fees / Expected IL Proxy                     │
│                                                            │
│    > 2.0 → Fees likely exceed IL → PROFITABLE              │
│    1.0-2.0 → Marginal → CAREFUL                            │
│    < 1.0 → IL likely exceeds fees → UNPROFITABLE           │
│                                                            │
│  This is the CORE LP profitability metric.                 │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### 5.2 Fee/Variance Ratio Implementation

```python
def compute_fee_variance_ratio(
    expected_daily_fee_rate: float,    # as decimal (e.g., 0.001 = 0.1%/day)
    realized_variance_daily: float,     # daily variance of returns
    position_size: float,               # in USD
    range_width: float,                 # as decimal (e.g., 0.30 = ±30%)
    holding_period_days: int = 30,
) -> dict:
    """
    Compute expected LP profitability ratio.
    
    Fee/Variance Ratio = Expected Fees / Expected IL Proxy
    
    This is the CORE metric for LP decision-making.
    v1.x never computed this, leading to blind decisions.
    """
    # ═══════════════════════════════════════════════════════
    # EXPECTED FEES
    # ═══════════════════════════════════════════════════════
    expected_fees = position_size * expected_daily_fee_rate * holding_period_days
    
    # ═══════════════════════════════════════════════════════
    # EXPECTED IL PROXY
    # Simplified IL model: IL ≈ variance / (8 * range_width²)
    # This is a heuristic, not precise, but directionally correct
    # ═══════════════════════════════════════════════════════
    # Total variance over holding period
    total_variance = realized_variance_daily * holding_period_days
    
    # IL proxy (simplified formula)
    # Wider range = less IL, Higher variance = more IL
    if range_width > 0:
        il_proxy_rate = total_variance / (8 * range_width**2)
        il_proxy_rate = min(il_proxy_rate, 0.5)  # Cap at 50% IL
    else:
        il_proxy_rate = 0.5
    
    expected_il = position_size * il_proxy_rate
    
    # ═══════════════════════════════════════════════════════
    # FEE/VARIANCE RATIO
    # ═══════════════════════════════════════════════════════
    if expected_il > 0:
        fee_variance_ratio = expected_fees / expected_il
    else:
        fee_variance_ratio = float('inf')
    
    # Classification
    if fee_variance_ratio > 3.0:
        profitability = "HIGHLY_PROFITABLE"
        confidence = "HIGH"
    elif fee_variance_ratio > 2.0:
        profitability = "PROFITABLE"
        confidence = "GOOD"
    elif fee_variance_ratio > 1.5:
        profitability = "MARGINALLY_PROFITABLE"
        confidence = "MODERATE"
    elif fee_variance_ratio > 1.0:
        profitability = "BREAK_EVEN"
        confidence = "LOW"
    else:
        profitability = "UNPROFITABLE"
        confidence = "AVOID"
    
    return {
        "expected_fees_usd": round(expected_fees, 2),
        "expected_il_proxy_usd": round(expected_il, 2),
        "expected_net_pnl_usd": round(expected_fees - expected_il, 2),
        "fee_variance_ratio": round(fee_variance_ratio, 2),
        "profitability": profitability,
        "confidence": confidence,
        "holding_period_days": holding_period_days,
        "inputs": {
            "daily_fee_rate": expected_daily_fee_rate,
            "daily_variance": realized_variance_daily,
            "range_width": range_width,
        },
    }
```

### 5.3 Fee/Variance Decision Table

```
┌────────────────────┬─────────────────────┬──────────────────────────────┐
│ Fee/Variance Ratio │ Profitability       │ Action                       │
├────────────────────┼─────────────────────┼──────────────────────────────┤
│ > 3.0              │ HIGHLY PROFITABLE   │ Maximize allocation          │
│ 2.0 - 3.0          │ PROFITABLE          │ Standard allocation          │
│ 1.5 - 2.0          │ MARGINAL            │ Cautious, monitor closely    │
│ 1.0 - 1.5          │ BREAK EVEN          │ Reduce or avoid              │
│ < 1.0              │ UNPROFITABLE        │ Exit or don't enter          │
└────────────────────┴─────────────────────┴──────────────────────────────┘
```

### 5.4 Fee/Variance in Decision Making

```python
def should_lp_based_on_fee_variance(
    fee_variance_ratio: float,
    risk_lp: float,
    vol_structure: str,
) -> dict:
    """
    LP decision incorporating fee/variance ratio.
    """
    # Hard thresholds
    if fee_variance_ratio < 1.0:
        return {
            "decision": "AVOID",
            "reason": f"Fee/Variance ratio {fee_variance_ratio:.1f} < 1.0 (unprofitable)",
            "override_risk_lp": True,
        }
    
    if fee_variance_ratio > 3.0 and risk_lp > -0.3:
        return {
            "decision": "MAXIMIZE",
            "reason": f"Fee/Variance ratio {fee_variance_ratio:.1f} > 3.0 (highly profitable)",
            "override_risk_lp": False,
        }
    
    # Blend with risk_lp for intermediate cases
    if fee_variance_ratio > 2.0:
        notional_multiplier = 1.0 + (risk_lp * 0.2)  # Minor risk adjustment
    elif fee_variance_ratio > 1.5:
        notional_multiplier = 0.8 + (risk_lp * 0.2)  # Moderate risk adjustment
    else:
        notional_multiplier = 0.5 + (risk_lp * 0.3)  # Heavy risk adjustment
    
    notional_multiplier = max(0.2, min(1.2, notional_multiplier))
    
    return {
        "decision": "PROCEED",
        "notional_multiplier": round(notional_multiplier, 2),
        "fee_variance_ratio": fee_variance_ratio,
        "risk_lp": risk_lp,
    }
```

---

## Part VI: LP Regime Taxonomy (NEW in v2.0.1)

### 6.1 The Need for LP-Specific Regimes

```
┌────────────────────────────────────────────────────────────┐
│         TRADER REGIMES vs LP REGIMES                       │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  TRADER TAXONOMY (v1.x):                                   │
│    BULL / BEAR / RANGE / TRANSITION                        │
│    Based on: price direction                               │
│                                                            │
│  LP TAXONOMY (v2.0.1):                                     │
│    HARVEST / TRENDING / BREAKOUT / MEAN_REVERT / CHOP      │
│    Based on: volatility behavior, fee opportunity          │
│                                                            │
│  KEY INSIGHT:                                              │
│    A "BEAR" market can be HARVEST for LP (high vol chop)   │
│    A "BULL" market can be TRENDING for LP (smooth up = IL) │
│                                                            │
│  LP doesn't care about direction, cares about BEHAVIOR.    │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### 6.2 LP Regime Definitions

```python
LP_REGIME_TAXONOMY = {
    # ═══════════════════════════════════════════════════════
    # HARVEST — Best regime for LP
    # ═══════════════════════════════════════════════════════
    "HARVEST": {
        "description": "High-vol choppy market, peak fee extraction",
        "characteristics": {
            "vol_structure": "RANGE_DOMINANT",
            "trend_persistence": "< 0.3",
            "fee_regime": ["ELEVATED", "NORMAL"],
            "uncertainty_value": "> 0.6",
        },
        "lp_opportunity": "MAXIMUM",
        "action": {
            "notional": "INCREASE_TO_90",
            "range": "TIGHTEN",
            "rebalance": "AGGRESSIVE",
        },
        "expected_outcome": "High fees, low IL",
    },
    
    # ═══════════════════════════════════════════════════════
    # MEAN_REVERT — Good regime for LP
    # ═══════════════════════════════════════════════════════
    "MEAN_REVERT": {
        "description": "Stable mean-reversion, reliable fee income",
        "characteristics": {
            "vol_structure": ["RANGE_DOMINANT", "BALANCED"],
            "trend_persistence": "< 0.35",
            "mean_reversion_strength": "> 0.2",
            "fee_regime": "NORMAL",
        },
        "lp_opportunity": "HIGH",
        "action": {
            "notional": "STANDARD_70",
            "range": "STANDARD",
            "rebalance": "NORMAL",
        },
        "expected_outcome": "Steady fees, manageable IL",
    },
    
    # ═══════════════════════════════════════════════════════
    # VOLATILE_CHOP — Good but risky
    # ═══════════════════════════════════════════════════════
    "VOLATILE_CHOP": {
        "description": "Extreme vol but non-directional",
        "characteristics": {
            "vol_structure": "RANGE_DOMINANT",
            "sigma_total": "> 0.80",
            "trend_persistence": "< 0.25",
            "jump_share": "< 0.15",
        },
        "lp_opportunity": "HIGH",
        "action": {
            "notional": "INCREASE_TO_80",
            "range": "WIDEN_SLIGHTLY",
            "rebalance": "ACTIVE",
        },
        "expected_outcome": "Peak fees, monitor for regime shift",
    },
    
    # ═══════════════════════════════════════════════════════
    # TRANSITION_OPPORTUNITY — Uncertainty as edge
    # ═══════════════════════════════════════════════════════
    "TRANSITION_OPPORTUNITY": {
        "description": "Market doesn't know direction, LP profits",
        "characteristics": {
            "regime": "TRANSITION",
            "transition_subtype": ["POST_TREND", "RANGE_EXHAUSTION"],
            "uncertainty_value": "> 0.7",
            "trend_persistence": "< 0.4",
        },
        "lp_opportunity": "HIGH",
        "action": {
            "notional": "INCREASE_TO_75",
            "range": "MODERATE",
            "rebalance": "ACTIVE",
        },
        "expected_outcome": "Capitalize on indecision",
    },
    
    # ═══════════════════════════════════════════════════════
    # TRENDING — Worst regime for LP
    # ═══════════════════════════════════════════════════════
    "TRENDING": {
        "description": "Strong directional move, IL accumulation",
        "characteristics": {
            "vol_structure": "TREND_DOMINANT",
            "trend_persistence": "> 0.5",
            "direction_consistency": "> 0.6",
        },
        "lp_opportunity": "VERY_LOW",
        "action": {
            "notional": "REDUCE_TO_30",
            "range": "WIDEN_SIGNIFICANTLY",
            "rebalance": "DISABLED",
        },
        "expected_outcome": "IL exceeds fees, minimize exposure",
    },
    
    # ═══════════════════════════════════════════════════════
    # BREAKOUT — Danger zone
    # ═══════════════════════════════════════════════════════
    "BREAKOUT": {
        "description": "Compression before move, imminent IL",
        "characteristics": {
            "transition_subtype": "PRE_BREAKOUT",
            "vol_trend": "DECREASING",
            "range_trend": "NARROWING",
        },
        "lp_opportunity": "LOW",
        "action": {
            "notional": "REDUCE_TO_40",
            "range": "WIDEN",
            "rebalance": "CAUTIOUS",
        },
        "expected_outcome": "Prepare for directional move",
    },
    
    # ═══════════════════════════════════════════════════════
    # CHURN — Avoid completely
    # ═══════════════════════════════════════════════════════
    "CHURN": {
        "description": "Rapid regime oscillation, costs exceed fees",
        "characteristics": {
            "transition_subtype": "CHURN",
            "regime_switches_7d": "> 3",
        },
        "lp_opportunity": "NEGATIVE",
        "action": {
            "notional": "EXIT_OR_MINIMAL",
            "range": "VERY_WIDE",
            "rebalance": "DISABLED",
        },
        "expected_outcome": "Rebalancing costs destroy P&L",
    },
    
    # ═══════════════════════════════════════════════════════
    # GAP_RISK — Special handling
    # ═══════════════════════════════════════════════════════
    "GAP_RISK": {
        "description": "Jump-elevated volatility, gap danger",
        "characteristics": {
            "vol_structure": "JUMP_ELEVATED",
            "jump_share": "> 0.20",
        },
        "lp_opportunity": "MODERATE",
        "action": {
            "notional": "MAINTAIN",
            "range": "WIDEN_SIGNIFICANTLY",
            "rebalance": "CAUTIOUS",
        },
        "expected_outcome": "Fees available but protect against gaps",
    },
}
```

### 6.3 LP Regime Classification Algorithm

```python
def classify_lp_regime(
    vol_structure: dict,
    trend_persistence: dict,
    transition_subtype: dict,
    uncertainty_value: dict,
    fee_regime: dict,
    market_data: dict,
) -> dict:
    """
    Classify current market into LP-specific regime.
    """
    vol_class = vol_structure.get("classification", "BALANCED")
    persistence = trend_persistence.get("persistence_score", 0.5)
    mr_strength = trend_persistence.get("mean_reversion_strength", 0)
    sigma_total = vol_structure.get("components", {}).get("sigma_total", 0.5)
    jump_share = vol_structure.get("components", {}).get("jump_share", 0)
    uncertainty = uncertainty_value.get("lp_uncertainty_value", 0.5)
    transition_sub = transition_subtype.get("subtype") if transition_subtype else None
    switches_7d = market_data.get("regime_switches_7d", 0)
    
    # ═══════════════════════════════════════════════════════
    # PRIORITY 1: Avoid dangerous regimes first
    # ═══════════════════════════════════════════════════════
    
    # CHURN: rapid regime oscillation
    if switches_7d >= 3:
        return {
            "lp_regime": "CHURN",
            **LP_REGIME_TAXONOMY["CHURN"],
            "confidence": 0.85,
        }
    
    # GAP_RISK: jump-elevated
    if jump_share > 0.20:
        return {
            "lp_regime": "GAP_RISK",
            **LP_REGIME_TAXONOMY["GAP_RISK"],
            "confidence": 0.80,
        }
    
    # TRENDING: strong trend persistence
    if persistence > 0.5 and vol_class == "TREND_DOMINANT":
        return {
            "lp_regime": "TRENDING",
            **LP_REGIME_TAXONOMY["TRENDING"],
            "confidence": 0.85,
        }
    
    # BREAKOUT: pre-breakout compression
    if transition_sub == "PRE_BREAKOUT":
        return {
            "lp_regime": "BREAKOUT",
            **LP_REGIME_TAXONOMY["BREAKOUT"],
            "confidence": 0.75,
        }
    
    # ═══════════════════════════════════════════════════════
    # PRIORITY 2: Identify opportunity regimes
    # ═══════════════════════════════════════════════════════
    
    # HARVEST: range-dominant, low persistence, high fees
    if (vol_class == "RANGE_DOMINANT" and 
        persistence < 0.3 and 
        uncertainty > 0.6):
        return {
            "lp_regime": "HARVEST",
            **LP_REGIME_TAXONOMY["HARVEST"],
            "confidence": 0.80,
        }
    
    # VOLATILE_CHOP: extreme vol but non-directional
    if (vol_class == "RANGE_DOMINANT" and 
        sigma_total > 0.80 and 
        persistence < 0.25):
        return {
            "lp_regime": "VOLATILE_CHOP",
            **LP_REGIME_TAXONOMY["VOLATILE_CHOP"],
            "confidence": 0.75,
        }
    
    # TRANSITION_OPPORTUNITY: post-trend or similar
    if (transition_sub in ["POST_TREND", "RANGE_EXHAUSTION"] and 
        uncertainty > 0.6):
        return {
            "lp_regime": "TRANSITION_OPPORTUNITY",
            **LP_REGIME_TAXONOMY["TRANSITION_OPPORTUNITY"],
            "confidence": 0.70,
        }
    
    # MEAN_REVERT: stable mean-reversion
    if (vol_class in ["RANGE_DOMINANT", "BALANCED"] and 
        persistence < 0.35 and 
        mr_strength > 0.2):
        return {
            "lp_regime": "MEAN_REVERT",
            **LP_REGIME_TAXONOMY["MEAN_REVERT"],
            "confidence": 0.75,
        }
    
    # ═══════════════════════════════════════════════════════
    # DEFAULT: Unclassified
    # ═══════════════════════════════════════════════════════
    return {
        "lp_regime": "UNCLASSIFIED",
        "description": "No clear LP regime identified",
        "lp_opportunity": "MODERATE",
        "action": {
            "notional": "STANDARD_50",
            "range": "STANDARD",
            "rebalance": "CAUTIOUS",
        },
        "confidence": 0.50,
    }
```

### 6.4 LP Regime Decision Matrix

```
┌─────────────────────┬──────────────┬─────────┬─────────┬──────────────┐
│ LP Regime           │ Notional     │ Range   │ Rebalance│ Expected     │
├─────────────────────┼──────────────┼─────────┼──────────┼──────────────┤
│ HARVEST             │ 90%          │ Tight   │ Aggressive│ +++ fees     │
│ MEAN_REVERT         │ 70%          │ Standard│ Normal   │ ++ fees      │
│ VOLATILE_CHOP       │ 80%          │ Slight+ │ Active   │ +++ fees*    │
│ TRANSITION_OPP      │ 75%          │ Moderate│ Active   │ ++ fees      │
│ GAP_RISK            │ 50%          │ Wide    │ Cautious │ + fees*      │
│ BREAKOUT            │ 40%          │ Wide    │ Cautious │ − IL risk    │
│ TRENDING            │ 30%          │ V.Wide  │ Disabled │ −− IL        │
│ CHURN               │ 10%/Exit     │ V.Wide  │ Disabled │ −−− costs    │
└─────────────────────┴──────────────┴─────────┴──────────┴──────────────┘
* with appropriate risk management
```

---

## Part VII: Enhanced Dual Risk Model

### 7.1 risk_lp Computation (Updated)

```python
def compute_risk_lp_v2(
    vol_structure: dict,
    trend_persistence: dict,
    uncertainty_value: dict,
    fee_variance_ratio: dict,
    transition_subtype: dict,
    fee_regime: dict,
) -> dict:
    """
    Compute LP-specific risk score.
    
    risk_lp ∈ [-1, +1]
    -1 = terrible for LP (trending, high costs)
    +1 = excellent for LP (choppy, high fees)
    
    Updated in v2.0.1 with new metrics.
    """
    risk_lp = 0.0
    components = {}
    
    # ═══════════════════════════════════════════════════════
    # COMPONENT 1: Volatility Structure (25% weight)
    # ═══════════════════════════════════════════════════════
    vol_class = vol_structure.get("classification", "BALANCED")
    vol_contribution = {
        "RANGE_DOMINANT": +0.5,
        "BALANCED": +0.1,
        "LOW_VOL": -0.2,
        "JUMP_ELEVATED": -0.3,
        "TREND_DOMINANT": -0.5,
    }.get(vol_class, 0)
    
    risk_lp += vol_contribution * 0.25
    components["vol_structure"] = vol_contribution
    
    # ═══════════════════════════════════════════════════════
    # COMPONENT 2: Trend Persistence (25% weight)
    # ═══════════════════════════════════════════════════════
    persistence = trend_persistence.get("persistence_score", 0.5)
    # Invert: low persistence = good for LP
    persistence_contribution = (0.5 - persistence) * 2  # ranges -1 to +1
    
    risk_lp += persistence_contribution * 0.25
    components["trend_persistence"] = round(persistence_contribution, 2)
    
    # ═══════════════════════════════════════════════════════
    # COMPONENT 3: Uncertainty Value (20% weight)
    # ═══════════════════════════════════════════════════════
    uncertainty = uncertainty_value.get("lp_uncertainty_value", 0.5)
    # Scale to [-1, +1]: 0 uncertainty = -1, 1 uncertainty = +1
    uncertainty_contribution = (uncertainty - 0.5) * 2
    
    risk_lp += uncertainty_contribution * 0.20
    components["uncertainty_value"] = round(uncertainty_contribution, 2)
    
    # ═══════════════════════════════════════════════════════
    # COMPONENT 4: Fee/Variance Ratio (20% weight)
    # ═══════════════════════════════════════════════════════
    fv_ratio = fee_variance_ratio.get("fee_variance_ratio", 1.5)
    # Scale: <1 = -1, 1-2 = 0, >3 = +1
    if fv_ratio < 1.0:
        fv_contribution = -1.0
    elif fv_ratio < 2.0:
        fv_contribution = (fv_ratio - 1.0) - 0.5  # -0.5 to 0.5
    else:
        fv_contribution = min(1.0, (fv_ratio - 2.0) / 2 + 0.5)  # 0.5 to 1.0
    
    risk_lp += fv_contribution * 0.20
    components["fee_variance"] = round(fv_contribution, 2)
    
    # ═══════════════════════════════════════════════════════
    # COMPONENT 5: Fee Regime (10% weight)
    # ═══════════════════════════════════════════════════════
    fee_reg = fee_regime.get("regime", "NORMAL")
    fee_contribution = {
        "ELEVATED": +0.5,
        "EXTREME": +0.3,
        "NORMAL": 0,
        "DEPRESSED": -0.5,
    }.get(fee_reg, 0)
    
    risk_lp += fee_contribution * 0.10
    components["fee_regime"] = fee_contribution
    
    # Clamp to [-1, +1]
    risk_lp = max(-1.0, min(1.0, risk_lp))
    
    # ═══════════════════════════════════════════════════════
    # INTERPRETATION
    # ═══════════════════════════════════════════════════════
    if risk_lp > 0.5:
        interpretation = "EXCELLENT_FOR_LP"
    elif risk_lp > 0.2:
        interpretation = "GOOD_FOR_LP"
    elif risk_lp > -0.2:
        interpretation = "NEUTRAL"
    elif risk_lp > -0.5:
        interpretation = "POOR_FOR_LP"
    else:
        interpretation = "AVOID_LP"
    
    return {
        "risk_lp": round(risk_lp, 2),
        "interpretation": interpretation,
        "components": components,
        "weights": {
            "vol_structure": 0.25,
            "trend_persistence": 0.25,
            "uncertainty_value": 0.20,
            "fee_variance": 0.20,
            "fee_regime": 0.10,
        },
    }
```

### 7.2 Risk Quadrant (Unchanged but Enhanced Context)

```
                    risk_lp
                      +1
                       │
         Q2           │           Q1
    LP OPPORTUNITY    │       FAVORABLE
                      │
    risk_dir < 0      │    Both positive
    risk_lp > 0       │    Full deployment
    "Choppy market"   │    
    "DEPLOY LP!"      │    
                      │
  ────────────────────┼──────────────────── risk_directional
        -1            │           +1
                      │
         Q4           │           Q3
      DEFENSIVE       │     SPOT_PREFERRED
                      │
    Both negative     │    risk_dir > 0
    "Trending down"   │    risk_lp < 0
    "EXIT LP"         │    "Trending up = IL"
                      │    "Hold spot, reduce LP"
                      -1

KEY v2.0.1 INSIGHT:
  Q2 is the MOST IMPORTANT quadrant for LP intelligence.
  v1.x would EXIT here (sees only risk_dir < 0).
  v2.0.1 DEPLOYS here (sees risk_lp > 0 = opportunity).
```

---

## Part VIII: Complete Decision Engine (v2.0.1)

### 8.1 Full Pipeline

```python
def lp_intelligence_engine_v201(
    regime_output: dict,
    price_data: pd.DataFrame,
    volume_data: dict,
    current_positions: dict,
    pool_configs: dict,
) -> dict:
    """
    LP Intelligence System v2.0.1 — Complete Decision Engine
    """
    timestamp = datetime.utcnow().isoformat()
    
    # ═══════════════════════════════════════════════════════
    # LAYER 1: MARKET STRUCTURE ANALYSIS
    # ═══════════════════════════════════════════════════════
    
    prices = price_data["close"].values
    returns = np.diff(np.log(prices))
    
    # 1.1 Volatility Decomposition
    vol_decomposition = decompose_volatility(prices)
    vol_structure = classify_vol_structure(vol_decomposition)
    
    # 1.2 Trend Persistence (NEW)
    trend_persistence = compute_trend_persistence(prices, returns)
    
    # 1.3 TRANSITION Subtype
    transition_subtype = None
    if regime_output["regime"] == "TRANSITION":
        transition_subtype = classify_transition_subtype(
            regime_output, vol_decomposition, volume_data
        )
    
    # 1.4 Fee Regime
    fee_regime = detect_fee_regime(
        volume_data["volume_24h"],
        volume_data["volume_30d_avg"],
        volume_data["volume_30d_std"],
        volume_data.get("spread_current", 0.003),
        volume_data.get("spread_30d_avg", 0.003),
        volume_data.get("spread_30d_std", 0.001),
    )
    
    # ═══════════════════════════════════════════════════════
    # LAYER 2: LP-SPECIFIC METRICS (NEW in v2.0.1)
    # ═══════════════════════════════════════════════════════
    
    # 2.1 Uncertainty Inversion
    model_clarity = regime_output.get("confidence", {}).get("score", 0.5)
    uncertainty_value = compute_uncertainty_value_for_lp(
        model_clarity,
        regime_output["regime"],
        trend_persistence["persistence_score"],
    )
    
    # 2.2 Fee/Variance Ratio (per pool)
    daily_variance = np.var(returns) if len(returns) > 0 else 0.001
    
    pool_fee_variance = {}
    for pool_id, config in pool_configs.items():
        pool_fee_variance[pool_id] = compute_fee_variance_ratio(
            expected_daily_fee_rate=config.get("expected_daily_fee_rate", 0.0005),
            realized_variance_daily=daily_variance,
            position_size=current_positions.get(pool_id, {}).get("size", 10000),
            range_width=config.get("range_width", 0.30),
            holding_period_days=30,
        )
    
    # Aggregate fee/variance for global decision
    avg_fv_ratio = np.mean([p["fee_variance_ratio"] for p in pool_fee_variance.values()])
    global_fee_variance = {
        "fee_variance_ratio": round(avg_fv_ratio, 2),
        "profitability": "PROFITABLE" if avg_fv_ratio > 2 else "MARGINAL" if avg_fv_ratio > 1 else "UNPROFITABLE",
    }
    
    # 2.3 LP Regime Classification
    lp_regime = classify_lp_regime(
        vol_structure=vol_structure,
        trend_persistence=trend_persistence,
        transition_subtype=transition_subtype,
        uncertainty_value=uncertainty_value,
        fee_regime=fee_regime,
        market_data={
            "regime_switches_7d": regime_output.get("confidence", {}).get("switches_7d", 0),
        },
    )
    
    # ═══════════════════════════════════════════════════════
    # LAYER 3: DUAL RISK MODEL
    # ═══════════════════════════════════════════════════════
    
    # 3.1 Directional Risk (from regime engine)
    risk_directional = regime_output.get("risk", {}).get("risk_level", 0)
    
    # 3.2 LP Risk (computed with new metrics)
    risk_lp_result = compute_risk_lp_v2(
        vol_structure=vol_structure,
        trend_persistence=trend_persistence,
        uncertainty_value=uncertainty_value,
        fee_variance_ratio=global_fee_variance,
        transition_subtype=transition_subtype,
        fee_regime=fee_regime,
    )
    
    # 3.3 Risk Quadrant
    risk_quadrant = classify_risk_quadrant(
        risk_directional, 
        risk_lp_result["risk_lp"]
    )
    
    # ═══════════════════════════════════════════════════════
    # LAYER 4: DECISION ENGINE
    # ═══════════════════════════════════════════════════════
    
    # 4.1 Get action from LP Regime
    lp_action = lp_regime.get("action", {})
    
    # 4.2 Per-position decisions
    position_decisions = {}
    for pool_id, position in current_positions.items():
        fv = pool_fee_variance.get(pool_id, global_fee_variance)
        
        # Opportunity cost
        costs = compute_complete_costs(
            position_size=position.get("size", 10000),
            expected_daily_fees=position.get("expected_daily_fees", 50),
            days_out_of_market=estimate_reentry_days(lp_regime["lp_regime"]),
            gas_cost=20,
            slippage_bps=10,
            reentry_slippage_bps=15,
        )
        
        # Exit decision
        exit_decision = should_exit_lp_v2(
            current_il=position.get("current_il", 0),
            expected_daily_fees=position.get("expected_daily_fees", 50),
            risk_lp=risk_lp_result["risk_lp"],
            position_size=position.get("size", 10000),
            expected_days_until_reentry=estimate_reentry_days(lp_regime["lp_regime"]),
        )
        
        position_decisions[pool_id] = {
            "fee_variance": fv,
            "opportunity_cost": costs,
            "exit_decision": exit_decision,
            "recommended_action": determine_position_action(
                lp_regime, fv, risk_lp_result, exit_decision
            ),
        }
    
    # ═══════════════════════════════════════════════════════
    # OUTPUT
    # ═══════════════════════════════════════════════════════
    
    return {
        "timestamp": timestamp,
        "version": "2.0.1",
        
        "market_structure": {
            "vol_structure": vol_structure,
            "trend_persistence": trend_persistence,
            "transition_subtype": transition_subtype,
            "fee_regime": fee_regime,
        },
        
        "lp_metrics": {
            "uncertainty_value": uncertainty_value,
            "fee_variance_ratio": global_fee_variance,
            "lp_regime": lp_regime,
        },
        
        "dual_risk": {
            "risk_directional": round(risk_directional, 2),
            "risk_lp": risk_lp_result,
            "quadrant": risk_quadrant,
        },
        
        "decision": {
            "lp_regime": lp_regime["lp_regime"],
            "action": lp_action,
            "confidence": lp_regime.get("confidence", 0.5),
        },
        
        "positions": position_decisions,
        
        "summary": generate_summary_v201(
            lp_regime, risk_lp_result, uncertainty_value, global_fee_variance
        ),
    }


def estimate_reentry_days(lp_regime: str) -> int:
    """Estimate days until would re-enter LP if exit now."""
    estimates = {
        "HARVEST": 1,
        "MEAN_REVERT": 2,
        "VOLATILE_CHOP": 2,
        "TRANSITION_OPPORTUNITY": 3,
        "GAP_RISK": 5,
        "BREAKOUT": 7,
        "TRENDING": 14,
        "CHURN": 10,
    }
    return estimates.get(lp_regime, 5)


def determine_position_action(lp_regime, fv, risk_lp, exit_decision):
    """Determine action for a specific position."""
    if exit_decision.get("action") == "EXIT":
        return "EXIT"
    
    if fv["profitability"] == "UNPROFITABLE":
        return "EXIT_LOW_FV"
    
    regime = lp_regime["lp_regime"]
    
    if regime in ["HARVEST", "VOLATILE_CHOP"]:
        return "INCREASE_OR_HOLD"
    elif regime in ["MEAN_REVERT", "TRANSITION_OPPORTUNITY"]:
        return "HOLD_OR_INCREASE"
    elif regime in ["GAP_RISK"]:
        return "HOLD_WIDEN_RANGE"
    elif regime in ["BREAKOUT"]:
        return "REDUCE_AND_WIDEN"
    elif regime in ["TRENDING"]:
        return "REDUCE_SIGNIFICANTLY"
    elif regime in ["CHURN"]:
        return "EXIT_OR_MINIMAL"
    else:
        return "HOLD"
```

---

## Part IX: Output Schema & Telegram Format

### 9.1 Complete Output Schema

```python
{
    "timestamp": "2026-02-08T16:00:00Z",
    "version": "2.0.1",
    
    "market_structure": {
        "vol_structure": {
            "classification": "RANGE_DOMINANT",
            "components": {
                "sigma_total": 0.72,
                "sigma_trend": 0.18,
                "sigma_range": 0.65,
                "sigma_jump": 0.15,
                "trend_share": 0.06,
                "range_share": 0.81,
                "jump_share": 0.04,
            },
            "lp_implication": "HIGH_FEE_OPPORTUNITY",
        },
        
        "trend_persistence": {
            "autocorrelation": 0.12,
            "direction_consistency": 0.35,
            "mean_reversion_strength": 0.28,
            "persistence_score": 0.22,
            "lp_implication": "CHOPPY",
            "lp_action": "INCREASE_EXPOSURE",
        },
        
        "transition_subtype": {
            "subtype": "POST_TREND",
            "confidence": 0.75,
            "lp_implication": "OPPORTUNITY",
        },
        
        "fee_regime": {
            "regime": "ELEVATED",
            "volume_z": 1.8,
            "spread_z": 1.2,
        },
    },
    
    "lp_metrics": {
        "uncertainty_value": {
            "model_clarity": 0.30,
            "lp_uncertainty_value": 0.84,
            "interpretation": "HIGH_LP_OPPORTUNITY",
            "action_hint": "Market directionless, harvest volatility",
        },
        
        "fee_variance_ratio": {
            "fee_variance_ratio": 2.8,
            "profitability": "PROFITABLE",
            "expected_monthly_fees": 450,
            "expected_il_proxy": 160,
            "expected_net_pnl": 290,
        },
        
        "lp_regime": {
            "lp_regime": "HARVEST",
            "lp_opportunity": "MAXIMUM",
            "confidence": 0.80,
            "action": {
                "notional": "INCREASE_TO_90",
                "range": "TIGHTEN",
                "rebalance": "AGGRESSIVE",
            },
        },
    },
    
    "dual_risk": {
        "risk_directional": -0.35,
        "risk_lp": {
            "risk_lp": 0.62,
            "interpretation": "EXCELLENT_FOR_LP",
            "components": {
                "vol_structure": 0.50,
                "trend_persistence": 0.56,
                "uncertainty_value": 0.68,
                "fee_variance": 0.45,
                "fee_regime": 0.50,
            },
        },
        "quadrant": {
            "quadrant": "Q2_LP_OPPORTUNITY",
            "description": "Bad for directional, excellent for LP",
        },
    },
    
    "decision": {
        "lp_regime": "HARVEST",
        "action": {
            "notional": "INCREASE_TO_90",
            "range": "TIGHTEN",
            "rebalance": "AGGRESSIVE",
        },
        "confidence": 0.80,
    },
    
    "positions": {
        "ETH-USDC": {
            "fee_variance": {
                "fee_variance_ratio": 2.8,
                "profitability": "PROFITABLE",
            },
            "opportunity_cost": {
                "cost_of_action": 65,
                "cost_of_inaction": 380,
                "recommendation": "STAY",
            },
            "recommended_action": "INCREASE_OR_HOLD",
        },
    },
    
    "summary": {
        "headline": "🌾 HARVEST REGIME — Peak LP Opportunity",
        "key_metrics": [
            "Vol structure: 81% range-dominant",
            "Trend persistence: 22% (choppy)",
            "Uncertainty value: 84% (directionless)",
            "Fee/Variance: 2.8x (profitable)",
        ],
        "primary_action": "Increase to 90% notional, tighten ranges",
        "v1_comparison": "v1.x would EXIT (risk_dir=-0.35). v2.0.1 DEPLOYS (risk_lp=+0.62)",
    },
}
```

### 9.2 Telegram Format v2.0.1

```
══════════════════════════════════════════
  LP INTELLIGENCE v2.0.1 — FINAL
  "Volatility as Opportunity"
══════════════════════════════════════════

🌾 LP REGIME: HARVEST
   Peak fee extraction opportunity

📊 VOLATILITY STRUCTURE
┌──────────────────────────────────────┐
│ ████████████████░░░ 81% RANGE       │ ← GOOD
│ ██░░░░░░░░░░░░░░░░░  6% trend       │ ← low
│ █░░░░░░░░░░░░░░░░░░  4% jump        │ ← low
└──────────────────────────────────────┘
σ_total = 72% | Classification: RANGE_DOMINANT

📈 TREND PERSISTENCE: 22% (CHOPPY)
├─ Autocorrelation: 0.12 (low)
├─ Direction consistency: 35% (unstable)
├─ Mean reversion: 0.28 (good)
└─ LP Implication: INCREASE EXPOSURE ✨

🎯 UNCERTAINTY VALUE: 84%
├─ Model clarity: 30% (low)
├─ LP interpretation: HIGH OPPORTUNITY
└─ "Market directionless = harvest vol"

💰 FEE/VARIANCE RATIO: 2.8x
├─ Expected fees/mo: $450
├─ Expected IL proxy: $160
├─ Expected net P&L: +$290
└─ Status: PROFITABLE ✓

📊 DUAL RISK MODEL
┌──────────────────────────────────────┐
│            risk_lp = +0.62          │
│                  │                  │
│    Q2 ██████████│      Q1          │
│    WE ARE HERE  │                  │
│  ───────────────┼────────────────  │
│    Q4           │      Q3          │
│                 │                  │
│       risk_dir = -0.35             │
└──────────────────────────────────────┘
Quadrant: Q2 — LP OPPORTUNITY
risk_lp breakdown:
  vol_structure:     +0.50
  trend_persistence: +0.56
  uncertainty_value: +0.68
  fee_variance:      +0.45
  fee_regime:        +0.50

💡 KEY INSIGHT
┌──────────────────────────────────────┐
│ v1.x sees: risk_dir = -0.35         │
│ v1.x says: "RISK OFF → EXIT LP"     │
│                                     │
│ v2.0.1 sees: risk_lp = +0.62        │
│ v2.0.1 says: "HARVEST → DEPLOY!"    │
│                                     │
│ The difference: $290/mo vs $0/mo    │
└──────────────────────────────────────┘

📋 DECISION
┌──────────────────────────────────────┐
│ LP Regime: HARVEST                  │
│ Notional:  INCREASE TO 90%          │
│ Range:     TIGHTEN                  │
│ Rebalance: AGGRESSIVE               │
│ Confidence: 80%                     │
└──────────────────────────────────────┘

📈 POSITION: ETH-USDC
├─ Fee/Variance: 2.8x (profitable)
├─ Opportunity cost if exit: $380
├─ Cost of exit: $65
└─ Action: INCREASE_OR_HOLD

══════════════════════════════════════════
```

---

## Part X: Configuration (v2.0.1)

```python
# ============================================================
# LP INTELLIGENCE SYSTEM v2.0.1 — CONFIGURATION
# ============================================================

LP_VERSION = "2.0.1"
LP_PARADIGM = "volatility_as_opportunity"

# ── Volatility Decomposition ──────────────────────────────
VOL_DECOMPOSITION = {
    "window": 30,
    "jump_threshold_sigma": 3.0,
    "trend_ma_window": 7,
}

VOL_STRUCTURE_THRESHOLDS = {
    "trend_dominant": 0.50,
    "range_dominant": 0.50,
    "jump_elevated": 0.20,
    "low_vol_annual": 0.25,
}

# ── Trend Persistence ─────────────────────────────────────
TREND_PERSISTENCE = {
    "window": 14,
    "trending_threshold": 0.5,
    "choppy_threshold": 0.2,
    "weights": {
        "autocorrelation": 0.4,
        "direction_consistency": 0.4,
        "mean_reversion": 0.2,
    },
}

# ── Uncertainty Inversion ─────────────────────────────────
UNCERTAINTY_INVERSION = {
    "regime_multipliers": {
        "BULL": 0.8,
        "BEAR": 0.8,
        "RANGE": 1.0,
        "TRANSITION": 1.2,
    },
    "high_opportunity_threshold": 0.7,
    "moderate_threshold": 0.4,
}

# ── Fee/Variance Ratio ────────────────────────────────────
FEE_VARIANCE = {
    "highly_profitable": 3.0,
    "profitable": 2.0,
    "marginal": 1.5,
    "break_even": 1.0,
    "holding_period_days": 30,
    "il_proxy_cap": 0.5,
}

# ── LP Regime Taxonomy ────────────────────────────────────
LP_REGIMES = {
    "HARVEST": {"notional": 0.90, "range_mult": 0.8, "rebalance": "aggressive"},
    "MEAN_REVERT": {"notional": 0.70, "range_mult": 1.0, "rebalance": "normal"},
    "VOLATILE_CHOP": {"notional": 0.80, "range_mult": 1.1, "rebalance": "active"},
    "TRANSITION_OPPORTUNITY": {"notional": 0.75, "range_mult": 1.2, "rebalance": "active"},
    "GAP_RISK": {"notional": 0.50, "range_mult": 1.5, "rebalance": "cautious"},
    "BREAKOUT": {"notional": 0.40, "range_mult": 1.5, "rebalance": "cautious"},
    "TRENDING": {"notional": 0.30, "range_mult": 2.0, "rebalance": "disabled"},
    "CHURN": {"notional": 0.10, "range_mult": 2.5, "rebalance": "disabled"},
}

# ── Dual Risk Model ───────────────────────────────────────
RISK_LP_WEIGHTS = {
    "vol_structure": 0.25,
    "trend_persistence": 0.25,
    "uncertainty_value": 0.20,
    "fee_variance": 0.20,
    "fee_regime": 0.10,
}

# ── Opportunity Cost ──────────────────────────────────────
OPPORTUNITY_COST = {
    "gas_cost_default": 20,
    "slippage_bps": 10,
    "reentry_slippage_bps": 15,
    "timing_risk_premium": 0.005,
}

# ── Position Limits ───────────────────────────────────────
LP_MAX_PORTFOLIO = 0.80          # higher than v1.x
LP_MIN_CASH = 0.10
LP_MAX_SINGLE_POOL = 0.30

# ── IL Thresholds ─────────────────────────────────────────
LP_IL_SOFT = -0.10
LP_IL_HARD = -0.20
```

---

## Part XI: Quick Reference Card (v2.0.1 FINAL)

```
╔════════════════════════════════════════════════════════════════╗
║          LP INTELLIGENCE v2.0.1 — QUICK REFERENCE              ║
╠════════════════════════════════════════════════════════════════╣
║                                                                ║
║  PARADIGM: Volatility = Structure, not just Risk               ║
║                                                                ║
║  ┌────────────────────────────────────────────────────────┐   ║
║  │ VOL STRUCTURE          │ LP IMPLICATION                │   ║
║  ├────────────────────────┼───────────────────────────────┤   ║
║  │ RANGE_DOMINANT (>50%)  │ HIGH FEE OPPORTUNITY ✨       │   ║
║  │ TREND_DOMINANT (>50%)  │ HIGH IL RISK ⚠️              │   ║
║  │ JUMP_ELEVATED (>20%)   │ GAP RISK 🚨                  │   ║
║  └────────────────────────┴───────────────────────────────┘   ║
║                                                                ║
║  ┌────────────────────────────────────────────────────────┐   ║
║  │ TREND PERSISTENCE      │ LP IMPLICATION                │   ║
║  ├────────────────────────┼───────────────────────────────┤   ║
║  │ > 0.5 (TRENDING)       │ REDUCE exposure               │   ║
║  │ < 0.2 (CHOPPY)         │ INCREASE exposure ✨          │   ║
║  └────────────────────────┴───────────────────────────────┘   ║
║                                                                ║
║  ┌────────────────────────────────────────────────────────┐   ║
║  │ UNCERTAINTY            │ LP IMPLICATION                │   ║
║  ├────────────────────────┼───────────────────────────────┤   ║
║  │ LOW clarity (v1.x: bad)│ v2.0.1: OPPORTUNITY ✨        │   ║
║  │ HIGH clarity (v1.x:good│ v2.0.1: TREND FORMING ⚠️     │   ║
║  └────────────────────────┴───────────────────────────────┘   ║
║                                                                ║
║  ┌────────────────────────────────────────────────────────┐   ║
║  │ FEE/VARIANCE RATIO     │ ACTION                        │   ║
║  ├────────────────────────┼───────────────────────────────┤   ║
║  │ > 3.0                  │ MAXIMIZE allocation           │   ║
║  │ 2.0 - 3.0              │ STANDARD allocation           │   ║
║  │ 1.0 - 2.0              │ CAUTIOUS                      │   ║
║  │ < 1.0                  │ AVOID / EXIT                  │   ║
║  └────────────────────────┴───────────────────────────────┘   ║
║                                                                ║
║  ┌────────────────────────────────────────────────────────┐   ║
║  │ LP REGIME              │ NOTIONAL │ RANGE │ REBALANCE  │   ║
║  ├────────────────────────┼──────────┼───────┼────────────┤   ║
║  │ HARVEST                │ 90%      │ Tight │ Aggressive │   ║
║  │ MEAN_REVERT            │ 70%      │ Std   │ Normal     │   ║
║  │ VOLATILE_CHOP          │ 80%      │ Slight│ Active     │   ║
║  │ TRANSITION_OPP         │ 75%      │ Mod   │ Active     │   ║
║  │ GAP_RISK               │ 50%      │ Wide  │ Cautious   │   ║
║  │ BREAKOUT               │ 40%      │ Wide  │ Cautious   │   ║
║  │ TRENDING               │ 30%      │ V.Wide│ Disabled   │   ║
║  │ CHURN                  │ 10%      │ V.Wide│ Disabled   │   ║
║  └────────────────────────┴──────────┴───────┴────────────┘   ║
║                                                                ║
║  RISK QUADRANT:                                                ║
║  ┌─────────────────────────────────────────────────────────┐  ║
║  │ Q2: dir-, lp+ → DEPLOY LP (KEY INSIGHT!)               │  ║
║  │ Q1: dir+, lp+ → FULL DEPLOYMENT                        │  ║
║  │ Q3: dir+, lp- → HOLD SPOT, REDUCE LP                   │  ║
║  │ Q4: dir-, lp- → MINIMIZE / EXIT                        │  ║
║  └─────────────────────────────────────────────────────────┘  ║
║                                                                ║
║  v1.x vs v2.0.1:                                               ║
║  risk_dir = -0.5 → v1.x: EXIT | v2.0.1: CHECK risk_lp FIRST   ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
```

---

## Part XII: Version Comparison (Final)

| Aspect | v1.x | v2.0.1 |
|--------|------|--------|
| Paradigm | Risk Governor | LP Intelligence |
| Volatility | Scalar (bad) | Decomposed (structure) |
| Trend | Momentum sign | **Persistence** |
| Uncertainty | Bad for LP | **Good for LP (inverted)** |
| Fee analysis | None | **Fee/Variance Ratio** |
| LP Regimes | None | **8 LP-specific regimes** |
| Risk model | 1D (directional) | **2D (directional + LP)** |
| Exit logic | Binary | Opportunity cost aware |
| TRANSITION | Avoid | **Subtype analysis** |
| Q2 quadrant | Exit (risk-off) | **Deploy (LP opportunity)** |

---

## Appendix: The Core Thesis

```
┌────────────────────────────────────────────────────────────┐
│                 THE LP INTELLIGENCE THESIS                 │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  LP is not a bet on price DIRECTION.                       │
│  LP is a bet on price BEHAVIOR.                            │
│                                                            │
│  The question is not: "Where will price go?"               │
│  The question is: "How will price get there?"              │
│                                                            │
│  Trending smoothly?     → LP loses (IL accumulates)        │
│  Chopping around?       → LP wins (fees accumulate)        │
│  Gapping violently?     → LP loses (gap risk)              │
│  Directionless chaos?   → LP wins (harvest vol)            │
│                                                            │
│  v2.0.1 asks the RIGHT question.                           │
│  v1.x asked the WRONG question (but protected capital).    │
│                                                            │
│  The key insight: UNCERTAINTY IS FUEL FOR LP.              │
│  When the market doesn't know where it's going,            │
│  LP profits from the indecision.                           │
│                                                            │
│  This is the fundamental paradigm shift.                   │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

---

**Status: READY FOR ANALYST REVIEW**
