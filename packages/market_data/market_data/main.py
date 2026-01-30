from __future__ import annotations
import asyncio

async def run_collectors():
    # TODO: wire Binance/Coinbase WS and write to store
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(run_collectors())
