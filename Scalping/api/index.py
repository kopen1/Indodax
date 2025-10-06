from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
import httpx
import math
import os

app = FastAPI()
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

# ----------------- util -----------------
def mean(arr):
    return sum(arr) / len(arr) if arr else 0

def stddev(arr):
    n = len(arr)
    if n <= 1:
        return 0.0
    m = mean(arr)
    s = sum((x - m) ** 2 for x in arr)
    return (s / (n - 1)) ** 0.5

async def safe_get(url, timeout=10):
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            r = await client.get(url)
            r.raise_for_status()
            return r.text
        except httpx.HTTPError as e:
            raise

# -------------- API endpoints --------------
@app.get("/api/markets", response_class=JSONResponse)
async def get_markets():
    """Return list of market ids from Indodax (lowercased)."""
    try:
        text = await safe_get("https://indodax.com/api/pairs")
        data = httpx.Response(200, content=text).json() if isinstance(text, bytes) else httpx._models.Response(200, content=text).json()
        # the above hack is only to parse JSON robustly; simpler:
    except Exception:
        # fallback parsing safe way:
        try:
            async with httpx.AsyncClient() as c:
                r = await c.get("https://indodax.com/api/pairs", timeout=10)
                r.raise_for_status()
                data = r.json()
        except Exception as e:
            return JSONResponse({"success": False, "error": f"Gagal mengambil daftar market: {str(e)}"}, status_code=502)

    try:
        ids = [str(item.get("id", "")).lower() for item in data]
        ids = [i for i in ids if i]
        return {"success": True, "markets": ids}
    except Exception as e:
        return JSONResponse({"success": False, "error": f"Parse error: {str(e)}"}, status_code=502)

@app.get("/api/analyze", response_class=JSONResponse)
async def analyze(pair: str = ""):
    """Analyze pair: Bollinger Bands + volume spike detection."""
    if not pair:
        raise HTTPException(status_code=400, detail="pair parameter required")
    pair = pair.lower()

    # fetch ticker and trades concurrently
    ticker_url = f"https://indodax.com/api/ticker/{pair}"
    trades_url = f"https://indodax.com/api/{pair}/trades"

    async with httpx.AsyncClient() as client:
        try:
            r1 = await client.get(ticker_url, timeout=10)
            r1.raise_for_status()
            ticker = r1.json()
        except Exception as e:
            return JSONResponse({"success": False, "error": f"Gagal fetch ticker: {str(e)}"}, status_code=502)
        try:
            r2 = await client.get(trades_url, timeout=10)
            r2.raise_for_status()
            trades = r2.json()
        except Exception as e:
            return JSONResponse({"success": False, "error": f"Gagal fetch trades: {str(e)}"}, status_code=502)

    try:
        last_price = float(ticker["ticker"]["last"])
    except Exception as e:
        return JSONResponse({"success": False, "error": f"Ticker invalid: {str(e)}"}, status_code=502)

    prices = []
    volumes = []
    for t in trades[:200]:
        try:
            p = float(t.get("price", 0))
            amt = float(t.get("amount", 0))
        except Exception:
            continue
        prices.append(p)
        volumes.append(amt * p)

    sma_period = 20
    if len(prices) < sma_period:
        return JSONResponse({"success": False, "error": "Data trades terlalu sedikit"}, status_code=422)

    sma = mean(prices[:sma_period])
    sd = stddev(prices[:sma_period])
    bb_upper = sma + 2 * sd
    bb_lower = sma - 2 * sd
    avg_volume = mean(volumes)
    recent_volume = volumes[0] if volumes else 0.0

    signal = "HOLD"
    reasons = []
    if last_price > bb_upper and recent_volume > avg_volume * 2.0:
        signal = "BUY"
        reasons.append("Price > Upper BB & volume spike")
    elif last_price < bb_lower:
        signal = "SELL"
        reasons.append("Price < Lower BB")
    else:
        if last_price > sma and recent_volume > avg_volume * 1.2:
            signal = "BUY"
            reasons.append("Above SMA & rising vol")
        elif last_price < sma and recent_volume > avg_volume * 1.2:
            signal = "SELL"
            reasons.append("Below SMA & rising vol")

    return {
        "success": True,
        "pair": pair,
        "last_price": last_price,
        "sma": sma,
        "bb_upper": bb_upper,
        "bb_lower": bb_lower,
        "avg_volume": avg_volume,
        "recent_volume": recent_volume,
        "signal": signal,
        "reasons": reasons,
    }

# ----------------- Frontend -----------------
# Simple single-page app served by FastAPI (Jinja2 templates)
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
