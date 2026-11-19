from dataclasses import asdict
import os
import random
import time
from typing import Protocol

import httpx

from .render import Notification


class Deliverer(Protocol):
    def send(self, notification: Notification) -> None: ...


class NtfyDeliverer:
    def __init__(self, topic=None, server=None, token=None, markdown=False, client=None):
        self.topic = topic or os.getenv("NTFY_TOPIC")
        self.server = (server or os.getenv("NTFY_SERVER") or "https://ntfy.sh").rstrip("/")
        self.token = token if token is not None else os.getenv("NTFY_TOKEN")
        self.markdown = markdown
        self.client = client or httpx
        if not self.topic:
            raise ValueError("NTFY_TOPIC is required")

    def send(self, notification: Notification) -> None:
        payload = {**asdict(notification), "topic": self.topic, "markdown": self.markdown}
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        for attempt in range(3):
            try:
                response = self.client.post(self.server, json=payload, headers=headers, timeout=15)
                if response.status_code == 429 or response.status_code >= 500:
                    if attempt < 2:
                        time.sleep((2 ** attempt) + random.random() * 0.1)
                        continue
                if response.status_code >= 400:
                    if response.status_code in (401, 403):
                        raise RuntimeError(f"ntfy rejected notification ({response.status_code}); check token or protected topic")
                    raise RuntimeError(f"ntfy rejected notification ({response.status_code})")
                return
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                if attempt == 2:
                    raise RuntimeError(f"Unable to deliver notification after 3 attempts: {type(exc).__name__}") from exc
                time.sleep((2 ** attempt) + random.random() * 0.1)
        raise RuntimeError("Unable to deliver notification after 3 attempts")


def send_all(deliverer: Deliverer, notifications, delay: float = 1, logger=None):
    for index, notification in enumerate(notifications, 1):
        deliverer.send(notification)
        if logger:
            logger.info("Sent notification %d", index)
        if index < len(notifications) and delay:
            time.sleep(delay)
