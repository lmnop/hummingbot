#!/usr/bin/env python
import sys
import asyncio
import unittest
import aiohttp
import logging
from os.path import join, realpath
from typing import Dict, Any
from hummingbot.connector.exchange.sfox.sfox_utils import aiohttp_response_with_errors
from hummingbot.logger.struct_logger import METRICS_LOG_LEVEL
from hummingbot.connector.exchange.sfox.sfox_constants import Constants
from hummingbot.connector.exchange.sfox.sfox_utils import convert_from_exchange_trading_pair

sys.path.insert(0, realpath(join(__file__, "../../../../../")))
logging.basicConfig(level=METRICS_LOG_LEVEL)


class TestAuth(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ev_loop: asyncio.BaseEventLoop = asyncio.get_event_loop()

    async def fetch_tickers(self) -> Dict[Any, Any]:
        endpoint = Constants.ENDPOINT['SYMBOL']
        http_client = aiohttp.ClientSession()
        http_status, response, request_errors = await aiohttp_response_with_errors(http_client.request(method='GET',
                                                                                                       url=f"{Constants.REST_URL}/{endpoint}"))
        await http_client.close()
        return response

    def test_order_status(self):
        result = self.ev_loop.run_until_complete(self.fetch_tickers())
        pairs = [i['pair'] for i in result.get('data', [])]
        unmatched_pairs = []
        for pair in pairs:
            matched_pair = convert_from_exchange_trading_pair(pair)
            if matched_pair is None or "none" in str(matched_pair).lower():
                print(f"\nUnmatched pair: {pair}")
                unmatched_pairs.append(pair)
        assert len(unmatched_pairs) == 0
