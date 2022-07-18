#!/usr/bin/env python
import time
import asyncio
import logging
from typing import (
    Any,
    AsyncIterable,
    List,
    Optional,
)
from hummingbot.core.api_throttler.async_throttler import AsyncThrottler
from hummingbot.core.data_type.user_stream_tracker_data_source import UserStreamTrackerDataSource
from hummingbot.logger import HummingbotLogger
from .sfox_constants import Constants
from .sfox_auth import SfoxAuth
from .sfox_utils import (
    SfoxAPIError,
)
from .sfox_websocket import SfoxWebsocket


class SfoxAPIUserStreamDataSource(UserStreamTrackerDataSource):

    _logger: Optional[HummingbotLogger] = None

    @classmethod
    def logger(cls) -> HummingbotLogger:
        if cls._logger is None:
            cls._logger = logging.getLogger(__name__)
        return cls._logger

    def __init__(self, throttler: AsyncThrottler, sfox_auth: SfoxAuth, trading_pairs: Optional[List[str]] = []):
        self._sfox_auth: SfoxAuth = sfox_auth
        self._ws: SfoxWebsocket = None
        self._trading_pairs = trading_pairs
        self._current_listen_key = None
        self._listen_for_user_stream_task = None
        self._last_recv_time: float = 0
        self._throttler = throttler
        super().__init__()

    @property
    def last_recv_time(self) -> float:
        return self._last_recv_time

    async def _listen_to_orders_trades_balances(self) -> AsyncIterable[Any]:
        """
        Subscribe to active orders via web socket
        """

        try:
            self._ws = SfoxWebsocket(self._sfox_auth, throttler=self._throttler)

            await self._ws.connect()

            user_channels = [
                Constants.WS_SUB['USER_BALANCE'],
                Constants.WS_SUB['USER_ORDERS'],
            ]

            await self._ws.subscribe(user_channels)

            async for msg in self._ws.on_message():
                self._last_recv_time = time.time()

                if msg is None:
                    # Skip empty subscribed/unsubscribed messages
                    continue

                if msg.get("payload", None) is None:
                    continue
                elif msg.get("recipient", None) in user_channels:
                    yield msg
        except Exception as e:
            raise e
        finally:
            await self._ws.disconnect()
            await asyncio.sleep(5)

    async def listen_for_user_stream(self, ev_loop: asyncio.BaseEventLoop, output: asyncio.Queue) -> AsyncIterable[Any]:
        """
        *required
        Subscribe to user stream via web socket, and keep the connection open for incoming messages
        :param ev_loop: ev_loop to execute this function in
        :param output: an async queue where the incoming messages are stored
        """

        while True:
            try:
                async for msg in self._listen_to_orders_trades_balances():
                    output.put_nowait(msg)
            except asyncio.CancelledError:
                raise
            except SfoxAPIError as e:
                self.logger().error(e.error_message, exc_info=True)
                raise
            except Exception:
                self.logger().error(
                    f"Unexpected error with {Constants.EXCHANGE_NAME} WebSocket connection. "
                    "Retrying after 30 seconds...", exc_info=True)
                await asyncio.sleep(30.0)
