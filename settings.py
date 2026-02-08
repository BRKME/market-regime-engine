# ============================================================
# LP POLICY ENGINE v2.0.1 — Configuration
# Add this section to the end of settings.py
# ============================================================

# ── Trend Persistence Thresholds ──────────────────────────
LP_PERSISTENCE_CHOPPY = 0.20
LP_PERSISTENCE_MODERATE = 0.40
LP_PERSISTENCE_TRENDING = 0.50

# ── Uncertainty Inversion ─────────────────────────────────
LP_UNCERTAINTY_REGIME_MULT = {
    "BULL": 0.8,
    "BEAR": 0.8,
    "RANGE": 1.0,
    "TRANSITION": 1.2,  # Uncertainty is premium for LP
}

# ── Fee/Variance Ratio Thresholds ─────────────────────────
LP_FV_HIGHLY_PROFITABLE = 3.0
LP_FV_PROFITABLE = 2.0
LP_FV_MARGINAL = 1.5
LP_FV_UNPROFITABLE = 1.0

# ── Fee Regime Multipliers ────────────────────────────────
LP_FEE_REGIME_MULT = {
    "ELEVATED": 1.5,
    "NORMAL": 1.0,
    "DEPRESSED": 0.6,
}

LP_FEE_REGIME_CONTRIB = {
    "ELEVATED": +0.5,
    "NORMAL": 0,
    "DEPRESSED": -0.5,
}

# ── Vol Structure Contribution to risk_lp ─────────────────
LP_VOL_STRUCTURE_CONTRIB = {
    "RANGE_DOMINANT": +0.5,
    "BALANCED": +0.1,
    "LOW_VOL": -0.2,
    "JUMP_ELEVATED": -0.3,
    "TREND_DOMINANT": -0.5,
}

# ── risk_lp Computation Weights ───────────────────────────
LP_RISK_WEIGHTS = {
    "vol_structure": 0.25,
    "trend_persistence": 0.25,
    "uncertainty_value": 0.20,
    "fee_variance": 0.20,
    "fee_regime": 0.10,
}

# ── Churn Detection ───────────────────────────────────────
LP_CHURN_SWITCHES = 5  # switches in 30d to trigger CHURN

# ── LP Regime Parameters ──────────────────────────────────
LP_REGIME_PARAMS = {
    "HARVEST": {"notional": 0.90, "range": "tight", "rebalance": "aggressive"},
    "MEAN_REVERT": {"notional": 0.70, "range": "standard", "rebalance": "normal"},
    "VOLATILE_CHOP": {"notional": 0.80, "range": "moderate", "rebalance": "active"},
    "TRENDING": {"notional": 0.30, "range": "wide", "rebalance": "minimal"},
    "BREAKOUT": {"notional": 0.40, "range": "wide", "rebalance": "cautious"},
    "CHURN": {"notional": 0.10, "range": "very_wide", "rebalance": "disabled"},
    "GAP_RISK": {"notional": 0.50, "range": "wide", "rebalance": "cautious"},
    "AVOID": {"notional": 0.00, "range": "n/a", "rebalance": "disabled"},
}

# ── LP Regime Emoji ───────────────────────────────────────
LP_REGIME_EMOJI = {
    "HARVEST": "🌾",
    "MEAN_REVERT": "🔄",
    "VOLATILE_CHOP": "⚡",
    "TRENDING": "📉",
    "BREAKOUT": "⚠️",
    "CHURN": "🚫",
    "GAP_RISK": "🕳",
    "AVOID": "🛑",
}

# ── Risk Quadrant Descriptions ────────────────────────────
LP_QUADRANT_DESC = {
    "Q1": "Q1: Both favorable",
    "Q2": "Q2: LP opportunity ✨",
    "Q3": "Q3: Prefer spot",
    "Q4": "Q4: Defensive",
}
