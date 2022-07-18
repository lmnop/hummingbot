#!/usr/bin/env python

import asyncio
import logging
from typing import (
    Optional,
    List,
)
from hummingbot.core.data_type.user_stream_tracker_data_source import UserStreamTrackerDataSource
from hummingbot.logger import HummingbotLogger
from hummingbot.core.api_throttler.async_throttler import AsyncThrottler
from hummingbot.core.data_type.user_stream_tracker import (
    UserStreamTracker
)
from hummingbot.core.utils.async_utils import (
    safe_ensure_future,
    safe_gather,
)
from hummingbot.connector.exchange.sfox.sfox_api_user_stream_data_source import \
    SfoxAPIUserStreamDataSource
from hummingbot.connector.exchange.sfox.sfox_auth import SfoxAuth
from hummingbot.connector.exchange.sfox.sfox_constants import Constants


class SfoxUserStreamTracker(UserStreamTracker):
    _cbpust_logger: Optional[HummingbotLogger] = None

    @classmethod
    def logger(cls) -> HummingbotLogger:
        if cls._bust_logger is None:
            cls._bust_logger = logging.getLogger(__name__)
        return cls._bust_logger

    def __init__(self,
                 throttler: Optional[AsyncThrottler] = None,
                 sfox_auth: Optional[SfoxAuth] = None,
                 trading_pairs: Optional[List[str]] = []):
        super().__init__()
        self._sfox_auth: SfoxAuth = sfox_auth
        self._trading_pairs: List[str] = trading_pairs
        self._ev_loop: asyncio.events.AbstractEventLoop = asyncio.get_event_loop()
        self._data_source: Optional[UserStreamTrackerDataSource] = None
        self._user_stream_tracking_task: Optional[asyncio.Task] = None
        self._throttler = throttler or AsyncThrottler(Constants.RATE_LIMITS)

    @property
    def data_source(self) -> UserStreamTrackerDataSource:
        """
        *required
        Initializes a user stream data source (user specific order diffs from live socket stream)
        :return: OrderBookTrackerDataSource
        """
        if not self._data_source:
            self._data_source = SfoxAPIUserStreamDataSource(
                throttler=self._throttler,
                sfox_auth=self._sfox_auth,
                trading_pairs=self._trading_pairs
            )
        return self._data_source

    @property
    def exchange_name(self) -> str:
        """
        *required
        Name of the current exchange
        """
        return Constants.EXCHANGE_NAME

    async def start(self):
        """
        *required
        Start all listeners and tasks
        """
        self._user_stream_tracking_task = safe_ensure_future(
            self.data_source.listen_for_user_stream(self._ev_loop, self._user_stream)
        )
        await safe_gather(self._user_stream_tracking_task)
