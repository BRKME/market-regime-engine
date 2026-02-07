"""
Market Regime Engine v3.3 — All weights, thresholds, and configuration.

Every tunable parameter lives here. No magic numbers in engine code.
"""

# ============================================================
# NORMALIZATION
# ============================================================

NORM_WINDOW_DEFAULT = 90
NORM_WINDOW_MIN = 30
NORM_WINDOW_MACRO = 180
Z_CLIP = 3.0

# Structural break detection
BREAK_VARIANCE_RATIO_THRESHOLD = 2.5
BREAK_T_STAT_THRESHOLD = 3.0
BREAK_SHORT_WINDOW = 30
BREAK_LONG_WINDOW = 60

# ============================================================
# MOMENTUM BUCKET WEIGHTS
# ============================================================

MOMENTUM_WEIGHTS = {
    "ROC_blend": 0.35,
    "Trend_strength": 0.25,
    "Alignment": 0.20,
    "DTMC": 0.20,
}

ROC_BLEND_30D_WEIGHT = 0.6
ROC_BLEND_90D_WEIGHT = 0.4

# Anti-decay
MOMENTUM_RELATIVE_WEIGHT = 0.75
MOMENTUM_ABSOLUTE_WEIGHT = 0.25
ABSOLUTE_ROC_THRESHOLD = 0.50  # 50% in 90d = extreme

# EMA periods for alignment
EMA_FAST = 20
EMA_MEDIUM = 50
EMA_SLOW = 200

# ADX
ADX_PERIOD = 14

# ============================================================
# STABILITY BUCKET WEIGHTS
# ============================================================

STABILITY_WEIGHTS = {
    "Vol": 0.40,
    "Liquidity": 0.35,
    "Depth": 0.25,
}

STABILITY_WEIGHTS_FALLBACK = {
    "Vol": 0.50,
    "Liquidity": 0.50,
}

REALIZED_VOL_WINDOW = 30

# ============================================================
# ROTATION BUCKET WEIGHTS
# ============================================================

ROTATION_VELOCITY_WEIGHT = 0.6
ROTATION_ACCEL_WEIGHT = 0.4

# Context adjustment
ROTATION_CONTEXT_MOMENTUM_THRESHOLD = 0.3
ROTATION_BULL_DAMPENING = 0.6
ROTATION_BEAR_DAMPENING = 0.4

# ============================================================
# SENTIMENT BUCKET WEIGHTS
# ============================================================

SENTIMENT_WEIGHTS = {
    "FG": 0.35,
    "Funding": 0.40,
    "OI": 0.25,
}

FG_ZONES = {
    (0, 25): -1.0,    # Extreme Fear
    (26, 45): -0.5,   # Fear
    (46, 55): 0.0,    # Neutral
    (56, 75): 0.5,    # Greed
    (76, 100): 1.0,   # Extreme Greed
}

# ============================================================
# MACRO BUCKET WEIGHTS
# ============================================================

MACRO_WEIGHTS = {
    "Dollar": 0.30,
    "Rate": 0.25,
    "YieldCurve": 0.20,
    "M2": 0.25,
}

MACRO_STALE_DAYS = 7
MACRO_STALE_PENALTY = 0.7
MACRO_EXPIRED_DAYS = 30

# ============================================================
# CROSS-ASSET
# ============================================================

CROSS_ASSET_CORR_WINDOW = 30
MACRO_BOOST_THRESHOLD = 0.6
MACRO_BOOST_MULTIPLIER = 1.3

# ============================================================
# LOGIT WEIGHTS
# ============================================================

LOGIT_BULL = {
    "Momentum": 1.2,
    "Stability": 0.5,
    "Rotation": -0.4,
    "Sentiment": 0.2,
    "Macro": 0.3,
}

LOGIT_BEAR = {
    "Momentum": -1.2,
    "Stability": -0.5,
    "Rotation": 0.4,
    "Sentiment": -0.2,
    "Macro": -0.3,
}

LOGIT_RANGE = {
    "abs_Momentum": -0.8,
    "Stability": 0.7,
    "abs_Vol_z": -0.3,
    "abs_Rotation": -0.3,
    "abs_Macro": -0.2,
}

LOGIT_TRANSITION = {
    "Vol_z": 0.7,
    "flip_signal": 1.0,
    "abs_dMacro_7d": 0.3,
}

# ============================================================
# SOFTMAX TEMPERATURE (f(Vol_z), no cycle)
# ============================================================

TEMPERATURE_MAP = [
    (2.0, 1.5),   # Vol_z > 2.0 → T = 1.5
    (1.0, 1.2),   # Vol_z > 1.0 → T = 1.2
    (0.0, 1.0),   # Vol_z > 0.0 → T = 1.0
    (float('-inf'), 0.8),  # else T = 0.8
]

# ============================================================
# EMA SMOOTHING
# ============================================================

EMA_ALPHA_MAP = [
    (1.5, 0.5),   # Vol_z > 1.5 → α = 0.5
    (0.5, 0.3),   # Vol_z > 0.5 → α = 0.3
    (float('-inf'), 0.2),  # else α = 0.2
]

# ============================================================
# REGIME SWITCHING — ASYMMETRIC (v3.3)
# ============================================================

REGIME_CONFIRMATION = {
    "BULL": {
        "consensus_threshold": 0.65,
        "consensus_days": 3,
        "leader_delta": 0.22,
        "leader_days": 2,
    },
    "BEAR": {
        "consensus_threshold": 0.55,
        "consensus_days": 1,
        "leader_delta": 0.18,
        "leader_days": 1,
    },
    "RANGE": {
        "consensus_threshold": 0.60,
        "consensus_days": 2,
        "leader_delta": 0.20,
        "leader_days": 1,
    },
    "TRANSITION": {
        "consensus_threshold": 0.55,
        "consensus_days": 1,
        "leader_delta": 0.18,
        "leader_days": 1,
    },
}

# ============================================================
# CONFIDENCE
# ============================================================

QUALITY_WEIGHTS = {
    "completeness": 0.30,
    "consistency": 0.25,
    "persistence": 0.25,
    "macro_agreement": 0.20,
}

PERSISTENCE_NORMALIZATION_DAYS = 7.0
PERSISTENCE_MIN = 0.3

SENTIMENT_EXTREME_THRESHOLD = 0.8
SENTIMENT_EXTREME_PENALTY = 0.85

DECOUPLED_CORR_THRESHOLD = 0.3
DECOUPLED_BONUS = 1.05
CONFIDENCE_CAP = 0.95

# Churn penalty (v3.3)
CHURN_WINDOW = 30
CHURN_FREE_SWITCHES = 2
CHURN_PENALTY_PER_SWITCH = 0.10
CHURN_FLOOR = 0.50

# ============================================================
# FLIP SIGNAL
# ============================================================

FLIP_MAJOR_THRESHOLD = 0.50
FLIP_MODERATE_THRESHOLD = 0.30
FLIP_DECAY = 0.7
FLIP_LOOKBACK = 3  # days

# ============================================================
# EDGE CASES
# ============================================================

DATA_QUALITY_MIN = 0.85
DATA_QUALITY_PENALTY = 0.5

MISSING_DAYS_FREEZE = 2
MISSING_DAYS_EMERGENCY = 5
EMERGENCY_CONFIDENCE = 0.30
EMERGENCY_EXPOSURE = 0.30

EXTREME_VOL_THRESHOLD = 2.5
EXTREME_VOL_TRANSITION_FLOOR = 0.40
EXTREME_VOL_CONFIDENCE_PENALTY = 0.7

FLASH_CRASH_THRESHOLD = -0.15  # -15% in 1h
FLASH_RECOVERY_CHECK_HOURS = [4, 8, 12, 24]
FLASH_RECOVERY_THRESHOLD = 0.50
FLASH_CRASH_REAL_THRESHOLD = 0.20

# ============================================================
# EXPOSURE CAP
# ============================================================

EXPOSURE_MAP = {
    "BULL": {
        "high_conf": (0.70, 0.80),   # conf > 0.70 → cap 0.80
        "med_conf": (0.50, 0.60),    # conf > 0.50 → cap 0.60
        "low_conf": (0.0, 0.40),     # else → cap 0.40
    },
    "BEAR": {
        "high_conf": (0.70, 0.30),
        "med_conf": (0.50, 0.40),
        "low_conf": (0.0, 0.50),
    },
    "RANGE": {
        "high_conf": (0.70, 0.60),
        "med_conf": (0.50, 0.50),
        "low_conf": (0.0, 0.35),
    },
    "TRANSITION": {
        "high_conf": (0.70, 0.40),
        "med_conf": (0.50, 0.30),
        "low_conf": (0.0, 0.20),
    },
}

# ============================================================
# BUCKET HEALTH
# ============================================================

BUCKET_HEALTH_LOOKBACK = 60
LOW_DIMENSIONALITY_THRESHOLD = 3
HIGH_CORR_THRESHOLD = 0.75

EXPECTED_CORRELATIONS = {
    ("Momentum", "Stability"): -0.3,
    ("Momentum", "Rotation"): -0.1,
    ("Momentum", "Sentiment"): 0.3,
    ("Momentum", "Macro"): 0.2,
    ("Stability", "Rotation"): 0.0,
    ("Stability", "Sentiment"): 0.1,
    ("Stability", "Macro"): 0.1,
    ("Rotation", "Sentiment"): 0.0,
    ("Rotation", "Macro"): 0.1,
    ("Sentiment", "Macro"): 0.2,
}

CORR_ANOMALY_THRESHOLD = 0.5

# ============================================================
# TRANSITION MATRIX
# ============================================================

TRANSITION_WINDOW = 180
TRANSITION_STICKY_THRESHOLD = 0.60
DIRECT_BULL_BEAR_THRESHOLD = 0.10
RARE_TRANSITION_MULTIPLIER = 10

# ============================================================
# RISK LEVEL (policy layer over regime detection)
# ============================================================

# Weights: Regime → Risk contribution
# Design: TRANSITION is worst (-1.0), BEAR severe (-0.9),
#          BULL strong positive (+0.8), RANGE mild positive (+0.4)
# Sum at uniform P=[0.25]*4 = -0.175 (Neutral) — correct
RISK_LEVEL_WEIGHTS = {
    "BULL": +0.80,
    "RANGE": +0.40,
    "BEAR": -0.90,
    "TRANSITION": -1.00,
}

# Risk state thresholds
RISK_ON_THRESHOLD = +0.30
RISK_OFF_THRESHOLD = -0.30

# Confidence gate: if confidence < this, risk_level capped at 0 (Neutral)
# Prevents false Risk-On when model is uncertain
RISK_CONFIDENCE_GATE = 0.15

# Risk Level → Exposure override (takes priority over regime-based exposure)
RISK_EXPOSURE_MAP = [
    (-1.0, -0.60, 0.10),  # deep Risk-Off → 10% max
    (-0.60, -0.30, 0.20),  # Risk-Off → 20% max
    (-0.30, +0.30, 0.50),  # Neutral → 50% max
    (+0.30, +0.60, 0.70),  # Risk-On → 70% max
    (+0.60, +1.01, 0.80),  # Strong Risk-On → 80% max
]

# Risk Level labels
RISK_STATE_LABELS = {
    "RISK_ON": "🟢 RISK-ON",
    "RISK_NEUTRAL": "🟡 RISK-NEUTRAL",
    "RISK_OFF": "🔴 RISK-OFF",
}

# ============================================================
# REGIMES LIST
# ============================================================

REGIMES = ["BULL", "BEAR", "RANGE", "TRANSITION"]
