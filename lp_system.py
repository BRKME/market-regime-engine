"""
LP Intelligence System - Unified Runner with History
Version: 2.0.0

Объединяет:
1. LP Monitor - мониторинг позиций
2. LP Opportunities - поиск лучших пулов  
3. LP Advisor - AI рекомендации
4. History - хранение и аналитика TVL

Расписание: 7:00 и 19:00 MSK (04:00 и 16:00 UTC)
"""

import json
import logging
import os
import sys
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

import requests

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

HISTORY_FILE = "state/lp_history.json"
MAX_HISTORY_DAYS = 90  # Keep 90 days of history

# ═══════════════════════════════════════════════════════════════════════════════
# HISTORY MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class DailySnapshot:
    """Daily portfolio snapshot"""
    date: str  # YYYY-MM-DD
    timestamp: str  # ISO format
    tvl: float
    fees: float  # Current uncollected fees
    fees_cumulative: float  # All fees earned ever (doesn't reset on harvest)
    positions_count: int
    positions_in_range: int
    by_wallet: Dict[str, float]  # wallet_name -> tvl
    by_wallet_fees: Dict[str, float]  # wallet_name -> fees


def load_history() -> List[dict]:
    """Load history from file"""
    if not os.path.exists(HISTORY_FILE):
        return []
    
    try:
        with open(HISTORY_FILE, 'r') as f:
            data = json.load(f)
            return data.get("snapshots", [])
    except Exception as e:
        logger.warning(f"Error loading history: {e}")
        return []


def save_history(snapshots: List[dict]):
    """Save history to file"""
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    
    # Keep only last MAX_HISTORY_DAYS
    cutoff_date = (datetime.now(timezone.utc) - timedelta(days=MAX_HISTORY_DAYS)).strftime("%Y-%m-%d")
    snapshots = [s for s in snapshots if s.get("date", "") >= cutoff_date]
    
    with open(HISTORY_FILE, 'w') as f:
        json.dump({"snapshots": snapshots, "updated": datetime.now(timezone.utc).isoformat()}, f, indent=2)
    
    logger.info(f"History saved: {len(snapshots)} snapshots")


def add_snapshot(tvl: float, fees: float, positions_count: int, in_range: int, 
                 by_wallet: Dict[str, float], by_wallet_fees: Dict[str, float]):
    """Add today's snapshot to history with cumulative fees tracking"""
    snapshots = load_history()
    
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    now = datetime.now(timezone.utc).isoformat()
    
    # Calculate cumulative fees
    # Logic: if current fees < previous fees, user did harvest
    # We add the positive delta to cumulative, never subtract
    fees_cumulative = fees  # default for first snapshot
    
    if snapshots:
        # Find the most recent snapshot (any date)
        prev_snapshot = snapshots[-1]
        prev_fees = prev_snapshot.get("fees", 0)
        prev_cumulative = prev_snapshot.get("fees_cumulative", prev_fees)
        
        if fees >= prev_fees:
            # Fees grew normally - add the delta
            fees_cumulative = prev_cumulative + (fees - prev_fees)
        else:
            # Fees dropped = harvest happened
            # The user collected prev_fees, now accumulating new fees
            # cumulative = prev_cumulative + (what was harvested is already in cumulative via prev deltas)
            # We just add current fees as new accumulation since harvest
            fees_cumulative = prev_cumulative + fees
            logger.info(f"Detected harvest: fees dropped from ${prev_fees:.2f} to ${fees:.2f}")
    
    # Check if today's snapshot exists
    existing_idx = None
    for i, s in enumerate(snapshots):
        if s.get("date") == today:
            existing_idx = i
            # Keep the higher cumulative (in case of multiple runs per day)
            prev_today_cumulative = s.get("fees_cumulative", 0)
            fees_cumulative = max(fees_cumulative, prev_today_cumulative)
            break
    
    snapshot = {
        "date": today,
        "timestamp": now,
        "tvl": tvl,
        "fees": fees,
        "fees_cumulative": fees_cumulative,
        "positions_count": positions_count,
        "positions_in_range": in_range,
        "by_wallet": by_wallet,
        "by_wallet_fees": by_wallet_fees,
    }
    
    if existing_idx is not None:
        # Update existing
        snapshots[existing_idx] = snapshot
    else:
        # Add new
        snapshots.append(snapshot)
    
    # Sort by date
    snapshots.sort(key=lambda x: x.get("date", ""))
    
    save_history(snapshots)
    
    logger.info(f"Snapshot saved: TVL=${tvl:.0f}, fees=${fees:.2f}, cumulative=${fees_cumulative:.2f}")
    return snapshot


def get_tvl_change(snapshots: List[dict], current_tvl: float, days: int) -> Tuple[Optional[float], Optional[float]]:
    """Get TVL change over N days. Returns (absolute_change, percent_change)"""
    if len(snapshots) < 2:
        return None, None
    
    target_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    
    # Find closest snapshot to target date
    past_snapshot = None
    for s in snapshots:
        if s.get("date", "") <= target_date:
            past_snapshot = s
    
    if not past_snapshot:
        return None, None
    
    past_tvl = past_snapshot.get("tvl", 0)
    if past_tvl == 0:
        return None, None
    
    abs_change = current_tvl - past_tvl
    pct_change = (abs_change / past_tvl) * 100
    
    return abs_change, pct_change


def calculate_portfolio_apy(snapshots: List[dict], current_tvl: float) -> Optional[float]:
    """Calculate portfolio APY based on cumulative fees earned"""
    if len(snapshots) < 2:
        return None
    
    # Get current snapshot (last one)
    current = snapshots[-1]
    current_cumulative = current.get("fees_cumulative", 0)
    
    # Try to find snapshot from ~7 days ago, then 3 days, then 1 day
    for days in [7, 3, 1]:
        target_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
        
        past_snapshot = None
        for s in snapshots:
            if s.get("date", "") <= target_date:
                past_snapshot = s
        
        if past_snapshot and past_snapshot.get("date") != current.get("date"):
            past_cumulative = past_snapshot.get("fees_cumulative", 0)
            past_tvl = past_snapshot.get("tvl", 0)
            
            # Calculate fees earned in this period
            fees_earned = current_cumulative - past_cumulative
            
            if fees_earned > 0 and past_tvl > 0:
                # Average TVL over period
                avg_tvl = (current_tvl + past_tvl) / 2
                
                # Calculate actual days between snapshots
                from datetime import datetime as dt
                current_date = dt.strptime(current.get("date"), "%Y-%m-%d")
                past_date = dt.strptime(past_snapshot.get("date"), "%Y-%m-%d")
                actual_days = (current_date - past_date).days
                
                if actual_days > 0:
                    # Annualize
                    apy = (fees_earned / avg_tvl) * (365 / actual_days) * 100
                    logger.info(f"APY calc: ${fees_earned:.2f} earned over {actual_days}d, avg TVL ${avg_tvl:.0f} = {apy:.1f}%")
                    return apy
    
    return None


def format_change(abs_change: Optional[float], pct_change: Optional[float]) -> str:
    """Format change for display"""
    if abs_change is None or pct_change is None:
        return "нет данных"
    
    # Don't show +$0 changes (means no historical data)
    if abs_change == 0 and pct_change == 0:
        return "нет данных"
    
    sign = "+" if abs_change >= 0 else ""
    return f"{sign}${abs_change:,.0f} ({sign}{pct_change:.1f}%)"


# ═══════════════════════════════════════════════════════════════════════════════
# UNIFIED RUNNER
# ═══════════════════════════════════════════════════════════════════════════════

def run_monitor() -> Optional[dict]:
    """Run LP Monitor and return summary"""
    try:
        from lp_monitor import LPMonitor
        
        monitor = LPMonitor()
        
        if not monitor.web3_clients:
            logger.warning("No chains connected")
            return None
        
        positions = monitor.scan_all_positions()
        
        if not positions:
            logger.warning("No positions found")
            return None
        
        summary = monitor.get_summary()
        monitor.save_state()
        
        return {
            "positions": [asdict(p) for p in monitor.positions],
            "summary": asdict(summary),
            "tvl": summary.total_balance_usd,
            "fees": summary.total_uncollected_fees_usd,
            "count": summary.total_positions,
            "in_range": summary.positions_in_range,
            "by_wallet": summary.by_wallet,
        }
        
    except Exception as e:
        logger.error(f"Monitor error: {e}")
        return None


def run_opportunities() -> Optional[dict]:
    """Run LP Opportunities Scanner and return top pools"""
    try:
        from lp_opportunities import LPOpportunitiesScanner
        from lp_config import REGIME_IL_PENALTY
        
        scanner = LPOpportunitiesScanner()
        opportunities = scanner.scan()
        
        if not opportunities:
            logger.warning("No opportunities found")
            return None
        
        scanner.save_state()
        rankings = scanner.get_rankings()
        
        # LP recommendation based on regime (Russian)
        regime = scanner.regime
        regime_penalty = REGIME_IL_PENALTY.get(regime, 0.4)
        
        lp_recommendations_ru = {
            "HARVEST": "Идеальные условия для LP. Используйте узкие диапазоны.",
            "RANGE": "Хорошие условия. Стандартные диапазоны работают.",
            "MEAN_REVERT": "Умеренные условия. Следите за границами.",
            "VOLATILE_CHOP": "Волатильность. Используйте широкие диапазоны.",
            "TRANSITION": "Переходный период. Осторожность.",
            "BULL": "Тренд вверх. Риск IL на short позициях.",
            "BEAR": "Тренд вниз. Высокий риск IL. Предпочитайте stable пары.",
            "TRENDING": "Сильный тренд. Минимизируйте LP экспозицию.",
            "BREAKOUT": "Пробой. Возможен сильный IL.",
            "CHURN": "Хаос. Лучше выйти из рисковых позиций.",
            "AVOID": "Избегайте LP. Высокий риск.",
        }
        
        return {
            "regime": regime,
            "regime_penalty": regime_penalty,
            "lp_recommendation": lp_recommendations_ru.get(regime, "Неизвестный режим."),
            "top_pools": [
                {
                    "symbol": o.symbol,
                    "chain": o.chain,
                    "apy": o.apy_total,
                    "risk_adj_apy": o.risk_adjusted_apy,
                    "tvl": o.tvl_usd,
                    "il_risk": o.il_risk_label,
                }
                for o in rankings["by_risk_adjusted"][:10]  # Top 10
            ]
        }
        
    except Exception as e:
        logger.error(f"Opportunities error: {e}")
        return None


def run_advisor(monitor_data: dict, opportunities_data: Optional[dict], history: List[dict]) -> Optional[str]:
    """Run LP Advisor with proper APY and regime analysis"""
    
    # Check for OpenAI key first
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        logger.warning("OPENAI_API_KEY not set - skipping AI summary")
        return None
    
    try:
        # === BUILD ANALYSIS CONTEXT ===
        
        tvl = monitor_data.get("tvl", 0)
        fees = monitor_data.get("fees", 0)
        positions = monitor_data.get("positions", [])
        
        # Regime info
        regime = opportunities_data.get("regime", "UNKNOWN") if opportunities_data else "UNKNOWN"
        regime_penalty = opportunities_data.get("regime_penalty", 0.4) if opportunities_data else 0.4
        
        # Portfolio APY (calculated from history)
        portfolio_apy = opportunities_data.get("portfolio_apy") if opportunities_data else None
        
        # Benchmark - average of top 5 pools
        benchmark_apy = None
        top_pools = []
        if opportunities_data and opportunities_data.get("top_pools"):
            top_pools = opportunities_data["top_pools"][:5]
            if top_pools:
                benchmark_apy = sum(p.get("risk_adj_apy", 0) for p in top_pools) / len(top_pools)
        
        # === ANALYZE EACH POSITION FOR REGIME FIT ===
        
        # Token type classification
        def get_token_type(symbol: str) -> str:
            s = symbol.upper()
            stables = {"USDC", "USDT", "DAI", "BUSD", "FRAX", "FDUSD"}
            majors = {"WETH", "ETH", "WBTC", "BTC", "BTCB", "WBNB", "BNB"}
            if s in stables:
                return "stable"
            if s in majors:
                return "major"
            return "alt"
        
        # Regime suitability
        def get_regime_fit(t0_type: str, t1_type: str, regime: str) -> str:
            """Evaluate if pair fits current regime"""
            pair_type = f"{t0_type}/{t1_type}"
            
            # Stable/stable - always good
            if t0_type == "stable" and t1_type == "stable":
                return "отлично"
            
            # Stable/major - good in most regimes
            if (t0_type == "stable" and t1_type == "major") or (t0_type == "major" and t1_type == "stable"):
                if regime in ["BEAR", "TRENDING", "CHURN"]:
                    return "умеренно (риск IL)"
                return "хорошо"
            
            # Major/major - moderate IL risk
            if t0_type == "major" and t1_type == "major":
                if regime in ["BEAR", "TRENDING"]:
                    return "риск IL при тренде"
                return "хорошо"
            
            # Anything with alt - high risk
            if t0_type == "alt" or t1_type == "alt":
                if regime in ["BEAR", "TRENDING", "CHURN"]:
                    return "высокий риск IL!"
                return "умеренный риск"
            
            return "неизвестно"
        
        # Analyze positions
        position_analyses = []
        for p in positions:
            t0 = p.get("token0_symbol", "")
            t1 = p.get("token1_symbol", "")
            balance = p.get("balance_usd", 0)
            in_range = p.get("in_range", False)
            wallet = p.get("wallet_name", "")
            
            t0_type = get_token_type(t0)
            t1_type = get_token_type(t1)
            regime_fit = get_regime_fit(t0_type, t1_type, regime)
            
            position_analyses.append({
                "wallet": wallet,
                "pair": f"{t0}-{t1}",
                "balance": balance,
                "in_range": in_range,
                "type": f"{t0_type}/{t1_type}",
                "regime_fit": regime_fit,
            })
        
        # Group by wallet for summary
        from collections import defaultdict
        by_wallet = defaultdict(list)
        for pa in position_analyses:
            by_wallet[pa["wallet"]].append(pa)
        
        # === BUILD AI PROMPT ===
        
        # APY comparison section
        apy_section = ""
        if portfolio_apy and benchmark_apy:
            diff = portfolio_apy - benchmark_apy
            if diff > 5:
                apy_section = f"Ваш портфель: {portfolio_apy:.1f}% APY, бенчмарк: {benchmark_apy:.1f}%. Вы обгоняете рынок на {diff:.1f}%!"
            elif diff > -5:
                apy_section = f"Ваш портфель: {portfolio_apy:.1f}% APY, бенчмарк: {benchmark_apy:.1f}%. Примерно на уровне рынка."
            else:
                apy_section = f"Ваш портфель: {portfolio_apy:.1f}% APY, бенчмарк: {benchmark_apy:.1f}%. Отстаёте на {abs(diff):.1f}%."
        elif portfolio_apy:
            apy_section = f"Ваш портфель: {portfolio_apy:.1f}% APY (недостаточно данных для сравнения с бенчмарком)."
        else:
            apy_section = "APY портфеля: недостаточно исторических данных (нужно минимум 2 дня)."
        
        # Regime section
        regime_descriptions = {
            "BULL": "бычий тренд - рынок растёт",
            "BEAR": "медвежий тренд - рынок падает",
            "RANGE": "боковик - рынок консолидируется",
            "TRENDING": "сильный тренд",
            "VOLATILE_CHOP": "высокая волатильность без направления",
            "TRANSITION": "переходный период, неопределённость",
            "HARVEST": "идеально для LP",
            "CHURN": "хаотичное движение",
        }
        regime_desc = regime_descriptions.get(regime, regime)
        
        # Position details by wallet
        wallet_details = []
        for wallet_name in sorted(by_wallet.keys()):
            positions_info = []
            for pa in by_wallet[wallet_name]:
                status = "✓" if pa["in_range"] else "✗"
                positions_info.append(f"{pa['pair']} (${pa['balance']:.0f}, {pa['type']}, {pa['regime_fit']})")
            wallet_details.append(f"{wallet_name}: {'; '.join(positions_info)}")
        
        prompt = f"""Ты LP-аналитик. Оцени портфель Uniswap V3 LP позиций.

=== ДОХОДНОСТЬ ===
{apy_section}

Топ пулы на рынке для сравнения:
{chr(10).join([f"- {p['symbol']}: {p['risk_adj_apy']:.1f}% APY" for p in top_pools[:3]]) if top_pools else "Нет данных"}

=== ФАЗА РЫНКА ===
Текущий режим: {regime} ({regime_desc})
Штраф IL: {regime_penalty:.0%}

Что это значит для LP:
- BEAR/TRENDING: активы падают/растут сильно → высокий Impermanent Loss
- RANGE/HARVEST: боковик → идеально для LP, IL минимален
- При текущем режиме {regime} рекомендуется: {'stable пары или широкие диапазоны' if regime in ['BEAR', 'TRENDING', 'CHURN'] else 'можно использовать стандартные стратегии'}

=== ПОЗИЦИИ ПО КОШЕЛЬКАМ ===
{chr(10).join(wallet_details)}

=== ЗАДАНИЕ ===
Дай краткую оценку (3-4 предложения):
1. Сравнение доходности портфеля с бенчмарком
2. Насколько текущие пары подходят под режим {regime}
3. Конкретные рекомендации (если нужны) или "портфель оптимален"

НЕ ПАНИКУЙ при просадках - это часть рынка. Фокус на структуре портфеля, а не на краткосрочных движениях.
Ответ на русском, максимум 500 символов."""

        # === CALL OPENAI ===
        
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {openai_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            "messages": [
                {
                    "role": "system",
                    "content": "Ты профессиональный DeFi LP аналитик. Даёшь практичные оценки без паники. Понимаешь Impermanent Loss и влияние рыночных режимов на LP позиции."
                },
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 350,
            "temperature": 0.7
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            ai_text = data["choices"][0]["message"]["content"]
            logger.info(f"AI response: {ai_text[:100]}...")
            return ai_text
        else:
            logger.error(f"OpenAI error: {response.status_code} - {response.text[:200]}")
            return None
            
    except Exception as e:
        logger.error(f"Advisor error: {e}")
        import traceback
        traceback.print_exc()
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# TELEGRAM REPORT
# ═══════════════════════════════════════════════════════════════════════════════

def format_unified_report(
    monitor_data: dict,
    opportunities_data: Optional[dict],
    ai_summary: Optional[str],
    history: List[dict]
) -> str:
    """Format unified Telegram report"""
    
    now = datetime.now(timezone.utc)
    msk_time = now + timedelta(hours=3)
    
    lines = [
        "#LP #Uniswap",
        f"📊 LP Report | {msk_time.strftime('%d.%m %H:%M')} MSK",
        "",
    ]
    
    # Summary
    tvl = monitor_data.get("tvl", 0)
    fees = monitor_data.get("fees", 0)
    count = monitor_data.get("count", 0)
    in_range = monitor_data.get("in_range", 0)
    
    lines.append(f"TVL: ${tvl:,.0f}")
    lines.append(f"Fees: ${fees:,.2f}")
    lines.append(f"In Range: {in_range}/{count}")
    
    # Portfolio APY if available
    portfolio_apy = opportunities_data.get("portfolio_apy") if opportunities_data else None
    benchmark_apy = None
    if opportunities_data and opportunities_data.get("top_pools"):
        top_5 = opportunities_data["top_pools"][:5]
        if top_5:
            benchmark_apy = sum(p.get("risk_adj_apy", 0) for p in top_5) / len(top_5)
    
    if portfolio_apy:
        apy_line = f"APY: {portfolio_apy:.1f}%"
        if benchmark_apy:
            diff = portfolio_apy - benchmark_apy
            if diff > 0:
                apy_line += f" (бенчмарк: {benchmark_apy:.1f}%, +{diff:.1f}%)"
            else:
                apy_line += f" (бенчмарк: {benchmark_apy:.1f}%, {diff:.1f}%)"
        lines.append(apy_line)
    
    # TVL Changes - only show if we have real data
    if len(history) >= 2:
        lines.append("")
        lines.append("Changes:")
        
        abs_1d, pct_1d = get_tvl_change(history, tvl, 1)
        abs_7d, pct_7d = get_tvl_change(history, tvl, 7)
        abs_30d, pct_30d = get_tvl_change(history, tvl, 30)
        
        lines.append(f"  24h: {format_change(abs_1d, pct_1d)}")
        lines.append(f"  7d:  {format_change(abs_7d, pct_7d)}")
        lines.append(f"  30d: {format_change(abs_30d, pct_30d)}")
    
    # Positions by wallet
    lines.append("")
    
    positions = monitor_data.get("positions", [])
    
    # Group positions by wallet
    from collections import defaultdict
    wallet_positions = defaultdict(list)
    for p in positions:
        wallet_positions[p.get("wallet_name", "")].append(p)
    
    for wallet_name in sorted(wallet_positions.keys()):
        w_positions = sorted(wallet_positions[wallet_name], key=lambda x: x.get("balance_usd", 0), reverse=True)
        w_total = sum(p.get("balance_usd", 0) for p in w_positions)
        w_fees = sum(p.get("uncollected_fees_usd", 0) for p in w_positions)
        
        lines.append(f"{wallet_name}: ${w_total:,.0f} (fees: ${w_fees:.2f})")
        
        for p in w_positions:
            # Emoji for in-range status
            status = "🟢" if p.get("in_range", False) else "🔴"
            symbol = f"{p.get('token0_symbol', '')}-{p.get('token1_symbol', '')}"
            balance = p.get("balance_usd", 0)
            lines.append(f"  {status} {symbol} ${balance:,.0f}")
            
            if not p.get("in_range", False):
                if p.get("current_tick", 0) < p.get("tick_lower", 0):
                    lines.append(f"    Below range {abs(p.get('distance_to_lower_pct', 0)):.1f}%")
                else:
                    lines.append(f"    Above range {abs(p.get('distance_to_upper_pct', 0)):.1f}%")
        
        lines.append("")
    
    # Top opportunities - expanded to 10, split by chain
    if opportunities_data and opportunities_data.get("top_pools"):
        arb_pools = [p for p in opportunities_data["top_pools"] if p.get("chain", "").lower() == "arbitrum"]
        bsc_pools = [p for p in opportunities_data["top_pools"] if p.get("chain", "").lower() == "bsc"]
        
        if arb_pools:
            lines.append("Top ARB:")
            for pool in arb_pools[:5]:
                lines.append(f"  {pool['symbol']}: {pool['risk_adj_apy']:.1f}%")
        
        if bsc_pools:
            lines.append("Top BSC:")
            for pool in bsc_pools[:5]:
                lines.append(f"  {pool['symbol']}: {pool['risk_adj_apy']:.1f}%")
        
        lines.append("")
    
    # Regime with LP policy details (Russian)
    if opportunities_data:
        regime = opportunities_data.get("regime", "UNKNOWN")
        regime_penalty = opportunities_data.get("regime_penalty", 0)
        lp_recommendation = opportunities_data.get("lp_recommendation", "")
        
        lines.append(f"Режим: {regime}")
        if regime_penalty:
            # IL Penalty - это штраф за риск Impermanent Loss при текущем режиме рынка
            lines.append(f"  Штраф IL: {regime_penalty:.0%} (коррекция APY за риск непостоянных потерь)")
        if lp_recommendation:
            lines.append(f"  {lp_recommendation}")
        lines.append("")
    
    # AI Summary
    if ai_summary:
        lines.append("AI:")
        lines.append(ai_summary)
    else:
        lines.append("AI: (нет ключа OpenAI)")
    
    return "\n".join(lines)


def send_telegram(message: str) -> bool:
    """Send message to Telegram"""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        logger.warning("Telegram credentials not set")
        return False
    
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        response = requests.post(url, data={"chat_id": chat_id, "text": message}, timeout=10)
        
        if response.status_code == 200:
            logger.info("Telegram sent")
            return True
        else:
            logger.error(f"Telegram error: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"Telegram exception: {e}")
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """Main entry point"""
    logger.info("=" * 60)
    logger.info("LP INTELLIGENCE SYSTEM v2.0.0")
    logger.info("=" * 60)
    
    # Load history
    history = load_history()
    logger.info(f"Loaded {len(history)} historical snapshots")
    
    # Stage 1: Monitor
    logger.info("\n--- STAGE 1: MONITOR ---")
    monitor_data = run_monitor()
    
    if not monitor_data:
        logger.error("Monitor failed - cannot continue")
        return 1
    
    logger.info(f"TVL: ${monitor_data['tvl']:,.0f}")
    logger.info(f"Positions: {monitor_data['count']}")
    
    # Save snapshot to history
    by_wallet_tvl = {k: v.get("balance_usd", 0) for k, v in monitor_data.get("by_wallet", {}).items()}
    by_wallet_fees = {k: v.get("fees_usd", 0) for k, v in monitor_data.get("by_wallet", {}).items()}
    add_snapshot(
        tvl=monitor_data["tvl"],
        fees=monitor_data["fees"],
        positions_count=monitor_data["count"],
        in_range=monitor_data["in_range"],
        by_wallet=by_wallet_tvl,
        by_wallet_fees=by_wallet_fees,
    )
    
    # Reload history after adding snapshot
    history = load_history()
    
    # Calculate portfolio APY (uses cumulative fees from history)
    portfolio_apy = calculate_portfolio_apy(history, monitor_data["tvl"])
    if portfolio_apy:
        logger.info(f"Portfolio APY: {portfolio_apy:.1f}%")
    
    # Stage 2: Opportunities
    logger.info("\n--- STAGE 2: OPPORTUNITIES ---")
    opportunities_data = run_opportunities()
    
    if opportunities_data:
        logger.info(f"Regime: {opportunities_data.get('regime')}")
        logger.info(f"Top pools: {len(opportunities_data.get('top_pools', []))}")
        # Add portfolio APY to opportunities data for comparison
        opportunities_data["portfolio_apy"] = portfolio_apy
    else:
        logger.warning("Opportunities scan failed")
    
    # Stage 3: Advisor
    logger.info("\n--- STAGE 3: ADVISOR ---")
    ai_summary = None
    
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        logger.warning("OPENAI_API_KEY not set - AI summary disabled")
    elif monitor_data:
        ai_summary = run_advisor(monitor_data, opportunities_data, history)
        if ai_summary:
            logger.info(f"AI summary: {ai_summary[:100]}...")
        else:
            logger.warning("AI summary failed")
    
    # Generate unified report
    logger.info("\n--- GENERATING REPORT ---")
    report = format_unified_report(monitor_data, opportunities_data, ai_summary, history)
    
    print("\n" + "=" * 60)
    print(report)
    print("=" * 60)
    
    # Send to Telegram
    send_telegram(report)
    
    logger.info("\nDone!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
