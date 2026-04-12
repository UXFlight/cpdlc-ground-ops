from pathlib import Path
from typing import List, cast

from xplane_airports.AptDat import AptDat, AptDatLine, RowCode
from app.utils.types import (
    AirportMapData,
    ParkingType,
    Runway,
    Helipad,
    Taxiway,
    ParkingPosition
)

class APTParser:
    APT_FILE_PATH: Path = Path(__file__).resolve().parent.parent / "data" / "apt.dat"

    def __init__(self):
        self.apt_dat = AptDat(self.APT_FILE_PATH)

    def parse_airport(self, icao: str) -> AirportMapData:
        airport = self._get_airport_by_icao(icao)

        return {
            "runways": self._parse_runways(airport),
            "helipads": self._parse_helipads(airport),
            "taxiways": self._parse_taxiways(airport),
            "parking": self._parse_parking_positions(airport),
            "airport_info": {
                "icao": airport.id,
                "name": airport.name,
                "elevation": airport.elevation_ft_amsl,
            }
        }

    def _get_airport_by_icao(self, icao: str):
        for airport in self.apt_dat.airports:
            if airport.id.upper() == icao.upper():
                return airport
        raise ValueError(f"[APTParser] ICAO {icao} not found in apt.dat")


    def _parse_runways(self, airport) -> List[Runway]:
        runways: List[Runway] = []
        for line in airport.text:
            if isinstance(line, AptDatLine) and line.tokens:
                code = line.tokens[0]
                if isinstance(code, RowCode):
                    code = code.value

                if code == RowCode.LAND_RUNWAY:
                    try:
                        tokens = line.tokens
                        runways.append({
                            "name": f"{tokens[8]}/{tokens[17]}",
                            "start": (float(tokens[9]), float(tokens[10])),
                            "end": (float(tokens[18]), float(tokens[19])),
                            "width": float(tokens[1]),
                            "surface": int(tokens[2])
                        })
                    except Exception:
                        continue
        return runways

    def _parse_helipads(self, airport) -> List[Helipad]:
        helipads: List[Helipad] = []
        for line in airport.text:
            if line.is_runway() and line.runway_type == RowCode.HELIPAD:
                try:
                    tokens = line.tokens
                    helipads.append({
                        "name": tokens[1],
                        "location": (float(tokens[2]), float(tokens[3])),
                        "heading": float(tokens[4]),
                        "length": float(tokens[5]),
                        "width": float(tokens[6]),
                    })
                except Exception as e:
                    print(f"[APTParser] Error parsing helipad: {tokens} → {e}")
        return helipads

    def _parse_taxiways(self, airport) -> List[Taxiway]:
        taxiways: List[Taxiway] = []
        network = airport.taxi_network

        for edge in network.edges:
            try:
                start = network.nodes[edge.node_begin]
                end = network.nodes[edge.node_end]

                taxiways.append({
                    "name": edge.name or "-",
                    "start": (start.lat, start.lon),
                    "end": (end.lat, end.lon),
                    "is_runway": edge.is_runway,
                    "one_way": edge.one_way,
                    "width": edge.icao_width.name if edge.icao_width else "C"
                })
            except Exception as e:
                print(f"[APTParser] Failed to parse taxiway: {e}")
        return taxiways

    def _parse_parking_positions(self, airport) -> List[ParkingPosition]:
        parking: List[ParkingPosition] = []
        for line in airport.text:
            if isinstance(line, AptDatLine) and line.tokens:
                code = line.tokens[0]
                if isinstance(code, RowCode):
                    code = code.value

                if int(code) == 1300:
                    try:
                        tokens = line.tokens
                        parking.append({
                            "location": (float(tokens[1]), float(tokens[2])),
                            "heading": float(tokens[3]),
                            "type": self.sanitize_parking_type(str(tokens[4])),
                            "name": " ".join(str(t) for t in tokens[6:]) if len(tokens) > 6 else "Unnamed"                        
                        })
                    except Exception as e:
                        print(f"[APTParser] Skipping bad parking line: {tokens} → {e}")
        return parking
    
    def sanitize_parking_type(self, value: str) -> ParkingType:
        v = value.strip().lower()
        if v in ("gate", "tie_down", "hangar", "ramp"):
            return cast(ParkingType, v)
        return "unknown"
