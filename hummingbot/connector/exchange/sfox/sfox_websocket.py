#!/usr/bin/env python
import asyncio
import logging
import websockets
import json
from typing import (
    Any,
    AsyncIterable,
    Dict,
    List,
    Optional,
)
from hummingbot.core.api_throttler.async_throttler import AsyncThrottler
from websockets.exceptions import ConnectionClosed
from hummingbot.logger import HummingbotLogger
from hummingbot.connector.exchange.sfox.sfox_constants import Constants
from hummingbot.connector.exchange.sfox.sfox_auth import SfoxAuth
from hummingbot.connector.exchange.sfox.sfox_utils import (
    SfoxAPIError,
)

# reusable websocket class
# ToDo: We should eventually remove this class, and instantiate web socket connection normally (see Binance for example)


class SfoxWebsocket():
    _logger: Optional[HummingbotLogger] = None

    @classmethod
    def logger(cls) -> HummingbotLogger:
        if cls._logger is None:
            cls._logger = logging.getLogger(__name__)
        return cls._logger

    def __init__(self,
                 auth: Optional[SfoxAuth] = None,
                 throttler: Optional[AsyncThrottler] = None):
        self._auth: Optional[SfoxAuth] = auth
        self._isPrivate = True if self._auth is not None else False
        self._WS_URL = Constants.WS_URL
        self._client: Optional[websockets.WebSocketClientProtocol] = None
        self._is_subscribed = False
        self._throttler = throttler or AsyncThrottler(Constants.RATE_LIMITS)

    @property
    def is_subscribed(self):
        return self._is_subscribed

    # connect to exchange
    async def connect(self):
        self._client = await websockets.connect(self._WS_URL)

        # if auth class was passed into websocket class
        # we need to emit authenticated requests
        if self._isPrivate:
            auth_params = {
                'apiKey': self._auth.get_ws_key(),
            }
            await self._emit(Constants.WS_METHOD_AUTHENTICATE, auth_params)
            raw_msg_str: str = await asyncio.wait_for(self._client.recv(), timeout=Constants.MESSAGE_TIMEOUT)
            json_msg = json.loads(raw_msg_str)
            if json_msg.get("type") != 'success':
                err_msg = json_msg.get('error', {}).get('message', json_msg)
                raise SfoxAPIError({"error": f"Failed to authenticate to websocket - {err_msg}."})

        return self._client

    # disconnect from exchange
    async def disconnect(self):
        if self._client is None:
            return

        await self._client.close()

    # receive & parse messages
    async def _messages(self) -> AsyncIterable[Any]:
        try:
            while True:
                try:
                    raw_msg_str: str = await asyncio.wait_for(self._client.recv(), timeout=Constants.MESSAGE_TIMEOUT)
                    try:
                        msg = json.loads(raw_msg_str)

                        # Raise API error for login failures.
                        if msg.get('error', None) is not None:
                            err_msg = msg.get('error', {}).get('message', msg['error'])
                            raise SfoxAPIError({"error_code": "WSS_ERROR", "error": f"Error received via websocket - {err_msg}."})

                        # Filter subscribed/unsubscribed messages
                        msg_event = msg.get('type', None)
                        if msg_event is not None:
                            if msg_event == 'success':
                                self._is_subscribed = True
                            yield None
                        else:
                            yield msg

                    except ValueError:
                        continue
                except asyncio.TimeoutError:
                    await asyncio.wait_for(self._client.ping(), timeout=Constants.PING_TIMEOUT)
        except asyncio.TimeoutError:
            self.logger().warning("WebSocket ping timed out. Going to reconnect...")
            return
        except ConnectionClosed:
            return
        finally:
            await self.disconnect()

    # emit messages
    async def _emit(self, method: str, data: Optional[Dict[str, Any]] = {}) -> int:
        payload = {
            "type": method,
            **data,
        }
        async with self._throttler.execute_task(method):
            await self._client.send(json.dumps(payload))
        return True

    # request via websocket
    async def request(self, method: str, data: Optional[Dict[str, Any]] = {}) -> int:
        return await self._emit(method, data)

    # subscribe to a channel
    async def subscribe(self,
                        channels: List[str],
                        trading_pairs: Optional[List[str]] = None) -> bool:
        if trading_pairs is not None:
            ws_params = {
                'feeds': [channel.format(trading_pair=pair) for pair in trading_pairs
                          for channel in channels],
            }
        else:
            ws_params = {
                'feeds': channels,
            }
        return await self.request(Constants.WS_METHOD_SUBSCRIBE, ws_params)

    # unsubscribe to a channel
    async def unsubscribe(self,
                          channel: str,
                          trading_pairs: Optional[List[str]] = None) -> bool:
        if trading_pairs is not None:
            ws_params = {
                'feeds': [channel.format(trading_pair=pair) for pair in trading_pairs],
            }
        else:
            ws_params = {
                'feeds': [channel],
            }
        return await self.request(Constants.WS_METHOD_UNSUBSCRIBE, ws_params)

    # listen to messages by channel
    async def on_message(self) -> AsyncIterable[Any]:
        async for msg in self._messages():
            yield msg
