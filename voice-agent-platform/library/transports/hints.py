"""Transport adapters (Daily / Twilio / WebRTC) — stubs until API tokens are set."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TransportHints:
    provider: str
    notes: str


def describe(provider: str) -> TransportHints:
    mapping = {
        "daily": TransportHints("daily", "Set DAILY_API_KEY; use Daily WebRTC rooms."),
        "twilio": TransportHints("twilio", "Set TWILIO_* ; media Streams to /voice/stream/{call_id}."),
        "webrtc": TransportHints("webrtc", "Browser client via /voice/incoming/web bootstrap."),
    }
    return mapping.get(provider, TransportHints(provider, "Unknown transport"))
