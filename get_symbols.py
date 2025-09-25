import time
import ccxt
import os


exchange = ccxt.bybit({
    'options': {'defaultType': 'future'}
})
markets = exchange.load_markets()

symbols = [
    f"{symbol}" for symbol, data in markets.items()
    if data.get("type") == "swap" and data.get("quote") == "USDT"
]

def clear_console():
    """Clears the console screen."""
    # For Windows
    if os.name == 'nt':
        os.system('cls')
    # For macOS and Linux
    else:
        os.system('clear')



with open("allsymbols.txt", "w") as f:
    for symbol in symbols:
        f.write(symbol + "\n")
