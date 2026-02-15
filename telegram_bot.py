"""
Telegram Bot — Action-First UI
One screen → one decision.
"""

import os
import logging
import requests

import settings as cfg

logger = logging.getLogger(__name__)


# ============================================================
# FORMAT OUTPUT
# ============================================================

def format_output(output: dict, lp_policy=None, allocation=None) -> str:
    """
    Action-first format.
    Показатели: English
    Комментарии: Русский
    """
    meta = output.get("metadata", {})
    risk = output.get("risk", {})
    conf = output.get("confidence", {})
    buckets = output.get("buckets", {})
    regime = output.get("regime", "?")
    probs = output.get("probabilities", {})
    flags = output.get("risk_flags", [])
    norm = output.get("normalization", {})
    
    btc_price = meta.get("btc_price", 0)
    risk_level = risk.get("risk_level", 0)
    conf_adj = conf.get("quality_adjusted", 0)
    days = meta.get("days_in_regime", 0)
    vol_z = meta.get("vol_z", 0)
    struct_break = norm.get("break_active", False)
    mom = buckets.get("Momentum", 0)
    
    # Tail risk
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
    # HEADER
    # ══════════════════════════════════════════════════════
    if tail_active:
        lines.append(f"🚨 ALERT: TAIL RISK · {risk_state}")
    elif risk_level < -0.3:
        lines.append(f"⚠️ RISK-OFF MODE")
    else:
        lines.append(f"📊 MONITORING · {risk_state}")
    
    lines.append(f"BTC ${btc_price:,.0f}")
    lines.append("")
    
    # ══════════════════════════════════════════════════════
    # REGIME + PROBABILITIES
    # ══════════════════════════════════════════════════════
    lines.append(f"{risk_emoji} REGIME: {regime}")
    
    # Phase
    if days <= 1:
        phase = "early"
    elif days <= 7:
        phase = f"{days}d"
    else:
        phase = f"{days}d mature"
    
    conf_pct = int(conf_adj * 100)
    lines.append(f"   Phase: {phase} · Confidence: {conf_pct}%")
    
    # Tail risk indicator
    if tail_active:
        if tail_polarity == "downside":
            lines.append(f"   Tail risk: ACTIVE ↓")
        else:
            lines.append(f"   Tail risk: ACTIVE ↑")
    
    # Probabilities with visual bars
    lines.append("")
    lines.append("Probabilities:")
    
    prob_bull = probs.get("BULL", 0)
    prob_bear = probs.get("BEAR", 0)
    prob_range = probs.get("RANGE", 0)
    prob_trans = probs.get("TRANSITION", 0)
    
    def make_bar(value, width=12):
        filled = int(value * width)
        return "█" * filled + "░" * (width - filled)
    
    lines.append(f"   BULL       {make_bar(prob_bull)} {prob_bull:.2f}")
    lines.append(f"   BEAR       {make_bar(prob_bear)} {prob_bear:.2f}")
    lines.append(f"   RANGE      {make_bar(prob_range)} {prob_range:.2f}")
    lines.append(f"   TRANSITION {make_bar(prob_trans)} {prob_trans:.2f}")
    
    # Rich logic comment (Russian)
    lines.append("")
    comment = _get_regime_comment(regime, days, tail_active, conf_adj, mom, risk_level)
    lines.append(f"→ {comment}")
    
    # ══════════════════════════════════════════════════════
    # DIRECTIONAL POLICY
    # ══════════════════════════════════════════════════════
    if allocation:
        btc = allocation.get("btc", {})
        eth = allocation.get("eth", {})
        
        btc_action = btc.get("action", "HOLD")
        eth_action = eth.get("action", "HOLD")
        btc_size = btc.get("size_pct", 0)
        eth_size = eth.get("size_pct", 0)
        
        lines.append("")
        lines.append("📉 DIRECTIONAL")
        
        # Actions
        btc_str = f"{btc_size:+.0%}" if btc_size != 0 else ""
        eth_str = f"{eth_size:+.0%}" if eth_size != 0 else ""
        
        lines.append(f"   BTC: {btc_action} {btc_str}")
        lines.append(f"   ETH: {eth_action} {eth_str}")
        
        # Reason (compact)
        if btc.get("blocked_by"):
            lines.append(f"   Blocked: {btc['blocked_by'].lower()}")
        
        # Directional comment (Russian)
        dir_comment = _get_directional_comment(btc_action, eth_action, regime, tail_active, conf_adj, mom)
        if dir_comment:
            lines.append(f"   → {dir_comment}")
    
    # ══════════════════════════════════════════════════════
    # LP POLICY with QUADRANT MATRIX
    # ══════════════════════════════════════════════════════
    if lp_policy:
        risk_lp = lp_policy.risk_lp
        risk_dir = lp_policy.risk_directional
        quadrant = lp_policy.risk_quadrant.value
        fv = lp_policy.fee_variance_ratio
        eff = int(lp_policy.effective_exposure * 100)
        max_exp = int(lp_policy.max_exposure * 100)
        hedge = lp_policy.hedge_recommended
        range_width = lp_policy.range_width
        
        lines.append("")
        lines.append("💧 LP POLICY")
        
        # Quadrant matrix (compact)
        lines.append("")
        lines.append("          Dir Risk →")
        lines.append("      ┌───────┬───────┐")
        
        # Mark current quadrant
        q3_mark = "[Q3]" if quadrant == "Q3" else " Q3 "
        q1_mark = "[Q1]" if quadrant == "Q1" else " Q1 "
        q4_mark = "[Q4]" if quadrant == "Q4" else " Q4 "
        q2_mark = "[Q2]" if quadrant == "Q2" else " Q2 "
        
        lines.append(f"  LP↑ │{q3_mark}  │{q1_mark}  │")
        lines.append(f"      │ spot  │ ideal │")
        lines.append("      ├───────┼───────┤")
        lines.append(f"  LP↓ │{q4_mark}  │{q2_mark}  │")
        lines.append(f"      │ exit  │ LP    │")
        lines.append("      └───────┴───────┘")
        
        lines.append("")
        lines.append(f"   Dir: {risk_dir:+.2f} · LP: {risk_lp:+.2f} · F/V: {fv:.1f}x")
        lines.append(f"   Exposure: {eff}% (max {max_exp}%)")
        lines.append(f"   Range: {range_width}")
        
        if hedge:
            lines.append(f"   Hedge: REQUIRED")
        
        # LP comment (Russian)
        lp_comment = _get_lp_comment(quadrant, risk_lp, risk_dir, eff, max_exp)
        lines.append(f"   → {lp_comment}")
    
    # ══════════════════════════════════════════════════════
    # FLAGS (if any)
    # ══════════════════════════════════════════════════════
    display_flags = []
    
    if tail_active:
        display_flags.append("Tail risk active")
    
    if struct_break:
        display_flags.append("Market structure break")
    
    # Check for data issues
    data_quality = meta.get("data_completeness", 1.0)
    if data_quality < 0.85 or any("DATA" in f for f in flags):
        display_flags.append("Partial data — проверь источники")
    
    if display_flags:
        lines.append("")
        lines.append("⚠️ FLAGS")
        for f in display_flags[:3]:
            lines.append(f"   • {f}")
    
    # ══════════════════════════════════════════════════════
    # FOOTER
    # ══════════════════════════════════════════════════════
    lines.append("")
    lines.append("v3.3 · LP v2.0.1 · AA v1.3.1")
    
    return "\n".join(lines)


def _get_regime_comment(regime: str, days: int, tail_active: bool, conf: float, mom: float, risk: float) -> str:
    """
    Rich logic комментарий по режиму (Russian).
    Контекстный — учитывает комбинацию факторов.
    """
    if regime == "BEAR":
        if tail_active and conf < 0.25:
            return "Паника на рынке. Возможно близко дно — не лучшее время продавать."
        elif tail_active:
            return "Сильный стресс. Защита капитала, но осторожно с продажами на лоях."
        elif days <= 2:
            return "Начало коррекции. Наблюдаем глубину падения."
        elif days > 14 and mom > -0.3:
            return "Затяжной медвежий тренд, но импульс слабеет. Возможен разворот."
        elif days > 14:
            return "Затяжной медвежий тренд. Терпение, ждём сигналы разворота."
        else:
            return "Рынок слабый. Защита капитала в приоритете."
    
    elif regime == "BULL":
        if tail_active:
            return "Рост перегрет. Фиксация прибыли разумна."
        elif days <= 2:
            return "Возможное начало роста. Подтверждение нужно."
        elif days > 14 and mom < 0.3:
            return "Зрелый бычий тренд, импульс слабеет. Осторожность."
        elif conf >= 0.6:
            return "Уверенный рост. Можно наращивать позиции."
        else:
            return "Рынок растёт. Умеренный риск допустим."
    
    elif regime == "TRANSITION":
        if risk < -0.3:
            return "Переходный период с негативным уклоном. Лучше подождать."
        elif risk > 0.3:
            return "Переходный период с позитивным уклоном. Наблюдаем."
        else:
            return "Неопределённость. Ждём ясности перед действиями."
    
    else:  # RANGE
        if conf >= 0.5:
            return "Боковик. Нет направления, но стабильно."
        else:
            return "Боковик с низкой уверенностью. Ждём."


def _get_directional_comment(btc_action: str, eth_action: str, regime: str, 
                              tail_active: bool, conf: float, mom: float) -> str:
    """
    Rich logic комментарий по directional (Russian).
    """
    if tail_active and "SELL" in btc_action:
        if conf < 0.25:
            return "Tail risk, но низкая уверенность — возможно паника. Осторожно."
        else:
            return "Tail risk активен — снижаем экспозицию."
    
    if btc_action == "HOLD" and eth_action == "HOLD":
        if conf < 0.4:
            return "Уверенность слишком низкая для действий."
        elif regime == "TRANSITION":
            return "Переходный режим — ждём подтверждения."
        else:
            return "Условия не соответствуют критериям входа/выхода."
    
    if "BUY" in btc_action:
        return "Условия для наращивания позиций."
    
    if "SELL" in btc_action and not tail_active:
        return "Условия для сокращения позиций."
    
    return ""


def _get_lp_comment(quadrant: str, risk_lp: float, risk_dir: float, eff: int, max_exp: int) -> str:
    """
    Rich logic комментарий по LP (Russian).
    """
    if quadrant == "Q1":
        return "Идеальные условия для LP. Низкий риск, хорошие комиссии."
    
    elif quadrant == "Q2":
        if eff < max_exp * 0.5:
            return "LP возможности есть, но капитал ограничен из-за направленного риска."
        else:
            return "LP opportunity при повышенном направленном риске."
    
    elif quadrant == "Q3":
        return "Spot лучше LP. Направленный риск низкий, но LP не оптимален."
    
    elif quadrant == "Q4":
        return "Худшие условия. Минимизируй LP экспозицию."
    
    return ""


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
