"""
Telegram Bot — Values + Explanations
Shows both numeric values and human-friendly comments.
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
    "RANGE": "Рынок в боковике. Нет явного направления.",
    "TRANSITION": "Рынок меняется. Старый тренд сломан, новый не определён.",
}

REGIME_EMOJI = {
    "BULL": "🟢",
    "BEAR": "🔴",
    "RANGE": "⚪",
    "TRANSITION": "🟡",
}

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

AA_EMOJI = {
    "STRONG_BUY": "🟢🟢",
    "BUY": "🟢",
    "HOLD": "⚪",
    "SELL": "🔴",
    "STRONG_SELL": "🔴🔴",
}


# ============================================================
# METRIC EXPLANATIONS (with values)
# ============================================================

def explain_momentum(val: float) -> str:
    """
    Моментум: скорость и направление движения цены за последние дни.
    Шкала: -1 (сильное падение) до +1 (сильный рост)
    """
    if val < -0.7:
        comment = "сильное падение"
    elif val < -0.3:
        comment = "умеренное падение"
    elif val < 0.3:
        comment = "без направления"
    elif val < 0.7:
        comment = "умеренный рост"
    else:
        comment = "сильный рост"
    return f"{val:+.2f} — {comment}"


def explain_stability(val: float) -> str:
    """
    Стабильность: насколько устойчиво текущее движение.
    -1 = хаотичные развороты, +1 = устойчивый тренд
    """
    if val < -0.7:
        comment = "хаос, частые развороты"
    elif val < -0.3:
        comment = "неустойчиво"
    elif val < 0.3:
        comment = "нейтрально"
    elif val < 0.7:
        comment = "устойчиво"
    else:
        comment = "очень устойчивый тренд"
    return f"{val:+.2f} — {comment}"


def explain_rotation(val: float) -> str:
    """
    Ротация: куда перетекают деньги — в BTC или в альткоины.
    -1 = альтсезон (деньги в альты), +1 = деньги в BTC
    """
    if val < -0.5:
        comment = "альтсезон, деньги в альткоины"
    elif val < -0.2:
        comment = "деньги перетекают в альты"
    elif val < 0.2:
        comment = "баланс, нет перетока"
    elif val < 0.5:
        comment = "деньги перетекают в BTC"
    else:
        comment = "BTC доминирует, альты слабеют"
    return f"{val:+.2f} — {comment}"


def explain_sentiment(val: float) -> str:
    """
    Сентимент: настроение рынка (Fear & Greed Index и др.)
    -1 = крайний страх, +1 = крайняя жадность
    """
    if val < -0.5:
        comment = "сильный страх"
    elif val < -0.2:
        comment = "страх"
    elif val < 0.2:
        comment = "нейтрально"
    elif val < 0.5:
        comment = "оптимизм"
    else:
        comment = "жадность"
    return f"{val:+.2f} — {comment}"


def explain_macro(val: float) -> str:
    """
    Макро: влияние внешних рынков (доллар, S&P500, ставки ФРС)
    -1 = макро давит на крипту, +1 = макро поддерживает
    """
    if val < -0.3:
        comment = "макро давит на крипту"
    elif val < 0.3:
        comment = "нейтральный фон"
    else:
        comment = "макро поддерживает рост"
    return f"{val:+.2f} — {comment}"


# ============================================================
# LP REGIME EXPLANATIONS
# ============================================================

def explain_lp_regime(regime: str, risk_directional: float) -> str:
    """
    Explain LP regime with context about direction.
    """
    explanations = {
        "HARVEST": "Идеальные условия для LP — волатильность без тренда, собирай комиссии",
        "MEAN_REVERT": "Цена колеблется вокруг среднего — хорошо для LP в узком диапазоне",
        "VOLATILE_CHOP": "Высокая волатильность, но без направления — LP может работать",
        "TRENDING": "Сильный тренд — LP опасно, impermanent loss съест прибыль",
        "BREAKOUT": "Рынок готовится к резкому движению (вверх или вниз) — LP рискованно",
        "CHURN": "Слишком много движений — комиссии не покрывают затрат на ребаланс",
        "GAP_RISK": "Риск гэпов (резких скачков цены) — LP опасно",
        "AVOID": "Условия не подходят для LP — лучше держать активы напрямую",
    }
    
    base = explanations.get(regime, regime)
    
    # Add direction context for BREAKOUT
    if regime == "BREAKOUT":
        if risk_directional < -0.3:
            base += "\n   📉 Вероятнее прорыв ВНИЗ (risk: {:.2f})".format(risk_directional)
        elif risk_directional > 0.3:
            base += "\n   📈 Вероятнее прорыв ВВЕРХ (risk: {:.2f})".format(risk_directional)
        else:
            base += "\n   ↔️ Направление неясно (risk: {:.2f})".format(risk_directional)
    
    return base


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def prob_bar(prob: float, width: int = 12) -> str:
    filled = int(prob * width)
    return "█" * filled + "░" * (width - filled)


def format_days_in_regime(days: int, struct_break: bool, regime: str) -> str:
    """Human-friendly explanation of time in regime."""
    if days <= 1:
        phase = "только начался"
    elif days <= 3:
        phase = "ранняя стадия"
    elif days <= 7:
        phase = "развивается"
    elif days <= 14:
        phase = "зрелая фаза"
    else:
        phase = "затянувшийся"
    
    result = f"{days} дней — {phase}"
    
    if struct_break:
        if regime == "TRANSITION":
            result += "\n   ⚠️ Структура рынка ломается — идёт переход к новому режиму"
        else:
            result += "\n   ⚠️ Структура нестабильна — возможна скорая смена режима"
    
    return result


def format_flags(flags: list) -> str:
    """Explain risk flags in human terms."""
    if not flags:
        return ""
    
    flag_explanations = {
        "DATA_QUALITY_DEGRADED": "Часть данных недоступна — точность снижена",
        "TRANSITION_STICKY": "Режим TRANSITION затянулся — рынок в неопределённости",
        "HIGH_VOLATILITY": "Волатильность выше нормы — осторожнее с позициями",
        "STRUCTURAL_BREAK": "Структура рынка меняется — старые паттерны не работают",
        "LOW_CONFIDENCE": "Модель не уверена в прогнозе — меньше риска",
        "CHURN_DETECTED": "Слишком много переключений — сигналы нестабильны",
    }
    
    lines = []
    lines.append("")
    lines.append("⚠️ ПРЕДУПРЕЖДЕНИЯ:")
    
    for flag in flags[:3]:  # Max 3
        explanation = flag_explanations.get(flag, flag)
        lines.append(f"   • {explanation}")
    
    if len(flags) > 3:
        lines.append(f"   ... и ещё {len(flags) - 3}")
    
    return "\n".join(lines)


# ============================================================
# BLOCK 1: MARKET PHASE
# ============================================================

def format_block_market(output: dict) -> str:
    """Block 1: Current Market Phase with values + explanations."""
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
    
    # Prices
    btc_price = meta.get("btc_price", 0)
    eth_price = meta.get("eth_price", 0)
    
    emoji = REGIME_EMOJI.get(regime, "❓")
    regime_desc = REGIME_DESC.get(regime, "")
    
    lines = []
    lines.append("━" * 42)
    lines.append("🧭  ТЕКУЩАЯ ФАЗА РЫНКА")
    lines.append("━" * 42)
    
    # Prices
    btc_str = f"${btc_price:,.0f}" if btc_price else "—"
    eth_str = f"${eth_price:,.0f}" if eth_price else "—"
    lines.append(f"💰 BTC: {btc_str}  ·  ETH: {eth_str}")
    lines.append("")
    
    # Regime + description
    conf_pct = int(conf_adj * 100)
    lines.append(f"{emoji} РЕЖИМ: {regime} (уверенность {conf_pct}%)")
    lines.append(f"   {regime_desc}")
    
    # Days in regime
    lines.append("")
    day_explanation = format_days_in_regime(days, struct_break, regime)
    lines.append(f"📅 {day_explanation}")
    
    # Probabilities
    lines.append("")
    lines.append("📊 ВЕРОЯТНОСТИ РЕЖИМОВ:")
    for r in ["BULL", "BEAR", "RANGE", "TRANSITION"]:
        p = probs.get(r, 0)
        e = REGIME_EMOJI.get(r, "·")
        name = r[:5].ljust(5)
        bar = prob_bar(p)
        pct = int(p * 100)
        lines.append(f"   {e} {name} {bar} {pct:2d}%")
    
    # Key metrics with VALUES + explanations
    lines.append("")
    lines.append("📌 ЧТО ПРОИСХОДИТ (значение · комментарий):")
    
    mom = buckets.get("Momentum", 0)
    stab = buckets.get("Stability", 0)
    rot = buckets.get("Rotation", 0)
    sent = buckets.get("Sentiment", 0)
    macro = buckets.get("Macro", 0)
    
    lines.append(f"   Движение цены:  {explain_momentum(mom)}")
    lines.append(f"   Устойчивость:   {explain_stability(stab)}")
    lines.append(f"   BTC vs Альты:   {explain_rotation(rot)}")
    lines.append(f"   Настроение:     {explain_sentiment(sent)}")
    lines.append(f"   Макро-факторы:  {explain_macro(macro)}")
    
    # Strategy recommendation
    lines.append("")
    lines.append("🛡️ РЕКОМЕНДАЦИЯ:")
    
    exp_pct = int(exposure * 100)
    
    if risk_level < -0.5:
        strat = "Защита капитала. Минимальные позиции."
        lev = "Плечо запрещено ❌"
    elif risk_level < -0.2:
        strat = "Осторожность. Сокращайте риски."
        lev = "Плечо запрещено ❌"
    elif risk_level < 0.2:
        strat = "Нейтрально. Следите за сигналами."
        lev = "Плечо до 1.5x ⚠️"
    elif risk_level < 0.5:
        strat = "Умеренный оптимизм. Можно наращивать."
        lev = "Плечо до 2x ✅"
    else:
        strat = "Агрессивный рост. Максимальные позиции."
        lev = "Плечо до 2x ✅"
    
    lines.append(f"   {strat}")
    lines.append(f"   Макс. позиция: {exp_pct}% · {lev}")
    lines.append(f"   Риск-скор: {risk_level:+.2f} (от -1 до +1)")
    
    # Flags
    if flags:
        lines.append(format_flags(flags))
    
    return "\n".join(lines)


# ============================================================
# BLOCK 2: LP INTELLIGENCE
# ============================================================

def format_block_lp(lp_policy) -> str:
    """Block 2: LP Intelligence with values + explanations."""
    if lp_policy is None:
        return ""
    
    lines = []
    lines.append("")
    lines.append("━" * 42)
    lines.append("💧  LP ПОЗИЦИИ (пулы ликвидности)")
    lines.append("━" * 42)
    
    # LP Regime with full explanation
    regime = lp_policy.lp_regime.value
    emoji = LP_REGIME_EMOJI.get(regime, "📊")
    risk_dir = lp_policy.risk_directional
    
    explanation = explain_lp_regime(regime, risk_dir)
    lines.append(f"{emoji} LP-РЕЖИМ: {regime}")
    lines.append(f"   {explanation}")
    
    # Risk scores
    lines.append("")
    risk_lp = lp_policy.risk_lp
    quadrant = lp_policy.risk_quadrant.value
    
    lines.append(f"📊 ОЦЕНКА РИСКОВ:")
    lines.append(f"   LP Risk:  {risk_lp:+.2f}  (от -1 плохо до +1 хорошо)")
    lines.append(f"   Dir Risk: {risk_dir:+.2f}  (от -1 падение до +1 рост)")
    
    # Quadrant visual + explanation
    lines.append("")
    lines.append(f"🎯 КВАДРАНТ: {quadrant}")
    lines.append(f"   ┌─────────────┬─────────────┐")
    lines.append(f"   │ Q3: Spot    │ Q1: Идеал   │  LP Risk +")
    lines.append(f"   │ лучше       │ всё хорошо  │")
    lines.append(f"   ├─────────────┼─────────────┤")
    lines.append(f"   │ Q4: Выход   │ Q2: LP      │  LP Risk -")
    lines.append(f"   │ всё плохо   │ opportunity │")
    lines.append(f"   └─────────────┴─────────────┘")
    lines.append(f"     Dir Risk -    Dir Risk +")
    
    q_explanations = {
        "Q1": "✅ Q1: Рынок растёт + LP выгодно — идеальные условия",
        "Q2": "💎 Q2: Рынок падает, но LP всё ещё прибыльно — редкая возможность!",
        "Q3": "⚠️ Q3: Рынок растёт, но LP невыгодно — лучше держать spot",
        "Q4": "❌ Q4: Всё плохо — и рынок падает, и LP убыточно — выходим",
    }
    lines.append(f"   {q_explanations.get(quadrant, quadrant)}")
    
    # Fee/Var ratio explanation
    fv = lp_policy.fee_variance_ratio
    lines.append("")
    lines.append(f"💰 ДОХОДНОСТЬ LP:")
    lines.append(f"   Комиссии / Потери = {fv:.2f}x")
    lines.append(f"   (сколько комиссий вы заработаете на каждый $1 потерь от IL)")
    if fv > 2.0:
        lines.append(f"   ✅ Выгодно: на $1 потерь получите ${fv:.1f} комиссий")
    elif fv > 1.5:
        lines.append(f"   ⚠️ На грани: комиссии ≈ потери, профит минимален")
    else:
        lines.append(f"   ❌ Невыгодно: потери от IL больше, чем комиссии")
        lines.append(f"      На $1 комиссий теряете ${1/fv:.1f} на IL")
    
    # Exposure
    lines.append("")
    raw = int(lp_policy.max_exposure * 100)
    eff = int(lp_policy.effective_exposure * 100)
    
    lines.append(f"📈 РЕКОМЕНДУЕМАЯ ПОЗИЦИЯ:")
    lines.append(f"   Базовая: {raw}% капитала")
    lines.append(f"   С учётом рисков: {eff}% капитала")
    if eff < raw:
        lines.append(f"   (снижено из-за направленного риска {risk_dir:+.2f})")
    
    lines.append(f"   Диапазон: {lp_policy.range_width}")
    lines.append(f"   Ребаланс: {lp_policy.rebalance}")
    
    if lp_policy.hedge_recommended:
        lines.append(f"   ⚠️ Хедж обязателен!")
    
    return "\n".join(lines)


# ============================================================
# BLOCK 3: ASSET ALLOCATION
# ============================================================

def format_block_allocation(allocation: dict) -> str:
    """Block 3: Asset Allocation with explanations."""
    if allocation is None:
        return ""
    
    btc = allocation.get("btc", {})
    eth = allocation.get("eth", {})
    meta = allocation.get("meta", {})
    
    lines = []
    lines.append("")
    lines.append("━" * 42)
    lines.append("📊  ЧТО ДЕЛАТЬ С АКТИВАМИ")
    lines.append("━" * 42)
    
    # Action descriptions
    action_desc = {
        "STRONG_BUY": "Агрессивно покупать",
        "BUY": "Покупать",
        "HOLD": "Держать, ничего не делать",
        "SELL": "Продавать часть",
        "STRONG_SELL": "Срочно сокращать позицию",
    }
    
    # BTC
    btc_action = btc.get("action", "HOLD")
    btc_size = btc.get("size_pct", 0)
    btc_emoji = AA_EMOJI.get(btc_action, "⚪")
    btc_desc = action_desc.get(btc_action, btc_action)
    btc_blocked = btc.get("blocked_by")
    
    lines.append(f"   BTC: {btc_emoji} {btc_action}")
    lines.append(f"        → {btc_desc}")
    if btc_size != 0:
        lines.append(f"        Изменение: {btc_size:+.0%} от текущей позиции")
    if btc_blocked:
        block_explanations = {
            "CONFIDENCE": "низкая уверенность модели",
            "COOLDOWN": "слишком рано после прошлой сделки",
            "CHURN": "слишком много сделок за месяц",
        }
        block_exp = block_explanations.get(btc_blocked, btc_blocked)
        lines.append(f"        ⛔ Заблокировано: {block_exp}")
    
    lines.append("")
    
    # ETH
    eth_action = eth.get("action", "HOLD")
    eth_size = eth.get("size_pct", 0)
    eth_emoji = AA_EMOJI.get(eth_action, "⚪")
    eth_desc = action_desc.get(eth_action, eth_action)
    eth_blocked = eth.get("blocked_by")
    
    lines.append(f"   ETH: {eth_emoji} {eth_action}")
    lines.append(f"        → {eth_desc}")
    if eth_size != 0:
        lines.append(f"        Изменение: {eth_size:+.0%} от текущей позиции")
    if eth_blocked:
        block_exp = block_explanations.get(eth_blocked, eth_blocked)
        lines.append(f"        ⛔ Заблокировано: {block_exp}")
    
    # Tail risk warning
    if meta.get("tail_risk_active"):
        polarity = meta.get("tail_polarity", "downside")
        lines.append("")
        lines.append("━" * 42)
        if polarity == "downside":
            lines.append("🚨 ЭКСТРЕННЫЙ РЕЖИМ: TAIL RISK ↓")
            lines.append("   Обнаружен экстремальный риск падения.")
            lines.append("   Волатильность аномально высокая.")
            lines.append("   Приоритет: защита капитала любой ценой.")
        else:
            lines.append("🚨 ЭКСТРЕННЫЙ РЕЖИМ: TAIL RISK ↑")
            lines.append("   Экстремальная волатильность вверх.")
            lines.append("   Возможен резкий разворот после роста.")
            lines.append("   Не FOMO, не докупать на хаях.")
    
    return "\n".join(lines)


# ============================================================
# MAIN FORMAT FUNCTION
# ============================================================

def format_output(output: dict, lp_policy=None, allocation=None) -> str:
    """Format complete output with values + explanations everywhere."""
    lines = []
    
    # Block 1: Market Phase
    lines.append(format_block_market(output))
    
    # Block 2: LP Intelligence
    if lp_policy is not None:
        lines.append(format_block_lp(lp_policy))
    
    # Block 3: Asset Allocation
    if allocation is not None:
        lines.append(format_block_allocation(allocation))
    
    # Footer
    lines.append("")
    lines.append("━" * 42)
    
    meta = output.get("metadata", {})
    vol_z = meta.get("vol_z", 0)
    
    # Technical footer (compact)
    lines.append(f"📡 vol_z: {vol_z:.2f} | Модель v3.3 + LP v2.0.1 + AA v1.3.1")
    lines.append("━" * 42)
    
    return "\n".join(lines)


# ============================================================
# SEND TELEGRAM
# ============================================================

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
