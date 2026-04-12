"""
Yahoo Finance MCP Server
========================
A production-quality Model Context Protocol (MCP) server that exposes
stock market data tools via SSE transport.

All data is fetched from Yahoo Finance via the `yfinance` library —
no API key required. Designed to be connected to Claude Desktop, MCP
Inspector, or any MCP-compatible AI client.

Usage:
    python server.py

Endpoints:
    GET   /sse       — MCP SSE stream (connect here from MCP Inspector)
    POST  /messages  — MCP message posting endpoint
    GET   /health    — Health check
    GET   /docs      — FastAPI Swagger UI
"""

import math
import os
from datetime import datetime
from typing import Any

import uvicorn
import yfinance as yf
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from mcp.server.fastmcp import FastMCP
from mcp.server.sse import SseServerTransport

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

load_dotenv()

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "7860"))

# ---------------------------------------------------------------------------
# FastMCP instance
# ---------------------------------------------------------------------------

mcp = FastMCP(
    name="yahoo-finance-mcp",
    instructions=(
        "You have access to real-time and historical stock market data via Yahoo Finance. "
        "Use the available tools to look up stock quotes, company fundamentals, price history, "
        "income statements, balance sheets, cash flows, and earnings data. "
        "All financial data is sourced from Yahoo Finance and is suitable for personal/educational use."
    ),
)

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------


def _safe_val(val: Any, default: Any = None) -> Any:
    """
    Guard against None, NaN, and non-finite floats that yfinance can return.

    yfinance frequently returns float('nan') or None for missing fields.
    JSON serialization will choke on NaN, so we normalize everything here.

    Args:
        val:     The raw value from yfinance (any type).
        default: Value to return when val is missing/invalid.

    Returns:
        The original value if it is valid, otherwise `default`.
    """
    if val is None:
        return default
    if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
        return default
    return val


def _fmt_large(n: Any) -> str:
    """
    Format large numbers into human-readable strings (T / B / M suffixes).

    Args:
        n: A numeric value (int or float). None / NaN → "N/A".

    Returns:
        Formatted string like "$1.23B", "$456.78M", or "N/A".

    Examples:
        >>> _fmt_large(1_230_000_000)
        '$1.23B'
        >>> _fmt_large(456_780_000)
        '$456.78M'
    """
    n = _safe_val(n)
    if n is None:
        return "N/A"
    try:
        n = float(n)
    except (ValueError, TypeError):
        return "N/A"

    if abs(n) >= 1_000_000_000_000:
        return f"${n / 1_000_000_000_000:.2f}T"
    if abs(n) >= 1_000_000_000:
        return f"${n / 1_000_000_000:.2f}B"
    if abs(n) >= 1_000_000:
        return f"${n / 1_000_000:.2f}M"
    return f"${n:,.0f}"


def _pct(value: Any, decimals: int = 2) -> str:
    """Format a ratio (0–1 float) as a percentage string, e.g. 0.0325 → '3.25%'."""
    v = _safe_val(value)
    if v is None:
        return "N/A"
    try:
        return f"{float(v) * 100:.{decimals}f}%"
    except (ValueError, TypeError):
        return "N/A"


def _round(value: Any, decimals: int = 2) -> Any:
    """Safely round a numeric value; return None if not numeric."""
    v = _safe_val(value)
    if v is None:
        return None
    try:
        return round(float(v), decimals)
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Tool 1 — Stock Quote
# ---------------------------------------------------------------------------


@mcp.tool()
def get_stock_quote(ticker: str) -> dict:
    """
    Get the current market quote for a stock ticker.

    Returns price, change, volume, market cap, valuation ratios,
    52-week range, and exchange metadata.

    Args:
        ticker: Stock ticker symbol, e.g. "AAPL", "MSFT", "TSLA".

    Returns:
        dict with keys: ticker, name, price, change, change_pct,
        volume, avg_volume, market_cap, pe_ratio, forward_pe,
        dividend_yield, week_52_high, week_52_low, exchange,
        currency, timestamp. On error: {"error": str}.
    """
    try:
        stock = yf.Ticker(ticker.upper())
        info = stock.info

        # yfinance returns an almost-empty dict for invalid tickers
        # rather than raising — check for a required field.
        if not info or "regularMarketPrice" not in info and "currentPrice" not in info:
            return {"error": f"No data found for ticker '{ticker}'. Check the symbol and try again."}

        # currentPrice is populated for most market hours;
        # regularMarketPrice is the last official close.
        price = _safe_val(info.get("currentPrice") or info.get("regularMarketPrice"))
        prev_close = _safe_val(info.get("regularMarketPreviousClose"))

        change = None
        change_pct = None
        if price is not None and prev_close is not None:
            change = round(price - prev_close, 4)
            change_pct = round((change / prev_close) * 100, 2)

        return {
            "ticker": ticker.upper(),
            "name": _safe_val(info.get("longName") or info.get("shortName"), ticker.upper()),
            "price": _round(price, 4),
            "change": change,
            "change_pct": f"{change_pct:+.2f}%" if change_pct is not None else "N/A",
            "previous_close": _round(prev_close, 4),
            "volume": _safe_val(info.get("regularMarketVolume") or info.get("volume")),
            "avg_volume": _safe_val(info.get("averageVolume")),
            "market_cap": _fmt_large(info.get("marketCap")),
            "pe_ratio": _round(info.get("trailingPE")),
            "forward_pe": _round(info.get("forwardPE")),
            "dividend_yield": _pct(info.get("dividendYield")),
            "week_52_high": _round(info.get("fiftyTwoWeekHigh"), 4),
            "week_52_low": _round(info.get("fiftyTwoWeekLow"), 4),
            "exchange": _safe_val(info.get("exchange")),
            "currency": _safe_val(info.get("currency")),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
    except Exception as exc:
        return {"error": f"Failed to fetch quote for '{ticker}': {exc}"}


# ---------------------------------------------------------------------------
# Tool 2 — Company Info
# ---------------------------------------------------------------------------


@mcp.tool()
def get_stock_info(ticker: str) -> dict:
    """
    Get detailed company profile and executive information.

    Args:
        ticker: Stock ticker symbol, e.g. "GOOGL".

    Returns:
        dict with keys: ticker, name, sector, industry, country,
        headquarters, description, employees, executives, website.
        On error: {"error": str}.
    """
    try:
        stock = yf.Ticker(ticker.upper())
        info = stock.info

        if not info or not info.get("longName"):
            return {"error": f"No company data found for ticker '{ticker}'."}

        # Truncate the business summary — it can be several paragraphs long
        description = _safe_val(info.get("longBusinessSummary"), "")
        if description and len(description) > 500:
            description = description[:497] + "..."

        # Officers list is a list of dicts; we pull the top 3 by totalPay desc
        # (yfinance doesn't always sort them, so we take the first 3 as-is).
        raw_officers = info.get("companyOfficers") or []
        executives = [
            {"name": o.get("name", "N/A"), "title": o.get("title", "N/A")}
            for o in raw_officers[:3]
        ]

        city = _safe_val(info.get("city"), "")
        state = _safe_val(info.get("state"), "")
        country = _safe_val(info.get("country"), "")
        headquarters_parts = [p for p in [city, state, country] if p]
        headquarters = ", ".join(headquarters_parts) if headquarters_parts else "N/A"

        return {
            "ticker": ticker.upper(),
            "name": _safe_val(info.get("longName")),
            "sector": _safe_val(info.get("sector")),
            "industry": _safe_val(info.get("industry")),
            "country": country or "N/A",
            "headquarters": headquarters,
            "description": description,
            "employees": _safe_val(info.get("fullTimeEmployees")),
            "executives": executives,
            "website": _safe_val(info.get("website")),
        }
    except Exception as exc:
        return {"error": f"Failed to fetch company info for '{ticker}': {exc}"}


# ---------------------------------------------------------------------------
# Tool 3 — Price History
# ---------------------------------------------------------------------------

_VALID_PERIODS = {"1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y"}
_VALID_INTERVALS = {"1d", "1wk", "1mo"}


@mcp.tool()
def get_price_history(
    ticker: str,
    period: str = "1mo",
    interval: str = "1d",
) -> dict:
    """
    Get OHLCV price history for a stock over a specified period.

    Args:
        ticker:   Stock ticker symbol, e.g. "SPY".
        period:   Lookback window. One of: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y.
                  Defaults to "1mo".
        interval: Bar interval. One of: 1d, 1wk, 1mo. Defaults to "1d".

    Returns:
        dict with keys: ticker, period, interval, records (list of OHLCV),
        summary (start/end price, % change, high, low, bar_count).
        On error: {"error": str}.
    """
    try:
        period = period.lower()
        interval = interval.lower()

        if period not in _VALID_PERIODS:
            return {"error": f"Invalid period '{period}'. Valid options: {sorted(_VALID_PERIODS)}"}
        if interval not in _VALID_INTERVALS:
            return {"error": f"Invalid interval '{interval}'. Valid options: {sorted(_VALID_INTERVALS)}"}

        stock = yf.Ticker(ticker.upper())
        # yfinance returns a pandas DataFrame with DatetimeIndex
        hist = stock.history(period=period, interval=interval)

        if hist.empty:
            return {"error": f"No price history found for '{ticker}' with period={period}, interval={interval}."}

        records = []
        for ts, row in hist.iterrows():
            records.append({
                "date": ts.strftime("%Y-%m-%d"),
                "open": _round(row.get("Open"), 4),
                "high": _round(row.get("High"), 4),
                "low": _round(row.get("Low"), 4),
                "close": _round(row.get("Close"), 4),
                "volume": int(row.get("Volume", 0)),
            })

        # Build a quick summary so the AI doesn't need to parse the whole list
        start_price = records[0]["close"]
        end_price = records[-1]["close"]
        closes = [r["close"] for r in records if r["close"] is not None]
        highs = [r["high"] for r in records if r["high"] is not None]
        lows = [r["low"] for r in records if r["low"] is not None]

        pct_change = None
        if start_price and end_price:
            pct_change = round(((end_price - start_price) / start_price) * 100, 2)

        summary = {
            "start_price": start_price,
            "end_price": end_price,
            "period_change_pct": f"{pct_change:+.2f}%" if pct_change is not None else "N/A",
            "period_high": max(highs) if highs else None,
            "period_low": min(lows) if lows else None,
            "bar_count": len(records),
        }

        return {
            "ticker": ticker.upper(),
            "period": period,
            "interval": interval,
            "summary": summary,
            "records": records,
        }
    except Exception as exc:
        return {"error": f"Failed to fetch price history for '{ticker}': {exc}"}


# ---------------------------------------------------------------------------
# Tool 4 — Income Statement
# ---------------------------------------------------------------------------


def _extract_financials(df, keys: list[tuple[str, str]], periods: int = 4) -> list[dict]:
    """
    Extract specific rows from a yfinance financial DataFrame.

    yfinance returns financials as a DataFrame where rows are metric names
    and columns are period dates. We transpose and pick the rows we need.

    Args:
        df:      Raw yfinance financials DataFrame.
        keys:    List of (yfinance_row_name, output_key_name) tuples.
        periods: Number of most-recent periods to return.

    Returns:
        List of dicts, one per period, with formatted values.
    """
    if df is None or df.empty:
        return []

    # Columns are Timestamps; take the most recent `periods`
    cols = df.columns[:periods]
    results = []

    for col in cols:
        record: dict[str, Any] = {"period": col.strftime("%Y-%m-%d")}
        for row_name, out_key in keys:
            try:
                val = df.loc[row_name, col] if row_name in df.index else None
            except KeyError:
                val = None
            record[out_key] = _fmt_large(val)
        results.append(record)

    return results


@mcp.tool()
def get_income_statement(ticker: str, quarterly: bool = False) -> dict:
    """
    Get the income statement (P&L) for a company.

    Covers revenue, gross profit, operating income, net income, and EBITDA
    for the last 4 annual or quarterly periods.

    Args:
        ticker:    Stock ticker symbol, e.g. "AMZN".
        quarterly: If True, return quarterly data. Defaults to annual.

    Returns:
        dict with keys: ticker, frequency, periods (list of period records).
        On error: {"error": str}.
    """
    try:
        stock = yf.Ticker(ticker.upper())

        # yfinance exposes .financials (annual) and .quarterly_financials
        df = stock.quarterly_financials if quarterly else stock.financials

        if df is None or df.empty:
            return {"error": f"No income statement data found for '{ticker}'."}

        # Map yfinance row labels → our output keys.
        # Row names can vary slightly by ticker; we handle missing gracefully
        # inside _extract_financials via try/except.
        row_map = [
            ("Total Revenue", "revenue"),
            ("Gross Profit", "gross_profit"),
            ("Operating Income", "operating_income"),
            ("Net Income", "net_income"),
            ("EBITDA", "ebitda"),
        ]

        periods = _extract_financials(df, row_map, periods=4)

        return {
            "ticker": ticker.upper(),
            "frequency": "quarterly" if quarterly else "annual",
            "periods": periods,
        }
    except Exception as exc:
        return {"error": f"Failed to fetch income statement for '{ticker}': {exc}"}


# ---------------------------------------------------------------------------
# Tool 5 — Balance Sheet
# ---------------------------------------------------------------------------


@mcp.tool()
def get_balance_sheet(ticker: str, quarterly: bool = False) -> dict:
    """
    Get the balance sheet for a company.

    Covers total assets, total liabilities, stockholders' equity,
    cash, total debt, and net debt for the last 4 periods.

    Args:
        ticker:    Stock ticker symbol, e.g. "JPM".
        quarterly: If True, return quarterly data. Defaults to annual.

    Returns:
        dict with keys: ticker, frequency, periods (list of period records).
        On error: {"error": str}.
    """
    try:
        stock = yf.Ticker(ticker.upper())
        df = stock.quarterly_balance_sheet if quarterly else stock.balance_sheet

        if df is None or df.empty:
            return {"error": f"No balance sheet data found for '{ticker}'."}

        row_map = [
            ("Total Assets", "total_assets"),
            ("Total Liabilities Net Minority Interest", "total_liabilities"),
            ("Stockholders Equity", "stockholders_equity"),
            ("Cash And Cash Equivalents", "cash_and_equivalents"),
            ("Total Debt", "total_debt"),
            ("Net Debt", "net_debt"),
        ]

        periods = _extract_financials(df, row_map, periods=4)

        return {
            "ticker": ticker.upper(),
            "frequency": "quarterly" if quarterly else "annual",
            "periods": periods,
        }
    except Exception as exc:
        return {"error": f"Failed to fetch balance sheet for '{ticker}': {exc}"}


# ---------------------------------------------------------------------------
# Tool 6 — Cash Flow Statement
# ---------------------------------------------------------------------------


@mcp.tool()
def get_cash_flow(ticker: str, quarterly: bool = False) -> dict:
    """
    Get the cash flow statement for a company.

    Covers operating, investing, and financing cash flows plus
    free cash flow (operating CF − capex) for the last 4 periods.

    Args:
        ticker:    Stock ticker symbol, e.g. "META".
        quarterly: If True, return quarterly data. Defaults to annual.

    Returns:
        dict with keys: ticker, frequency, periods (list of period records,
        each including a computed free_cash_flow field).
        On error: {"error": str}.
    """
    try:
        stock = yf.Ticker(ticker.upper())
        df = stock.quarterly_cashflow if quarterly else stock.cashflow

        if df is None or df.empty:
            return {"error": f"No cash flow data found for '{ticker}'."}

        row_map = [
            ("Operating Cash Flow", "operating_cash_flow"),
            ("Investing Cash Flow", "investing_cash_flow"),
            ("Financing Cash Flow", "financing_cash_flow"),
            ("Capital Expenditure", "capex"),
        ]

        periods = _extract_financials(df, row_map, periods=4)

        # Compute free cash flow = operating CF - abs(capex).
        # Capex is typically reported as a negative number by yfinance;
        # we add it (which is equivalent to subtracting the magnitude).
        for record in periods:
            try:
                op_cf_raw = df.loc["Operating Cash Flow", :].iloc[periods.index(record)]
                capex_raw = df.loc["Capital Expenditure", :].iloc[periods.index(record)]
                op_cf = _safe_val(op_cf_raw)
                capex = _safe_val(capex_raw)
                if op_cf is not None and capex is not None:
                    fcf = float(op_cf) + float(capex)  # capex is negative
                    record["free_cash_flow"] = _fmt_large(fcf)
                else:
                    record["free_cash_flow"] = "N/A"
            except Exception:
                record["free_cash_flow"] = "N/A"

        return {
            "ticker": ticker.upper(),
            "frequency": "quarterly" if quarterly else "annual",
            "periods": periods,
        }
    except Exception as exc:
        return {"error": f"Failed to fetch cash flow for '{ticker}': {exc}"}


# ---------------------------------------------------------------------------
# Tool 7 — Earnings
# ---------------------------------------------------------------------------


@mcp.tool()
def get_earnings(ticker: str) -> dict:
    """
    Get EPS earnings history (actual vs. estimated) and annual EPS trend.

    Shows the last 4 quarters of reported EPS with beat/miss classification
    and surprise percentage, plus annual EPS for the last 4 years.

    Args:
        ticker: Stock ticker symbol, e.g. "NVDA".

    Returns:
        dict with keys: ticker, next_earnings_date, quarterly_history
        (last 4 quarters with actual, estimated, surprise_pct, beat_miss),
        annual_eps (last 4 years).
        On error: {"error": str}.
    """
    try:
        stock = yf.Ticker(ticker.upper())
        info = stock.info

        # --- Next earnings date ---
        next_date = _safe_val(info.get("earningsTimestamp"))
        if next_date:
            try:
                next_date = datetime.utcfromtimestamp(next_date).strftime("%Y-%m-%d")
            except Exception:
                next_date = None

        # --- Quarterly EPS history ---
        # earnings_history is a DataFrame with columns: EPS Estimate, Reported EPS, Surprise(%)
        quarterly_history = []
        try:
            eh = stock.earnings_history
            if eh is not None and not eh.empty:
                # Take the last 4 rows (most recent quarters)
                for ts, row in eh.tail(4).iterrows():
                    actual = _safe_val(row.get("epsActual") or row.get("Reported EPS"))
                    estimated = _safe_val(row.get("epsEstimate") or row.get("EPS Estimate"))
                    surprise_pct = _safe_val(row.get("epsDifference") or row.get("Surprise(%)"))

                    # Determine beat / miss / meet
                    if actual is not None and estimated is not None:
                        diff = float(actual) - float(estimated)
                        if diff > 0:
                            beat_miss = "BEAT"
                        elif diff < 0:
                            beat_miss = "MISS"
                        else:
                            beat_miss = "MET"
                    else:
                        beat_miss = "N/A"

                    quarterly_history.append({
                        "quarter": ts.strftime("%Y-%m-%d") if hasattr(ts, "strftime") else str(ts),
                        "eps_actual": _round(actual, 4),
                        "eps_estimated": _round(estimated, 4),
                        "surprise_pct": (
                            f"{float(surprise_pct) * 100:+.2f}%"
                            if surprise_pct is not None
                            else "N/A"
                        ),
                        "beat_miss": beat_miss,
                    })
        except Exception:
            # earnings_history may not be available for all tickers
            quarterly_history = []

        # --- Annual EPS trend ---
        annual_eps = []
        try:
            ae = stock.earnings  # DataFrame: index=Year, columns=[Revenue, Earnings]
            if ae is not None and not ae.empty:
                for year, row in ae.tail(4).iterrows():
                    annual_eps.append({
                        "year": str(year),
                        "eps": _round(row.get("Earnings"), 4),
                    })
        except Exception:
            annual_eps = []

        return {
            "ticker": ticker.upper(),
            "next_earnings_date": next_date,
            "quarterly_history": quarterly_history,
            "annual_eps": annual_eps,
        }
    except Exception as exc:
        return {"error": f"Failed to fetch earnings for '{ticker}': {exc}"}


# ---------------------------------------------------------------------------
# Application assembly — FastAPI + explicit SSE transport
# ---------------------------------------------------------------------------

# Using explicit SSE transport rather than FastMCP's built-in HTTP runner.
# FastMCP's streamable_http_app() has mounting issues in some deployment
# environments (including Hugging Face Spaces). The explicit pattern below
# gives full control over routing and works reliably with MCP Inspector.

app = FastAPI(title="Yahoo Finance MCP", version="1.0.0")

# SseServerTransport handles the SSE stream and message posting.
# The path passed here ("/messages") is where clients POST messages back.
sse = SseServerTransport("/messages")


@app.get("/sse")
async def handle_sse(request: Request):
    """
    MCP SSE endpoint — connect here from MCP Inspector or any MCP client.
    Transport: SSE, URL: <host>/sse
    """
    async with sse.connect_sse(
        request.scope, request.receive, request._send
    ) as streams:
        await mcp._mcp_server.run(
            streams[0],
            streams[1],
            mcp._mcp_server.create_initialization_options(),
        )


@app.post("/messages")
async def handle_messages(request: Request):
    """MCP message posting endpoint — used by the SSE transport internally."""
    await sse.handle_post_message(request.scope, request.receive, request._send)


@app.get("/health")
async def health():
    """Liveness probe — useful for Docker/K8s health checks."""
    return {"status": "ok", "server": "yahoo-finance-mcp"}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print(f"\n{'=' * 60}")
    print("  Yahoo Finance MCP Server")
    print(f"{'=' * 60}")
    print(f"  SSE endpoint : http://{HOST}:{PORT}/sse")
    print(f"  Health check : http://localhost:{PORT}/health")
    print(f"  API docs     : http://localhost:{PORT}/docs")
    print(f"  Transport    : SSE")
    print(f"{'=' * 60}\n")

    uvicorn.run(
        "server:app",
        host=HOST,
        port=PORT,
        reload=False,
        log_level="info",
    )
