#!/usr/bin/env python

from typing import (
    Dict,
    List,
    Optional,
)

from hummingbot.core.data_type.order_book_row import OrderBookRow
from hummingbot.core.data_type.order_book_message import (
    OrderBookMessage,
    OrderBookMessageType,
)
from .sfox_constants import Constants
from .sfox_utils import (
    convert_from_exchange_trading_pair,
)


class SfoxOrderBookMessage(OrderBookMessage):
    def __new__(
        cls,
        message_type: OrderBookMessageType,
        content: Dict[str, any],
        timestamp: Optional[float] = None,
        *args,
        **kwargs,
    ):
        if timestamp is None:
            if message_type is OrderBookMessageType.SNAPSHOT:
                raise ValueError("timestamp must not be None when initializing snapshot messages.")
            timestamp = content["timestamp"]

        return super(SfoxOrderBookMessage, cls).__new__(
            cls, message_type, content, timestamp=timestamp, *args, **kwargs
        )

    @property
    def update_id(self) -> int:
        if self.type in [OrderBookMessageType.DIFF, OrderBookMessageType.SNAPSHOT]:
            return int(self.timestamp)
        else:
            return -1

    @property
    def trade_id(self) -> int:
        if self.type is OrderBookMessageType.TRADE:
            return int(self.timestamp)
        return -1

    @property
    def trading_pair(self) -> str:
        if "trading_pair" in self.content:
            return self.content["trading_pair"]
        elif "pair" in self.content:
            return convert_from_exchange_trading_pair(self.content["pair"])

    # The `asks` and `bids` properties are only used in the methods below.
    # They are all replaced or unused in this connector:
    #     OrderBook.restore_from_snapshot_and_diffs
    #     OrderBookTracker._track_single_book
    #     MockAPIOrderBookDataSource.get_tracking_pairs
    @property
    def asks(self) -> List[OrderBookRow]:
        raise NotImplementedError(Constants.EXCHANGE_NAME + " order book uses active_order_tracker.")

    @property
    def bids(self) -> List[OrderBookRow]:
        raise NotImplementedError(Constants.EXCHANGE_NAME + " order book uses active_order_tracker.")

    def __eq__(self, other) -> bool:
        return self.type == other.type and self.timestamp == other.timestamp

    def __lt__(self, other) -> bool:
        if self.timestamp != other.timestamp:
            return self.timestamp < other.timestamp
        else:
            """
            If timestamp is the same, the ordering is snapshot < diff < trade
            """
            return self.type.value < other.type.value
