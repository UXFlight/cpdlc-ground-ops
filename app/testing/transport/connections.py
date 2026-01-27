from typing import Dict, Optional, Tuple


class ConnectionRegistry:
    def __init__(self) -> None:
        self._sid_to_role: Dict[str, str] = {}
        self._sid_to_pilot: Dict[str, str] = {}

    def register(self, sid: str, role: str, pilot_id: Optional[str]) -> None:
        self._sid_to_role[sid] = role
        if pilot_id:
            self._sid_to_pilot[sid] = pilot_id

    def unregister(self, sid: str) -> Tuple[Optional[str], Optional[str]]:
        role = self._sid_to_role.pop(sid, None)
        pilot_id = self._sid_to_pilot.pop(sid, None)
        return role, pilot_id

    def get_role(self, sid: str) -> Optional[str]:
        return self._sid_to_role.get(sid)

    def get_pilot_id(self, sid: str) -> Optional[str]:
        return self._sid_to_pilot.get(sid)
