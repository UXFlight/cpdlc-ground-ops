import argparse
import threading
import time

import socketio

from ..core.constants import (
    EVENT_ATC_MESSAGE,
    EVENT_PILOT_MESSAGE,
    EVENT_REGISTER,
    EVENT_REGISTERED,
    ROLE_ATC,
    ROLE_PILOT,
)


class LoadClient:
    def __init__(self, role: str, client_id: str, server_url: str,
                 target_pilots: list[str], interval_s: float, duration_s: float) -> None:
        self.role = role
        self.client_id = client_id
        self.server_url = server_url
        self.target_pilots = target_pilots
        self.interval_s = interval_s
        self.duration_s = duration_s
        self._sio = socketio.Client(reconnection=False, logger=False,
                                    engineio_logger=False)
        self._registered = threading.Event()
        self._seq = 0

        @self._sio.on(EVENT_REGISTERED)
        def _registered(data):
            if data.get("client_id") == self.client_id:
                self._registered.set()

    def start(self) -> None:
        try:
            self._sio.connect(self.server_url, transports=["polling"], wait_timeout=3)
        except Exception:
            return
        self._sio.emit(EVENT_REGISTER, {"role": self.role, "client_id": self.client_id})
        self._registered.wait(timeout=2.0)
        if not self._registered.is_set():
            self._sio.disconnect()
            return
        end_ts = time.time() + self.duration_s
        while time.time() < end_ts:
            if not self._sio.connected:
                break
            self._send_once()
            time.sleep(self.interval_s)
        self._sio.disconnect()

    def _send_once(self) -> None:
        self._seq += 1
        payload = {"body": f"msg:{self.client_id}:{self._seq}", "client_sent_ts": time.time()}
        if self.role == ROLE_PILOT:
            try:
                self._sio.emit(EVENT_PILOT_MESSAGE, payload)
            except Exception:
                return
            return
        if not self.target_pilots:
            return
        target = self.target_pilots[self._seq % len(self.target_pilots)]
        payload["pilot_id"] = target
        try:
            self._sio.emit(EVENT_ATC_MESSAGE, payload)
        except Exception:
            return


def _build_target_pilots(prefix: str, count: int) -> list[str]:
    return [f"{prefix}{i}" for i in range(count)]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--role", choices=[ROLE_PILOT, ROLE_ATC], required=True)
    parser.add_argument("--count", type=int, default=1)
    parser.add_argument("--server", default="http://localhost:5322")
    parser.add_argument("--duration", type=float, default=10.0)
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--pilot-prefix", default="pilot-")
    parser.add_argument("--pilot-count", type=int, default=1)
    args = parser.parse_args()

    target_pilots = _build_target_pilots(args.pilot_prefix, args.pilot_count)
    threads = []
    for i in range(args.count):
        client_id = f"{args.pilot_prefix}{i}" if args.role == ROLE_PILOT else f"atc-{i}"
        client = LoadClient(args.role, client_id, args.server,
                            target_pilots if args.role == ROLE_ATC else [],
                            args.interval, args.duration)
        t = threading.Thread(target=client.start, daemon=True)
        threads.append(t)
        t.start()
    for t in threads:
        t.join()


if __name__ == "__main__":
    main()
