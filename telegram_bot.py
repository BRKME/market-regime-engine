"""
Telegram Bot — Clean UI v2
Compact, consistent, no contradictions.
"""

import os
import logging
import requests

import settings as cfg

logger = logging.getLogger(__name__)


# ============================================================
# DESCRIPTIONS
# ============================================================

REGIME_DESC = {
    "BULL": "Рынок растёт. Покупатели доминируют.",
    "BEAR": "Рынок падает. Продавцы доминируют.",
    "RANGE": "Боковик. Нет явного направления.",
    "TRANSITION": "Перелом. Старый тренд сломан, новый не определён.",
}

REGIME_EMOJI = {"BULL": "🟢", "BEAR": "🔴", "RANGE": "⚪", "TRANSITION": "🟡"}

LP_REGIME_EMOJI = {
    "HARVEST": "🌾", "MEAN_REVERT": "🔄", "VOLATILE_CHOP": "⚡",
    "TRENDING": "📉", "BREAKOUT": "⚠️", "CHURN": "🚫", "GAP_RISK": "🕳", "AVOID": "🛑",
}

AA_EMOJI = {
    "STRONG_BUY": "🟢🟢", "BUY": "🟢", "HOLD": "⚪",
    "SELL": "🔴", "STRONG_SELL": "🔴🔴",
}


# ============================================================
# HELPERS
# ============================================================

def days_word(n: int) -> str:
    """Правильное склонение: 1 день, 2 дня, 5 дней"""
    if n % 10 == 1 and n % 100 != 11:
        return f"{n} день"
    elif 2 <= n % 10 <= 4 and (n % 100 < 10 or n % 100 >= 20):
        return f"{n} дня"
    else:
        return f"{n} дней"


def prob_bar(prob: float, width: int = 10) -> str:
    filled = int(prob * width)
    return "█" * filled + "░" * (width - filled)


def format_metric(val: float, explanations: dict) -> str:
    """Format metric value with explanation."""
    for threshold, text in sorted(explanations.items(), reverse=True):
        if val >= threshold:
            return f"{val:+.2f}  {text}"
    return f"{val:+.2f}"


# ============================================================
# METRIC EXPLANATIONS
# ============================================================

MOMENTUM_EXP = {
    0.7: "📈 сильный рост",
    0.3: "↗️ рост",
    -0.3: "➡️ без направления",
    -0.7: "↘️ падение",
    -999: "📉 сильное падение",
}

STABILITY_EXP = {
    0.5: "устойчивый тренд",
    0.0: "нейтрально",
    -0.5: "неустойчиво",
    -999: "хаос, развороты",
}

ROTATION_EXP = {
    0.3: "→ деньги в BTC",
    -0.3: "баланс BTC/альты",
    -999: "→ деньги в альты",
}

SENTIMENT_EXP = {
    0.5: "😀 жадность",
    0.2: "🙂 оптимизм",
    -0.2: "😐 нейтрально",
    -0.5: "😟 страх",
    -999: "😨 сильный страх",
}

MACRO_EXP = {
    0.3: "✅ поддерживает крипту",
    -0.3: "нейтрально",
    -999: "⚠️ давит на крипту",
}


def explain_metric(name: str, val: float) -> str:
    exp_map = {
        "Momentum": MOMENTUM_EXP,
        "Stability": STABILITY_EXP,
        "Rotation": ROTATION_EXP,
        "Sentiment": SENTIMENT_EXP,
        "Macro": MACRO_EXP,
    }
    explanations = exp_map.get(name, {})
    for threshold, text in sorted(explanations.items(), reverse=True):
        if val >= threshold:
            return text
    return ""


# ============================================================
# FLAG EXPLANATIONS  
# ============================================================

FLAG_EXPLANATIONS = {
    "DATA_QUALITY_DEGRADED": "Часть данных недоступна",
    "TRANSITION_STICKY": "Затянувшаяся неопределённость",
    "HIGH_VOLATILITY": "Высокая волатильность",
    "STRUCTURAL_BREAK": "Структура рынка меняется",
    "LOW_CONFIDENCE": "Модель не уверена",
    "CHURN_DETECTED": "Частые ложные сигналы",
}


# ============================================================
# BLOCK 1: MARKET PHASE
# ============================================================

def format_block_market(output: dict) -> str:
    regime = output.get("regime", "?")
    probs = output.get("probabilities", {})
    conf = output.get("confidence", {})
    buckets = output.get("buckets", {})
    risk = output.get("risk", {})
    meta = output.get("metadata", {})
    norm = output.get("normalization", {})
    flags = output.get("risk_flags", [])
    
    conf_adj = conf.get("quality_adjusted", 0)
    risk_level = risk.get("risk_level", 0)
    days = meta.get("days_in_regime", 0)
    struct_break = norm.get("break_active", False)
    exposure = risk.get("risk_exposure_cap", 0.5)
    
    btc_price = meta.get("btc_price", 0)
    eth_price = meta.get("eth_price", 0)
    
    emoji = REGIME_EMOJI.get(regime, "❓")
    
    lines = []
    lines.append("━" * 42)
    lines.append("🧭  ТЕКУЩАЯ ФАЗА РЫНКА")
    lines.append("━" * 42)
    
    # Prices (only show ETH if available)
    if eth_price:
        lines.append(f"💰 BTC: ${btc_price:,.0f}  ·  ETH: ${eth_price:,.0f}")
    else:
        lines.append(f"💰 BTC: ${btc_price:,.0f}")
    
    # Regime
    conf_pct = int(conf_adj * 100)
    regime_desc = REGIME_DESC.get(regime, "")
    lines.append("")
    lines.append(f"{emoji} {regime} · уверенность {conf_pct}%")
    lines.append(f"   {regime_desc}")
    
    # Days in regime
    day_str = days_word(days)
    if days <= 1:
        phase = "только начался"
    elif days <= 3:
        phase = "ранняя стадия"
    elif days <= 7:
        phase = "развивается"
    elif days <= 14:
        phase = "зрелая фаза"
    else:
        phase = "затянулся"
    
    lines.append(f"   {day_str} — {phase}")
    
    if struct_break:
        lines.append(f"   ⚠️ Структура рынка нестабильна")
    
    # Probabilities (compact)
    lines.append("")
    lines.append("📊 Вероятности:")
    for r in ["BULL", "BEAR", "RANGE", "TRANSITION"]:
        p = probs.get(r, 0)
        e = REGIME_EMOJI.get(r, "·")
        bar = prob_bar(p)
        pct = int(p * 100)
        lines.append(f"   {e} {r:<6} {bar} {pct:2d}%")
    
    # Metrics (compact table)
    lines.append("")
    lines.append("📌 Индикаторы:")
    
    metrics = [
        ("Движение", "Momentum"),
        ("Устойчивость", "Stability"),
        ("BTC/Альты", "Rotation"),
        ("Настроение", "Sentiment"),
        ("Макро", "Macro"),
    ]
    
    for label, key in metrics:
        val = buckets.get(key, 0)
        exp = explain_metric(key, val)
        lines.append(f"   {label:<12} {val:+.2f}  {exp}")
    
    # Recommendation (compact)
    lines.append("")
    exp_pct = int(exposure * 100)
    
    if risk_level < -0.5:
        rec = "🛡️ ЗАЩИТА КАПИТАЛА"
        lev = "плечо ❌"
    elif risk_level < -0.2:
        rec = "⚠️ ОСТОРОЖНОСТЬ"
        lev = "плечо ❌"
    elif risk_level < 0.2:
        rec = "➡️ НЕЙТРАЛЬНО"
        lev = "плечо ≤1.5x"
    elif risk_level < 0.5:
        rec = "📈 УМЕРЕННЫЙ РИСК"
        lev = "плечо ≤2x"
    else:
        rec = "🚀 АГРЕССИЯ"
        lev = "плечо ≤2x"
    
    lines.append(f"{rec}")
    lines.append(f"   Позиция: ≤{exp_pct}% · {lev} · риск: {risk_level:+.2f}")
    
    # Flags (compact, translated)
    if flags:
        lines.append("")
        flag_texts = []
        for f in flags[:2]:
            # Extract key part and translate
            key = f.split(":")[0] if ":" in f else f
            text = FLAG_EXPLANATIONS.get(key, key)
            flag_texts.append(text)
        lines.append(f"⚠️ {' · '.join(flag_texts)}")
    
    return "\n".join(lines)


# ============================================================
# BLOCK 2: LP INTELLIGENCE
# ============================================================

def format_block_lp(lp_policy) -> str:
    if lp_policy is None:
        return ""
    
    lines = []
    lines.append("")
    lines.append("━" * 42)
    lines.append("💧  LP ПОЗИЦИИ")
    lines.append("━" * 42)
    
    regime = lp_policy.lp_regime.value
    emoji = LP_REGIME_EMOJI.get(regime, "📊")
    risk_lp = lp_policy.risk_lp
    risk_dir = lp_policy.risk_directional
    quadrant = lp_policy.risk_quadrant.value
    fv = lp_policy.fee_variance_ratio
    
    # LP Regime with direction
    lp_desc = {
        "HARVEST": "собираем комиссии",
        "MEAN_REVERT": "возврат к среднему",
        "VOLATILE_CHOP": "волатильно, но без тренда",
        "TRENDING": "тренд — IL риск!",
        "BREAKOUT": "возможен прорыв",
        "CHURN": "комиссии < затрат",
        "GAP_RISK": "риск гэпов",
        "AVOID": "избегать LP",
    }.get(regime, regime)
    
    lines.append(f"{emoji} {regime}: {lp_desc}")
    
    if regime == "BREAKOUT":
        if risk_dir < -0.3:
            lines.append(f"   📉 Вероятнее вниз (risk: {risk_dir:+.2f})")
        elif risk_dir > 0.3:
            lines.append(f"   📈 Вероятнее вверх (risk: {risk_dir:+.2f})")
    
    # Quadrant (compact — одна строка)
    lines.append("")
    q_emoji = {"Q1": "✅", "Q2": "💎", "Q3": "⚠️", "Q4": "❌"}.get(quadrant, "·")
    q_text = {
        "Q1": "всё хорошо — LP идеален",
        "Q2": "рынок ↓, но LP работает",
        "Q3": "рынок ↑, но LP невыгоден — держи spot",
        "Q4": "всё плохо — выходим",
    }.get(quadrant, quadrant)
    
    lines.append(f"🎯 Квадрант {quadrant} {q_emoji}")
    lines.append(f"   {q_text}")
    lines.append(f"   LP risk: {risk_lp:+.2f} · Dir risk: {risk_dir:+.2f}")
    
    # Fee/Variance (понятнее)
    lines.append("")
    if fv >= 1.5:
        fv_verdict = "✅ выгодно"
        fv_explain = f"на $1 IL получаете ${fv:.1f} комиссий"
    elif fv >= 1.0:
        fv_verdict = "⚠️ на грани"
        fv_explain = "комиссии ≈ потери"
    else:
        fv_verdict = "❌ убыточно"
        fv_explain = f"на $1 комиссий теряете ${1/fv:.1f} на IL"
    
    lines.append(f"💰 Доходность: {fv:.2f}x {fv_verdict}")
    lines.append(f"   {fv_explain}")
    
    # Position
    lines.append("")
    raw = int(lp_policy.max_exposure * 100)
    eff = int(lp_policy.effective_exposure * 100)
    
    range_ru = {"tight": "узкий", "standard": "стандарт", "moderate": "средний",
                "wide": "широкий", "very_wide": "очень широкий"}.get(lp_policy.range_width, lp_policy.range_width)
    
    lines.append(f"📈 Позиция: {eff}% капитала")
    if eff < raw:
        lines.append(f"   (базовая {raw}%, снижена из-за риска)")
    lines.append(f"   Диапазон: {range_ru}")
    
    if lp_policy.hedge_recommended:
        lines.append(f"   ⚠️ Хедж обязателен!")
    
    return "\n".join(lines)


# ============================================================
# BLOCK 3: ASSET ALLOCATION
# ============================================================

def format_block_allocation(allocation: dict) -> str:
    if allocation is None:
        return ""
    
    btc = allocation.get("btc", {})
    eth = allocation.get("eth", {})
    meta = allocation.get("meta", {})
    
    lines = []
    lines.append("")
    lines.append("━" * 42)
    lines.append("📊  ЧТО ДЕЛАТЬ")
    lines.append("━" * 42)
    
    action_ru = {
        "STRONG_BUY": "агрессивно покупать",
        "BUY": "покупать",
        "HOLD": "держать",
        "SELL": "продавать часть",
        "STRONG_SELL": "срочно сокращать",
    }
    
    # BTC
    btc_action = btc.get("action", "HOLD")
    btc_size = btc.get("size_pct", 0)
    btc_emoji = AA_EMOJI.get(btc_action, "⚪")
    btc_ru = action_ru.get(btc_action, btc_action)
    
    size_str = f" ({btc_size:+.0%})" if btc_size != 0 else ""
    lines.append(f"   BTC  {btc_emoji} {btc_action}{size_str}")
    lines.append(f"        → {btc_ru}")
    
    if btc.get("blocked_by"):
        block_ru = {"CONFIDENCE": "низкая уверенность", "COOLDOWN": "ждём после сделки",
                    "CHURN": "лимит сделок"}.get(btc["blocked_by"], btc["blocked_by"])
        lines.append(f"        ⛔ {block_ru}")
    
    # ETH
    eth_action = eth.get("action", "HOLD")
    eth_size = eth.get("size_pct", 0)
    eth_emoji = AA_EMOJI.get(eth_action, "⚪")
    eth_ru = action_ru.get(eth_action, eth_action)
    
    size_str = f" ({eth_size:+.0%})" if eth_size != 0 else ""
    lines.append(f"   ETH  {eth_emoji} {eth_action}{size_str}")
    lines.append(f"        → {eth_ru}")
    
    if eth.get("blocked_by"):
        block_ru = {"CONFIDENCE": "низкая уверенность", "COOLDOWN": "ждём после сделки",
                    "CHURN": "лимит сделок"}.get(eth["blocked_by"], eth["blocked_by"])
        lines.append(f"        ⛔ {block_ru}")
    
    # Tail risk
    if meta.get("tail_risk_active"):
        polarity = meta.get("tail_polarity", "downside")
        lines.append("")
        lines.append("━" * 42)
        if polarity == "downside":
            lines.append("🚨 TAIL RISK ↓ · ЗАЩИТА КАПИТАЛА")
            lines.append("   Экстремальный риск. Сокращаем всё.")
        else:
            lines.append("🚨 TAIL RISK ↑ · ОСТОРОЖНО")
            lines.append("   Экстрим вверх. Возможен разворот.")
    
    return "\n".join(lines)


# ============================================================
# MAIN FORMAT
# ============================================================

def format_output(output: dict, lp_policy=None, allocation=None) -> str:
    lines = []
    
    lines.append(format_block_market(output))
    
    if lp_policy is not None:
        lines.append(format_block_lp(lp_policy))
    
    if allocation is not None:
        lines.append(format_block_allocation(allocation))
    
    # Footer
    lines.append("")
    lines.append("━" * 42)
    meta = output.get("metadata", {})
    vol_z = meta.get("vol_z", 0)
    lines.append(f"v3.3 + LP v2.0.1 + AA v1.3.1 · vol_z: {vol_z:.1f}")
    
    return "\n".join(lines)


# ============================================================
# SEND
# ============================================================

def send_telegram(output: dict, lp_policy=None, allocation=None) -> bool:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        logger.warning("Telegram credentials not set.")
        return False

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
