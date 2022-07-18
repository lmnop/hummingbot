#!/usr/bin/env python
import asyncio
import logging
import time
import pandas as pd
from decimal import Decimal
from typing import Optional, List, Dict, Any, Union
from hummingbot.core.api_throttler.async_throttler import AsyncThrottler
from hummingbot.core.data_type.order_book import OrderBook
from hummingbot.core.data_type.order_book_message import OrderBookMessage
from hummingbot.core.data_type.order_book_tracker_data_source import OrderBookTrackerDataSource
from hummingbot.logger import HummingbotLogger
from .sfox_constants import Constants
from .sfox_active_order_tracker import SfoxActiveOrderTracker
from .sfox_order_book import SfoxOrderBook
from .sfox_websocket import SfoxWebsocket
from .sfox_utils import (
    convert_to_exchange_trading_pair,
    convert_from_exchange_trading_pair,
    api_call_with_retries,
    SfoxAPIError,
    str_date_to_ts,
)


class SfoxAPIOrderBookDataSource(OrderBookTrackerDataSource):
    _logger: Optional[HummingbotLogger] = None

    @classmethod
    def logger(cls) -> HummingbotLogger:
        if cls._logger is None:
            cls._logger = logging.getLogger(__name__)
        return cls._logger

    def __init__(self,
                 throttler: Optional[AsyncThrottler] = None,
                 trading_pairs: List[str] = None,
                 ):
        super().__init__(trading_pairs)
        self._throttler = throttler or self._get_throttler_instance()
        self._trading_pairs: List[str] = trading_pairs
        self._snapshot_msg: Dict[str, any] = {}

    @classmethod
    def _get_throttler_instance(cls) -> AsyncThrottler:
        throttler = AsyncThrottler(Constants.RATE_LIMITS)
        return throttler

    @classmethod
    async def get_last_traded_prices(cls,
                                     trading_pairs: List[str],
                                     throttler: Optional[AsyncThrottler] = None) -> Dict[str, Decimal]:
        throttler = throttler or cls._get_throttler_instance()
        results = {}
        endpoint = Constants.ENDPOINT["TICKER"]
        if len(trading_pairs) == 1:
            endpoint = Constants.ENDPOINT["TICKER_SINGLE"].format(trading_pair=convert_to_exchange_trading_pair(trading_pairs[0]))
        tickers: Union[List[Dict[Any]], Dict[Any]] = await api_call_with_retries("GET", endpoint, throttler=throttler, limit_id=Constants.RL_ID_TICKER)
        if isinstance(tickers, dict):
            tickers: List[Dict[Any]] = tickers.get('data', [])
        for trading_pair in trading_pairs:
            ex_pair: str = convert_to_exchange_trading_pair(trading_pair)
            ticker: Dict[Any] = list([tic for tic in tickers if tic['pair'] == ex_pair])[0]
            results[trading_pair]: Decimal = Decimal(str(ticker["last"]))
        return results

    @classmethod
    async def fetch_trading_pairs(cls, throttler: Optional[AsyncThrottler] = None) -> List[str]:
        throttler = throttler or cls._get_throttler_instance()
        try:
            symbols: List[Dict[str, Any]] = await api_call_with_retries("GET", Constants.ENDPOINT["SYMBOL"], throttler=throttler)
            trading_pairs: List[str] = list([convert_from_exchange_trading_pair(sym["pair"]) for sym in symbols.get('data', [])])
            # Filter out unmatched pairs so nothing breaks
            return [sym for sym in trading_pairs if sym is not None]
        except Exception:
            # Do nothing if the request fails -- there will be no autocomplete for SFOX trading pairs
            pass
        return []

    @classmethod
    async def get_order_book_data(cls,
                                  trading_pair: str,
                                  throttler: Optional[AsyncThrottler] = None) -> Dict[str, any]:
        """
        Get whole orderbook
        """
        throttler = throttler or cls._get_throttler_instance()
        try:
            ex_pair = convert_to_exchange_trading_pair(trading_pair)
            orderbook_response: Dict[Any] = await api_call_with_retries("GET",
                                                                        Constants.ENDPOINT["ORDER_BOOK"].format(trading_pair=ex_pair),
                                                                        throttler=throttler, limit_id=Constants.RL_ID_ORDER_BOOK)
            return orderbook_response
        except SfoxAPIError as e:
            raise IOError(
                f"Error fetching OrderBook for {trading_pair} at {Constants.EXCHANGE_NAME}. "
                f"HTTP status is {e.http_status}. Error is {e.error_message}.")

    async def get_new_order_book(self, trading_pair: str) -> OrderBook:
        snapshot: Dict[str, Any] = await self.get_order_book_data(trading_pair)
        snapshot_timestamp: float = time.time()
        snapshot_msg: OrderBookMessage = SfoxOrderBook.snapshot_message_from_exchange(
            snapshot,
            snapshot_timestamp,
            metadata={"trading_pair": trading_pair})
        order_book = self.order_book_create_function()
        active_order_tracker: SfoxActiveOrderTracker = SfoxActiveOrderTracker()
        bids, asks = active_order_tracker.convert_snapshot_message_to_order_book_row(snapshot_msg)
        order_book.apply_snapshot(bids, asks, snapshot_msg.update_id)
        return order_book

    async def listen_for_trades(self, ev_loop: asyncio.BaseEventLoop, output: asyncio.Queue):
        """
        Listen for trades using websocket trade channel
        """
        while True:
            try:
                ws = SfoxWebsocket(throttler=self._throttler)
                await ws.connect()

                await ws.subscribe([Constants.WS_SUB["TRADES"]],
                                   [convert_to_exchange_trading_pair(pair) for pair in self._trading_pairs])

                async for response in ws.on_message():
                    if response is None:
                        # Skip empty subscribed/unsubscribed messages
                        continue

                    trade_data: Dict[Any] = response.get("payload", None)

                    if trade_data is None:
                        continue

                    pair: str = convert_from_exchange_trading_pair(trade_data.get("pair", None))

                    if pair is None:
                        continue

                    ts_str: str = trade_data.get("timestamp", None)
                    trade_timestamp: int = int(time.time() * 1e3) if ts_str is None else str_date_to_ts(ts_str)
                    trade_msg: OrderBookMessage = SfoxOrderBook.trade_message_from_exchange(
                        trade_data,
                        trade_timestamp,
                        metadata={"trading_pair": pair})
                    output.put_nowait(trade_msg)

            except asyncio.CancelledError:
                raise
            except Exception:
                self.logger().error("Unexpected error.", exc_info=True)
                await asyncio.sleep(5.0)
            finally:
                await ws.disconnect()

    async def listen_for_order_book_diffs(self, ev_loop: asyncio.BaseEventLoop, output: asyncio.Queue):
        """
        Listen for orderbook diffs using websocket book channel - we receive full order book snapshots
        """
        while True:
            try:
                ws = SfoxWebsocket(throttler=self._throttler)
                await ws.connect()

                await ws.subscribe([Constants.WS_SUB['ORDERS_SNAPSHOT']],
                                   [convert_to_exchange_trading_pair(pair) for pair in self._trading_pairs])

                async for response in ws.on_message():
                    if response is None:
                        # Skip empty subscribed/unsubscribed messages
                        continue

                    order_book_data: str = response.get("payload", None)

                    if order_book_data is None:
                        continue

                    timestamp: int = order_book_data.get("lastpublished", int(time.time() * 1e3))
                    pair: str = convert_from_exchange_trading_pair(order_book_data["pair"])

                    orderbook_msg: OrderBookMessage = SfoxOrderBook.snapshot_message_from_exchange(
                        order_book_data,
                        timestamp,
                        metadata={"trading_pair": pair})
                    output.put_nowait(orderbook_msg)

            except asyncio.CancelledError:
                raise
            except Exception:
                self.logger().network(
                    "Unexpected error with WebSocket connection.", exc_info=True,
                    app_warning_msg="Unexpected error with WebSocket connection. Retrying in 30 seconds. "
                                    "Check network connection.")
                await asyncio.sleep(30.0)
            finally:
                await ws.disconnect()

    async def listen_for_order_book_snapshots(self, ev_loop: asyncio.BaseEventLoop, output: asyncio.Queue):
        """
        Listen for orderbook snapshots by fetching orderbook
        """
        while True:
            try:
                for trading_pair in self._trading_pairs:
                    try:
                        snapshot: Dict[str, any] = await self.get_order_book_data(trading_pair)
                        snapshot_timestamp: int = snapshot.get('lastpublished', int(time.time() * 1e3))
                        snapshot_msg: OrderBookMessage = SfoxOrderBook.snapshot_message_from_exchange(
                            snapshot,
                            snapshot_timestamp,
                            metadata={"trading_pair": trading_pair}
                        )
                        output.put_nowait(snapshot_msg)
                        self.logger().debug(f"Saved order book snapshot for {trading_pair}")
                        # Be careful not to go above API rate limits.
                        await asyncio.sleep(5.0)
                    except asyncio.CancelledError:
                        raise
                    except Exception:
                        self.logger().network(
                            "Unexpected error with WebSocket connection.", exc_info=True,
                            app_warning_msg="Unexpected error with WebSocket connection. Retrying in 5 seconds. "
                                            "Check network connection.")
                        await asyncio.sleep(5.0)
                this_hour: pd.Timestamp = pd.Timestamp.utcnow().replace(minute=0, second=0, microsecond=0)
                next_hour: pd.Timestamp = this_hour + pd.Timedelta(hours=1)
                delta: float = next_hour.timestamp() - time.time()
                await asyncio.sleep(delta)
            except asyncio.CancelledError:
                raise
            except Exception:
                self.logger().error("Unexpected error.", exc_info=True)
                await asyncio.sleep(5.0)
