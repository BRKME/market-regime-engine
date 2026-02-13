"""
LP Policy Engine v2.0.1 — "Volatility as Opportunity"

This module does NOT replace Market Regime Engine.
It uses regime output to answer a DIFFERENT question:
"Does LP have positive expected value, and how to manage it?"

Architecture:
  Regime Engine → LP Policy Engine → LP Decision
  (market risk)   (LP-specific)      (allocation)

Key insight: risk_directional ≠ risk_lp
  - Directional risk = "where will price go?"
  - LP risk = "is LP profitable regardless of direction?"
"""

import numpy as np
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional

import settings as cfg


# ============================================================
# ENUMS
# ============================================================

class LPRegime(Enum):
    """LP-specific regime classification."""
    HARVEST = "HARVEST"              # Peak fee extraction
    MEAN_REVERT = "MEAN_REVERT"      # Stable range LP
    VOLATILE_CHOP = "VOLATILE_CHOP"  # High vol, non-directional
    TRENDING = "TRENDING"            # IL accumulation risk
    BREAKOUT = "BREAKOUT"            # Pre-breakout danger
    CHURN = "CHURN"                  # Costs > fees
    GAP_RISK = "GAP_RISK"            # Jump-elevated
    AVOID = "AVOID"                  # Capital preservation


class RiskQuadrant(Enum):
    """Dual risk model quadrant."""
    Q1_FAVORABLE = "Q1"          # dir+, lp+ → full deployment
    Q2_LP_OPPORTUNITY = "Q2"     # dir-, lp+ → LP focus (KEY!)
    Q3_SPOT_PREFERRED = "Q3"     # dir+, lp- → hold spot
    Q4_DEFENSIVE = "Q4"          # dir-, lp- → minimize


# ============================================================
# DATA CLASSES
# ============================================================

@dataclass
class LPPolicy:
    """Final LP policy output."""
    lp_regime: LPRegime
    risk_lp: float
    risk_directional: float
    risk_quadrant: RiskQuadrant
    fee_variance_ratio: float
    uncertainty_value: float
    trend_persistence: float
    vol_structure: str
    
    # Policy parameters
    max_exposure: float           # Raw LP exposure (of LP book)
    effective_exposure: float     # Risk-adjusted effective exposure
    range_width: str
    rebalance: str
    hedge_recommended: bool
    
    # Signals for explanation
    signals: List[str]
    
    # Confidence
    confidence: float


# ============================================================
# CORE COMPUTATIONS
# ============================================================

def estimate_vol_structure(
    vol_z: float,
    momentum: float,
    stability: float,
) -> Dict:
    """
    Estimate volatility structure from regime engine buckets.
    
    Returns decomposition into trend/range/jump components.
    """
    # Convert vol_z to annual vol estimate
    vol_total = vol_z * 0.30  # rough: vol_z=1 ≈ 30% annual
    
    # Heuristic: high |momentum| + stable direction = trending
    trend_factor = (abs(momentum) + max(0, stability)) / 2
    trend_factor = min(1.0, trend_factor)
    
    # Range component: what's left after trend
    range_factor = 1.0 - trend_factor * 0.7
    
    # Jump component: elevated if vol_z is extreme
    jump_factor = 0.1 if vol_z < 2.0 else 0.2 if vol_z < 3.0 else 0.3
    
    # Normalize
    total = trend_factor + range_factor + jump_factor
    trend_share = trend_factor / total
    range_share = range_factor / total
    jump_share = jump_factor / total
    
    # Classification
    if vol_total < 0.25:
        classification = "LOW_VOL"
    elif jump_share > 0.20:
        classification = "JUMP_ELEVATED"
    elif trend_share > 0.50:
        classification = "TREND_DOMINANT"
    elif range_share > 0.50:
        classification = "RANGE_DOMINANT"
    else:
        classification = "BALANCED"
    
    return {
        "sigma_total": round(vol_total, 4),
        "trend_share": round(trend_share, 3),
        "range_share": round(range_share, 3),
        "jump_share": round(jump_share, 3),
        "classification": classification,
    }


def compute_trend_persistence(
    momentum: float,
    stability: float,
    switches_30d: int,
) -> Dict:
    """
    Compute trend persistence from regime engine buckets.
    
    Key insight: We care about STABILITY of direction, not the sign.
    High |momentum| + high stability = trending = BAD for LP.
    """
    # Direction consistency from stability
    # stability > 0 = stable = high persistence
    direction_consistency = (stability + 1) / 2  # map [-1,1] to [0,1]
    
    # Autocorrelation proxy from momentum magnitude
    autocorr_proxy = abs(momentum)
    
    # Mean reversion strength from switches
    if switches_30d <= 2:
        mr_strength = 0.3
    elif switches_30d <= 4:
        mr_strength = 0.5  # good mean reversion
    else:
        mr_strength = 0.2  # too much = churn
    
    # Composite persistence score
    persistence_score = (
        autocorr_proxy * 0.4 +
        direction_consistency * 0.4 +
        (1 - mr_strength) * 0.2
    )
    persistence_score = max(0, min(1, persistence_score))
    
    # LP implication
    if persistence_score > cfg.LP_PERSISTENCE_TRENDING:
        lp_implication = "TRENDING"
    elif persistence_score > cfg.LP_PERSISTENCE_MODERATE:
        lp_implication = "MODERATE"
    else:
        lp_implication = "CHOPPY"
    
    return {
        "autocorrelation": round(autocorr_proxy, 3),
        "direction_consistency": round(direction_consistency, 3),
        "mean_reversion_strength": round(mr_strength, 3),
        "persistence_score": round(persistence_score, 3),
        "lp_implication": lp_implication,
    }


def compute_uncertainty_value(
    model_clarity: float,
    regime: str,
    trend_persistence: float,
) -> float:
    """
    Compute LP uncertainty value (INVERTED from clarity).
    
    KEY INSIGHT:
    For LP, low clarity = no clear trend = OPPORTUNITY
    This INVERTS the directional trading signal.
    """
    # Base: invert clarity
    base_uncertainty = 1.0 - model_clarity
    
    # Regime multiplier (TRANSITION uncertainty is especially valuable)
    regime_mult = cfg.LP_UNCERTAINTY_REGIME_MULT.get(regime, 1.0)
    
    # Persistence bonus (low persistence + low clarity = maximum opportunity)
    persistence_bonus = (1 - trend_persistence) * 0.2
    
    uncertainty_value = min(1.0, base_uncertainty * regime_mult + persistence_bonus)
    
    return round(uncertainty_value, 2)


def compute_fee_variance_ratio(
    vol_structure: Dict,
    fee_regime: str = "NORMAL",
) -> float:
    """
    Estimate fee/variance ratio.
    
    Simplified model:
    - Range vol generates fees
    - Trend vol generates IL
    - Ratio determines profitability
    """
    range_share = vol_structure["range_share"]
    trend_share = vol_structure["trend_share"]
    sigma_total = vol_structure["sigma_total"]
    
    # Fee proxy: range component * vol level * fee multiplier
    fee_mult = cfg.LP_FEE_REGIME_MULT.get(fee_regime, 1.0)
    fee_proxy = range_share * sigma_total * fee_mult
    
    # IL proxy: trend component * vol level
    il_proxy = trend_share * sigma_total + 0.05  # floor
    
    # Ratio
    ratio = fee_proxy / il_proxy if il_proxy > 0 else 5.0
    
    return round(min(5.0, max(0.1, ratio)), 2)


def compute_risk_lp(
    vol_structure: Dict,
    trend_persistence: Dict,
    uncertainty_value: float,
    fee_variance_ratio: float,
    fee_regime: str = "NORMAL",
) -> float:
    """
    Compute LP-specific risk score.
    
    risk_lp ∈ [-1, +1]
    -1 = terrible for LP (trending, high costs)
    +1 = excellent for LP (choppy, high fees)
    
    INDEPENDENT from risk_directional!
    """
    weights = cfg.LP_RISK_WEIGHTS
    risk_lp = 0.0
    
    # Component 1: Vol structure
    vol_contrib = cfg.LP_VOL_STRUCTURE_CONTRIB.get(
        vol_structure["classification"], 0
    )
    risk_lp += vol_contrib * weights["vol_structure"]
    
    # Component 2: Trend persistence (inverted)
    persistence = trend_persistence["persistence_score"]
    persistence_contrib = (0.5 - persistence) * 2  # low = good
    risk_lp += persistence_contrib * weights["trend_persistence"]
    
    # Component 3: Uncertainty value (high = good)
    uncertainty_contrib = (uncertainty_value - 0.5) * 2
    risk_lp += uncertainty_contrib * weights["uncertainty_value"]
    
    # Component 4: Fee/variance ratio
    if fee_variance_ratio < cfg.LP_FV_UNPROFITABLE:
        fv_contrib = -1.0
    elif fee_variance_ratio < cfg.LP_FV_PROFITABLE:
        fv_contrib = (fee_variance_ratio - 1.0) / 2 - 0.25
    else:
        fv_contrib = min(1.0, (fee_variance_ratio - 2.0) / 2 + 0.5)
    risk_lp += fv_contrib * weights["fee_variance"]
    
    # Component 5: Fee regime
    fee_contrib = cfg.LP_FEE_REGIME_CONTRIB.get(fee_regime, 0)
    risk_lp += fee_contrib * weights["fee_regime"]
    
    return round(max(-1.0, min(1.0, risk_lp)), 2)


def classify_risk_quadrant(
    risk_directional: float,
    risk_lp: float,
) -> RiskQuadrant:
    """
    Classify into risk quadrant.
    
    KEY INSIGHT: Q2 is where LP Intelligence shines.
    risk_dir < 0, risk_lp > 0 → DEPLOY LP (not exit!)
    """
    if risk_directional >= 0 and risk_lp >= 0:
        return RiskQuadrant.Q1_FAVORABLE
    elif risk_directional < 0 and risk_lp >= 0:
        return RiskQuadrant.Q2_LP_OPPORTUNITY  # KEY!
    elif risk_directional >= 0 and risk_lp < 0:
        return RiskQuadrant.Q3_SPOT_PREFERRED
    else:
        return RiskQuadrant.Q4_DEFENSIVE


def classify_lp_regime(
    vol_structure: Dict,
    trend_persistence: Dict,
    uncertainty_value: float,
    fee_variance_ratio: float,
    risk_lp: float,
    switches_30d: int,
    structural_break: bool,
) -> LPRegime:
    """
    Classify into LP-specific regime.
    """
    vol_class = vol_structure["classification"]
    persistence = trend_persistence["persistence_score"]
    
    # Priority 1: Avoid dangerous situations
    if switches_30d >= cfg.LP_CHURN_SWITCHES:
        return LPRegime.CHURN
    
    if fee_variance_ratio < cfg.LP_FV_UNPROFITABLE:
        return LPRegime.AVOID
    
    if vol_class == "JUMP_ELEVATED":
        return LPRegime.GAP_RISK
    
    if persistence > cfg.LP_PERSISTENCE_TRENDING and vol_class == "TREND_DOMINANT":
        return LPRegime.TRENDING
    
    # Priority 2: Identify opportunities
    if (vol_class == "RANGE_DOMINANT" and
        persistence < cfg.LP_PERSISTENCE_CHOPPY and
        uncertainty_value > 0.6):
        return LPRegime.HARVEST
    
    if (vol_class == "RANGE_DOMINANT" and
        vol_structure["sigma_total"] > 0.80 and
        persistence < 0.25):
        return LPRegime.VOLATILE_CHOP
    
    if (vol_class in ["RANGE_DOMINANT", "BALANCED"] and
        persistence < cfg.LP_PERSISTENCE_MODERATE and
        trend_persistence["mean_reversion_strength"] > 0.2):
        return LPRegime.MEAN_REVERT
    
    # Default based on risk_lp
    if risk_lp > 0.3:
        return LPRegime.MEAN_REVERT
    elif risk_lp > -0.3:
        return LPRegime.BREAKOUT
    else:
        return LPRegime.AVOID


# ============================================================
# MAIN POLICY ENGINE
# ============================================================

def compute_lp_policy(regime_output: Dict) -> LPPolicy:
    """
    Main LP Policy Engine entry point.
    
    Takes Regime Engine output, computes LP-specific metrics,
    returns LP policy recommendation.
    """
    # Extract from regime output
    regime = regime_output.get("regime", "TRANSITION")
    risk_info = regime_output.get("risk", {})
    risk_directional = risk_info.get("risk_level", 0)
    
    conf = regime_output.get("confidence", {})
    model_clarity = conf.get("quality_adjusted", 0.5)
    switches_30d = conf.get("switches_30d", 0)
    
    buckets = regime_output.get("buckets", {})
    momentum = buckets.get("Momentum", 0)
    stability = buckets.get("Stability", 0)
    
    meta = regime_output.get("metadata", {})
    vol_z = meta.get("vol_z", 1.0)
    
    norm = regime_output.get("normalization", {})
    structural_break = norm.get("break_active", False)
    
    # Determine fee regime from vol_z
    if vol_z > 2.0:
        fee_regime = "ELEVATED"
    elif vol_z < 0.5:
        fee_regime = "DEPRESSED"
    else:
        fee_regime = "NORMAL"
    
    # ── Step 1: Estimate vol structure ────────────────────
    vol_structure = estimate_vol_structure(vol_z, momentum, stability)
    
    # ── Step 2: Compute trend persistence ─────────────────
    trend_pers = compute_trend_persistence(momentum, stability, switches_30d)
    
    # ── Step 3: Compute uncertainty value (INVERTED) ──────
    uncertainty = compute_uncertainty_value(
        model_clarity, regime, trend_pers["persistence_score"]
    )
    
    # ── Step 4: Compute fee/variance ratio ────────────────
    fee_var_ratio = compute_fee_variance_ratio(vol_structure, fee_regime)
    
    # ── Step 5: Compute risk_lp ───────────────────────────
    risk_lp = compute_risk_lp(
        vol_structure, trend_pers, uncertainty, fee_var_ratio, fee_regime
    )
    
    # ── Step 6: Classify quadrant and regime ──────────────
    quadrant = classify_risk_quadrant(risk_directional, risk_lp)
    
    lp_regime = classify_lp_regime(
        vol_structure, trend_pers, uncertainty,
        fee_var_ratio, risk_lp, switches_30d, structural_break
    )
    
    # ── Step 7: Get policy parameters ─────────────────────
    regime_params = cfg.LP_REGIME_PARAMS.get(
        lp_regime.value,
        {"notional": 0.50, "range": "standard", "rebalance": "cautious"}
    )
    
    # Adjust for structural break
    if structural_break:
        regime_params = {
            "notional": min(regime_params["notional"], 0.40),
            "range": "wide",
            "rebalance": "cautious",
        }
    
    # Hedge recommendation
    hedge_recommended = (
        quadrant == RiskQuadrant.Q2_LP_OPPORTUNITY and
        risk_directional < -0.5
    )
    
    # ── Step 8: Generate explanation signals ──────────────
    signals = []
    
    if uncertainty > 0.6:
        signals.append("High uncertainty → fee opportunity")
    
    # Fix: distinguish directional vs non-directional persistence
    if trend_pers["lp_implication"] == "CHOPPY":
        signals.append("Low trend persistence → mean reversion")
    elif trend_pers["lp_implication"] == "TRENDING":
        # Check if it's truly directional or just high local persistence
        if stability > 0.3:
            signals.append("High trend persistence → IL risk")
        else:
            signals.append("Persistence high but unstable (churn)")
    
    if vol_structure["classification"] == "RANGE_DOMINANT":
        signals.append("Range-dominant volatility")
    elif vol_structure["classification"] == "TREND_DOMINANT":
        signals.append("Trend-dominant volatility")
    
    if fee_var_ratio > 2.0:
        signals.append(f"Fee/Var {fee_var_ratio:.1f}x → profitable")
    elif fee_var_ratio < 1.0:
        signals.append(f"Fee/Var {fee_var_ratio:.1f}x → unprofitable")
    
    if quadrant == RiskQuadrant.Q2_LP_OPPORTUNITY:
        signals.append("Q2: Dir risk high, LP opportunity exists")
    
    if structural_break:
        signals.append("Structural break → conservative")
    
    # Confidence
    confidence = min(0.95, 0.5 + abs(risk_lp) * 0.3 + (1 - trend_pers["persistence_score"]) * 0.2)
    
    # ── Step 9: Compute risk-adjusted effective exposure ──
    # Institutional rule: LP exposure capped by directional risk
    # effective = raw × risk_adjustment_factor
    raw_exposure = regime_params["notional"]
    
    # Risk adjustment factor: (1 + risk_dir) / 2 maps [-1,+1] to [0,1]
    # At risk_dir = -0.83: factor = 0.085
    # At risk_dir = 0: factor = 0.5
    # At risk_dir = +0.5: factor = 0.75
    risk_adjustment = (1 + risk_directional) / 2
    risk_adjustment = max(0.1, min(1.0, risk_adjustment))  # floor at 10%
    
    # Q2 bonus: if LP opportunity exists despite directional risk
    if quadrant == RiskQuadrant.Q2_LP_OPPORTUNITY and risk_lp > 0.3:
        risk_adjustment = max(risk_adjustment, 0.25)  # minimum 25% in Q2
    
    effective_exposure = round(raw_exposure * risk_adjustment, 2)
    
    # ── Return policy ─────────────────────────────────────
    return LPPolicy(
        lp_regime=lp_regime,
        risk_lp=risk_lp,
        risk_directional=risk_directional,
        risk_quadrant=quadrant,
        fee_variance_ratio=fee_var_ratio,
        uncertainty_value=uncertainty,
        trend_persistence=trend_pers["persistence_score"],
        vol_structure=vol_structure["classification"],
        max_exposure=raw_exposure,
        effective_exposure=effective_exposure,
        range_width=regime_params["range"],
        rebalance=regime_params["rebalance"],
        hedge_recommended=hedge_recommended,
        signals=signals,
        confidence=round(confidence, 2),
    )
