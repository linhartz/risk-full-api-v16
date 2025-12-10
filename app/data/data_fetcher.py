# data/data_fetcher.py
from typing import Dict, Any
import requests
import time
import os

# optional import; not required on startup
try:
    import yfinance as yf
except Exception:
    yf = None

OPENFIGI_API = os.getenv("OPENFIGI_API_KEY")  # optional

def _openfigi_map_isin_to_ticker(isin: str) -> str:
    """
    Try to map ISIN -> exchange ticker using OpenFIGI (if key set).
    Returns ticker string suitable for yfinance (e.g. 'AAPL' or 'VOW3.DE') or ''
    """
    if not OPENFIGI_API:
        return ""
    url = "https://api.openfigi.com/v3/mapping"
    headers = {"Content-Type": "application/json", "X-OPENFIGI-APIKEY": OPENFIGI_API}
    body = [{"idType":"ID_ISIN", "idValue": isin}]
    try:
        r = requests.post(url, json=body, headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json()
        if data and isinstance(data, list) and data[0].get('data'):
            rec = data[0]['data'][0]
            # try to get ticker + exchCode
            ticker = rec.get('ticker') or rec.get('compositeFIGI') or ""
            exch = rec.get('exchCode')
            if ticker and exch:
                # return with exchange suffix common for yfinance (best-effort)
                return f"{ticker}.{exch}"
            return ticker or ""
    except Exception:
        return ""
    return ""

def fetch_enriched_feed_for_isin(isin: str, source="yfinance") -> Dict[str, Any]:
    """
    Returns dict: { change_percent, indicators, series, enriched }
    Defensive: never raise except for catastrophic errors; returns minimal dict on failure.
    """
    result = {"change_percent": 0.0, "indicators": {}, "series": [], "enriched": {}}
    if not isin:
        return result

    # Try yfinance first (works with tickers; yfinance may accept some ISINs)
    if yf:
        try:
            # yfinance expects ticker symbols; many ISINs are not accepted directly.
            # Try direct ticker first (some users provide ticker already), else try openfigi mapping
            ticker_candidate = isin
            try:
                t = yf.Ticker(ticker_candidate)
                hist = t.history(period="6mo")
                if hist is None or hist.empty:
                    raise ValueError("No data via direct ticker")
                close = hist['Close']
                if len(close) >= 2:
                    change = (close[-1] - close[-2]) / close[-2] * 100.0
                else:
                    change = 0.0
                result.update({
                    "change_percent": float(change),
                    "series": close.fillna(0).tolist(),
                    "indicators": {},
                    "enriched": {}
                })
                return result
            except Exception:
                # try OpenFIGI mapping if available
                mapped = _openfigi_map_isin_to_ticker(isin)
                if mapped and mapped != isin:
                    try:
                        t2 = yf.Ticker(mapped)
                        hist2 = t2.history(period="6mo")
                        if hist2 is not None and not hist2.empty:
                            close = hist2['Close']
                            change = (close[-1] - close[-2]) / close[-2] * 100.0 if len(close) >= 2 else 0.0
                            result.update({
                                "change_percent": float(change),
                                "series": close.fillna(0).tolist(),
                                "indicators": {},
                                "enriched": {"mapped_ticker": mapped}
                            })
                            return result
                    except Exception:
                        pass
        except Exception:
            # swallow yfinance exceptions to avoid crash
            pass

    # If we reach here, no data found
    result['error'] = f"No data for ISIN {isin}"
    return result
