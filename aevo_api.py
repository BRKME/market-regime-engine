"""
Aevo API Integration v1.0
Получение реальных цен опционов с DEX Aevo.

API Documentation: https://api-docs.aevo.xyz/
REST API: https://api.aevo.xyz
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

AEVO_API_BASE = "https://api.aevo.xyz"
AEVO_CACHE_FILE = "state/aevo_options_cache.json"
CACHE_TTL_SECONDS = 300  # 5 minutes


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class OptionQuote:
    """Option quote data"""
    instrument_name: str
    underlying: str  # ETH, BTC
    option_type: str  # C (call) or P (put)
    strike: float
    expiry: str  # Date string
    expiry_timestamp: int
    
    # Prices
    mark_price: float  # Mark price in USD
    bid_price: Optional[float]
    ask_price: Optional[float]
    
    # Greeks (if available)
    iv: Optional[float]  # Implied volatility
    delta: Optional[float]
    
    # Calculated
    premium_pct: float  # Premium as % of underlying price
    days_to_expiry: int


@dataclass
class OptionChain:
    """Option chain for an underlying"""
    underlying: str
    spot_price: float
    timestamp: str
    puts: List[OptionQuote]
    calls: List[OptionQuote]


# ═══════════════════════════════════════════════════════════════════════════════
# API FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def get_aevo_markets(asset: str = "ETH") -> Optional[List[dict]]:
    """
    Get all markets for an asset from Aevo.
    
    GET /markets?asset={asset}
    """
    try:
        url = f"{AEVO_API_BASE}/markets"
        params = {"asset": asset}
        
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Loaded {len(data)} markets for {asset}")
            return data
        else:
            logger.error(f"Aevo API error: {response.status_code}")
            return None
            
    except Exception as e:
        logger.error(f"Aevo API exception: {e}")
        return None


def get_aevo_index_price(asset: str = "ETH") -> Optional[float]:
    """
    Get current index price for an asset.
    
    GET /index?asset={asset}
    """
    try:
        url = f"{AEVO_API_BASE}/index"
        params = {"asset": asset}
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            price = float(data.get("price", 0))
            logger.info(f"{asset} index price: ${price:,.2f}")
            return price
        else:
            logger.error(f"Aevo index API error: {response.status_code}")
            return None
            
    except Exception as e:
        logger.error(f"Aevo index API exception: {e}")
        return None


def get_aevo_orderbook(instrument_name: str) -> Optional[dict]:
    """
    Get orderbook for an instrument.
    
    GET /orderbook?instrument_name={instrument_name}
    """
    try:
        url = f"{AEVO_API_BASE}/orderbook"
        params = {"instrument_name": instrument_name}
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.warning(f"Orderbook not available for {instrument_name}")
            return None
            
    except Exception as e:
        logger.warning(f"Orderbook exception for {instrument_name}: {e}")
        return None


def get_aevo_statistics(instrument_name: str) -> Optional[dict]:
    """
    Get statistics for an instrument (mark price, IV, etc).
    
    GET /statistics?instrument_name={instrument_name}
    """
    try:
        url = f"{AEVO_API_BASE}/statistics"
        params = {"instrument_name": instrument_name}
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            return response.json()
        else:
            return None
            
    except Exception as e:
        logger.warning(f"Statistics exception: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# PARSING
# ═══════════════════════════════════════════════════════════════════════════════

def parse_instrument_name(name: str) -> Optional[dict]:
    """
    Parse Aevo instrument name.
    
    Format: ETH-28FEB25-2500-P
    - ETH = underlying
    - 28FEB25 = expiry date
    - 2500 = strike price
    - P = put (C = call)
    """
    try:
        parts = name.split("-")
        if len(parts) != 4:
            return None
        
        underlying = parts[0]
        expiry_str = parts[1]
        strike = float(parts[2])
        option_type = parts[3]  # P or C
        
        # Parse expiry date (e.g., 28FEB25)
        day = int(expiry_str[:2])
        month_str = expiry_str[2:5]
        year_str = expiry_str[5:]
        
        month_map = {
            'JAN': 1, 'FEB': 2, 'MAR': 3, 'APR': 4, 'MAY': 5, 'JUN': 6,
            'JUL': 7, 'AUG': 8, 'SEP': 9, 'OCT': 10, 'NOV': 11, 'DEC': 12
        }
        month = month_map.get(month_str.upper(), 1)
        year = 2000 + int(year_str)
        
        expiry_date = datetime(year, month, day, tzinfo=timezone.utc)
        
        return {
            "underlying": underlying,
            "expiry_str": expiry_str,
            "expiry_date": expiry_date,
            "strike": strike,
            "option_type": option_type
        }
        
    except Exception as e:
        logger.warning(f"Failed to parse instrument: {name} - {e}")
        return None


def filter_options(
    markets: List[dict],
    option_type: str = "P",  # P for puts
    min_days: int = 7,
    max_days: int = 30,
    spot_price: float = 0,
    strike_range: Tuple[float, float] = (0.85, 1.0)  # -15% to ATM
) -> List[dict]:
    """
    Filter options by criteria.
    """
    
    now = datetime.now(timezone.utc)
    filtered = []
    
    for market in markets:
        instrument_name = market.get("instrument_name", "")
        
        # Skip perpetuals and non-options
        if "PERPETUAL" in instrument_name:
            continue
        
        parsed = parse_instrument_name(instrument_name)
        if not parsed:
            continue
        
        # Filter by type
        if parsed["option_type"] != option_type:
            continue
        
        # Filter by expiry
        days_to_expiry = (parsed["expiry_date"] - now).days
        if days_to_expiry < min_days or days_to_expiry > max_days:
            continue
        
        # Filter by strike (relative to spot)
        if spot_price > 0:
            strike_ratio = parsed["strike"] / spot_price
            if strike_ratio < strike_range[0] or strike_ratio > strike_range[1]:
                continue
        
        market["parsed"] = parsed
        market["days_to_expiry"] = days_to_expiry
        filtered.append(market)
    
    # Sort by expiry, then strike
    filtered.sort(key=lambda x: (x["days_to_expiry"], x["parsed"]["strike"]))
    
    return filtered


# ═══════════════════════════════════════════════════════════════════════════════
# OPTION CHAIN
# ═══════════════════════════════════════════════════════════════════════════════

def build_option_chain(asset: str = "ETH", target_days: int = 14) -> Optional[OptionChain]:
    """
    Build option chain for an asset.
    
    Returns puts and calls around the target expiry.
    """
    
    # Get spot price
    spot_price = get_aevo_index_price(asset)
    if not spot_price:
        logger.error(f"Failed to get {asset} spot price")
        return None
    
    # Get all markets
    markets = get_aevo_markets(asset)
    if not markets:
        logger.error(f"Failed to get {asset} markets")
        return None
    
    # Filter puts (for hedging)
    puts = filter_options(
        markets,
        option_type="P",
        min_days=7,
        max_days=30,
        spot_price=spot_price,
        strike_range=(0.80, 1.0)  # -20% to ATM
    )
    
    # Filter calls (for reference)
    calls = filter_options(
        markets,
        option_type="C",
        min_days=7,
        max_days=30,
        spot_price=spot_price,
        strike_range=(1.0, 1.20)  # ATM to +20%
    )
    
    logger.info(f"Found {len(puts)} puts and {len(calls)} calls for {asset}")
    
    # Get quotes for top options
    put_quotes = []
    for market in puts[:10]:  # Top 10 puts
        quote = get_option_quote(market, spot_price)
        if quote:
            put_quotes.append(quote)
    
    call_quotes = []
    for market in calls[:5]:  # Top 5 calls
        quote = get_option_quote(market, spot_price)
        if quote:
            call_quotes.append(quote)
    
    return OptionChain(
        underlying=asset,
        spot_price=spot_price,
        timestamp=datetime.now(timezone.utc).isoformat(),
        puts=put_quotes,
        calls=call_quotes
    )


def get_option_quote(market: dict, spot_price: float) -> Optional[OptionQuote]:
    """
    Get full quote for an option including orderbook.
    """
    
    instrument_name = market.get("instrument_name", "")
    parsed = market.get("parsed", {})
    
    # Get mark price from market data
    mark_price = float(market.get("mark_price", 0) or 0)
    
    # Get orderbook for bid/ask
    orderbook = get_aevo_orderbook(instrument_name)
    bid_price = None
    ask_price = None
    
    if orderbook:
        bids = orderbook.get("bids", [])
        asks = orderbook.get("asks", [])
        
        if bids:
            bid_price = float(bids[0][0])  # Best bid
        if asks:
            ask_price = float(asks[0][0])  # Best ask
    
    # Get IV from statistics
    stats = get_aevo_statistics(instrument_name)
    iv = None
    delta = None
    
    if stats:
        iv = float(stats.get("iv", 0) or 0)
        delta = float(stats.get("delta", 0) or 0)
    
    # Calculate premium as % of spot
    if mark_price > 0 and spot_price > 0:
        premium_pct = mark_price / spot_price * 100
    else:
        premium_pct = 0
    
    return OptionQuote(
        instrument_name=instrument_name,
        underlying=parsed.get("underlying", ""),
        option_type=parsed.get("option_type", ""),
        strike=parsed.get("strike", 0),
        expiry=parsed.get("expiry_str", ""),
        expiry_timestamp=int(parsed.get("expiry_date", datetime.now()).timestamp()),
        mark_price=mark_price,
        bid_price=bid_price,
        ask_price=ask_price,
        iv=iv,
        delta=delta,
        premium_pct=premium_pct,
        days_to_expiry=market.get("days_to_expiry", 0)
    )


# ═══════════════════════════════════════════════════════════════════════════════
# HEDGE PRICING
# ═══════════════════════════════════════════════════════════════════════════════

def find_best_put(
    chain: OptionChain,
    target_strike_pct: float = 0.90,  # -10% from spot
    target_days: int = 14
) -> Optional[OptionQuote]:
    """
    Find the best PUT option matching criteria.
    """
    
    if not chain.puts:
        return None
    
    target_strike = chain.spot_price * target_strike_pct
    
    # Score options
    scored = []
    for put in chain.puts:
        # Distance from target strike
        strike_diff = abs(put.strike - target_strike) / chain.spot_price
        
        # Distance from target days
        days_diff = abs(put.days_to_expiry - target_days) / 30
        
        # Prefer options with orderbook liquidity
        liquidity_bonus = 0
        if put.bid_price and put.ask_price:
            spread = (put.ask_price - put.bid_price) / put.mark_price if put.mark_price > 0 else 1
            if spread < 0.1:  # <10% spread
                liquidity_bonus = 0.2
        
        # Lower score = better
        score = strike_diff + days_diff - liquidity_bonus
        scored.append((score, put))
    
    # Sort by score
    scored.sort(key=lambda x: x[0])
    
    return scored[0][1] if scored else None


def get_hedge_pricing(
    underlying: str,
    notional_usd: float,
    strike_pct: float = 0.90,  # -10%
    expiry_days: int = 14
) -> Optional[dict]:
    """
    Get real pricing for a hedge position.
    """
    
    # Build option chain
    chain = build_option_chain(underlying)
    if not chain:
        return None
    
    # Find best matching PUT
    best_put = find_best_put(chain, strike_pct, expiry_days)
    if not best_put:
        logger.warning(f"No suitable PUT found for {underlying}")
        return None
    
    # Calculate number of contracts
    # 1 contract = 1 underlying unit (e.g., 1 ETH)
    contracts = notional_usd / chain.spot_price
    
    # Total premium
    total_premium = contracts * best_put.mark_price
    premium_pct = total_premium / notional_usd * 100
    
    return {
        "underlying": underlying,
        "spot_price": chain.spot_price,
        "option": asdict(best_put),
        "contracts": contracts,
        "notional_usd": notional_usd,
        "total_premium_usd": total_premium,
        "premium_pct": premium_pct,
        "iv": best_put.iv,
        "timestamp": chain.timestamp
    }


# ═══════════════════════════════════════════════════════════════════════════════
# CACHING
# ═══════════════════════════════════════════════════════════════════════════════

def load_cache() -> Optional[dict]:
    """Load cached option data"""
    if not os.path.exists(AEVO_CACHE_FILE):
        return None
    
    try:
        with open(AEVO_CACHE_FILE, 'r') as f:
            data = json.load(f)
        
        # Check TTL
        cached_at = datetime.fromisoformat(data.get("timestamp", "2000-01-01"))
        age = (datetime.now(timezone.utc) - cached_at).total_seconds()
        
        if age > CACHE_TTL_SECONDS:
            logger.info("Cache expired")
            return None
        
        return data
        
    except Exception as e:
        logger.warning(f"Cache load error: {e}")
        return None


def save_cache(data: dict):
    """Save data to cache"""
    os.makedirs(os.path.dirname(AEVO_CACHE_FILE), exist_ok=True)
    
    data["timestamp"] = datetime.now(timezone.utc).isoformat()
    
    with open(AEVO_CACHE_FILE, 'w') as f:
        json.dump(data, f, indent=2)
    
    logger.info("Cache saved")


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════════════════════

def get_hedge_quotes(
    eth_notional: float = 0,
    btc_notional: float = 0,
    strike_pct: float = 0.90,
    expiry_days: int = 14
) -> dict:
    """
    Get hedge quotes for ETH and BTC.
    
    Returns real pricing from Aevo DEX.
    """
    
    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "eth": None,
        "btc": None,
        "error": None
    }
    
    try:
        if eth_notional > 0:
            eth_pricing = get_hedge_pricing("ETH", eth_notional, strike_pct, expiry_days)
            if eth_pricing:
                result["eth"] = eth_pricing
        
        if btc_notional > 0:
            btc_pricing = get_hedge_pricing("BTC", btc_notional, strike_pct, expiry_days)
            if btc_pricing:
                result["btc"] = btc_pricing
        
        # Save to cache
        save_cache(result)
        
    except Exception as e:
        logger.error(f"Hedge quotes error: {e}")
        result["error"] = str(e)
    
    return result


def format_hedge_quote(quote: dict) -> str:
    """Format hedge quote for display"""
    
    if not quote:
        return "Нет данных"
    
    option = quote.get("option", {})
    
    lines = [
        f"  Инструмент: {option.get('instrument_name', 'N/A')}",
        f"  Страйк: ${option.get('strike', 0):,.0f}",
        f"  Экспирация: {option.get('expiry', 'N/A')} ({option.get('days_to_expiry', 0)}d)",
        f"  Mark: ${option.get('mark_price', 0):.2f}",
    ]
    
    if option.get("bid_price") and option.get("ask_price"):
        lines.append(f"  Bid/Ask: ${option['bid_price']:.2f} / ${option['ask_price']:.2f}")
    
    if option.get("iv"):
        lines.append(f"  IV: {option['iv']*100:.1f}%")
    
    lines.extend([
        f"  Контрактов: {quote.get('contracts', 0):.3f}",
        f"  Премия: ${quote.get('total_premium_usd', 0):.2f} ({quote.get('premium_pct', 0):.2f}%)",
    ])
    
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Test
    print("=" * 60)
    print("AEVO API TEST")
    print("=" * 60)
    
    # Get ETH price
    eth_price = get_aevo_index_price("ETH")
    print(f"\nETH Price: ${eth_price:,.2f}" if eth_price else "ETH price unavailable")
    
    # Get BTC price
    btc_price = get_aevo_index_price("BTC")
    print(f"BTC Price: ${btc_price:,.2f}" if btc_price else "BTC price unavailable")
    
    # Get hedge quotes
    print("\n" + "=" * 60)
    print("HEDGE QUOTES")
    print("=" * 60)
    
    quotes = get_hedge_quotes(
        eth_notional=5000,
        btc_notional=3000,
        strike_pct=0.90,
        expiry_days=14
    )
    
    if quotes.get("eth"):
        print("\nETH PUT:")
        print(format_hedge_quote(quotes["eth"]))
    
    if quotes.get("btc"):
        print("\nBTC PUT:")
        print(format_hedge_quote(quotes["btc"]))
    
    if quotes.get("error"):
        print(f"\nError: {quotes['error']}")
