"""Thin HTTP client for the SwiftVerifyNG reseller API.

Every call to the parent platform goes through this module. When the parent
contract changes (new endpoint, renamed param, method swap), this is the only
file the child panel needs to update.

Base URL comes from config.json (`PARENT_API_BASE`) so staging vs. production
is a config change, not a code change. Paths live here as constants — they're
part of the protocol contract and changing one always requires a code change
anyway.

Contract reference: README.md "Public API Reference" in the parent repo.
"""
from dataclasses import dataclass
from typing import Optional

import requests

from config import get_config_value


PATH_GET_NUMBER    = "/api/getNumber"
PATH_GET_STATUS    = "/api/getStatus"
PATH_SET_STATUS    = "/api/setStatus"
PATH_GET_PRICES    = "/api/getPrices"
PATH_GET_COUNTRIES = "/api/get_countries"
PATH_GET_SERVICES  = "/api/get_services"

DEFAULT_TIMEOUT = 20


@dataclass
class ClientResult:
    ok: bool
    status_code: int
    data: Optional[dict]   # parsed JSON on success
    error: Optional[str]   # plain-text body on failure (BAD_KEY, NO_NUMBERS, …)


def _base_url() -> str:
    return str(get_config_value("PARENT_API_BASE")).rstrip("/")


def _request(method: str, path: str, api_key: str,
             params: Optional[dict] = None,
             data: Optional[dict] = None) -> ClientResult:
    url = f"{_base_url()}{path}"
    headers = {"X-Api-Key": api_key, "Accept": "application/json"}
    try:
        if method == "GET":
            r = requests.get(url, headers=headers, params=params, timeout=DEFAULT_TIMEOUT)
        else:
            r = requests.post(url, headers=headers, params=params, data=data, timeout=DEFAULT_TIMEOUT)
    except requests.RequestException as e:
        return ClientResult(ok=False, status_code=0, data=None, error=f"NETWORK_ERROR - {e}")

    ctype = r.headers.get("content-type", "")
    if "application/json" in ctype:
        try:
            return ClientResult(ok=r.ok, status_code=r.status_code, data=r.json(), error=None)
        except ValueError:
            pass
    return ClientResult(ok=False, status_code=r.status_code, data=None,
                        error=(r.text or "").strip() or "EMPTY_RESPONSE")


def get_number(api_key: str, service, country, pool,
               max_price=None, areas=None, carriers=None, number=None) -> ClientResult:
    data = {"service": service, "country": country, "pool": pool}
    if max_price is not None:
        data["max_price"] = str(max_price)
    if areas:
        data["areas"] = areas
    if carriers:
        data["carriers"] = carriers
    if number:
        data["number"] = number
    return _request("POST", PATH_GET_NUMBER, api_key, data=data)


def get_status(api_key: str, activation_id) -> ClientResult:
    return _request("GET", PATH_GET_STATUS, api_key, params={"id": activation_id})


def set_status(api_key: str, activation_id, status) -> ClientResult:
    return _request("POST", PATH_SET_STATUS, api_key,
                    data={"id": activation_id, "status": int(status)})


def get_prices(api_key: str, service, country) -> ClientResult:
    return _request("GET", PATH_GET_PRICES, api_key,
                    params={"service": service, "country": country})


def get_countries(api_key: str) -> ClientResult:
    return _request("GET", PATH_GET_COUNTRIES, api_key)


def get_services(api_key: str) -> ClientResult:
    return _request("GET", PATH_GET_SERVICES, api_key)
