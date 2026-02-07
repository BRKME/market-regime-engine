"""
Data Pipeline — fetches all inputs from free public APIs.

Sources:
  - Binance: BTC price OHLCV, funding rate, open interest
  - CoinGecko: total market cap, BTC dominance
  - alternative.me: Fear & Greed Index
  - Yahoo Finance: DXY, SPX, Gold
  - FRED: US Treasury yields, M2
"""

import os
import time
import logging
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
import pandas as pd
import requests

logger = logging.getLogger(__name__)


# ============================================================
# BINANCE (no auth needed)
# ============================================================

BINANCE_BASE = "https://api.binance.com"


def fetch_binance_klines(symbol: str = "BTCUSDT", interval: str = "1d",
                         limit: int = 200) -> pd.DataFrame:
    """Fetch OHLCV candles from Binance."""
    url = f"{BINANCE_BASE}/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}

    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    df = pd.DataFrame(data, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_volume", "trades", "taker_buy_base",
        "taker_buy_quote", "ignore"
    ])

    df["date"] = pd.to_datetime(df["open_time"], unit="ms").dt.date
    for col in ["open", "high", "low", "close", "volume", "quote_volume"]:
        df[col] = df[col].astype(float)

    return df[["date", "open", "high", "low", "close", "volume", "quote_volume"]].copy()


def fetch_binance_funding_rate(symbol: str = "BTCUSDT", limit: int = 100) -> pd.DataFrame:
    """Fetch perpetual funding rate history."""
    url = f"{BINANCE_BASE}/fapi/v1/fundingRate"
    params = {"symbol": symbol, "limit": limit}

    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        df = pd.DataFrame(data)
        df["date"] = pd.to_datetime(df["fundingTime"], unit="ms").dt.date
        df["fundingRate"] = df["fundingRate"].astype(float)

        # Average daily funding rate
        daily = df.groupby("date")["fundingRate"].mean().reset_index()
        return daily
    except Exception as e:
        logger.warning(f"Funding rate fetch failed: {e}")
        return pd.DataFrame(columns=["date", "fundingRate"])


def fetch_binance_open_interest(symbol: str = "BTCUSDT") -> Optional[float]:
    """Fetch current open interest."""
    url = f"{BINANCE_BASE}/fapi/v1/openInterest"
    params = {"symbol": symbol}

    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return float(data["openInterest"])
    except Exception as e:
        logger.warning(f"Open interest fetch failed: {e}")
        return None


# ============================================================
# COINGECKO (no auth, rate-limited)
# ============================================================

CG_BASE = "https://api.coingecko.com/api/v3"


def fetch_coingecko_global() -> dict:
    """Fetch global market data: total market cap, BTC dominance."""
    url = f"{CG_BASE}/global"

    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()["data"]

        return {
            "total_market_cap_usd": data["total_market_cap"].get("usd", 0),
            "btc_dominance": data.get("market_cap_percentage", {}).get("btc", 0),
        }
    except Exception as e:
        logger.warning(f"CoinGecko global fetch failed: {e}")
        return {"total_market_cap_usd": None, "btc_dominance": None}


def fetch_coingecko_market_cap_history(days: int = 120) -> pd.DataFrame:
    """Fetch BTC market chart for total market cap proxy."""
    url = f"{CG_BASE}/coins/bitcoin/market_chart"
    params = {"vs_currency": "usd", "days": days, "interval": "daily"}

    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        mc = pd.DataFrame(data["market_caps"], columns=["timestamp", "market_cap"])
        mc["date"] = pd.to_datetime(mc["timestamp"], unit="ms").dt.date
        return mc[["date", "market_cap"]]
    except Exception as e:
        logger.warning(f"CoinGecko market chart failed: {e}")
        return pd.DataFrame(columns=["date", "market_cap"])


# ============================================================
# FEAR & GREED (no auth)
# ============================================================

def fetch_fear_greed(limit: int = 90) -> pd.DataFrame:
    """Fetch Fear & Greed Index from alternative.me."""
    url = "https://api.alternative.me/fng/"
    params = {"limit": limit, "format": "json"}

    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()["data"]

        df = pd.DataFrame(data)
        df["date"] = pd.to_datetime(df["timestamp"].astype(int), unit="s").dt.date
        df["value"] = df["value"].astype(int)
        return df[["date", "value"]].rename(columns={"value": "fear_greed"})
    except Exception as e:
        logger.warning(f"Fear & Greed fetch failed: {e}")
        return pd.DataFrame(columns=["date", "fear_greed"])


# ============================================================
# YAHOO FINANCE (no auth, via yfinance)
# ============================================================

def fetch_yahoo_series(tickers: dict, period: str = "6mo") -> pd.DataFrame:
    """
    Fetch daily close for multiple tickers.
    tickers: {"DXY": "DX-Y.NYB", "SPX": "^GSPC", "GOLD": "GC=F"}
    """
    try:
        import yfinance as yf

        frames = {}
        for name, symbol in tickers.items():
            try:
                data = yf.download(symbol, period=period, progress=False, auto_adjust=True)
                if not data.empty:
                    series = data["Close"].copy()
                    # Handle MultiIndex columns from yfinance
                    if hasattr(series, 'columns'):
                        series = series.iloc[:, 0]
                    series.name = name
                    frames[name] = series
            except Exception as e:
                logger.warning(f"Yahoo {name} ({symbol}) failed: {e}")

        if not frames:
            return pd.DataFrame()

        df = pd.DataFrame(frames)
        df.index = pd.to_datetime(df.index).date
        df.index.name = "date"
        return df.reset_index()

    except ImportError:
        logger.warning("yfinance not installed, skipping Yahoo data")
        return pd.DataFrame()


# ============================================================
# FRED (needs free API key)
# ============================================================

def fetch_fred_series(series_ids: dict, observation_start: str = None) -> pd.DataFrame:
    """
    Fetch FRED data series.
    series_ids: {"US_10Y": "DGS10", "US_2Y": "DGS2", "M2": "M2SL"}
    """
    api_key = os.getenv("FRED_API_KEY")
    if not api_key:
        logger.warning("FRED_API_KEY not set, skipping macro data")
        return pd.DataFrame()

    if observation_start is None:
        observation_start = (datetime.now() - timedelta(days=400)).strftime("%Y-%m-%d")

    try:
        from fredapi import Fred
        fred = Fred(api_key=api_key)

        frames = {}
        for name, series_id in series_ids.items():
            try:
                s = fred.get_series(series_id, observation_start=observation_start)
                s.name = name
                frames[name] = s
            except Exception as e:
                logger.warning(f"FRED {name} ({series_id}) failed: {e}")

        if not frames:
            return pd.DataFrame()

        df = pd.DataFrame(frames)
        df.index = pd.to_datetime(df.index).date
        df.index.name = "date"
        # Forward-fill missing days (weekends, holidays)
        df = df.ffill()
        return df.reset_index()

    except ImportError:
        logger.warning("fredapi not installed, skipping FRED data")
        return pd.DataFrame()


# ============================================================
# AGGREGATE PIPELINE
# ============================================================

def fetch_all_data() -> dict:
    """
    Fetch all data sources and return structured dict.
    Handles failures gracefully — missing data flagged, not fatal.
    """
    logger.info("Fetching data from all sources...")
    result = {
        "price": None,
        "funding": None,
        "open_interest": None,
        "global": None,
        "market_cap_history": None,
        "fear_greed": None,
        "yahoo": None,
        "fred": None,
        "quality": {"completeness": 1.0, "sources_available": 0, "sources_total": 8},
        "fetch_time": datetime.utcnow().isoformat(),
    }

    sources_ok = 0

    # 1. Binance OHLCV
    try:
        result["price"] = fetch_binance_klines(limit=250)
        sources_ok += 1
        logger.info(f"  ✓ Binance price: {len(result['price'])} candles")
    except Exception as e:
        logger.error(f"  ✗ Binance price: {e}")

    # 2. Funding rate
    try:
        result["funding"] = fetch_binance_funding_rate()
        if not result["funding"].empty:
            sources_ok += 1
            logger.info(f"  ✓ Funding rate: {len(result['funding'])} days")
    except Exception as e:
        logger.error(f"  ✗ Funding rate: {e}")

    # 3. Open interest
    try:
        result["open_interest"] = fetch_binance_open_interest()
        if result["open_interest"] is not None:
            sources_ok += 1
            logger.info(f"  ✓ Open interest: {result['open_interest']:.0f}")
    except Exception as e:
        logger.error(f"  ✗ Open interest: {e}")

    time.sleep(1)  # Rate limit courtesy

    # 4. CoinGecko global
    try:
        result["global"] = fetch_coingecko_global()
        if result["global"]["total_market_cap_usd"] is not None:
            sources_ok += 1
            logger.info(f"  ✓ CoinGecko global: TMC=${result['global']['total_market_cap_usd']/1e12:.2f}T")
    except Exception as e:
        logger.error(f"  ✗ CoinGecko global: {e}")

    time.sleep(2)  # CoinGecko rate limit

    # 5. CoinGecko market cap history
    try:
        result["market_cap_history"] = fetch_coingecko_market_cap_history(days=120)
        if not result["market_cap_history"].empty:
            sources_ok += 1
            logger.info(f"  ✓ Market cap history: {len(result['market_cap_history'])} days")
    except Exception as e:
        logger.error(f"  ✗ Market cap history: {e}")

    # 6. Fear & Greed
    try:
        result["fear_greed"] = fetch_fear_greed()
        if not result["fear_greed"].empty:
            sources_ok += 1
            logger.info(f"  ✓ Fear & Greed: {len(result['fear_greed'])} days")
    except Exception as e:
        logger.error(f"  ✗ Fear & Greed: {e}")

    # 7. Yahoo Finance
    try:
        result["yahoo"] = fetch_yahoo_series({
            "DXY": "DX-Y.NYB",
            "SPX": "^GSPC",
            "GOLD": "GC=F",
        })
        if not result["yahoo"].empty:
            sources_ok += 1
            logger.info(f"  ✓ Yahoo Finance: {len(result['yahoo'])} days")
    except Exception as e:
        logger.error(f"  ✗ Yahoo Finance: {e}")

    # 8. FRED
    try:
        result["fred"] = fetch_fred_series({
            "US_10Y": "DGS10",
            "US_2Y": "DGS2",
            "M2": "M2SL",
        })
        if not result["fred"].empty:
            sources_ok += 1
            logger.info(f"  ✓ FRED: {len(result['fred'])} rows")
    except Exception as e:
        logger.error(f"  ✗ FRED: {e}")

    result["quality"]["sources_available"] = sources_ok
    result["quality"]["completeness"] = sources_ok / result["quality"]["sources_total"]

    logger.info(f"Data fetch complete: {sources_ok}/{result['quality']['sources_total']} sources OK")

    return result
