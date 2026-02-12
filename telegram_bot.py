"""
Telegram Bot — sends regime engine output as formatted messages.
Risk Level displayed first as policy-level signal.
LP Intelligence v2.0.1 integrated.
"""

import os
import logging
import requests

import settings as cfg

logger = logging.getLogger(__name__)


# Regime emoji map
REGIME_EMOJI = {
    "BULL": "🟢",
    "BEAR": "🔴",
    "RANGE": "🟡",
    "TRANSITION": "⚪",
}

REGIME_LABEL = {
    "BULL": "BULL 📈",
    "BEAR": "BEAR 📉",
    "RANGE": "RANGE ↔️",
    "TRANSITION": "TRANSITION ⏳",
}

RISK_STATE_EMOJI = {
    "RISK_ON": "🟢",
    "RISK_NEUTRAL": "🟡",
    "RISK_OFF": "🔴",
}

RISK_STATE_LABEL = {
    "RISK_ON": "RISK-ON",
    "RISK_NEUTRAL": "RISK-NEUTRAL",
    "RISK_OFF": "RISK-OFF",
}


def risk_bar(level: float, width: int = 16) -> str:
    """
    Visual risk bar: ████████|░░░░░░░░
    Center = 0. Left = Risk-Off, Right = Risk-On.
    """
    half = width // 2
    if level >= 0:
        left = "░" * half
        filled = int(level * half)
        right = "█" * filled + "░" * (half - filled)
    else:
        filled = int(abs(level) * half)
        left = "░" * (half - filled) + "█" * filled
        right = "░" * half
    return f"  OFF {left}|{right} ON"


def lp_risk_bar(level: float, width: int = 8) -> str:
    """
    LP risk bar: BAD ░░░░████ GOOD
    -1 = bad, +1 = good for LP
    """
    pct = (level + 1) / 2  # map [-1,1] to [0,1]
    filled = int(pct * width)
    empty = width - filled
    if level < 0:
        bar = "░" * empty + "█" * filled
    else:
        bar = "█" * filled + "░" * empty
    return f"  BAD {bar} GOOD"


def format_probability_bar(regime: str, prob: float, width: int = 12) -> str:
    filled = int(prob * width)
    empty = width - filled
    return f"    {regime:<6} {'█' * filled}{'░' * empty} {prob:.2f}"


def format_lp_block(lp_policy) -> str:
    """
    Format LP Policy as Telegram block.
    Integrated inside main message.
    """
    if lp_policy is None:
        return ""
    
    lines = []
    lines.append("─" * 34)
    lines.append("  💧 LP INTELLIGENCE v2.0.1")
    lines.append("─" * 34)
    
    # LP Regime with emoji
    regime_emoji = cfg.LP_REGIME_EMOJI.get(lp_policy.lp_regime.value, "📊")
    lines.append(f"  {regime_emoji} LP Regime: {lp_policy.lp_regime.value}")
    
    # Risk LP
    lines.append(f"  Risk LP: {lp_policy.risk_lp:+.2f}")
    lines.append(lp_risk_bar(lp_policy.risk_lp))
    
    # Quadrant
    quadrant_desc = cfg.LP_QUADRANT_DESC.get(
        lp_policy.risk_quadrant.value, 
        lp_policy.risk_quadrant.value
    )
    lines.append(f"  Quadrant: {quadrant_desc}")
    
    # Fee/Variance ratio
    lines.append(f"  Fee/Var: {lp_policy.fee_variance_ratio:.1f}x")
    lines.append("")
    
    # Policy with CLEAR separation
    lines.append("  LP Policy:")
    lines.append(f"    LP book exposure: {int(lp_policy.max_exposure * 100)}%")
    lines.append(f"    Risk-adjusted: {int(lp_policy.effective_exposure * 100)}%")
    lines.append(f"    Range: {lp_policy.range_width}")
    lines.append(f"    Rebalance: {lp_policy.rebalance}")
    
    # Hedge: conditional mandatory in Q2 with high dir risk
    if lp_policy.hedge_recommended:
        hedge_text = "conditional mandatory"
    else:
        hedge_text = "optional"
    lines.append(f"    Hedge: {hedge_text}")
    lines.append("")
    
    # Signals (top 4)
    lines.append("  Signals:")
    for sig in lp_policy.signals[:4]:
        lines.append(f"    • {sig}")
    
    # Q2 note (key insight)
    if lp_policy.risk_quadrant.value == "Q2":
        lines.append("")
        lines.append("  💡 Note: Directional risk is high,")
        lines.append("     but LP payoff remains positive.")
        lines.append(f"     Effective exposure capped at {int(lp_policy.effective_exposure * 100)}%")
    
    return "\n".join(lines)


# ── Asset Allocation Block ────────────────────────────────

AA_ACTION_EMOJI = {
    "STRONG_BUY": "🟢🟢",
    "BUY": "🟢",
    "HOLD": "⚪️",
    "SELL": "🔴",
    "STRONG_SELL": "🔴🔴",
}


def format_allocation_block(allocation: dict) -> str:
    """
    Format Asset Allocation as Telegram block.
    """
    if allocation is None:
        return ""
    
    btc = allocation.get("btc", {})
    eth = allocation.get("eth", {})
    meta = allocation.get("meta", {})
    
    lines = []
    lines.append("─" * 34)
    lines.append("  📊 ASSET ALLOCATION v1.3.1")
    lines.append("─" * 34)
    
    # BTC
    btc_action = btc.get("action", "HOLD")
    btc_size = btc.get("size_pct", 0)
    btc_emoji = AA_ACTION_EMOJI.get(btc_action, "⚪️")
    btc_blocked = btc.get("blocked_by")
    
    size_str = f"{btc_size:+.0%}" if btc_size != 0 else "0%"
    lines.append(f"  BTC: {btc_emoji} {btc_action} ({size_str})")
    if btc_blocked:
        lines.append(f"       Blocked: {btc_blocked}")
    
    # ETH
    eth_action = eth.get("action", "HOLD")
    eth_size = eth.get("size_pct", 0)
    eth_emoji = AA_ACTION_EMOJI.get(eth_action, "⚪️")
    eth_blocked = eth.get("blocked_by")
    
    size_str = f"{eth_size:+.0%}" if eth_size != 0 else "0%"
    lines.append(f"  ETH: {eth_emoji} {eth_action} ({size_str})")
    if eth_blocked:
        lines.append(f"       Blocked: {eth_blocked}")
    
    lines.append("")
    
    # Stance
    stance = btc.get("stance", "RISK_NEUTRAL")
    conf = btc.get("confidence", 0)
    lines.append(f"  Stance: {stance}")
    lines.append(f"  Confidence: {conf:.2f}")
    
    # Tail risk warning
    if meta.get("tail_risk_active"):
        polarity = meta.get("tail_polarity", "downside")
        lines.append("")
        if polarity == "downside":
            lines.append("  ⚠️ DOWNSIDE TAIL RISK ACTIVE")
        else:
            lines.append("  ⚠️ UPSIDE TAIL RISK ACTIVE")
    
    # Top reasoning (first 2)
    btc_reasons = btc.get("reasoning", [])
    if btc_reasons:
        lines.append("")
        lines.append("  Reasoning:")
        for r in btc_reasons[:2]:
            lines.append(f"    • {r}")
    
    return "\n".join(lines)


def format_output(output: dict, lp_policy=None, allocation=None) -> str:
    """Format engine output as Telegram message."""
    risk = output.get("risk", {})
    regime = output.get("regime", "?")
    probs = output.get("probabilities", {})
    conf = output.get("confidence", {})
    buckets = output.get("buckets", {})
    hints = output.get("operational_hints", {})
    meta = output.get("metadata", {})
    flags = output.get("risk_flags", [])
    exposure = output.get("exposure_cap", 0)

    btc_price = meta.get("btc_price")
    btc_str = f"${btc_price:,.0f}" if btc_price else "N/A"

    lines = []

    # ── Header ────────────────────────────────────────
    lines.append("═" * 34)
    lines.append(f"  REGIME ENGINE v3.3")
    lines.append(f"  BTC: {btc_str}")
    lines.append("═" * 34)

    # ── RISK LEVEL — top priority ─────────────────────
    risk_level = risk.get("risk_level", 0)
    risk_state = risk.get("risk_state", "RISK_NEUTRAL")
    risk_strength = risk.get("strength", "?")
    risk_emoji = RISK_STATE_EMOJI.get(risk_state, "❓")
    risk_label = RISK_STATE_LABEL.get(risk_state, risk_state)
    risk_exp = risk.get("risk_exposure_cap", 0)

    lines.append("")
    lines.append(f"  {risk_emoji} {risk_label}  ({risk_strength})")
    lines.append(f"  Risk Level: {risk_level:+.2f}")
    lines.append(risk_bar(risk_level))
    lines.append("")

    # Policy block (directional)
    lines.append("  Policy:")
    lines.append(f"    Max exposure: {risk_exp:.0%}")

    if risk_level < -0.50:
        lines.append("    Leverage: PROHIBITED")
    elif risk_level < -0.30:
        lines.append("    Leverage: PROHIBITED")
    elif risk_level < 0.30:
        lines.append("    Leverage: cautious (≤1.5x)")
    else:
        lines.append("    Leverage: available (≤2x)")

    if risk.get("confidence_gated"):
        lines.append("    ⚠ Confidence gate active")

    # Risk reasons
    reasons = risk.get("reasons", [])
    if reasons:
        lines.append(f"    Reason: {', '.join(reasons)}")

    # ── LP INTELLIGENCE BLOCK ─────────────────────────
    if lp_policy is not None:
        lines.append("")
        lines.append(format_lp_block(lp_policy))

    # ── ASSET ALLOCATION BLOCK ────────────────────────
    if allocation is not None:
        lines.append("")
        lines.append(format_allocation_block(allocation))

    # ── Regime detail ─────────────────────────────────
    lines.append("")
    lines.append("─" * 34)

    emoji = REGIME_EMOJI.get(regime, "❓")
    label = REGIME_LABEL.get(regime, regime)

    lines.append(f"  {emoji} Regime: {label}")
    lines.append(f"  📊 Confidence: {conf.get('quality_adjusted', 0):.2f}")
    lines.append(f"  📅 Days in regime: {meta.get('days_in_regime', '?')}")
    lines.append("")

    # Probabilities
    lines.append("  Probabilities:")
    for r in ["BULL", "BEAR", "RANGE", "TRANSITION"]:
        p = probs.get(r, 0)
        lines.append(format_probability_bar(r, p))
    lines.append("")

    # Buckets
    lines.append("  Buckets:")
    for name in ["Momentum", "Stability", "Rotation", "Sentiment", "Macro"]:
        v = buckets.get(name, 0)
        sign = "+" if v >= 0 else ""
        lines.append(f"    {name:<10} {sign}{v:.2f}")
    lines.append("")

    # Confidence breakdown
    churn = conf.get("churn_penalty", 1.0)
    switches = conf.get("switches_30d", 0)
    lines.append(f"  Confidence:")
    lines.append(f"    Base:  {conf.get('base', 0):.2f}")
    lines.append(f"    Adj:   {conf.get('quality_adjusted', 0):.2f}")
    lines.append(f"    Churn: {churn:.2f} ({switches} sw/30d)")
    lines.append("")

    # Strategy hints
    strategy = hints.get("strategy_class", "?")
    urgency = hints.get("rebalance_urgency", "?")
    lines.append(f"  💡 Strategy: {strategy}")
    lines.append(f"  ⚡ Rebalance: {urgency}")

    if "range_type" in hints:
        lines.append(f"  📐 Range: {hints['range_type']}")
    if "breakout_proximity" in hints:
        lines.append(f"  🎯 Breakout: {hints['breakout_proximity']} "
                     f"({hints.get('breakout_direction', '?')})")

    lines.append(f"  🛡 Exposure cap: {exposure:.0%}")

    # Flags
    if flags:
        lines.append("")
        lines.append("  ⚠️ Flags:")
        for f in flags[:5]:
            lines.append(f"    • {f}")

    # Diagnostics
    vol_z = meta.get("vol_z", 0)
    norm_info = output.get("normalization", {})
    lines.append("")
    lines.append(f"  Vol_z: {vol_z:.2f} | T: {meta.get('temperature', 1):.1f} "
                 f"| α: {meta.get('smoothing_alpha', 0.3):.1f}")
    if norm_info.get("break_active"):
        lines.append(f"  ⚠️ Struct break (window: "
                     f"{norm_info.get('price_window', '?')}d)")

    bh = output.get("bucket_health", {})
    eff_dim = bh.get("effective_dimensionality", "?")
    lines.append(f"  Bucket dim: {eff_dim}/5")

    lines.append("")
    lines.append("═" * 34)

    return "\n".join(lines)


def send_telegram(output: dict, lp_policy=None, allocation=None) -> bool:
    """Send formatted output to Telegram."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        logger.warning("Telegram credentials not set. Skipping.")
        return False

    text = format_output(output, lp_policy, allocation)

    # Telegram limit: 4096 chars
    if len(text) > 4096:
        text = text[:4090] + "\n..."

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": f"```\n{text}\n```",
        "parse_mode": "Markdown",
    }

    try:
        resp = requests.post(url, json=payload, timeout=15)
        if resp.status_code == 200:
            logger.info("✓ Telegram message sent")
            return True
        else:
            logger.error(f"Telegram API error: {resp.status_code} — {resp.text}")
            return False
    except Exception as e:
        logger.error(f"Telegram send failed: {e}")
        return False
