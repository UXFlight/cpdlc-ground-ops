from typing import Dict, List, Optional

from .models import PilotState, AtcState


class StateStore:
    def __init__(self) -> None:
        self._pilots: Dict[str, PilotState] = {}
        self._atc_state = AtcState()

    def register_pilot(self, pilot_id: str) -> PilotState:
        if pilot_id not in self._pilots:
            self._pilots[pilot_id] = PilotState(pilot_id=pilot_id)
        self._sync_atc_state()
        return self._pilots[pilot_id]

    def unregister_pilot(self, pilot_id: str) -> None:
        self._pilots.pop(pilot_id, None)
        self._sync_atc_state()

    def add_pilot_message(self, pilot_id: str, message: dict) -> None:
        if pilot_id not in self._pilots:
            self.register_pilot(pilot_id)
        self._pilots[pilot_id].append_message(message)

    def get_pilot_state(self, pilot_id: str) -> Optional[PilotState]:
        return self._pilots.get(pilot_id)

    def get_pilot_state_data(self, pilot_id: str) -> Optional[dict]:
        state = self.get_pilot_state(pilot_id)
        return state.to_dict() if state else None

    def get_atc_state_data(self) -> dict:
        return self._atc_state.to_dict()

    def list_pilot_ids(self) -> List[str]:
        return list(self._pilots.keys())

    def snapshot(self) -> dict:
        pilots = {pid: state.to_dict() for pid, state in self._pilots.items()}
        return {"atc_state": self._atc_state.to_dict(), "pilots": pilots}

    def validate_state(self) -> List[str]:
        issues: List[str] = []
        for pilot_id, state in self._pilots.items():
            for msg in state.message_log:
                if msg.get("pilot_id") != pilot_id:
                    issues.append(f"cross_pilot_message:{pilot_id}")
                    break
        return issues

    def _sync_atc_state(self) -> None:
        self._atc_state.set_pilot_ids(sorted(self._pilots.keys()))
