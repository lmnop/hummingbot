#!/usr/bin/env python

import sys
import asyncio
import logging
import unittest
import conf

from os.path import join, realpath
from hummingbot.connector.exchange.sfox.sfox_user_stream_tracker import SfoxUserStreamTracker
from hummingbot.connector.exchange.sfox.sfox_auth import SfoxAuth
from hummingbot.core.utils.async_utils import safe_ensure_future
from hummingbot.logger.struct_logger import METRICS_LOG_LEVEL


sys.path.insert(0, realpath(join(__file__, "../../../../../")))
logging.basicConfig(level=METRICS_LOG_LEVEL)


class SfoxUserStreamTrackerUnitTest(unittest.TestCase):
    api_key = conf.sfox_api_key

    @classmethod
    def setUpClass(cls):
        cls.ev_loop: asyncio.BaseEventLoop = asyncio.get_event_loop()
        cls.trading_pairs = ["BTC-USDT"]
        cls.user_stream_tracker: SfoxUserStreamTracker = SfoxUserStreamTracker(
            sfox_auth=SfoxAuth(cls.api_key),
            trading_pairs=cls.trading_pairs)
        cls.user_stream_tracker_task: asyncio.Task = safe_ensure_future(cls.user_stream_tracker.start())

    def test_user_stream(self):
        # Wait process some msgs.
        print("Sleeping for 30s to gather some user stream messages.")
        self.ev_loop.run_until_complete(asyncio.sleep(30.0))
        print(self.user_stream_tracker.user_stream)
