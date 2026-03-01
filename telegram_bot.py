"""
Telegram Bot — Action-First UI v1.1
With Cycle Position support.
One screen → one decision.
"""

import os
import logging
import requests

logger = logging.getLogger(__name__)


# ============================================================
# FORMAT OUTPUT
# ============================================================

def format_output(output: dict, lp_policy=None, allocation=None) -> str:
    """
    Action-first format with cycle position.
    Decision in 5 seconds.
    """
    meta = output.get("metadata", {})
    risk = output.get("risk", {})
    conf = output.get("confidence", {})
    buckets = output.get("buckets", {})
    regime = output.get("regime", "?")
    flags = output.get("risk_flags", [])
    norm = output.get("normalization", {})
    
    btc_price = meta.get("btc_price", 0)
    risk_level = risk.get("risk_level", 0)
    conf_adj = conf.get("quality_adjusted", 0)
    days = meta.get("days_in_regime", 0)
    struct_break = norm.get("break_active", False)
    
    # Determine action state
    tail_active = False
    tail_polarity = None
    if allocation:
        tail_active = allocation.get("meta", {}).get("tail_risk_active", False)
        tail_polarity = allocation.get("meta", {}).get("tail_polarity", "downside")
    
    # Risk state
    if risk_level < -0.5:
        risk_state = "RISK-OFF"
        risk_emoji = "🔴"
    elif risk_level < 0:
        risk_state = "CAUTIOUS"
        risk_emoji = "🟡"
    elif risk_level < 0.5:
        risk_state = "NEUTRAL"
        risk_emoji = "⚪"
    else:
        risk_state = "RISK-ON"
        risk_emoji = "🟢"
    
    lines = []
    
    # ══════════════════════════════════════════════════════
    # HEADER: ACTION REQUIRED or STATUS
    # ══════════════════════════════════════════════════════
    lines.append("━" * 36)
    
    if tail_active:
        lines.append(f"🚨 ACTION REQUIRED · {risk_state}")
    elif risk_level < -0.3:
        lines.append(f"⚠️ CAUTION · {risk_state}")
    else:
        lines.append(f"📊 STATUS · {risk_state}")
    
    lines.append("━" * 36)
    lines.append(f"BTC ${btc_price:,.0f}")
    lines.append("")
    
    # ══════════════════════════════════════════════════════
    # MARKET STATE (compact)
    # ══════════════════════════════════════════════════════
    lines.append(f"{risk_emoji} MARKET: {regime}")
    
    # Phase
    if days <= 1:
        phase = "early"
    elif days <= 7:
        phase = f"{days}d"
    else:
        phase = f"{days}d mature"
    
    conf_pct = int(conf_adj * 100)
    
    # Confidence interpretation
    if conf_adj < 0.25:
        conf_label = "LOW"
    elif conf_adj < 0.50:
        conf_label = "MEDIUM"
    else:
        conf_label = "HIGH"
    
    lines.append(f"   {phase} · confidence {conf_label} ({conf_pct}%)")
    
    # Tail risk indicator
    if tail_active:
        if tail_polarity == "downside":
            lines.append(f"   Tail risk: HIGH ↓")
        else:
            lines.append(f"   Tail risk: HIGH ↑")
    
    # One-line summary
    if regime == "BEAR":
        lines.append(f"→ Рынок опасен. Защита капитала.")
    elif regime == "BULL":
        lines.append(f"→ Рынок растёт. Можно рисковать.")
    elif regime == "TRANSITION":
        lines.append(f"→ Неопределённость. Ждём ясности.")
    else:
        lines.append(f"→ Боковик. Нет направления.")
    
    # ══════════════════════════════════════════════════════
    # DIRECTIONAL POLICY with CYCLE POSITION
    # ══════════════════════════════════════════════════════
    if allocation:
        btc = allocation.get("btc", {})
        eth = allocation.get("eth", {})
        cycle = allocation.get("cycle", {})
        
        btc_action = btc.get("action", "HOLD")
        eth_action = eth.get("action", "HOLD")
        btc_size = btc.get("size_pct", 0)
        eth_size = eth.get("size_pct", 0)
        
        lines.append("")
        lines.append("━" * 36)
        lines.append("📉 DIRECTIONAL")
        lines.append("━" * 36)
        
        # Cycle position bar (if available)
        if cycle:
            cycle_pos = cycle.get("cycle_position", 50)
            phase_name = cycle.get("phase", "")
            bottom_prox = cycle.get("bottom_proximity", 0)
            top_prox = cycle.get("top_proximity", 0)
            bt_signal = cycle.get("bottom_top_signal", "")
            
            # Visual cycle bar
            bar_pos = int(cycle_pos / 10)
            bar = "─" * bar_pos + "●" + "─" * (10 - bar_pos)
            lines.append(f"BOTTOM [{bar}] TOP")
            lines.append(f"       {cycle_pos:.0f}/100 · {phase_name}")
            
            # Bottom/Top signal highlight
            if bt_signal and bt_signal not in ["NO_SIGNAL", ""]:
                if "GLOBAL_BOTTOM" in bt_signal:
                    lines.append(f"🟢🟢 {bt_signal} — редкий сигнал!")
                elif "LOCAL_BOTTOM" in bt_signal:
                    lines.append(f"🟢 {bt_signal}")
                elif "GLOBAL_TOP" in bt_signal:
                    lines.append(f"🔴🔴 {bt_signal} — редкий сигнал!")
                elif "LOCAL_TOP" in bt_signal:
                    lines.append(f"🔴 {bt_signal}")
            
            # Proximity indicators
            if bottom_prox >= 0.5:
                lines.append(f"   ↓ Bottom proximity: {bottom_prox:.0%}")
            if top_prox >= 0.5:
                lines.append(f"   ↑ Top proximity: {top_prox:.0%}")
            
            lines.append("")
        
        # Actions with emoji
        action_emoji = {
            "STRONG_BUY": "🟢🟢",
            "BUY": "🟢",
            "HOLD": "⚪",
            "SELL": "🔴",
            "STRONG_SELL": "🔴🔴",
        }
        
        btc_emoji = action_emoji.get(btc_action, "⚪")
        eth_emoji = action_emoji.get(eth_action, "⚪")
        
        btc_str = f"{btc_size:+.0%}" if btc_size != 0 else ""
        eth_str = f"{eth_size:+.0%}" if eth_size != 0 else ""
        
        lines.append(f"BTC: {btc_emoji} {btc_action} {btc_str}")
        lines.append(f"ETH: {eth_emoji} {eth_action} {eth_str}")
        
        # Reasons (compact, grouped)
        primary_reasons = []
        secondary_reasons = []
        
        mom = buckets.get("Momentum", 0)
        
        # Primary reasons
        if mom < -0.5:
            primary_reasons.append("downtrend")
        elif mom > 0.5:
            primary_reasons.append("uptrend")
        
        if tail_active:
            primary_reasons.append("tail-risk")
        
        # Cycle-based reason
        if cycle:
            bt = cycle.get("bottom_top_signal", "")
            if "BOTTOM" in bt:
                primary_reasons.append("near bottom")
            elif "TOP" in bt:
                primary_reasons.append("near top")
        
        # Secondary reasons (in parentheses)
        if conf_adj < 0.30:
            secondary_reasons.append("low confidence")
        
        if btc.get("blocked_by"):
            secondary_reasons.append(f"blocked: {btc['blocked_by'].lower()}")
        
        if primary_reasons or secondary_reasons:
            reason_str = " + ".join(primary_reasons) if primary_reasons else ""
            if secondary_reasons:
                sec_str = ", ".join(secondary_reasons)
                if reason_str:
                    reason_str += f" ({sec_str})"
                else:
                    reason_str = sec_str
            lines.append(f"   → {reason_str}")
    
    # ══════════════════════════════════════════════════════
    # LP POLICY (separate)
    # ══════════════════════════════════════════════════════
    if lp_policy:
        risk_lp = lp_policy.risk_lp
        risk_dir = lp_policy.risk_directional
        quadrant = lp_policy.risk_quadrant.value
        fv = lp_policy.fee_variance_ratio
        eff = int(lp_policy.effective_exposure * 100)
        hedge = lp_policy.hedge_recommended
        
        lines.append("")
        lines.append("━" * 36)
        
        # LP header reflects constraint status
        if eff < int(lp_policy.max_exposure * 100) * 0.5:
            lines.append("💧 LP POLICY (CONSTRAINED · SECONDARY)")
        else:
            lines.append("💧 LP POLICY (SECONDARY)")
        
        lines.append("━" * 36)
        
        lines.append(f"Quadrant: {quadrant}")
        lines.append(f"Dir: {risk_dir:+.2f} · LP: {risk_lp:+.2f} · F/V: {fv:.1f}x")
        
        # LP Action
        lines.append("")
        lines.append(f"Exposure: {eff}%")
        
        range_ru = {
            "tight": "tight", "standard": "std", "moderate": "med",
            "wide": "wide", "very_wide": "v.wide"
        }.get(lp_policy.range_width, lp_policy.range_width)
        
        lines.append(f"Range: {range_ru}")
        
        if hedge:
            lines.append(f"Hedge: REQUIRED")
        
        # Note for Q2
        if quadrant == "Q2" and risk_lp > 0:
            lines.append("")
            lines.append("Note: LP edge exists, but")
            lines.append("capital at risk is capped.")
    
    # ══════════════════════════════════════════════════════
    # FLAGS (if critical) - ordered by severity
    # ══════════════════════════════════════════════════════
    critical_flags = []
    
    # Priority 1: Tail risk
    if tail_active:
        critical_flags.append("Tail risk active")
    
    # Priority 2: Structure break
    if struct_break:
        critical_flags.append("Market structure break")
    
    # Priority 3: Data issues
    if any("DATA" in f for f in flags):
        critical_flags.append("Partial data")
    
    if critical_flags:
        lines.append("")
        lines.append("━" * 36)
        lines.append("⚠️ FLAGS")
        lines.append("━" * 36)
        for f in critical_flags[:3]:
            lines.append(f"• {f}")
    
    # ══════════════════════════════════════════════════════
    # FOOTER
    # ══════════════════════════════════════════════════════
    lines.append("")
    lines.append("━" * 36)
    lines.append(f"v3.3 · LP v2.0.1 · AA v1.3.1 · Cycle v1.0")
    
    return "\n".join(lines)


# ============================================================
# SHORT FORMAT (for daily summary)
# ============================================================

def format_short(output: dict, lp_policy=None, allocation=None) -> str:
    """
    Ultra-short format for daily notifications.
    """
    regime = output.get("regime", "?")
    risk = output.get("risk", {})
    risk_level = risk.get("risk_level", 0)
    meta = output.get("metadata", {})
    btc_price = meta.get("btc_price", 0)
    
    # Risk state
    if risk_level < -0.3:
        risk_state = "RISK-OFF"
    elif risk_level > 0.3:
        risk_state = "RISK-ON"
    else:
        risk_state = "NEUTRAL"
    
    lines = []
    lines.append(f"{risk_state} · {regime}")
    lines.append(f"BTC ${btc_price:,.0f}")
    
    if allocation:
        btc = allocation.get("btc", {})
        eth = allocation.get("eth", {})
        btc_action = btc.get("action", "HOLD")
        eth_action = eth.get("action", "HOLD")
        lines.append(f"BTC {btc_action} | ETH {eth_action}")
        
        # Cycle signal
        cycle = allocation.get("cycle", {})
        if cycle:
            bt = cycle.get("bottom_top_signal", "")
            if bt and bt != "NO_SIGNAL":
                lines.append(f"Cycle: {bt}")
    
    if lp_policy:
        eff = int(lp_policy.effective_exposure * 100)
        hedge = "hedged" if lp_policy.hedge_recommended else ""
        lines.append(f"LP: {eff}% {hedge}".strip())
    
    if allocation and allocation.get("meta", {}).get("tail_risk_active"):
        lines.append("⚠️ Tail risk active")
    
    return "\n".join(lines)


# ============================================================
# SEND
# ============================================================

def send_telegram(output: dict, lp_policy=None, allocation=None, short=False) -> bool:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        logger.warning("Telegram credentials not set.")
        return False

    if short:
        text = format_short(output, lp_policy, allocation)
    else:
        text = format_output(output, lp_policy, allocation)

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
            logger.info("✓ Telegram sent")
            return True
        else:
            logger.error(f"Telegram error: {resp.status_code}")
            return False
    except Exception as e:
        logger.error(f"Telegram failed: {e}")
        return False
