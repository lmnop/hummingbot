from hummingbot.core.api_throttler.data_types import RateLimit, LinkedLimitWeightPair


# A single source of truth for constant variables related to the exchange
class Constants:
    EXCHANGE_NAME = "sfox"
    REST_URL = "https://api.sfox.com/v1"
    REST_URL_AUTH = "/v1"
    WS_URL = "wss://ws.sfox.com/ws"

    HBOT_BROKER_ID = "hummingbot"
    HBOT_ORDER_ID = "HBOT"

    ENDPOINT = {
        # Public Endpoints
        "NETWORK_CHECK": "health",
        "TICKER": "markets/tickers",
        "TICKER_SINGLE": "markets/ticker/{trading_pair}",
        "SYMBOL": "markets/tickers",
        "ORDER_BOOK": "markets/orderbook/{trading_pair}",
        "ORDER_CREATE": "orders/{side}",
        "ORDER_DELETE": "orders/{id}",
        "ORDER_STATUS": "orders/{id}",
        "USER_ORDERS": "orders",
        "USER_BALANCES": "user/balance",
    }

    WS_SUB = {
        "TRADES": "trades.sfox.{trading_pair}",
        "ORDERS_SNAPSHOT": "orderbook.net.{trading_pair}",
        "USER_ORDERS": "private.user.open-orders",
        "USER_BALANCE": "private.user.balances",

    }

    WS_METHOD_AUTHENTICATE = "authenticate"
    WS_METHOD_SUBSCRIBE = "subscribe"
    WS_METHOD_UNSUBSCRIBE = "unsubscribe"

    FIAT_ASSETS = ["GBP", "USD"]

    # Timeouts
    MESSAGE_TIMEOUT = 30.0
    PING_TIMEOUT = 10.0
    API_CALL_TIMEOUT = 10.0
    API_MAX_RETRIES = 4

    # Intervals
    # Only used when nothing is received from WS
    SHORT_POLL_INTERVAL = 5
    # 60 seconds should be fine since we get trades, orders and balances via WS
    LONG_POLL_INTERVAL = 60
    # One minute should be fine since we get trades, orders and balances via WS
    UPDATE_ORDER_STATUS_INTERVAL = 60
    # One minute should be fine since we get balances via WS
    UPDATE_BALANCE_INTERVAL = 60
    # 10 minute interval to update trading rules, these would likely never change whilst running.
    INTERVAL_TRADING_RULES = 600

    # Trading pair splitter regex
    TRADING_PAIR_SPLITTER = r"^(\w+)(btc|gbp|pax|usdc|usdt|usd|dai)$"

    RL_TIME_INTERVAL = 60
    RL_ID_HTTP_ENDPOINTS = "AllHTTP"
    RL_ID_WS_ENDPOINTS = "AllWs"
    RL_ID_WS_AUTH = "AllWsAuth"
    RL_ID_TICKER = "Ticker"
    RL_ID_ORDER_BOOK = "OrderBook"
    RL_ID_ORDER_CREATE = "OrderCreate"
    RL_ID_ORDER_DELETE = "OrderDelete"
    RL_ID_ORDER_STATUS = "OrderStatus"
    RL_HTTP_LIMIT = 60000
    RL_WS_LIMIT = 500
    RATE_LIMITS = [
        RateLimit(
            limit_id=RL_ID_HTTP_ENDPOINTS,
            limit=RL_HTTP_LIMIT,
            time_interval=RL_TIME_INTERVAL
        ),
        # http
        RateLimit(
            limit_id=ENDPOINT["NETWORK_CHECK"],
            limit=RL_HTTP_LIMIT,
            time_interval=RL_TIME_INTERVAL,
            linked_limits=[LinkedLimitWeightPair(RL_ID_HTTP_ENDPOINTS)],
        ),
        RateLimit(
            limit_id=RL_ID_TICKER,
            limit=RL_HTTP_LIMIT,
            time_interval=RL_TIME_INTERVAL,
            linked_limits=[LinkedLimitWeightPair(RL_ID_HTTP_ENDPOINTS)],
        ),
        RateLimit(
            limit_id=ENDPOINT["SYMBOL"],
            limit=RL_HTTP_LIMIT,
            time_interval=RL_TIME_INTERVAL,
            linked_limits=[LinkedLimitWeightPair(RL_ID_HTTP_ENDPOINTS)],
        ),
        RateLimit(
            limit_id=RL_ID_ORDER_BOOK,
            limit=RL_HTTP_LIMIT,
            time_interval=RL_TIME_INTERVAL,
            linked_limits=[LinkedLimitWeightPair(RL_ID_HTTP_ENDPOINTS)],
        ),
        RateLimit(
            limit_id=RL_ID_ORDER_CREATE,
            limit=RL_HTTP_LIMIT,
            time_interval=RL_TIME_INTERVAL,
            linked_limits=[LinkedLimitWeightPair(RL_ID_HTTP_ENDPOINTS)],
        ),
        RateLimit(
            limit_id=RL_ID_ORDER_DELETE,
            limit=RL_HTTP_LIMIT,
            time_interval=RL_TIME_INTERVAL,
            linked_limits=[LinkedLimitWeightPair(RL_ID_HTTP_ENDPOINTS)],
        ),
        RateLimit(
            limit_id=RL_ID_ORDER_STATUS,
            limit=RL_HTTP_LIMIT,
            time_interval=RL_TIME_INTERVAL,
            linked_limits=[LinkedLimitWeightPair(RL_ID_HTTP_ENDPOINTS)],
        ),
        RateLimit(
            limit_id=ENDPOINT["USER_ORDERS"],
            limit=RL_HTTP_LIMIT,
            time_interval=RL_TIME_INTERVAL,
            linked_limits=[LinkedLimitWeightPair(RL_ID_HTTP_ENDPOINTS)],
        ),
        RateLimit(
            limit_id=ENDPOINT["USER_BALANCES"],
            limit=RL_HTTP_LIMIT,
            time_interval=RL_TIME_INTERVAL,
            linked_limits=[LinkedLimitWeightPair(RL_ID_HTTP_ENDPOINTS)],
        ),
        # ws
        RateLimit(limit_id=RL_ID_WS_AUTH, limit=50, time_interval=RL_TIME_INTERVAL),
        RateLimit(limit_id=RL_ID_WS_ENDPOINTS, limit=RL_WS_LIMIT, time_interval=RL_TIME_INTERVAL),
        RateLimit(
            limit_id=WS_METHOD_AUTHENTICATE,
            limit=50,
            time_interval=RL_TIME_INTERVAL,
            linked_limits=[LinkedLimitWeightPair(RL_ID_WS_AUTH)],
        ),
        RateLimit(
            limit_id=WS_METHOD_SUBSCRIBE,
            limit=RL_WS_LIMIT,
            time_interval=RL_TIME_INTERVAL,
            linked_limits=[LinkedLimitWeightPair(RL_ID_WS_ENDPOINTS)],
        ),
        RateLimit(
            limit_id=WS_METHOD_UNSUBSCRIBE,
            limit=RL_WS_LIMIT,
            time_interval=RL_TIME_INTERVAL,
            linked_limits=[LinkedLimitWeightPair(RL_ID_WS_ENDPOINTS)],
        ),
    ]
