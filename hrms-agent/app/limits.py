"""进程内限流：每个用户每分钟最多 N 次（默认 30）。

只是防止"脚本刷接口把 token 烧光"，不是生产级限流；
多实例场景应换成 Redis 计数器（接口保持不变）。
"""

from __future__ import annotations

import time
from collections import deque

from app import config


class RateLimiter:
    def __init__(self, max_per_minute: int) -> None:
        self.max_per_minute = max_per_minute
        self._hits: dict[str, deque[float]] = {}

    def check(self, key: str) -> tuple[bool, int]:
        """返回 (是否放行, 建议等待秒数)。"""
        now = time.time()
        window = self._hits.setdefault(key, deque())
        while window and now - window[0] > 60:
            window.popleft()
        if len(window) >= self.max_per_minute:
            retry = int(60 - (now - window[0])) + 1
            return False, retry
        window.append(now)
        return True, 0


LIMITER = RateLimiter(config.RATE_LIMIT_PER_MINUTE)
