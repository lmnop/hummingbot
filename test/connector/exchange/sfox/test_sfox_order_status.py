#!/usr/bin/env python
import sys
import asyncio
import unittest
import aiohttp
import conf
import logging
import os
from os.path import join, realpath
from typing import Dict, Any
from hummingbot.connector.exchange.sfox.sfox_auth import SfoxAuth
from hummingbot.connector.exchange.sfox.sfox_utils import aiohttp_response_with_errors
from hummingbot.logger.struct_logger import METRICS_LOG_LEVEL
from hummingbot.connector.exchange.sfox.sfox_constants import Constants

sys.path.insert(0, realpath(join(__file__, "../../../../../")))
logging.basicConfig(level=METRICS_LOG_LEVEL)


class TestAuth(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ev_loop: asyncio.BaseEventLoop = asyncio.get_event_loop()
        api_key = conf.sfox_api_key
        cls.auth = SfoxAuth(api_key)
        cls.exchange_order_id = os.getenv("SFOX_TEST_ORDER_ID")
        cls.test_open_orders = os.getenv("SFOX_TEST_OPEN_ORDERS")

    async def fetch_order_status(self) -> Dict[Any, Any]:
        endpoint = Constants.ENDPOINT['ORDER_STATUS'].format(id=self.exchange_order_id)
        http_client = aiohttp.ClientSession()
        headers = self.auth.get_headers("GET", f"{Constants.REST_URL_AUTH}/{endpoint}")
        http_status, response, request_errors = await aiohttp_response_with_errors(http_client.request(method='GET',
                                                                                                       url=f"{Constants.REST_URL}/{endpoint}",
                                                                                                       headers=headers))
        await http_client.close()
        return response

    async def fetch_order_statuses(self) -> Dict[Any, Any]:
        endpoint = Constants.ENDPOINT['USER_ORDERS']
        http_client = aiohttp.ClientSession()
        headers = self.auth.get_headers("GET", f"{Constants.REST_URL_AUTH}/{endpoint}")
        http_status, response, request_errors = await aiohttp_response_with_errors(http_client.request(method='GET',
                                                                                                       url=f"{Constants.REST_URL}/{endpoint}",
                                                                                                       headers=headers))
        await http_client.close()
        return response

    def test_order_status(self):
        status_test_ready = all({
                                'id': self.exchange_order_id is not None and len(self.exchange_order_id),
                                }.values())
        if status_test_ready:
            result = self.ev_loop.run_until_complete(self.fetch_order_status())
            print(f"Response:\n{result}")

    def test_order_statuses(self):
        status_test_ready = all({
                                'id': self.test_open_orders is not None,
                                }.values())
        if status_test_ready:
            result = self.ev_loop.run_until_complete(self.fetch_order_statuses())
            print(f"Response:\n{result}")
