"""
Signal Buckets — Momentum, Stability, Rotation, Sentiment, Macro.
Each bucket outputs a value in [-1, +1].
"""

import numpy as np
import pandas as pd
import settings as cfg
from normalization import AdaptiveNormalizer


def clip(x: float) -> float:
    return float(np.clip(x, -1.0, 1.0))


# ============================================================
# TECHNICAL HELPERS
# ============================================================

def compute_ema(prices: np.ndarray, period: int) -> np.ndarray:
    """Exponential moving average."""
    alpha = 2.0 / (period + 1)
    ema = np.full_like(prices, np.nan, dtype=float)
    if len(prices) < period:
        return ema
    ema[period - 1] = np.mean(prices[:period])
    for i in range(period, len(prices)):
        ema[i] = alpha * prices[i] + (1 - alpha) * ema[i - 1]
    return ema


def compute_roc(prices: np.ndarray, period: int) -> np.ndarray:
    """Rate of change."""
    roc = np.full_like(prices, np.nan, dtype=float)
    for i in range(period, len(prices)):
        if prices[i - period] != 0:
            roc[i] = prices[i] / prices[i - period] - 1.0
    return roc


def compute_adx(high: np.ndarray, low: np.ndarray, close: np.ndarray,
                period: int = 14) -> tuple:
    """
    Average Directional Index.
    Returns (ADX, +DI, -DI) arrays.
    """
    n = len(close)
    if n < period + 1:
        return np.zeros(n), np.zeros(n), np.zeros(n)

    # True Range
    tr = np.zeros(n)
    plus_dm = np.zeros(n)
    minus_dm = np.zeros(n)

    for i in range(1, n):
        h_l = high[i] - low[i]
        h_pc = abs(high[i] - close[i - 1])
        l_pc = abs(low[i] - close[i - 1])
        tr[i] = max(h_l, h_pc, l_pc)

        up = high[i] - high[i - 1]
        down = low[i - 1] - low[i]

        plus_dm[i] = up if (up > down and up > 0) else 0.0
        minus_dm[i] = down if (down > up and down > 0) else 0.0

    # Smoothed (Wilder's)
    atr = np.zeros(n)
    s_plus = np.zeros(n)
    s_minus = np.zeros(n)

    atr[period] = np.sum(tr[1:period + 1])
    s_plus[period] = np.sum(plus_dm[1:period + 1])
    s_minus[period] = np.sum(minus_dm[1:period + 1])

    for i in range(period + 1, n):
        atr[i] = atr[i - 1] - atr[i - 1] / period + tr[i]
        s_plus[i] = s_plus[i - 1] - s_plus[i - 1] / period + plus_dm[i]
        s_minus[i] = s_minus[i - 1] - s_minus[i - 1] / period + minus_dm[i]

    with np.errstate(divide='ignore', invalid='ignore'):
        plus_di = np.where(atr > 0, 100 * s_plus / atr, 0)
        minus_di = np.where(atr > 0, 100 * s_minus / atr, 0)

        di_sum = plus_di + minus_di
        dx = np.where(
            di_sum > 0,
            100 * np.abs(plus_di - minus_di) / di_sum,
            0
        )

    adx = np.zeros(n)
    start = 2 * period
    if start < n:
        adx[start] = np.mean(dx[period:start + 1])
        for i in range(start + 1, n):
            adx[i] = (adx[i - 1] * (period - 1) + dx[i]) / period

    return adx, plus_di, minus_di


def compute_realized_vol(close: np.ndarray, window: int = 30) -> np.ndarray:
    """Realized volatility (annualized std of log returns)."""
    log_ret = np.diff(np.log(close + 1e-12))
    vol = np.full(len(close), np.nan)
    for i in range(window, len(log_ret) + 1):
        vol[i] = np.std(log_ret[i - window:i]) * np.sqrt(365)
    return vol


def rolling_correlation(a: np.ndarray, b: np.ndarray, window: int) -> float:
    """Rolling correlation between two series, returns last value."""
    if len(a) < window or len(b) < window:
        return 0.0
    a_w = a[-window:]
    b_w = b[-window:]
    mask = ~(np.isnan(a_w) | np.isnan(b_w))
    if mask.sum() < 10:
        return 0.0
    return float(np.corrcoef(a_w[mask], b_w[mask])[0, 1])


# ============================================================
# MOMENTUM BUCKET
# ============================================================

def compute_momentum(close: np.ndarray, high: np.ndarray, low: np.ndarray,
                     tmc_history: np.ndarray, norm: AdaptiveNormalizer) -> dict:
    """
    Multi-indicator Momentum bucket.
    Returns dict with value and components.
    """
    n = len(close)

    # Component 1: ROC blend
    roc_30 = compute_roc(close, 30)
    roc_90 = compute_roc(close, 90)

    roc_blend = np.where(
        ~np.isnan(roc_30) & ~np.isnan(roc_90),
        cfg.ROC_BLEND_30D_WEIGHT * roc_30 + cfg.ROC_BLEND_90D_WEIGHT * roc_90,
        np.where(~np.isnan(roc_30), roc_30, 0.0)
    )
    roc_blend_z = norm.normalize(roc_blend[~np.isnan(roc_blend)])

    # Component 2: ADX directed
    adx, plus_di, minus_di = compute_adx(high, low, close, cfg.ADX_PERIOD)
    adx_clean = adx[~np.isnan(adx)]
    adx_z = norm.normalize(adx_clean) if len(adx_clean) > 5 else 0.0

    di_direction = 1.0 if plus_di[-1] > minus_di[-1] else -1.0
    trend_strength_z = adx_z * di_direction

    # Component 3: Alignment
    ema_20 = compute_ema(close, cfg.EMA_FAST)
    ema_50 = compute_ema(close, cfg.EMA_MEDIUM)
    ema_200 = compute_ema(close, cfg.EMA_SLOW)

    if not np.isnan(ema_20[-1]) and not np.isnan(ema_50[-1]):
        align_20_50 = 0.5 * np.sign(ema_20[-1] - ema_50[-1])
    else:
        align_20_50 = 0.0

    if not np.isnan(ema_50[-1]) and not np.isnan(ema_200[-1]):
        align_50_200 = 0.5 * np.sign(ema_50[-1] - ema_200[-1])
    else:
        align_50_200 = 0.0

    alignment = align_20_50 + align_50_200

    # Component 4: ΔTMC
    if len(tmc_history) >= 30:
        dtmc_30 = tmc_history[-1] / tmc_history[-30] - 1.0 if tmc_history[-30] > 0 else 0.0
        dtmc_arr = np.array([
            tmc_history[i] / tmc_history[max(0, i - 30)] - 1.0
            for i in range(30, len(tmc_history))
            if tmc_history[max(0, i - 30)] > 0
        ])
        dtmc_z = norm.normalize(dtmc_arr) if len(dtmc_arr) > 5 else 0.0
    else:
        dtmc_z = 0.0

    # Composite
    w = cfg.MOMENTUM_WEIGHTS
    momentum_raw = (
        w["ROC_blend"] * roc_blend_z +
        w["Trend_strength"] * trend_strength_z +
        w["Alignment"] * alignment +
        w["DTMC"] * dtmc_z
    )
    momentum = clip(momentum_raw)

    # Anti-decay: absolute component
    last_roc_90 = roc_90[-1] if not np.isnan(roc_90[-1]) else 0.0
    abs_mom = clip(last_roc_90 / cfg.ABSOLUTE_ROC_THRESHOLD)
    momentum_final = clip(
        cfg.MOMENTUM_RELATIVE_WEIGHT * momentum +
        cfg.MOMENTUM_ABSOLUTE_WEIGHT * abs_mom
    )

    return {
        "value": momentum_final,
        "components": {
            "roc_blend_z": roc_blend_z,
            "trend_strength_z": trend_strength_z,
            "alignment": alignment,
            "dtmc_z": dtmc_z,
            "absolute_momentum": abs_mom,
        }
    }


# ============================================================
# STABILITY BUCKET
# ============================================================

def compute_stability(close: np.ndarray, volume: np.ndarray,
                      norm: AdaptiveNormalizer) -> dict:
    """Stability bucket: inverse vol + liquidity + depth proxy."""
    # Realized vol
    rvol = compute_realized_vol(close, cfg.REALIZED_VOL_WINDOW)
    rvol_clean = rvol[~np.isnan(rvol)]
    vol_z = norm.normalize(rvol_clean) if len(rvol_clean) > 5 else 0.0

    # Liquidity: volume / price as proxy for turnover
    if len(close) > 0 and close[-1] > 0:
        liq_series = volume / close
        liq_clean = liq_series[~np.isnan(liq_series)]
        liq_z = norm.normalize(liq_clean) if len(liq_clean) > 5 else 0.0
    else:
        liq_z = 0.0

    # Depth proxy: volume / vol
    if len(rvol_clean) > 0 and rvol_clean[-1] > 0:
        depth_series = volume[-len(rvol_clean):] / (rvol_clean + 1e-12)
        depth_clean = depth_series[~np.isnan(depth_series)]
        depth_z = norm.normalize(depth_clean) if len(depth_clean) > 5 else 0.0
        use_depth = True
    else:
        depth_z = 0.0
        use_depth = False

    if use_depth:
        w = cfg.STABILITY_WEIGHTS
        raw = w["Vol"] * (-vol_z) + w["Liquidity"] * liq_z + w["Depth"] * depth_z
    else:
        w = cfg.STABILITY_WEIGHTS_FALLBACK
        raw = w["Vol"] * (-vol_z) + w["Liquidity"] * liq_z

    return {
        "value": clip(raw),
        "vol_z": vol_z,
        "components": {
            "neg_vol_z": -vol_z,
            "liquidity_z": liq_z,
            "depth_z": depth_z,
        }
    }


# ============================================================
# ROTATION BUCKET
# ============================================================

def compute_rotation(btc_dominance: np.ndarray, momentum_value: float,
                     norm: AdaptiveNormalizer) -> dict:
    """
    Capital rotation (BTC dominance velocity + acceleration).
    Context-adjusted by Momentum.
    """
    if len(btc_dominance) < 30:
        return {"value": 0.0, "base": 0.0, "context_adjusted": True, "components": {}}

    # Velocity: 7d change
    vel_7d = np.array([
        btc_dominance[i] - btc_dominance[i - 7]
        for i in range(7, len(btc_dominance))
    ])

    # Acceleration: 7d change - 30d change
    vel_30d = np.array([
        btc_dominance[i] - btc_dominance[max(0, i - 30)]
        for i in range(30, len(btc_dominance))
    ])

    vel_z = norm.normalize(vel_7d) if len(vel_7d) > 5 else 0.0

    min_len = min(len(vel_7d), len(vel_30d))
    if min_len > 5:
        accel = vel_7d[-min_len:] - vel_30d[-min_len:]
        accel_z = norm.normalize(accel)
    else:
        accel_z = 0.0

    rotation_base = clip(
        cfg.ROTATION_VELOCITY_WEIGHT * vel_z +
        cfg.ROTATION_ACCEL_WEIGHT * accel_z
    )

    # Context adjustment
    thresh = cfg.ROTATION_CONTEXT_MOMENTUM_THRESHOLD
    if momentum_value > thresh and rotation_base > 0:
        dampening = 1.0 - cfg.ROTATION_BULL_DAMPENING * min(momentum_value, 1.0)
        rotation = rotation_base * dampening
    elif momentum_value < -thresh and rotation_base < 0:
        dampening = 1.0 - cfg.ROTATION_BEAR_DAMPENING * min(abs(momentum_value), 1.0)
        rotation = rotation_base * dampening
    else:
        rotation = rotation_base

    return {
        "value": clip(rotation),
        "base": rotation_base,
        "context_adjusted": abs(rotation - rotation_base) > 0.01,
        "components": {"velocity_z": vel_z, "accel_z": accel_z},
    }


# ============================================================
# SENTIMENT BUCKET
# ============================================================

def compute_sentiment(fear_greed_value: int,
                      funding_rates: np.ndarray,
                      oi_history: np.ndarray,
                      norm: AdaptiveNormalizer) -> dict:
    """Sentiment: FG + Funding Rate + OI momentum."""

    # Fear & Greed zone score
    fg_score = 0.0
    for (lo, hi), score in cfg.FG_ZONES.items():
        if lo <= fear_greed_value <= hi:
            fg_score = score
            break

    # Funding rate z-score
    if len(funding_rates) >= 7:
        avg_7d = np.mean(funding_rates[-7:])
        fund_arr = np.array([np.mean(funding_rates[max(0, i - 7):i])
                            for i in range(7, len(funding_rates))])
        fund_z = norm.normalize(fund_arr) if len(fund_arr) > 5 else 0.0
        funding_score = clip(fund_z)
    else:
        funding_score = 0.0

    # OI momentum
    if len(oi_history) >= 7:
        oi_changes = np.diff(oi_history) / (oi_history[:-1] + 1e-12)
        oi_z = norm.normalize(oi_changes) if len(oi_changes) > 5 else 0.0
        oi_score = clip(oi_z)
    else:
        oi_score = 0.0

    w = cfg.SENTIMENT_WEIGHTS
    raw = w["FG"] * fg_score + w["Funding"] * funding_score + w["OI"] * oi_score

    return {
        "value": clip(raw),
        "components": {
            "fg_score": fg_score,
            "funding_score": funding_score,
            "oi_score": oi_score,
            "fg_raw": fear_greed_value,
        }
    }


# ============================================================
# MACRO BUCKET
# ============================================================

def compute_macro(dxy: np.ndarray, us10y: np.ndarray, us2y: np.ndarray,
                  m2: np.ndarray, norm: AdaptiveNormalizer,
                  macro_norm: AdaptiveNormalizer) -> dict:
    """
    Macro Liquidity bucket: DXY + real rates + yield curve + M2.
    Returns neutral (0.0) if insufficient data.
    """
    components = {}
    available = 0
    total = 4

    # Dollar signal
    if len(dxy) > 10:
        dxy_z = norm.normalize(dxy)
        dollar_signal = -dxy_z  # Strong dollar = bearish
        components["dollar_signal"] = dollar_signal
        available += 1
    else:
        dollar_signal = 0.0
        components["dollar_signal"] = None

    # Rate signal (using 10Y as proxy for real rates)
    if len(us10y) > 10:
        rate_z = norm.normalize(us10y)
        rate_signal = -rate_z  # High rates = tight = bearish
        components["rate_signal"] = rate_signal
        available += 1
    else:
        rate_signal = 0.0
        components["rate_signal"] = None

    # Yield curve
    if len(us10y) > 10 and len(us2y) > 10:
        min_len = min(len(us10y), len(us2y))
        yc = us10y[-min_len:] - us2y[-min_len:]
        yc_z = norm.normalize(yc)
        components["yc_z"] = yc_z
        available += 1
    else:
        yc_z = 0.0
        components["yc_z"] = None

    # M2 momentum (slower normalization)
    if len(m2) > 30:
        m2_mom = np.array([
            m2[i] / m2[max(0, i - 90)] - 1.0
            for i in range(90, len(m2))
            if m2[max(0, i - 90)] > 0
        ])
        m2_z = macro_norm.normalize(m2_mom) if len(m2_mom) > 5 else 0.0
        components["m2_z"] = m2_z
        available += 1
    else:
        m2_z = 0.0
        components["m2_z"] = None

    if available < 2:
        return {"value": 0.0, "available": available, "total": total,
                "components": components, "disabled": True}

    w = cfg.MACRO_WEIGHTS
    raw = (
        w["Dollar"] * dollar_signal +
        w["Rate"] * rate_signal +
        w["YieldCurve"] * yc_z +
        w["M2"] * m2_z
    )

    return {
        "value": clip(raw),
        "available": available,
        "total": total,
        "components": components,
        "disabled": False,
    }


# ============================================================
# CROSS-ASSET CORRELATION
# ============================================================

def compute_cross_asset(btc_returns: np.ndarray, spx_returns: np.ndarray,
                        gold_returns: np.ndarray) -> dict:
    """BTC/SPX and BTC/Gold correlations → macro_weight_boost."""
    window = cfg.CROSS_ASSET_CORR_WINDOW

    corr_spx = rolling_correlation(btc_returns, spx_returns, window)
    corr_gold = rolling_correlation(btc_returns, gold_returns, window)

    if abs(corr_spx) > cfg.MACRO_BOOST_THRESHOLD:
        macro_boost = cfg.MACRO_BOOST_MULTIPLIER
    else:
        macro_boost = 1.0

    return {
        "corr_BTC_SPX": round(corr_spx, 3),
        "corr_BTC_Gold": round(corr_gold, 3),
        "macro_weight_boost": macro_boost,
    }
