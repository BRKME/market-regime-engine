"""
Normalization — z-score with structural break detection (v3.3).
"""

import numpy as np
from config import settings as cfg


def z_score(values: np.ndarray, window: int = None) -> float:
    """
    Z-score of the last value in array, using rolling window.
    Clips to [-3, +3].
    """
    if window is None:
        window = cfg.NORM_WINDOW_DEFAULT

    if len(values) < 5:
        return 0.0

    lookback = values[-window:] if len(values) >= window else values
    mean = np.nanmean(lookback)
    std = np.nanstd(lookback)

    z = (values[-1] - mean) / (std + 1e-8)
    return float(np.clip(z, -cfg.Z_CLIP, cfg.Z_CLIP))


def detect_structural_break(values: np.ndarray) -> tuple:
    """
    Detect structural break via variance ratio + mean shift.
    Returns (break_detected: bool, variance_ratio: float, t_stat: float)
    """
    short_w = cfg.BREAK_SHORT_WINDOW
    long_w = cfg.BREAK_LONG_WINDOW
    min_len = short_w + long_w

    if len(values) < min_len:
        return False, 0.0, 0.0

    recent = values[-short_w:]
    prior = values[-(short_w + long_w):-short_w]

    # Remove NaNs
    recent = recent[~np.isnan(recent)]
    prior = prior[~np.isnan(prior)]

    if len(recent) < 10 or len(prior) < 10:
        return False, 0.0, 0.0

    var_recent = np.var(recent)
    var_prior = np.var(prior)
    variance_ratio = max(var_recent, var_prior) / (min(var_recent, var_prior) + 1e-12)

    mean_diff = abs(np.mean(recent) - np.mean(prior))
    pooled_std = np.sqrt(var_recent / len(recent) + var_prior / len(prior))
    t_stat = mean_diff / (pooled_std + 1e-12)

    break_detected = (
        variance_ratio > cfg.BREAK_VARIANCE_RATIO_THRESHOLD
        or t_stat > cfg.BREAK_T_STAT_THRESHOLD
    )

    return break_detected, float(variance_ratio), float(t_stat)


class AdaptiveNormalizer:
    """
    Manages per-signal normalization with structural break tracking.
    """

    def __init__(self, base_window: int = None):
        self.base_window = base_window or cfg.NORM_WINDOW_DEFAULT
        self.days_since_break = self.base_window  # start as if no recent break
        self.break_active = False

    def normalize(self, values: np.ndarray) -> float:
        """
        Z-score with adaptive window. If break detected, shrink window.
        """
        if len(values) < 5:
            return 0.0

        break_detected, vr, ts = detect_structural_break(values)

        if break_detected:
            self.days_since_break = 0
            self.break_active = True
        else:
            self.days_since_break += 1

        # Effective window: min 30, expands back to base
        if self.break_active:
            effective = max(cfg.NORM_WINDOW_MIN, min(self.base_window, self.days_since_break))
            if self.days_since_break >= self.base_window:
                self.break_active = False
        else:
            effective = self.base_window

        return z_score(values, window=effective)

    @property
    def effective_window(self) -> int:
        if self.break_active:
            return max(cfg.NORM_WINDOW_MIN, min(self.base_window, self.days_since_break))
        return self.base_window

    @property
    def status(self) -> dict:
        return {
            "base_window": self.base_window,
            "effective_window": self.effective_window,
            "break_active": self.break_active,
            "days_since_break": self.days_since_break,
        }
