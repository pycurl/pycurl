#! /usr/bin/env python
"""Drive a single transfer through ``AsyncCurlMulti`` from asyncio.

Run with::

    python examples/async_multi.py [URL]
"""

from __future__ import annotations

import asyncio
import sys
from io import BytesIO

import pycurl


async def main(url: str) -> None:
    async with pycurl.AsyncCurlMulti() as multi:
        curl = pycurl.Curl()
        curl.setopt(pycurl.URL, url)
        body = BytesIO()
        curl.setopt(pycurl.WRITEDATA, body)
        try:
            await multi.perform(curl)
            print(f"status: {curl.getinfo(pycurl.RESPONSE_CODE)}")
            print(f"bytes:  {len(body.getvalue())}")
        finally:
            curl.close()


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "https://example.com/"
    asyncio.run(main(target))
