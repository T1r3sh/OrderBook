
from decimal import Decimal
from order_book import OrderBook

import requests

ob = OrderBook()

# get some orderbook data
data = requests.get("https://api.pro.coinbase.com/products/BTC-USD/book?level=2").json()

ob.bids = {Decimal(price): size for price, size, _ in data["bids"]}
ob.asks = {Decimal(price): size for price, size, _ in data["asks"]}

# OR

for side in data:
    # there is additional data we need to ignore
    if side in {"bids", "asks"}:
        ob[side] = {Decimal(price): size for price, size, _ in data[side]}


# Data is accessible by .index(), which returns a tuple of (price, size) at that level in the book
price, size = ob.bids.index(0)
print(f"Best bid price: {price} size: {size}")

price, size = ob.asks.index(0)
print(f"Best ask price: {price} size: {size}")

print(f"The spread is {ob.asks.index(0)[0] - ob.bids.index(0)[0]}\n\n")
