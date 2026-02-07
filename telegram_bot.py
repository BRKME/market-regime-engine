"""
Telegram Bot — sends regime engine output as formatted messages.
"""

import os
import logging
import requests

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


def make_bar(value: float, width: int = 12) -> str:
    """Visual bar: ████░░░░"""
    filled = int(abs(value) * width)
    empty = width - filled
    sign = "+" if value >= 0 else "-"
    return f"{sign}{abs(value):.2f} {'█' * filled}{'░' * empty}"


def format_probability_bar(regime: str, prob: float, width: int = 12) -> str:
    filled = int(prob * width)
    empty = width - filled
    return f"  {regime:<6} {'█' * filled}{'░' * empty} {prob:.2f}"


def format_output(output: dict) -> str:
    """Format engine output as Telegram message (MarkdownV2-safe plain text)."""
    regime = output["regime"]
    probs = output["probabilities"]
    conf = output.get("confidence", {})
    buckets = output.get("buckets", {})
    hints = output.get("operational_hints", {})
    meta = output.get("metadata", {})
    flags = output.get("risk_flags", [])
    exposure = output.get("exposure_cap", 0)

    emoji = REGIME_EMOJI.get(regime, "❓")
    label = REGIME_LABEL.get(regime, regime)

    btc_price = meta.get("btc_price")
    btc_str = f"${btc_price:,.0f}" if btc_price else "N/A"

    lines = []
    lines.append("═" * 34)
    lines.append(f"  REGIME ENGINE v3.3")
    lines.append(f"  BTC: {btc_str}")
    lines.append("═" * 34)
    lines.append("")

    # Regime
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
    lines.append(f"  Confidence detail:")
    lines.append(f"    Base:  {conf.get('base', 0):.2f}")
    lines.append(f"    Adj:   {conf.get('quality_adjusted', 0):.2f}")
    lines.append(f"    Churn: {churn:.2f} ({switches} sw/30d)")
    lines.append("")

    # Operational hints
    strategy = hints.get("strategy_class", "?")
    lp_mode = hints.get("suggested_lp_mode", "?")
    urgency = hints.get("rebalance_urgency", "?")
    lines.append(f"  💡 Strategy: {strategy}")
    lines.append(f"  📌 LP mode: {lp_mode}")
    lines.append(f"  ⚡ Rebalance: {urgency}")

    # Range sub-type if applicable
    if "range_type" in hints:
        lines.append(f"  📐 Range type: {hints['range_type']}")
    if "breakout_proximity" in hints:
        lines.append(f"  🎯 Breakout: {hints['breakout_proximity']} ({hints.get('breakout_direction', '?')})")

    lines.append("")
    lines.append(f"  🛡 Exposure cap: {exposure:.0%}")

    # Flags
    if flags:
        lines.append("")
        lines.append("  ⚠️ Flags:")
        for f in flags[:5]:  # limit to 5
            lines.append(f"    • {f}")

    # Vol and normalization
    vol_z = meta.get("vol_z", 0)
    norm_info = output.get("normalization", {})
    lines.append("")
    lines.append(f"  Vol z: {vol_z:.2f} | T: {meta.get('temperature', 1):.1f} | α: {meta.get('smoothing_alpha', 0.3):.1f}")
    if norm_info.get("break_active"):
        lines.append(f"  ⚠️ Structural break active (window: {norm_info.get('price_window', '?')}d)")

    # Bucket health
    bh = output.get("bucket_health", {})
    eff_dim = bh.get("effective_dimensionality", "?")
    lines.append(f"  Bucket health: {eff_dim}/5 dim")

    lines.append("")
    lines.append("═" * 34)

    return "\n".join(lines)


def send_telegram(output: dict) -> bool:
    """Send formatted output to Telegram."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        logger.warning("Telegram credentials not set. Skipping notification.")
        logger.info("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in environment.")
        return False

    text = format_output(output)

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
