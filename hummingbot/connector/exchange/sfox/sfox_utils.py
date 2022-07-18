import aiohttp
import asyncio
import random
import re
from dateutil.parser import parse as dateparse
from typing import (
    Any,
    Dict,
    Optional,
    Tuple,
)

from hummingbot.core.utils.tracking_nonce import get_tracking_nonce
from hummingbot.client.config.config_var import ConfigVar
from hummingbot.client.config.config_methods import using_exchange
from .sfox_constants import Constants


TRADING_PAIR_SPLITTER = re.compile(Constants.TRADING_PAIR_SPLITTER)

CENTRALIZED = True

EXAMPLE_PAIR = "BTC-USD"

DEFAULT_FEES = [0.25, 0.25]


class SfoxAPIError(IOError):
    def __init__(self, error_payload: Dict[str, Any], http_status: str):
        super().__init__(str(error_payload))
        self.error_payload = error_payload
        self.http_status = http_status
        if isinstance(error_payload, dict):
            self.error_message = error_payload.get('error', error_payload)
            self.error_code = error_payload.get('error_code', error_payload)
        else:
            self.error_message = error_payload
            self.error_code = error_payload


# convert date string to timestamp
def str_date_to_ts(date: str) -> int:
    return int(dateparse(date).timestamp() * 1e3)


def split_trading_pair(trading_pair: str) -> Optional[Tuple[str, str]]:
    try:
        m = TRADING_PAIR_SPLITTER.match(trading_pair)
        return m.group(1), m.group(2)
    # Exceptions are now logged as warnings in trading pair fetcher
    except Exception:
        return None


def convert_from_exchange_trading_pair(ex_trading_pair: str) -> Optional[str]:
    regex_match = split_trading_pair(ex_trading_pair)
    if regex_match is None:
        return None
    # SFOX uses uppercase with underscore split (BTC_USDT)
    base_asset, quote_asset = split_trading_pair(ex_trading_pair)
    return f"{base_asset.upper()}-{quote_asset.upper()}"


def convert_to_exchange_trading_pair(hb_trading_pair: str) -> str:
    # SFOX uses lowercase (btcusd)
    return hb_trading_pair.replace("-", "").lower()


def is_fiat_quote_pair(hb_trading_pair: str) -> bool:
    quote_asset = hb_trading_pair.split("-")[1]
    return any(asset in quote_asset for asset in Constants.FIAT_ASSETS)


def get_new_client_order_id(is_buy: bool, trading_pair: str) -> str:
    side = "B" if is_buy else "S"
    symbols = trading_pair.split("-")
    base = symbols[0].upper()
    quote = symbols[1].upper()
    base_str = f"{base[0:1]}{base[-1]}"
    quote_str = f"{quote[0:1]}{quote[-1]}"
    return f"{Constants.HBOT_ORDER_ID}-{side}-{base_str}{quote_str}-{get_tracking_nonce()}"


def retry_sleep_time(try_count: int) -> float:
    random.seed()
    randSleep = 1 + float(random.randint(1, 10) / 100)
    return float(2 + float(randSleep * (1 + (try_count ** try_count))))


async def aiohttp_response_with_errors(request_coroutine):
    http_status, parsed_response, request_errors = None, None, False
    try:
        async with request_coroutine as response:
            http_status = response.status
            try:
                parsed_response = await response.json()
            except Exception:
                request_errors = True
                try:
                    parsed_response = str(await response.read())
                    if len(parsed_response) > 100:
                        parsed_response = f"{parsed_response[:100]} ... (truncated)"
                except Exception:
                    pass
            TempFailure = (parsed_response is None or
                           (response.status not in [200, 201, 204] and "error" not in parsed_response))
            if TempFailure:
                parsed_response = response.reason if parsed_response is None else parsed_response
                request_errors = True
    except Exception:
        request_errors = True
    return http_status, parsed_response, request_errors


async def api_call_with_retries(method,
                                endpoint,
                                params: Optional[Dict[str, Any]] = None,
                                shared_client=None,
                                throttler: Optional[Any] = None,
                                limit_id: Optional[str] = None,
                                try_count: int = 0) -> Dict[str, Any]:
    _limit_id = limit_id or endpoint
    async with throttler.execute_task(_limit_id):
        url = f"{Constants.REST_URL}/{endpoint}"
        headers = {"Content-Type": "application/json"}
        http_client = shared_client if shared_client is not None else aiohttp.ClientSession()
        # Build request coro
        response_coro = http_client.request(method=method.upper(), url=url, headers=headers,
                                            params=params, timeout=Constants.API_CALL_TIMEOUT)
        http_status, parsed_response, request_errors = await aiohttp_response_with_errors(response_coro)
        if shared_client is None:
            await http_client.close()
        if request_errors or parsed_response is None or "error" in parsed_response:
            if try_count < Constants.API_MAX_RETRIES and "error" not in parsed_response:
                try_count += 1
                time_sleep = retry_sleep_time(try_count)
                print(f"Error fetching data from {url}. HTTP status is {http_status}. "
                      f"Retrying in {time_sleep:.0f}s.")
                await asyncio.sleep(time_sleep)
                return await api_call_with_retries(method=method, endpoint=endpoint, params=params,
                                                   shared_client=shared_client, throttler=throttler,
                                                   limit_id=limit_id, try_count=try_count)
            else:
                raise SfoxAPIError(parsed_response, http_status)
        return parsed_response


KEYS = {
    "sfox_api_key":
        ConfigVar(key="sfox_api_key",
                  prompt=f"Enter your {Constants.EXCHANGE_NAME} API key >>> ",
                  required_if=using_exchange("sfox"),
                  is_secure=True,
                  is_connect_key=True),
}
