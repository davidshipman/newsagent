from dataclasses import dataclass

import httpx
import pytest

from briefing.deliver import NtfyDeliverer
from briefing.render import Notification


@dataclass
class Response:
    status_code: int


class Client:
    def __init__(self, codes):
        self.codes, self.calls = iter(codes), []

    def post(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return Response(next(self.codes))


def notification():
    return Notification("Topic", "text", [], 3, "https://x", [])


def test_payload_and_token_header_and_retry(monkeypatch):
    monkeypatch.setattr("briefing.deliver.time.sleep", lambda *_: None)
    client = Client([503, 429, 200])
    deliverer = NtfyDeliverer("private-topic", token="secret", client=client)
    deliverer.send(notification())
    args, kwargs = client.calls[-1]
    assert args[0] == "https://ntfy.sh"
    assert kwargs["headers"] == {"Authorization": "Bearer secret"}
    assert kwargs["json"]["topic"] == "private-topic"
    assert kwargs["json"]["title"] == "Topic"


def test_unauthorized_does_not_retry(monkeypatch):
    client = Client([401])
    with pytest.raises(RuntimeError, match="check token"):
        NtfyDeliverer("topic", client=client).send(notification())
    assert len(client.calls) == 1


def test_network_retry():
    class NetworkClient:
        def __init__(self): self.calls = 0
        def post(self, *args, **kwargs):
            self.calls += 1
            if self.calls == 1: raise httpx.ConnectError("offline")
            return Response(200)
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr("briefing.deliver.time.sleep", lambda *_: None)
    client = NetworkClient()
    NtfyDeliverer("topic", client=client).send(notification())
    assert client.calls == 2
    monkeypatch.undo()
