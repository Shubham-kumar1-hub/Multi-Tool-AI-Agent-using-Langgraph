import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import time
from backend.Agent_backend import get_stock_price

print("First call (should be slow — hits the real API):")
start = time.time()
result1 = get_stock_price.invoke({"symbol": "AAPL"})
duration1 = time.time() - start
print(f"  Took {duration1:.2f}s")
print(f"  Result: {result1}")

print("\nSecond call, same symbol (should be fast — hits the cache):")
start = time.time()
result2 = get_stock_price.invoke({"symbol": "AAPL"})
duration2 = time.time() - start
print(f"  Took {duration2:.2f}s")
print(f"  Result: {result2}")

print(f"\nSpeedup: {duration1 / duration2:.1f}x faster" if duration2 > 0 else "\nSecond call was instant (0.00s)")