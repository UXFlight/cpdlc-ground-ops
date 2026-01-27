from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import time
import uuid

from .constants import MAX_MESSAGE_LOG


def now_ts() -> float:
    return time.time()


@dataclass
class Message:
    msg_id: str
    from_role: str
    to_role: str
    pilot_id: str
    body: str
    server_received_ts: float
    client_sent_ts: Optional[float] = None

    @classmethod
    def create(cls, from_role: str, to_role: str, pilot_id: str, body: str,
               client_sent_ts: Optional[float]) -> "Message":
        return cls(
            msg_id=str(uuid.uuid4()),
            from_role=from_role,
            to_role=to_role,
            pilot_id=pilot_id,
            body=body,
            server_received_ts=now_ts(),
            client_sent_ts=client_sent_ts,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "msg_id": self.msg_id,
            "from_role": self.from_role,
            "to_role": self.to_role,
            "pilot_id": self.pilot_id,
            "body": self.body,
            "server_received_ts": self.server_received_ts,
            "client_sent_ts": self.client_sent_ts,
        }


@dataclass
class PilotState:
    pilot_id: str
    last_update_ts: float = field(default_factory=now_ts)
    message_log: List[Dict[str, Any]] = field(default_factory=list)

    def append_message(self, message: Dict[str, Any]) -> None:
        self.message_log.append(message)
        if len(self.message_log) > MAX_MESSAGE_LOG:
            self.message_log = self.message_log[-MAX_MESSAGE_LOG:]
        self.last_update_ts = now_ts()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pilot_id": self.pilot_id,
            "last_update_ts": self.last_update_ts,
            "message_log": list(self.message_log),
        }


@dataclass
class AtcState:
    pilot_ids: List[str] = field(default_factory=list)
    last_update_ts: float = field(default_factory=now_ts)

    def set_pilot_ids(self, pilot_ids: List[str]) -> None:
        self.pilot_ids = list(pilot_ids)
        self.last_update_ts = now_ts()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pilot_ids": list(self.pilot_ids),
            "last_update_ts": self.last_update_ts,
        }
