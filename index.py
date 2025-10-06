from flask import Flask, render_template_string
import requests
import pandas as pd
import numpy as np

app = Flask(__name__)

def get_indodax_data(symbol, interval='15m', limit=100):
    url = f"https://indodax.com/api/chart/{symbol}/{interval}?limit={limit}"
    r = requests.get(url)
    data = r.json()
    df = pd.DataFrame(data['data'], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['close'] = df['close'].astype(float)
    return df

def bollinger_signal(df):
    df['MA20'] = df['close'].rolling(20).mean()
    df['STD'] = df['close'].rolling(20).std()
    df['Upper'] = df['MA20'] + (df['STD'] * 2)
    df['Lower'] = df['MA20'] - (df['STD'] * 2)

    latest = df.iloc[-1]
    signal = "Buy Area ✅" if latest['close'] <= latest['Lower'] * 1.02 else "Wait ⏳"
    return signal, latest['close'], latest['Lower'], latest['Upper']

@app.route("/")
def index():
    symbols = ["btc_idr", "eth_idr", "bnb_idr", "cng_idr", "dupe_idr"]
    results = []

    for s in symbols:
        try:
            df = get_indodax_data(s)
            sig, close, low, up = bollinger_signal(df)
            results.append({
                "pair": s.upper(),
                "price": f"{close:,.0f}",
                "lower": f"{low:,.0f}",
                "signal": sig
            })
        except Exception:
            results.append({"pair": s.upper(), "price": "-", "lower": "-", "signal": "Error"})

    html = '''
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Indodax Screener</title>
        <style>
            body { font-family: Arial; background: #f5f6fa; padding: 10px; }
            table { border-collapse: collapse; width: 100%; }
            th, td { border: 1px solid #ccc; padding: 8px; text-align: center; }
            th { background: #2f3640; color: white; }
            tr:nth-child(even) { background: #f1f2f6; }
            .buy { background: #d4edda; color: #155724; font-weight: bold; }
            .wait { background: #f8d7da; color: #721c24; font-weight: bold; }
        </style>
    </head>
    <body>
        <h2>🚀 Indodax Screener (15m - Bollinger Band)</h2>
        <table>
            <tr><th>Pair</th><th>Price</th><th>Lower BB</th><th>Signal</th></tr>
            {% for r in results %}
            <tr class="{{ 'buy' if 'Buy' in r.signal else 'wait' }}">
                <td>{{ r.pair }}</td>
                <td>{{ r.price }}</td>
                <td>{{ r.lower }}</td>
                <td>{{ r.signal }}</td>
            </tr>
            {% endfor %}
        </table>
        <p style="text-align:center;color:#555;margin-top:10px;">Update otomatis setiap refresh 🔁</p>
    </body>
    </html>
    '''
    return render_template_string(html, results=results)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
