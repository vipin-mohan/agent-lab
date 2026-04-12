---
title: Yahoo Finance MCP
emoji: 📈
colorFrom: green
colorTo: blue
sdk: docker
pinned: false
---

# Yahoo Finance MCP Server

An MCP server that exposes Yahoo Finance data as callable tools for AI agents and LLM clients — stock quotes, company financials, earnings history, and price history. Built with Python and `yfinance`. No API key needed.

**Run locally — see Getting Started below**

---

## Hosted Demo

The server is deployed and publicly accessible on Hugging Face Spaces (free tier, always-on, no sign-in required):

- **MCP endpoint:** https://vipinmohan-yahoo-finance-mcp.hf.space/mcp
- **Health check:** https://vipinmohan-yahoo-finance-mcp.hf.space/health

---

## What It Does

Yahoo Finance MCP gives AI assistants direct access to real stock market data through seven structured tools:

- **get_stock_quote**: Current price, intraday change, volume, market cap (formatted), P/E ratio, forward P/E, dividend yield, and 52-week high/low — everything you'd check on a ticker page.
- **get_stock_info**: Company overview — sector, industry, headquarters, employee count, top executives, business description, and website.
- **get_price_history**: OHLCV bars for a ticker over any supported period (1d to 5y), with a summary showing start price, end price, % change, and period high/low.
- **get_income_statement**: Revenue, gross profit, operating income, net income, and EBITDA for the last 4 annual or quarterly periods.
- **get_balance_sheet**: Total assets, liabilities, stockholders' equity, cash, total debt, and net debt — annual or quarterly.
- **get_cash_flow**: Operating, investing, and financing cash flows, plus free cash flow (operating CF minus capex) — annual or quarterly.
- **get_earnings**: Quarterly EPS history with actual vs. estimated, beat/miss classification and surprise %, next earnings date, and annual EPS trend.

Every tool returns structured JSON. Every tool handles missing data, NaN values, and empty responses gracefully — you'll never get a serialization error or an unhandled exception surfaced to the client.

---

## Why I Built This

I've spent the past two years building agentic AI products at AWS — agent routing systems, MCP integrations, multi-agent orchestration pipelines. Most of that work is on the product and architecture side: deciding what tools agents should have, how they should be described, what failure modes matter, where the sharp edges are.

This project is me going to the other side of that table. What does it actually take to design and publish clean, reliable MCP tools that an AI agent can call without breaking? Where does yfinance get weird? How do you structure a tool manifest so the AI uses it correctly the first time? These are questions I think about at work — and the best way I know to answer them is to build it myself.

I picked finance as the domain because it's one I care about personally. Investing has been a long-standing interest, and Yahoo Finance via `yfinance` gives real, live data with no API cost — making this something anyone can clone and run in five minutes.

## How It Works

1. You connect an MCP client (Claude Desktop, a custom agent, or any MCP-compatible tool) to the server's HTTP endpoint
2. The client reads the tool manifest — seven tools, each with typed parameters and descriptions
3. When the AI decides a tool is relevant, it sends a structured POST to `/mcp`
4. The server calls `yfinance`, normalizes the response (handling NaN, None, and missing fields), and returns structured JSON
5. The response streams back to the client over SSE — the same connection, no polling required

The server uses Streamable HTTP transport, which means it runs as a normal web server. You can test individual tools with `curl`, inspect responses in a browser, or point any MCP-compatible client at it over a network.

---

## Tech Stack

- **Language:** Python 3.11+
- **MCP Framework:** FastMCP (Anthropic's official MCP SDK)
- **Data:** yfinance — wraps Yahoo Finance's internal APIs, no API key required
- **Transport:** Streamable HTTP / SSE
- **Server:** Uvicorn (ASGI)
- **Config:** python-dotenv

---

## Repository Layout

```
yahoo-finance-mcp/
├── server.py           # MCP server and all 7 tool definitions
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variable template
└── README.md
```

---

## Getting Started (Local)

### 1. Clone the repo

```bash
git clone https://github.com/vipin-mohan/agent-lab.git
cd agent-lab/yahoo-finance-mcp
```

### 2. (Recommended) Create and activate a virtual environment

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # PowerShell on Windows
# or
source .venv/bin/activate      # macOS / Linux
```

### 3. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. (Optional) Configure environment

```bash
cp .env.example .env
# Edit .env if you want a port other than 8000
```

### 5. Start the server

```bash
python server.py
```

You should see:

```
============================================================
  Yahoo Finance MCP Server
============================================================
  MCP endpoint : http://0.0.0.0:8000/mcp
  Health check : http://localhost:8000/health
  Transport    : Streamable HTTP (SSE)
============================================================
```

Confirm it's running:

```bash
curl http://localhost:8000/health
# {"status":"ok","server":"yahoo-finance-mcp"}
```

---

## Connecting to Claude Desktop

Open your Claude Desktop MCP config file:

- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

### Option A — Local server

Add the following inside the `mcpServers` object:

```json
{
  "mcpServers": {
    "yahoo-finance": {
      "transport": {
        "type": "http",
        "url": "http://localhost:8000/mcp"
      }
    }
  }
}
```

Restart Claude Desktop. The seven Yahoo Finance tools will appear in the tool picker automatically.

### Option B — Hosted version (Hugging Face Spaces)

Claude Desktop cannot connect directly to a remote HTTP/SSE server, but it can proxy through [`mcp-remote`](https://github.com/geelen/mcp-remote). This requires Node.js installed locally.

```json
{
  "mcpServers": {
    "yahoo-finance": {
      "command": "npx",
      "args": [
        "mcp-remote",
        "https://vipinmohan-yahoo-finance-mcp.hf.space/mcp"
      ]
    }
  }
}
```

`npx` will download `mcp-remote` on first run. No separate install step needed beyond having Node.js available.

---

## Example Prompts

Once connected, try these in Claude Desktop:

1. **"What is Apple's current stock price, P/E ratio, and 52-week range?"**
   — calls `get_stock_quote("AAPL")`

2. **"Give me a company overview for NVIDIA — sector, employees, top executives, and a one-paragraph description."**
   — calls `get_stock_info("NVDA")`

3. **"Show me Tesla's daily price history for the last 3 months. How did it perform?"**
   — calls `get_price_history("TSLA", period="3mo", interval="1d")`

4. **"Compare Amazon and Microsoft's revenue and net income over the last four years."**
   — calls `get_income_statement("AMZN")` and `get_income_statement("MSFT")`

5. **"Did NVIDIA beat earnings estimates last quarter? What was the EPS surprise?"**
   — calls `get_earnings("NVDA")`

6. **"What is Meta's free cash flow trend over the last four years?"**
   — calls `get_cash_flow("META")`

7. **"Pull JPMorgan's latest balance sheet and calculate its debt-to-equity ratio."**
   — calls `get_balance_sheet("JPM")`

---

## Responsible Use

Data returned by this server is sourced from Yahoo Finance via the `yfinance` library. Yahoo Finance data is intended for **personal and educational use only** — it is not licensed for commercial redistribution, automated trading systems, or resale. If you are building a production application that depends on financial data, use a licensed data vendor. Be respectful of request volume; `yfinance` is a scraping library, not an official API.

---

## About the Author

I'm Vipin Mohan — Head of Product for Agentic AI at AWS, UC Berkeley Haas MBA coach, and co-founder of a smart water tech startup. I've shipped 15+ AI agent integrations using MCP and A2A protocols, and I coach MBA students at Haas on breaking into product management.

This repo is where I build things outside of work: real apps, real use cases, using the same AI APIs and agent patterns I work with professionally. Finance and agentic AI felt like a natural intersection — and `yfinance` makes the barrier to entry zero.

[LinkedIn](https://www.linkedin.com/in/vipinmohan) · [GitHub](https://github.com/vipin-mohan)
