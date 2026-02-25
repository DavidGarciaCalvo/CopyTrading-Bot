import requests

def obtener_precio_binance(symbol):
    # Convertimos SOL/USDT a SOLUSDT
    symbol_formatted = symbol.replace("/", "")
    # Usamos bookTicker para obtener el precio de compra real (askPrice)
    url = f"https://api.binance.com/api/v3/ticker/bookTicker?symbol={symbol_formatted}"
    
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            # El 'askPrice' es el precio al que realmente te venderán el token
            return float(data['askPrice'])
        return None
    except Exception as e:
        print(f"⚠️ Error capturando precio: {e}")
        return None