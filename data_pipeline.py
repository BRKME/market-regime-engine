"""
Data Pipeline — fetches all inputs from free public APIs.

Sources:
  Price OHLCV:
    Primary:  Yahoo Finance (BTC-USD) — works everywhere incl. GitHub Actions
    Fallback: CoinGecko OHLC (no volume, but OHLC accurate)
  Funding / OI:
    Binance Futures (optional — blocked on US IPs, graceful degradation)
  Market data:
    CoinGecko: total market cap, BTC dominance
  Sentiment:
    alternative.me: Fear & Greed Index
  Macro:
    Yahoo Finance: DXY, SPX, Gold
    FRED: US Treasury yields, M2

Note: Binance returns HTTP 451 from GitHub Actions (US geo-restriction).
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
# YAHOO FINANCE — PRIMARY PRICE SOURCE
# ============================================================

def fetch_btc_price_yahoo(period: str = "1y") -> pd.DataFrame:
    """
    Fetch BTC OHLCV from Yahoo Finance (BTC-USD).
    Works on all IPs including GitHub Actions.
    """
    try:
        import yfinance as yf
        data = yf.download("BTC-USD", period=period, progress=False, auto_adjust=True)

        if data.empty:
            logger.warning("Yahoo BTC-USD returned empty data")
            return pd.DataFrame()

        df = data.copy()

        # Handle MultiIndex columns from yfinance
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df = df.reset_index()
        df = df.rename(columns={
            "Date": "date",
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
        })
        df["date"] = pd.to_datetime(df["date"]).dt.date

        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = df[col].astype(float)

        # quote_volume ≈ volume_BTC × close_price
        df["quote_volume"] = df["volume"] * df["close"]

        return df[["date", "open", "high", "low", "close", "volume", "quote_volume"]].copy()

    except Exception as e:
        logger.error(f"Yahoo BTC-USD failed: {e}")
        return pd.DataFrame()


# ============================================================
# COINGECKO — FALLBACK PRICE + MARKET DATA
# ============================================================

CG_BASE = "https://api.coingecko.com/api/v3"


def fetch_btc_price_coingecko(days: int = 365) -> pd.DataFrame:
    """
    Fallback: BTC OHLC from CoinGecko.
    For days > 90, returns daily candles.
    """
    url = f"{CG_BASE}/coins/bitcoin/ohlc"
    params = {"vs_currency": "usd", "days": days}

    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        if not data:
            return pd.DataFrame()

        df = pd.DataFrame(data, columns=["timestamp", "open", "high", "low", "close"])
        df["date"] = pd.to_datetime(df["timestamp"], unit="ms").dt.date

        # Aggregate to daily (CoinGecko may give sub-daily candles)
        daily = df.groupby("date").agg({
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
        }).reset_index()

        for col in ["open", "high", "low", "close"]:
            daily[col] = daily[col].astype(float)

        daily["volume"] = 0.0
        daily["quote_volume"] = 0.0

        return daily

    except Exception as e:
        logger.error(f"CoinGecko OHLC failed: {e}")
        return pd.DataFrame()


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
        logger.warning(f"CoinGecko global failed: {e}")
        return {"total_market_cap_usd": None, "btc_dominance": None}


def fetch_coingecko_market_cap_history(days: int = 120) -> pd.DataFrame:
    """Fetch total market cap history."""
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
# BINANCE — FUNDING RATE + OI (optional, geo-restricted)
# ============================================================

BINANCE_BASE = "https://api.binance.com"


def fetch_binance_funding_rate(symbol: str = "BTCUSDT", limit: int = 100) -> pd.DataFrame:
    """Fetch funding rate. Non-critical — will be empty if Binance blocked."""
    url = f"{BINANCE_BASE}/fapi/v1/fundingRate"
    params = {"symbol": symbol, "limit": limit}

    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        df = pd.DataFrame(data)
        df["date"] = pd.to_datetime(df["fundingTime"], unit="ms").dt.date
        df["fundingRate"] = df["fundingRate"].astype(float)
        return df.groupby("date")["fundingRate"].mean().reset_index()
    except Exception as e:
        logger.info(f"  ○ Binance funding rate unavailable: {type(e).__name__}")
        return pd.DataFrame(columns=["date", "fundingRate"])


def fetch_binance_open_interest(symbol: str = "BTCUSDT") -> Optional[float]:
    """Fetch open interest. Non-critical."""
    url = f"{BINANCE_BASE}/fapi/v1/openInterest"
    params = {"symbol": symbol}

    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        return float(resp.json()["openInterest"])
    except Exception as e:
        logger.info(f"  ○ Binance OI unavailable: {type(e).__name__}")
        return None


# ============================================================
# FEAR & GREED (no auth)
# ============================================================

def fetch_fear_greed(limit: int = 90) -> pd.DataFrame:
    """Fetch Crypto Fear & Greed Index."""
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
        logger.warning(f"Fear & Greed failed: {e}")
        return pd.DataFrame(columns=["date", "fear_greed"])


# ============================================================
# YAHOO FINANCE — MACRO SERIES
# ============================================================

def fetch_yahoo_series(tickers: dict, period: str = "6mo") -> pd.DataFrame:
    """Fetch daily close for macro tickers."""
    try:
        import yfinance as yf

        frames = {}
        for name, symbol in tickers.items():
            try:
                data = yf.download(symbol, period=period, progress=False, auto_adjust=True)
                if not data.empty:
                    series = data["Close"].copy()
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
        logger.warning("yfinance not installed")
        return pd.DataFrame()


# ============================================================
# FRED (needs free API key)
# ============================================================

def fetch_fred_series(series_ids: dict, observation_start: str = None) -> pd.DataFrame:
    """Fetch FRED economic data series."""
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
        df = df.ffill()
        return df.reset_index()

    except ImportError:
        logger.warning("fredapi not installed")
        return pd.DataFrame()


# ============================================================
# AGGREGATE PIPELINE
# ============================================================

def fetch_all_data() -> dict:
    """
    Fetch all data sources. Handles failures gracefully.
    
    Price chain: Yahoo Finance → CoinGecko OHLC
    Binance data (funding/OI): optional, non-blocking
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

    # ── 1. BTC Price (Yahoo → CoinGecko fallback) ──────────
    logger.info("  [1/8] BTC price (Yahoo Finance)...")
    price_df = fetch_btc_price_yahoo(period="1y")

    if price_df.empty:
        logger.warning("  Yahoo failed, trying CoinGecko OHLC...")
        time.sleep(2)
        price_df = fetch_btc_price_coingecko(days=365)

    if not price_df.empty:
        result["price"] = price_df
        sources_ok += 1
        logger.info(f"  ✓ BTC price: {len(price_df)} days, "
                    f"last=${price_df['close'].iloc[-1]:,.0f}")
    else:
        logger.error("  ✗ BTC price: ALL SOURCES FAILED")

    # ── 2. Funding rate (Binance, optional) ─────────────────
    logger.info("  [2/8] Funding rate (Binance)...")
    result["funding"] = fetch_binance_funding_rate()
    if not result["funding"].empty:
        sources_ok += 1
        logger.info(f"  ✓ Funding rate: {len(result['funding'])} days")

    # ── 3. Open interest (Binance, optional) ────────────────
    logger.info("  [3/8] Open interest (Binance)...")
    result["open_interest"] = fetch_binance_open_interest()
    if result["open_interest"] is not None:
        sources_ok += 1
        logger.info(f"  ✓ Open interest: {result['open_interest']:,.0f}")

    time.sleep(1)

    # ── 4. CoinGecko global ─────────────────────────────────
    logger.info("  [4/8] CoinGecko global...")
    result["global"] = fetch_coingecko_global()
    if result["global"]["total_market_cap_usd"] is not None:
        sources_ok += 1
        logger.info(f"  ✓ TMC=${result['global']['total_market_cap_usd']/1e12:.2f}T, "
                    f"BTC.D={result['global']['btc_dominance']:.1f}%")

    time.sleep(2)

    # ── 5. Market cap history ───────────────────────────────
    logger.info("  [5/8] Market cap history...")
    result["market_cap_history"] = fetch_coingecko_market_cap_history(days=120)
    if not result["market_cap_history"].empty:
        sources_ok += 1
        logger.info(f"  ✓ MCap history: {len(result['market_cap_history'])} days")

    # ── 6. Fear & Greed ─────────────────────────────────────
    logger.info("  [6/8] Fear & Greed...")
    result["fear_greed"] = fetch_fear_greed()
    if not result["fear_greed"].empty:
        sources_ok += 1
        fg_now = result["fear_greed"].iloc[0]["fear_greed"]
        logger.info(f"  ✓ Fear & Greed: {len(result['fear_greed'])} days, current={fg_now}")

    # ── 7. Yahoo macro ──────────────────────────────────────
    logger.info("  [7/8] Yahoo macro (DXY, SPX, Gold)...")
    result["yahoo"] = fetch_yahoo_series({
        "DXY": "DX-Y.NYB",
        "SPX": "^GSPC",
        "GOLD": "GC=F",
    })
    if not result["yahoo"].empty:
        sources_ok += 1
        logger.info(f"  ✓ Yahoo macro: {len(result['yahoo'])} days")

    # ── 8. FRED ─────────────────────────────────────────────
    logger.info("  [8/8] FRED (yields, M2)...")
    result["fred"] = fetch_fred_series({
        "US_10Y": "DGS10",
        "US_2Y": "DGS2",
        "M2": "M2SL",
    })
    if not result["fred"].empty:
        sources_ok += 1
        logger.info(f"  ✓ FRED: {len(result['fred'])} rows")

    result["quality"]["sources_available"] = sources_ok
    result["quality"]["completeness"] = sources_ok / result["quality"]["sources_total"]

    logger.info("=" * 50)
    logger.info(f"DATA: {sources_ok}/{result['quality']['sources_total']} sources OK "
                f"({result['quality']['completeness']:.0%})")
    logger.info("=" * 50)

    return result
