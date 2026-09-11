"""http_client.py 通用现代化 HTTP 客户端基类

设计目标（可靠性工程，非指纹伪装）：
- HTTP/2 多路复用（httpx + h2），单连接并发请求，减少握手开销
- 统一超时策略：连接/读/写分别设置，避免任一环节无限挂起
- 指数退避重试：仅针对网络层异常与 5xx，4xx 不重试（语义上不可恢复）
- 连接池复用 + keepalive，配合 Session 语义维护 cookie
- 子类可通过 override 钩子定制默认头、认证、限速，无需改动重试/超时骨架
"""

from __future__ import annotations

import logging
import random
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class HTTPClientError(Exception):
    """重试耗尽或不可恢复的客户端错误"""


class ModernHTTPClient:
    """现代化 HTTP 客户端基类。

    子类按需 override:
        default_headers()  -> 注入业务必需的头（如 Authorization）
        before_request()   -> 每次请求前回调（限速、埋点）
    """

    # 连接/读/写超时分离：连接失败快速暴露，读超时给慢接口留余地
    TIMEOUT = httpx.Timeout(connect=10.0, read=30.0, write=30.0, pool=5.0)
    # 指数退避基数：2s, 4s, 8s, 16s + 抖动
    MAX_RETRIES = 4
    BACKOFF_BASE = 2.0
    # 单实例连接池上限
    MAX_CONNECTIONS = 20
    KEEPALIVE_EXPIRY = 30.0

    def __init__(self, base_url: str = "", http2: bool = True, proxy: str | None = None):
        self._client = httpx.Client(
            base_url=base_url,
            http2=http2,
            timeout=self.TIMEOUT,
            proxy=proxy,
            follow_redirects=True,
            limits=httpx.Limits(
                max_connections=self.MAX_CONNECTIONS,
                max_keepalive_connections=self.MAX_CONNECTIONS // 2,
                keepalive_expiry=self.KEEPALIVE_EXPIRY,
            ),
            # 诚实标识：默认头只声明客户端自身，不伪装成浏览器
            headers=self.default_headers(),
        )

    # ── 供子类定制的钩子 ────────────────────────────────────────────
    def default_headers(self) -> dict[str, str]:
        """默认请求头。子类添加业务头时应基于 super() 合并，保持
        Accept-Encoding/Connection 等传输头交给 httpx 按协议自动管理。"""
        return {"accept": "application/json"}

    def before_request(self, method: str, url: str) -> None:
        """请求前回调，默认无限速；子类可实现令牌桶等限速策略。"""

    # ── 核心请求方法 ────────────────────────────────────────────────
    def request(self, method: str, url: str, *, retries: int | None = None, **kwargs: Any) -> httpx.Response:
        """带指数退避重试的请求入口。

        重试范围：网络层异常(ConnectError/TimeoutException) 与 5xx；
        4xx 属于请求语义错误，重试无意义，直接返回由调用方处理。
        """
        attempts = self.MAX_RETRIES if retries is None else retries
        last_exc: Exception | None = None

        for attempt in range(1, attempts + 1):
            self.before_request(method, url)
            try:
                response = self._client.request(method, url, **kwargs)
            except (httpx.ConnectError, httpx.TimeoutException) as exc:
                last_exc = exc
                logger.warning("网络异常 (attempt %d/%d): %s", attempt, attempts, exc)
            else:
                if response.status_code < 500:
                    return response
                last_exc = HTTPClientError(f"server error {response.status_code}")
                logger.warning("服务端 5xx (attempt %d/%d): %d", attempt, attempts, response.status_code)

            if attempt < attempts:
                delay = self.BACKOFF_BASE**attempt + random.uniform(0, 1)
                logger.info("退避 %.1fs 后重试...", delay)
                time.sleep(delay)

        raise HTTPClientError(f"{method} {url} 重试{attempts}次后仍失败") from last_exc

    def get(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, json: Any | None = None, **kwargs: Any) -> httpx.Response:
        kwargs.setdefault("json", json)
        return self.request("POST", url, **kwargs)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "ModernHTTPClient":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()
