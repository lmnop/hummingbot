from decimal import Decimal
from typing import (
    Any,
    Dict,
    Optional,
)
import asyncio
from hummingbot.core.event.events import (
    OrderType,
    TradeType
)
from hummingbot.connector.in_flight_order_base import InFlightOrderBase

s_decimal_0 = Decimal(0)


class SfoxInFlightOrder(InFlightOrderBase):
    def __init__(self,
                 client_order_id: str,
                 exchange_order_id: Optional[str],
                 trading_pair: str,
                 order_type: OrderType,
                 trade_type: TradeType,
                 price: Decimal,
                 amount: Decimal,
                 initial_state: str = "new"):
        super().__init__(
            client_order_id,
            exchange_order_id,
            trading_pair,
            order_type,
            trade_type,
            price,
            amount,
            initial_state,
        )
        # self.trade_update_id_set = set()
        # self.order_update_id_set = set()
        self.cancelled_event = asyncio.Event()

    @property
    def is_done(self) -> bool:
        return self.last_state in {"cancel pending", "filled", "done", "canceled", "rejected"}

    @property
    def is_failure(self) -> bool:
        return self.last_state in {"rejected", "cancel pending"}

    @property
    def is_cancelled(self) -> bool:
        return self.last_state in {"canceled", "cancel pending"}

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> InFlightOrderBase:
        """
        :param data: json data from API
        :return: formatted InFlightOrder
        """
        retval = SfoxInFlightOrder(
            data["client_order_id"],
            data["exchange_order_id"],
            data["trading_pair"],
            getattr(OrderType, data["order_type"]),
            getattr(TradeType, data["trade_type"]),
            Decimal(data["price"]),
            Decimal(data["amount"]),
            data["last_state"]
        )
        retval.executed_amount_base = Decimal(data["executed_amount_base"])
        retval.executed_amount_quote = Decimal(data["executed_amount_quote"])
        retval.fee_asset = data["fee_asset"]
        retval.fee_paid = Decimal(data["fee_paid"])
        retval.last_state = data["last_state"]
        return retval

    def update_with_order_update(self, order_update: Dict[str, Any]) -> bool:
        """
        Updates the in flight order with order update (from private/get-order-detail end point)
        return: True if the order gets updated otherwise False
        Example Order:
        {
            "id": 573600369,
            "side_id": 500,
            "action": "Buy",
            "algorithm_id": 201,
            "algorithm": "Limit",
            "type": "Limit",
            "pair": "btcusd",
            "quantity": 0.00324,
            "price": 42302.01,
            "amount": 0,
            "net_market_amount": 0,
            "filled": 0,
            "vwap": 0,
            "filled_amount": 0,
            "fees": 0,
            "net_proceeds": 0,
            "status": "Started",
            "status_code": 100,
            "routing_option": "BestPrice",
            "routing_type": "NetPrice",
            "time_in_force": "GTC",
            "expires": null,
            "dateupdated": "2021-08-16T18:52:58.000Z",
            "client_order_id": "HBOT-B-BCUD-1629139970003913",
            "user_tx_id": "HBOT-B-BCUD-1629139970003913",
            "o_action": "Buy",
            "algo_id": 201,
            "algorithm_options": null,
            "destination": ""
        }
        """
        # Update order execution status
        self.last_state = order_update.get("status", "").lower()

        if 'filled' not in order_update:
            return False

        # Set executed amounts
        executed_amount_base = Decimal(str(order_update["filled"]))
        executed_price = Decimal(str(order_update.get("price", "0")))
        if executed_amount_base <= s_decimal_0 or executed_price <= s_decimal_0:
            # Skip these.
            return False

        self.executed_amount_quote = executed_amount_base * executed_price
        self.executed_amount_base = executed_amount_base
        if 'fees' in order_update:
            self.fee_paid = Decimal(str(order_update.get("fees")))
        if not self.fee_asset:
            self.fee_asset = self.quote_asset
        return True
