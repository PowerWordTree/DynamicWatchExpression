import random
import re
import time
from functools import wraps
from hashlib import sha1, sha256
from typing import Any, Callable

from requests import RequestException

from pwt.utils.http import Http
from pwt.utils.retry import (
    Retry,
    exponential_backoff_interval,
    fixd_retryable,
)

PROTO = "http://"
HOST = "miwifi.com"
URI = "/cgi-bin/luci"

LOGIN_WEB_URI = "/web"
INIT_INFO_URI = "/api/xqsystem/init_info"
LOGIN_URI = "/api/xqsystem/login"
PPPOE_STATUS_URI = "/api/xqnetwork/pppoe_status"
WAN_INFO_URI = "/api/xqnetwork/wan_info"

DEFAULT_MAC_ADDR = "58:11:22:c7:94:7b"
DEFAULT_ENCRYPT_KEY = "a2ffa5c9be07488bbb04a3a47d3c5f6a"
DEFAULT_ENCRYPT_IV = "64175472480004614961023454661220"
REGEX_MAC_ADDR = r"""deviceId[ ]*=[ ]*['"]([0-9a-f:]{17})['"][ ]*;"""
REGEX_ENCRYPT_KEY = r"""key[ ]*:[ ]*['"]([0-9a-f]{32})['"][ ]*,"""
REGEX_ENCRYPT_IV = r"""iv[ ]*:[ ]*['"]([0-9a-f]{32})['"][ ]*,"""

_retry = Retry(
    interval=exponential_backoff_interval(factor=1.2, maximum=30, jitter=True),
    retryable=fixd_retryable(retries=3, exceptions={RequestException}, results={None}),
)


class CodeError(Exception):
    def __init__(self, code: int, msg: str) -> None:
        super().__init__(code, msg)
        self.code = code
        self.msg = msg

    def __str__(self) -> str:
        return f"返回错误码 - {self.code} - {self.msg}"


def _check_json(func: Callable) -> Callable:
    @wraps(func)
    def wrapper(*args: Any, **kwds: Any) -> Any:
        json = func(*args, **kwds)
        if json.get("code") != 0:
            raise CodeError(json.get("code"), json.get("msg"))
        return json

    return wrapper


class MiWifi:
    def __init__(self, host: str = HOST):
        self._base_url = PROTO + host + URI
        self._http = Http(self._base_url)
        self._stok = ""

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        self._http.close()

    def login(self, password: str) -> None:
        login_params = self.get_login_params()
        is_new_encrypt = self.get_init_info().get("newEncryptMode") == 1
        nonce = self._get_nonce(login_params["mac_addr"])
        encoded_password = self._encrypt_password(
            password, nonce, login_params["encrypt_key"], is_new_encrypt
        )
        json = self.get_login(encoded_password, nonce)
        self._stok = "/;stok=" + json["token"]

    @_retry
    def get_login_params(self) -> dict[str, Any]:
        """
        获取登录参数
        """

        result = {}
        html = self._http.text(LOGIN_WEB_URI)
        mac_addr = re.compile(REGEX_MAC_ADDR, re.IGNORECASE).findall(html)
        if mac_addr:
            result.update(mac_addr=mac_addr[0])
        else:
            result.update(mac_addr=DEFAULT_MAC_ADDR)
        encrypt_key = re.compile(REGEX_ENCRYPT_KEY, re.IGNORECASE).findall(html)
        if encrypt_key:
            result.update(encrypt_key=encrypt_key[0])
        else:
            result.update(encrypt_key=DEFAULT_ENCRYPT_KEY)
        encrypt_iv = re.compile(REGEX_ENCRYPT_IV, re.IGNORECASE).findall(html)
        if encrypt_iv:
            result.update(encrypt_iv=encrypt_iv[0])
        else:
            result.update(encrypt_iv=DEFAULT_ENCRYPT_IV)
        return result

    @_check_json
    @_retry
    def get_init_info(self) -> dict[str, Any]:
        return self._http.json(INIT_INFO_URI)

    @_check_json
    def get_login(self, encoded_password: str, nonce: str) -> dict[str, Any]:
        return self._http.json(
            LOGIN_URI,
            data={
                "username": "admin",
                "password": encoded_password,
                "logtype": "2",
                "nonce": nonce,
            },
        )

    @_check_json
    @_retry
    def get_pppoe_status(self) -> dict[str, Any]:
        return self._http.json(self._stok + PPPOE_STATUS_URI)

    @_check_json
    @_retry
    def get_wan_info(self) -> dict[str, Any]:
        return self._http.json(self._stok + WAN_INFO_URI)

    def _get_nonce(self, mac_addr: str) -> str:
        """
        获取随机因子字符串

        参数:
            mac_addr: 传递带分隔符的mac地址字符串
        返回:
            随机因子字符串
                格式: 类型_MAC地址_时间戳_随机数
                示例: 0_58:11:22:c7:94:7b_1712240841_6778
        """

        type = "0"
        mac_addr = ":".join(re.split(r"[^0-9a-f]", mac_addr.lower()))
        timestamp = str(round(time.time()))
        rand = str(random.randint(1000, 10000))
        return "_".join([type, mac_addr, timestamp, rand])

    def _encrypt_password(
        self, password: str, nonce: str, key: str, new_encrypt: bool
    ) -> str:
        if new_encrypt:
            result = sha256((password + key).encode("utf-8")).hexdigest()
            result = sha256((nonce + result).encode("utf-8")).hexdigest()
            return result
        result = sha1((password + key).encode("utf-8")).hexdigest()
        result = sha1((nonce + result).encode("utf-8")).hexdigest()
        return result
