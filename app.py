app_code = """
from flask import Flask, render_template, request
import requests
import pandas as pd
import numpy as np

app = Flask(__name__)

COINS = ["btc_idr", "eth_idr", "bnb_idr", "xrp_idr", "doge_idr", "sol_idr", "ada_idr", "ltc_idr", "cng_idr", "dupe_idr"]

def fetch_data():
    url = "https://indodax.com/api/ticker_all"
    r = requests.get(url, timeout=10)
    return r.json().get("tickers", {})

def analyze_coin(coin_data):
    try:
        closes = [float(coin_data['last']) for _ in range(20)]
        df = pd.DataFrame(closes, columns=['close'])
        df['mean'] = df['close'].rolling(20).mean()
        df['std'] = df['close'].rolling(20).std()
        df['lower'] = df['mean'] - (2 * df['std'])
        df['upper'] = df['mean'] + (2 * df['std'])
        close = df['close'].iloc[-1]
        lower = df['lower'].iloc[-1]
        signal = 'Buy Area' if close <= lower * 1.02 else 'Wait'
        return signal
    except Exception:
        return 'Error ❌'

@app.route('/')
def index():
    tf = request.args.get('tf', '15m')
    data = fetch_data()
    rows = []
    for coin in COINS:
        coin_data = data.get(coin, {})
        if not coin_data:
            rows.append((coin.upper(), '-', '-', 'Error ❌'))
            continue
        price = float(coin_data.get('last', 0))
        vol = float(coin_data.get('vol_idr', 0))
        signal = analyze_coin(coin_data)
        rows.append((coin.upper(), f"{price:,.0f}", f"{vol:,.0f}", signal))
    return render_template('index.html', rows=rows, tf=tf)

if __name__ == '__main__':
    app.run()
