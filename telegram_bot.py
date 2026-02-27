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
    Structured risk-focused format.
    Metric names: English
    Comments: Russian
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
    eth_price = meta.get("eth_price", 0)
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
    
    conf_pct = int(conf_adj * 100)
    
    lines = []
    
    # ══════════════════════════════════════════════════════
    # 1. MARKET PHASE - Visual scale
    # ══════════════════════════════════════════════════════
    
    # Position marker based on regime
    phase_positions = {
        "BULL": 0,
        "RANGE": 1, 
        "TRANSITION": 2,
        "BEAR": 3
    }
    current_pos = phase_positions.get(regime, 2)
    
    # Build scale line
    scale_labels = "BULL ─── RANGE ─── TRANSITION ─── BEAR"
    # Marker positions (approximate character positions)
    marker_positions = [2, 13, 26, 43]
    marker_line = " " * marker_positions[current_pos] + "▲"
    
    lines.append(scale_labels)
    lines.append(marker_line)
    lines.append("")
    
    # Regime emoji and info
    regime_emoji = {"BULL": "🟢", "BEAR": "🔴", "RANGE": "🟡", "TRANSITION": "⚪"}.get(regime, "⚪")
    
    # Visual confidence bar
    filled = int(conf_adj * 10)
    empty = 10 - filled
    conf_bar = '█' * filled + '░' * empty
    
    lines.append(f"{regime_emoji} {regime} ({days}d)")
    lines.append(f"[{conf_bar}] {conf_pct}%")
    
    # Directional pressure
    if risk_level < 0:
        lines.append(f"↓ Downside pressure. Dir: ↓ {abs(risk_level):.2f}")
    else:
        lines.append(f"↑ Upside pressure. Dir: ↑ {abs(risk_level):.2f}")
    
    lines.append("")
    
    # Regime probabilities with visual bars
    prob_bull = probs.get("BULL", 0)
    prob_bear = probs.get("BEAR", 0)
    prob_range = probs.get("RANGE", 0)
    prob_trans = probs.get("TRANSITION", 0)
    
    def make_bar(value, width=12):
        filled = int(value * width)
        return "█" * filled + "░" * (width - filled)
    
    lines.append("Regime probabilities:")
    lines.append(f"BULL       {make_bar(prob_bull)} {int(prob_bull*100)}%")
    lines.append(f"BEAR       {make_bar(prob_bear)} {int(prob_bear*100)}%")
    lines.append(f"RANGE      {make_bar(prob_range)} {int(prob_range*100)}%")
    lines.append(f"TRANSITION {make_bar(prob_trans)} {int(prob_trans*100)}%")
    
    lines.append("")
    
    # AI Comment - analytical, no emotions
    ai_comment = _generate_analytical_comment(
        regime=regime,
        prob_bear=prob_bear,
        prob_trans=prob_trans,
        prob_bull=prob_bull,
        conf_pct=conf_pct,
        dir_value=risk_level,
        tail_active=tail_active,
        struct_break=struct_break,
        vol_z=vol_z
    )
    lines.append(f"→ {ai_comment}")
    
    lines.append("")
    
    # ══════════════════════════════════════════════════════
    # 2. RISK SCALE
    # ══════════════════════════════════════════════════════
    
    # Determine risk state
    if tail_active:
        risk_state = "TAIL"
        risk_pos = 2
    elif vol_z > 1.5 or struct_break:
        risk_state = "ELEVATED"
        risk_pos = 1
    elif vol_z > 2.5:
        risk_state = "CRISIS"
        risk_pos = 3
    else:
        risk_state = "NORMAL"
        risk_pos = 0
    
    lines.append("⚠️ RISK SCALE")
    risk_scale = "NORMAL ─── ELEVATED ─── TAIL ─── CRISIS"
    risk_marker_positions = [3, 18, 32, 42]
    risk_marker_line = " " * risk_marker_positions[risk_pos] + "▲"
    lines.append(risk_scale)
    lines.append(risk_marker_line)
    lines.append("")
    
    # Risk components with Russian comments
    # Volatility
    if vol_z > 2.0:
        vol_regime = "TAIL (p95+)"
        vol_comment = "Волатильность выше 95-го перцентиля; повышена вероятность резких импульсов."
    elif vol_z > 1.5:
        vol_regime = "ELEVATED"
        vol_comment = "Волатильность повышена; рекомендуется снижение размера позиций."
    elif vol_z > 1.0:
        vol_regime = "MODERATE"
        vol_comment = "Волатильность умеренно повышена."
    else:
        vol_regime = "NORMAL"
        vol_comment = "Волатильность в пределах нормы."
    
    lines.append(f"Volatility: {vol_regime}")
    lines.append(f"  → {vol_comment}")
    
    # Structure
    if struct_break:
        lines.append("Structure: BREAK")
        lines.append("  → Нарушена рыночная структура; фаза перераспределения.")
    else:
        lines.append("Structure: INTACT")
        lines.append("  → Структура сохранена.")
    
    lines.append("")
    
    # ══════════════════════════════════════════════════════
    # 3. SPOT POSITIONS - Fixed contradiction
    # ══════════════════════════════════════════════════════
    if allocation:
        btc = allocation.get("btc", {})
        eth = allocation.get("eth", {})
        
        btc_action = btc.get("action", "HOLD")
        eth_action = eth.get("action", "HOLD")
        btc_size = btc.get("size_pct", 0)
        eth_size = eth.get("size_pct", 0)
        
        # Only show if there's a signal
        if btc_action != "HOLD" or eth_action != "HOLD":
            lines.append("📉 SPOT BIAS (base signal):")
            
            if btc_size != 0:
                lines.append(f"  BTC: {btc_size:+.0%}")
            if eth_size != 0:
                lines.append(f"  ETH: {eth_size:+.0%}")
            
            lines.append(f"  Model confidence: {conf_pct}% ({'low' if conf_pct < 40 else 'moderate' if conf_pct < 60 else 'high'})")
            
            # Confidence-adjusted exposure
            adj_btc = btc_size * conf_adj
            adj_eth = eth_size * conf_adj
            
            lines.append("")
            lines.append("Confidence-adjusted exposure:")
            if btc_size != 0:
                lines.append(f"  BTC: {adj_btc:+.0%}")
            if eth_size != 0:
                lines.append(f"  ETH: {adj_eth:+.0%}")
            
            lines.append("")
            lines.append("Interpretation:")
            
            # Generate interpretation based on signals
            if btc_size < 0:
                signal_type = "медвежий"
            else:
                signal_type = "бычий"
            
            if conf_pct < 30:
                reliability = "статистическая устойчивость низкая"
            elif conf_pct < 50:
                reliability = "статистическая устойчивость умеренная"
            else:
                reliability = "статистическая устойчивость высокая"
            
            if vol_z > 1.5:
                vol_note = "Высокая волатильность повышает риск резких контртрендовых движений."
            else:
                vol_note = ""
            
            interp = f"  Сигнал {signal_type}, {reliability}."
            if vol_note:
                interp += f" {vol_note}"
            
            lines.append(interp)
            lines.append("")
    
    # ══════════════════════════════════════════════════════
    # 4. LP POLICY - Keep as is (good)
    # ══════════════════════════════════════════════════════
    if lp_policy:
        risk_lp = lp_policy.risk_lp
        risk_dir = lp_policy.risk_directional
        quadrant = lp_policy.risk_quadrant.value
        fv = lp_policy.fee_variance_ratio
        max_exp = int(lp_policy.max_exposure * 100)
        hedge = lp_policy.hedge_recommended
        range_width = lp_policy.range_width
        
        # Simple quadrant description
        quadrant_desc = {
            "Q1": "🟢 LP: Ideal conditions",
            "Q2": "🔵 LP: Good, but hedge needed",
            "Q3": "🟡 LP: Spot preferred",
            "Q4": "🔴 LP: Minimize exposure",
        }
        lines.append(quadrant_desc.get(quadrant, f"LP: {quadrant}"))
        
        # Key metrics
        lines.append(f"  Exposure: {max_exp}% | Range: {range_width}")
        
        # Fee vs IL ratio
        if fv >= 1.5:
            lines.append(f"  Fees vs IL: {fv:.1f}x ✓")
        elif fv >= 1.0:
            lines.append(f"  Fees vs IL: {fv:.1f}x (marginal)")
        else:
            lines.append(f"  Fees vs IL: {fv:.1f}x (IL превышает)")
        
        if hedge:
            lines.append(f"  Hedge: REQUIRED")
        
        # LP comment
        lp_comment = _get_lp_comment(quadrant, risk_lp, risk_dir, max_exp, max_exp)
        lines.append(f"  → {lp_comment}")
        
        lines.append("")
    
    # ══════════════════════════════════════════════════════
    # 5. FLAGS - Fully restored
    # ══════════════════════════════════════════════════════
    display_flags = []
    
    if tail_active:
        display_flags.append("Tail risk (экстремальная волатильность)")
    
    if struct_break:
        display_flags.append("Structure break (слом структуры)")
    
    # Data quality
    data_quality = meta.get("data_completeness", 1.0)
    failed_sources = meta.get("failed_sources", [])
    
    if failed_sources:
        display_flags.append(f"Нет данных: {', '.join(failed_sources)}")
    elif data_quality < 0.85:
        display_flags.append("Partial data — проверь источники")
    
    if display_flags:
        lines.append("FLAGS")
        for f in display_flags:
            lines.append(f"  • {f}")
        lines.append("")
    
    # ══════════════════════════════════════════════════════
    # FOOTER
    # ══════════════════════════════════════════════════════
    lines.append("v3.6")
    
    return "\n".join(lines)


def _generate_analytical_comment(
    regime: str,
    prob_bear: float,
    prob_trans: float,
    prob_bull: float,
    conf_pct: int,
    dir_value: float,
    tail_active: bool,
    struct_break: bool,
    vol_z: float
) -> str:
    """
    Generate analytical comment without emotional language.
    
    Requirements:
    - No emotional words (паника, дно, страх)
    - No reversal predictions
    - Reflect regime conflict
    - Highlight low confidence
    - Note probability of sharp moves
    - Neutral, risk-oriented tone
    - Max 2-3 sentences
    """
    
    parts = []
    
    # Volatility state
    if vol_z > 2.0 or tail_active:
        vol_state = "Экстремальная волатильность"
    elif vol_z > 1.5:
        vol_state = "Повышенная волатильность"
    else:
        vol_state = None
    
    # Structure state
    struct_state = "слом структуры" if struct_break else None
    
    # Build first part
    first_part_items = [x for x in [vol_state, struct_state] if x]
    if first_part_items:
        first_part = " и ".join(first_part_items).capitalize()
    else:
        first_part = None
    
    # Regime conflict analysis
    max_prob = max(prob_bear, prob_trans, prob_bull)
    second_prob = sorted([prob_bear, prob_trans, prob_bull])[-2]
    
    if abs(prob_bear - prob_trans) < 0.15 and prob_bear > 0.3 and prob_trans > 0.3:
        regime_conflict = f"Конфликт TRANSITION ({int(prob_trans*100)}%) и BEAR ({int(prob_bear*100)}%) указывает на нестабильную фазу перераспределения риска."
    elif prob_trans > prob_bear and prob_trans > 0.4:
        regime_conflict = f"Доминирование переходного режима ({int(prob_trans*100)}%) при медвежьем уклоне."
    elif prob_bear > 0.5:
        regime_conflict = f"Выраженный медвежий режим ({int(prob_bear*100)}%)."
    elif prob_bull > 0.5:
        regime_conflict = f"Выраженный бычий режим ({int(prob_bull*100)}%)."
    else:
        regime_conflict = "Смешанные сигналы без выраженного доминирования."
    
    # Confidence impact
    if conf_pct < 25:
        conf_impact = f"Низкая уверенность модели ({conf_pct}%) повышает вероятность резких и разнонаправленных импульсов без устойчивого трендового подтверждения."
    elif conf_pct < 40:
        conf_impact = f"Умеренно низкая уверенность ({conf_pct}%) снижает надёжность текущего режима."
    else:
        conf_impact = None
    
    # Combine
    if first_part:
        parts.append(first_part + " " + regime_conflict.lower() if regime_conflict[0].isupper() else first_part + ".")
        if conf_impact:
            parts.append(conf_impact)
    else:
        parts.append(regime_conflict)
        if conf_impact:
            parts.append(conf_impact)
    
    return " ".join(parts)


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
            return "Сигнал ниже порога — без действий"
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
        return "LP профитабелен, но высокий направленный риск — нужен хедж"
    
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
