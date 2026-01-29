from app.classes.airport_cache import AirportCache
from app.classes.apt_parser import APTParser
from app.utils.simulate_pos import simulate_plane_from_map
from app.utils.types import AirportMapData, Plane

ICAO_DEFAULT = "OEDF"  # DEFAULT ICAO, CAN CHANGE IT BASED ON YOUR NEEDS

class AirportMapManager:
    def __init__(self, icao: str = ICAO_DEFAULT):
        self.icao = icao
        self.cache = AirportCache()
        self.map_data = self.get_or_parse_map(icao)
        self.parser = None

    def get_or_parse_map(self, icao: str) -> AirportMapData:
        if self.cache.is_cached(icao):
            print(f"[AirportMapManager] Loading {icao} from cache")
            return self.cache.load(icao)

        print(f"[AirportMapManager] Parsing {icao} via apt.dat")

        try:
            self.parser = APTParser()
            parsed = self.parser.parse_airport(icao)
            self.cache.save(icao, parsed)
            return parsed

        except FileNotFoundError:
            print(f"[ERROR] apt.dat file not found")
            raise RuntimeError(
                f"\n\n######################\napt.dat file not found on /data. either download it via X-Plane, or use one of the airports I pushed manually on /data (like OMDB). You can always contact me on X (@simy46_) if you want a specific airport\n######################\n\n"
            )

        except Exception as e:
            print(f"[ERROR] Failed to parse airport {icao}: {e}")
            raise RuntimeError(
                f"\n\n######################\nCould not parse airport {icao}: {e}\n######################\n\n"
            )

    # for ingescape!
    def change_airport(self, new_icao: str):
        if new_icao != self.icao:
            self.icao = new_icao
            self.map_data = self.get_or_parse_map(new_icao)

    def get_map(self) -> AirportMapData:
        return self.map_data

    def simulate_plane(self) -> Plane:
        map = self.get_map()
        return simulate_plane_from_map(map)
    