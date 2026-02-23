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
    fees: float
    positions_count: int
    positions_in_range: int
    by_wallet: Dict[str, float]  # wallet_name -> tvl


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


def add_snapshot(tvl: float, fees: float, positions_count: int, in_range: int, by_wallet: Dict[str, float]):
    """Add today's snapshot to history"""
    snapshots = load_history()
    
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    now = datetime.now(timezone.utc).isoformat()
    
    # Check if today's snapshot exists
    existing_idx = None
    for i, s in enumerate(snapshots):
        if s.get("date") == today:
            existing_idx = i
            break
    
    snapshot = {
        "date": today,
        "timestamp": now,
        "tvl": tvl,
        "fees": fees,
        "positions_count": positions_count,
        "positions_in_range": in_range,
        "by_wallet": by_wallet,
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
    return snapshot


def get_tvl_change(snapshots: List[dict], current_tvl: float, days: int) -> Tuple[Optional[float], Optional[float]]:
    """Get TVL change over N days. Returns (absolute_change, percent_change)"""
    if not snapshots:
        return None, None
    
    target_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    
    # Find closest snapshot to target date
    past_snapshot = None
    for s in snapshots:
        if s.get("date", "") <= target_date:
            past_snapshot = s
    
    if not past_snapshot:
        # Try to get oldest available
        if snapshots:
            past_snapshot = snapshots[0]
        else:
            return None, None
    
    past_tvl = past_snapshot.get("tvl", 0)
    if past_tvl == 0:
        return None, None
    
    abs_change = current_tvl - past_tvl
    pct_change = (abs_change / past_tvl) * 100
    
    return abs_change, pct_change


def format_change(abs_change: Optional[float], pct_change: Optional[float]) -> str:
    """Format change for display"""
    if abs_change is None or pct_change is None:
        return "n/a"
    
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
        
        # LP recommendation based on regime
        regime = scanner.regime
        regime_penalty = REGIME_IL_PENALTY.get(regime, 0.4)
        
        lp_recommendations = {
            "HARVEST": "Ideal for LP. Use tight ranges.",
            "RANGE": "Good for LP. Standard ranges work.",
            "MEAN_REVERT": "Moderate. Watch range edges.",
            "VOLATILE_CHOP": "Use wide ranges.",
            "TRANSITION": "Caution advised.",
            "BULL": "IL risk on short positions.",
            "BEAR": "High IL risk. Prefer stable pairs.",
            "TRENDING": "Minimize LP exposure.",
            "BREAKOUT": "Possible strong IL.",
            "CHURN": "Exit risky positions.",
            "AVOID": "Avoid LP. High risk.",
        }
        
        return {
            "regime": regime,
            "regime_penalty": regime_penalty,
            "lp_recommendation": lp_recommendations.get(regime, "Unknown regime."),
            "top_pools": [
                {
                    "symbol": o.symbol,
                    "chain": o.chain,
                    "apy": o.apy_total,
                    "risk_adj_apy": o.risk_adjusted_apy,
                    "tvl": o.tvl_usd,
                    "il_risk": o.il_risk_label,
                }
                for o in rankings["by_risk_adjusted"][:10]  # Top 10 instead of 5
            ]
        }
        
    except Exception as e:
        logger.error(f"Opportunities error: {e}")
        return None


def run_advisor(monitor_data: dict, opportunities_data: Optional[dict]) -> Optional[str]:
    """Run LP Advisor and return AI summary"""
    
    # Check for OpenAI key first
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        logger.warning("OPENAI_API_KEY not set - skipping AI summary")
        return None
    
    try:
        # Build context for AI
        tvl = monitor_data.get("tvl", 0)
        fees = monitor_data.get("fees", 0)
        count = monitor_data.get("count", 0)
        in_range = monitor_data.get("in_range", 0)
        out_range = count - in_range
        
        positions = monitor_data.get("positions", [])
        
        # Position details
        position_details = []
        for p in positions[:10]:  # Limit to 10
            symbol = f"{p.get('token0_symbol', '')}-{p.get('token1_symbol', '')}"
            balance = p.get("balance_usd", 0)
            status = "in-range" if p.get("in_range", False) else "OUT OF RANGE"
            position_details.append(f"{symbol}: ${balance:.0f} ({status})")
        
        # Regime info
        regime = opportunities_data.get("regime", "UNKNOWN") if opportunities_data else "UNKNOWN"
        regime_penalty = opportunities_data.get("regime_penalty", 0.4) if opportunities_data else 0.4
        
        # Top pools
        top_pools = []
        if opportunities_data and opportunities_data.get("top_pools"):
            for p in opportunities_data["top_pools"][:3]:
                top_pools.append(f"{p['symbol']}: {p['risk_adj_apy']:.1f}%")
        
        prompt = f"""LP Portfolio Analysis:

Regime: {regime} (IL penalty: {regime_penalty:.0%})
TVL: ${tvl:,.0f}
Fees uncollected: ${fees:.2f}
Positions: {count} total, {in_range} in-range, {out_range} out-of-range

Positions:
{chr(10).join(position_details)}

Top market opportunities:
{chr(10).join(top_pools) if top_pools else "N/A"}

Give brief assessment (2-3 sentences) and 1-2 specific actions. Russian language."""

        # Call OpenAI
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
                    "content": "You are a DeFi LP advisor. Be concise and actionable. Russian language. Max 300 chars."
                },
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 200,
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
    
    # TVL Changes
    if history:
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
    
    # Regime with LP policy details
    if opportunities_data:
        regime = opportunities_data.get("regime", "UNKNOWN")
        regime_penalty = opportunities_data.get("regime_penalty", 0)
        lp_recommendation = opportunities_data.get("lp_recommendation", "")
        
        lines.append(f"Regime: {regime}")
        if regime_penalty:
            lines.append(f"  IL Penalty: {regime_penalty:.0%}")
        if lp_recommendation:
            lines.append(f"  {lp_recommendation}")
        lines.append("")
    
    # AI Summary
    if ai_summary:
        lines.append("AI:")
        lines.append(ai_summary)
    else:
        lines.append("AI: (no OpenAI key or error)")
    
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
    add_snapshot(
        tvl=monitor_data["tvl"],
        fees=monitor_data["fees"],
        positions_count=monitor_data["count"],
        in_range=monitor_data["in_range"],
        by_wallet=by_wallet_tvl,
    )
    
    # Reload history after adding snapshot
    history = load_history()
    
    # Stage 2: Opportunities
    logger.info("\n--- STAGE 2: OPPORTUNITIES ---")
    opportunities_data = run_opportunities()
    
    if opportunities_data:
        logger.info(f"Regime: {opportunities_data.get('regime')}")
        logger.info(f"Top pools: {len(opportunities_data.get('top_pools', []))}")
    else:
        logger.warning("Opportunities scan failed")
    
    # Stage 3: Advisor
    logger.info("\n--- STAGE 3: ADVISOR ---")
    ai_summary = None
    
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        logger.warning("OPENAI_API_KEY not set - AI summary disabled")
    elif monitor_data:
        ai_summary = run_advisor(monitor_data, opportunities_data)
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
