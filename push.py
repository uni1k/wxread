# push.py 支持 PushPlus、ServerChan、wxpusher、Telegram 的消息推送模块
import json
import logging
import os
import random
import time

import requests
from urllib.parse import quote

from config import (
    BARK_URL,
    PUSHPLUS_TOKEN,
    SERVERCHAN_SPT,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    WXPUSHER_SPT,
)

logger = logging.getLogger(__name__)


class PushNotification:
    def __init__(self):
        self.pushplus_url = "https://www.pushplus.plus/send"
        self.telegram_url = "https://api.telegram.org/bot{}/sendMessage"
        self.server_chan_url = "https://sctapi.ftqq.com/{}.send"
        self.wxpusher_simple_url = "https://wxpusher.zjiecode.com/api/send/message/{}/{}"
        # BARK_URL 示例：官方 https://api.day.app/{key} 或自建 https://your.host/{key}
        self.bark_url = BARK_URL
        self.headers = {"Content-Type": "application/json"}
        # 从环境变量获取代理设置
        self.proxies = {
            "http": os.getenv("http_proxy"),
            "https": os.getenv("https_proxy"),
        }

    def push_pushplus(self, content, token, is_success):
        """PushPlus消息推送"""
        attempts = 5
        title = f"微信阅读-{'成功' if is_success else '失败'}"
        for attempt in range(attempts):
            try:
                response = requests.post(
                    self.pushplus_url,
                    data=json.dumps({"token": token, "title": title, "content": content}).encode("utf-8"),
                    headers=self.headers,
                    timeout=10,
                )
                response.raise_for_status()
                logger.info("✅ PushPlus响应: %s", response.text)
                return True
            except requests.exceptions.RequestException as exc:
                logger.error("❌ PushPlus推送失败: %s", exc)
                if attempt < attempts - 1:
                    sleep_time = random.randint(180, 360)  # 随机3到6分钟
                    logger.info("将在 %d 秒后重试...", sleep_time)
                    time.sleep(sleep_time)
        return False

    def push_telegram(self, content, bot_token, chat_id):
        """Telegram消息推送，失败时自动尝试直连"""
        url = self.telegram_url.format(bot_token)
        payload = {"chat_id": chat_id, "text": content}

        try:
            # 先尝试代理
            response = requests.post(url, json=payload, proxies=self.proxies, timeout=30)
            logger.info("✅ Telegram响应: %s", response.text)
            response.raise_for_status()
            return True
        except Exception as exc:
            logger.error("❌ Telegram代理发送失败: %s", exc)
            try:
                # 代理失败后直连
                response = requests.post(url, json=payload, timeout=30)
                response.raise_for_status()
                return True
            except Exception as inner_exc:
                logger.error("❌ Telegram发送失败: %s", inner_exc)
                return False

    def push_wxpusher(self, content, spt):
        """WxPusher消息推送（极简方式）"""
        attempts = 5
        url = self.wxpusher_simple_url.format(spt, content)

        for attempt in range(attempts):
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                logger.info("✅ WxPusher响应: %s", response.text)
                return True
            except requests.exceptions.RequestException as exc:
                logger.error("❌ WxPusher推送失败: %s", exc)
                if attempt < attempts - 1:
                    sleep_time = random.randint(180, 360)
                    logger.info("将在 %d 秒后重试...", sleep_time)
                    time.sleep(sleep_time)
        return False

    def push_serverChan(self, content, spt, is_success):
        """ServerChan消息推送"""
        attempts = 5
        url = self.server_chan_url.format(spt)
        title = f"微信阅读-{'成功' if is_success else '失败'}"

        for attempt in range(attempts):
            try:
                response = requests.post(
                    url,
                    data=json.dumps({"title": title, "desp": content}).encode("utf-8"),
                    headers=self.headers,
                    timeout=15,
                )
                response.raise_for_status()
                logger.info("✅ ServerChan响应: %s", response.text)
                return True
            except requests.exceptions.RequestException as exc:
                logger.error("❌ ServerChan推送失败: %s", exc)
                if attempt < attempts - 1:
                    sleep_time = random.randint(180, 360)
                    logger.info("将在 %d 秒后重试...", sleep_time)
                    time.sleep(sleep_time)
        return False


    def push_bark(self, content, bark_url, is_success):
        """Bark消息推送（iOS），bark_url 含 key，如 https://api.day.app/xxxxxxxx"""
        attempts = 5
        title = f"微信阅读-{'成功' if is_success else '失败'}"
        url = f"{bark_url.rstrip('/')}/{quote(title, safe='')}/{quote(content, safe='')}?group=wxread"

        for attempt in range(attempts):
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                logger.info("✅ Bark响应: %s", response.text)
                return True
            except requests.exceptions.RequestException as exc:
                logger.error("❌ Bark推送失败: %s", exc)
                if attempt < attempts - 1:
                    sleep_time = random.randint(180, 360)
                    logger.info("将在 %d 秒后重试...", sleep_time)
                    time.sleep(sleep_time)
        return False


def push(content, method, is_success=True):
    """统一推送接口，支持 PushPlus、Telegram、WxPusher 和 ServerChan"""
    notifier = PushNotification()

    if method in (None, ""):
        logger.warning("未配置推送渠道，跳过推送。")
        return False

    method = str(method).lower()

    if method == "pushplus":
        return notifier.push_pushplus(content, PUSHPLUS_TOKEN, is_success)
    if method == "telegram":
        return notifier.push_telegram(content, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
    if method == "wxpusher":
        return notifier.push_wxpusher(content, WXPUSHER_SPT)
    if method == "serverchan":
        return notifier.push_serverChan(content, SERVERCHAN_SPT, is_success)
    if method == "bark":
        if not BARK_URL:
            logger.warning("BARK_URL 未配置，跳过 Bark 推送。")
            return False
        return notifier.push_bark(content, BARK_URL, is_success)

    logger.warning("无效的通知渠道 '%s'，已跳过推送。支持：pushplus、telegram、wxpusher、serverchan", method)
    return False
