from typing import TYPE_CHECKING

from app.utils.types import AtcPublicView

if TYPE_CHECKING:
    from app.classes.atc import Atc

class AtcManager:
    def __init__(self):
        self._atcs: dict[str, "Atc"] = {}  # sid -> Atc

    def create(self, sid: str) -> None:
        from app.classes.atc import Atc
        if self.exists(sid):
            raise ValueError(f"ATC with SID {sid} already exists.")
        self._atcs[sid] = Atc(sid)

    def get(self, sid: str) -> "Atc":
        if not self.exists(sid):
            raise KeyError(f"ATC with SID {sid} does not exist.")
        return self._atcs[sid]

    def remove(self, sid: str) -> None:
        self._atcs.pop(sid, None)

    def exists(self, sid: str) -> bool:
        return sid in self._atcs

    def get_all_sids(self) -> list[str]:
        return list(self._atcs.keys())

    def get_all(self) -> list[AtcPublicView]:
        return [atc.to_public() for atc in self._atcs.values()]

    def get_all_atcs(self) -> list["Atc"]:
        return list(self._atcs.values())

    def has_any(self) -> bool:
        return len(self._atcs) > 0
