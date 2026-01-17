import json
from pathlib import Path
from typing import Optional, Set
from app.utils.types import AirportMapData


class AirportCache:
    def __init__(self, cache_dir: Path = Path(__file__).resolve().parent.parent / "data"):
        self.cache_dir = cache_dir
        self.available_icaos: Set[str] = self._scan_cache()
        print("[AirportCache] Available ICAOs:")
        for icao in self.available_icaos:
            print(f" - {icao}")

    def _scan_cache(self) -> Set[str]:
        if not self.cache_dir.exists():
            self.cache_dir.mkdir(parents=True)
        return {
            f.stem.upper()
            for f in self.cache_dir.glob("*.json")
            if f.is_file()
        }

    def is_cached(self, icao: str) -> bool:
        print(f"[AirportCache] Checking cache for {icao}")
        return icao.upper() in self.available_icaos

    def load(self, icao: str) -> AirportMapData:
        path = self.cache_dir / f"{icao.upper()}.json"
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def save(self, icao: str, data: AirportMapData) -> None:
        try:
            path = self.cache_dir / f"{icao.upper()}.json"
            with path.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            self.available_icaos.add(icao.upper())
            print(f"[AirportCache] Saved cache for {icao}")
        except Exception as e:
            print(f"[AirportCache] Error saving {icao}: {e}")
