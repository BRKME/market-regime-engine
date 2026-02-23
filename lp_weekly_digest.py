"""
LP Weekly Digest v1.0
Еженедельный отчёт по LP позициям.

Запуск: каждое воскресенье
Содержание:
- Изменение TVL за неделю
- Заработанные fees
- APY портфеля
- Лучшие/худшие позиции
- Сравнение с бенчмарком
"""

import json
import logging
import os
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
POSITIONS_FILE = "state/lp_positions.json"
DIGEST_FILE = "state/lp_weekly_digest.json"


# ═══════════════════════════════════════════════════════════════════════════════
# DATA LOADING
# ═══════════════════════════════════════════════════════════════════════════════

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


def load_positions() -> List[dict]:
    """Load current positions"""
    if not os.path.exists(POSITIONS_FILE):
        return []
    
    try:
        with open(POSITIONS_FILE, 'r') as f:
            data = json.load(f)
            return data.get("positions", [])
    except Exception as e:
        logger.warning(f"Error loading positions: {e}")
        return []


# ═══════════════════════════════════════════════════════════════════════════════
# CALCULATIONS
# ═══════════════════════════════════════════════════════════════════════════════

def get_week_range() -> Tuple[str, str]:
    """Get date range for the past week"""
    today = datetime.now(timezone.utc)
    week_ago = today - timedelta(days=7)
    return week_ago.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")


def get_snapshot_for_date(snapshots: List[dict], target_date: str) -> Optional[dict]:
    """Find snapshot closest to target date"""
    closest = None
    for s in snapshots:
        if s.get("date", "") <= target_date:
            closest = s
    return closest


def calculate_weekly_stats(snapshots: List[dict]) -> dict:
    """Calculate weekly statistics"""
    
    if len(snapshots) < 2:
        return {
            "has_data": False,
            "reason": "Недостаточно данных (нужно минимум 2 дня)"
        }
    
    week_start, week_end = get_week_range()
    
    # Get snapshots
    start_snapshot = get_snapshot_for_date(snapshots, week_start)
    end_snapshot = snapshots[-1]  # Latest
    
    if not start_snapshot:
        start_snapshot = snapshots[0]  # Use oldest available
    
    # TVL change
    start_tvl = start_snapshot.get("tvl", 0)
    end_tvl = end_snapshot.get("tvl", 0)
    tvl_change = end_tvl - start_tvl
    tvl_change_pct = (tvl_change / start_tvl * 100) if start_tvl > 0 else 0
    
    # Fees earned (from cumulative)
    start_cumulative = start_snapshot.get("fees_cumulative", start_snapshot.get("fees", 0))
    end_cumulative = end_snapshot.get("fees_cumulative", end_snapshot.get("fees", 0))
    fees_earned = end_cumulative - start_cumulative
    
    # APY calculation
    if fees_earned > 0 and start_tvl > 0:
        days = max(1, len([s for s in snapshots if s.get("date", "") >= start_snapshot.get("date", "")]))
        avg_tvl = (start_tvl + end_tvl) / 2
        apy = (fees_earned / avg_tvl) * (365 / days) * 100
    else:
        apy = None
    
    # Wallet performance
    start_wallets = start_snapshot.get("by_wallet", {})
    end_wallets = end_snapshot.get("by_wallet", {})
    
    wallet_performance = []
    for wallet, end_value in end_wallets.items():
        start_value = start_wallets.get(wallet, end_value)
        change = end_value - start_value
        change_pct = (change / start_value * 100) if start_value > 0 else 0
        wallet_performance.append({
            "wallet": wallet,
            "start_tvl": start_value,
            "end_tvl": end_value,
            "change": change,
            "change_pct": change_pct
        })
    
    # Sort by performance
    wallet_performance.sort(key=lambda x: x["change_pct"], reverse=True)
    
    return {
        "has_data": True,
        "period": {
            "start": start_snapshot.get("date"),
            "end": end_snapshot.get("date"),
            "days": (datetime.strptime(end_snapshot.get("date", "2025-01-01"), "%Y-%m-%d") - 
                    datetime.strptime(start_snapshot.get("date", "2025-01-01"), "%Y-%m-%d")).days
        },
        "tvl": {
            "start": start_tvl,
            "end": end_tvl,
            "change": tvl_change,
            "change_pct": tvl_change_pct
        },
        "fees": {
            "earned": fees_earned,
            "current_uncollected": end_snapshot.get("fees", 0)
        },
        "apy": apy,
        "positions": {
            "count": end_snapshot.get("positions_count", 0),
            "in_range": end_snapshot.get("positions_in_range", 0)
        },
        "wallet_performance": wallet_performance
    }


def analyze_positions(positions: List[dict]) -> dict:
    """Analyze current positions"""
    
    if not positions:
        return {"has_data": False}
    
    # Group by pair
    pairs = {}
    for pos in positions:
        t0 = pos.get("token0_symbol", "")
        t1 = pos.get("token1_symbol", "")
        pair = f"{t0}-{t1}"
        
        if pair not in pairs:
            pairs[pair] = {
                "pair": pair,
                "balance_usd": 0,
                "fees_usd": 0,
                "count": 0,
                "in_range": 0
            }
        
        pairs[pair]["balance_usd"] += pos.get("balance_usd", 0)
        pairs[pair]["fees_usd"] += pos.get("uncollected_fees_usd", 0)
        pairs[pair]["count"] += 1
        if pos.get("in_range", False):
            pairs[pair]["in_range"] += 1
    
    # Calculate fee rate for each pair
    for pair_data in pairs.values():
        if pair_data["balance_usd"] > 0:
            pair_data["fee_rate"] = pair_data["fees_usd"] / pair_data["balance_usd"] * 100
        else:
            pair_data["fee_rate"] = 0
    
    # Sort by TVL
    pairs_list = sorted(pairs.values(), key=lambda x: x["balance_usd"], reverse=True)
    
    # Best/worst by fee rate
    pairs_by_fees = sorted(pairs.values(), key=lambda x: x["fee_rate"], reverse=True)
    
    return {
        "has_data": True,
        "pairs": pairs_list,
        "best_performers": pairs_by_fees[:3] if len(pairs_by_fees) >= 3 else pairs_by_fees,
        "worst_performers": pairs_by_fees[-3:][::-1] if len(pairs_by_fees) >= 3 else []
    }


# ═══════════════════════════════════════════════════════════════════════════════
# REPORT FORMATTING
# ═══════════════════════════════════════════════════════════════════════════════

def format_weekly_digest(stats: dict, positions_analysis: dict) -> str:
    """Format weekly digest for Telegram"""
    
    now = datetime.now(timezone.utc)
    msk_time = now + timedelta(hours=3)
    
    lines = [
        "#LP #Weekly",
        f"📅 Недельный дайджест | {msk_time.strftime('%d.%m.%Y')}",
        "",
    ]
    
    if not stats.get("has_data"):
        lines.append(f"⚠️ {stats.get('reason', 'Нет данных')}")
        return "\n".join(lines)
    
    # Period
    period = stats.get("period", {})
    lines.append(f"Период: {period.get('start')} — {period.get('end')} ({period.get('days')}д)")
    lines.append("")
    
    # TVL
    tvl = stats.get("tvl", {})
    tvl_emoji = "📈" if tvl.get("change", 0) >= 0 else "📉"
    lines.append(f"{tvl_emoji} TVL: ${tvl.get('end', 0):,.0f}")
    
    change = tvl.get("change", 0)
    change_pct = tvl.get("change_pct", 0)
    sign = "+" if change >= 0 else ""
    lines.append(f"  Изменение: {sign}${change:,.0f} ({sign}{change_pct:.1f}%)")
    
    # Fees
    fees = stats.get("fees", {})
    lines.append("")
    lines.append(f"💰 Fees заработано: ${fees.get('earned', 0):,.2f}")
    lines.append(f"  Не собрано: ${fees.get('current_uncollected', 0):,.2f}")
    
    # APY
    apy = stats.get("apy")
    if apy:
        lines.append("")
        lines.append(f"📊 APY портфеля: {apy:.1f}%")
    
    # Positions
    pos = stats.get("positions", {})
    lines.append("")
    lines.append(f"Позиций: {pos.get('count', 0)}, в диапазоне: {pos.get('in_range', 0)}")
    
    # Wallet performance
    wallet_perf = stats.get("wallet_performance", [])
    if wallet_perf:
        lines.append("")
        lines.append("👛 По кошелькам:")
        for wp in wallet_perf:
            sign = "+" if wp["change"] >= 0 else ""
            emoji = "🟢" if wp["change"] >= 0 else "🔴"
            lines.append(f"  {emoji} {wp['wallet']}: ${wp['end_tvl']:,.0f} ({sign}{wp['change_pct']:.1f}%)")
    
    # Best/worst pairs
    if positions_analysis.get("has_data"):
        best = positions_analysis.get("best_performers", [])
        if best:
            lines.append("")
            lines.append("⭐ Лучшие пары (по fee rate):")
            for p in best[:3]:
                lines.append(f"  {p['pair']}: {p['fee_rate']:.2f}% (${p['balance_usd']:,.0f})")
        
        worst = positions_analysis.get("worst_performers", [])
        if worst and len(positions_analysis.get("pairs", [])) > 3:
            lines.append("")
            lines.append("⚠️ Худшие пары:")
            for p in worst[:2]:
                lines.append(f"  {p['pair']}: {p['fee_rate']:.2f}% (${p['balance_usd']:,.0f})")
    
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# TELEGRAM
# ═══════════════════════════════════════════════════════════════════════════════

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

def save_digest(stats: dict, positions_analysis: dict):
    """Save digest to file"""
    os.makedirs(os.path.dirname(DIGEST_FILE), exist_ok=True)
    
    data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "stats": stats,
        "positions_analysis": positions_analysis
    }
    
    with open(DIGEST_FILE, 'w') as f:
        json.dump(data, f, indent=2)
    
    logger.info(f"Digest saved to {DIGEST_FILE}")


def main():
    """Main entry point"""
    logger.info("=" * 60)
    logger.info("LP WEEKLY DIGEST v1.0")
    logger.info("=" * 60)
    
    # Load data
    snapshots = load_history()
    logger.info(f"Loaded {len(snapshots)} history snapshots")
    
    positions = load_positions()
    logger.info(f"Loaded {len(positions)} positions")
    
    # Calculate stats
    stats = calculate_weekly_stats(snapshots)
    positions_analysis = analyze_positions(positions)
    
    # Save
    save_digest(stats, positions_analysis)
    
    # Format report
    report = format_weekly_digest(stats, positions_analysis)
    
    print("\n" + "=" * 60)
    print(report)
    print("=" * 60)
    
    # Send to Telegram
    send_telegram(report)
    
    logger.info("\nDone!")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
