from math import atan2, degrees
import random
from app.utils.types import AirportMapData, LonLat, Plane


from math import atan2, degrees
import random
from app.utils.types import AirportMapData, LocationInfo, Plane


def simulate_plane_from_map(map_data: AirportMapData) -> Plane:
    spawn = choose_spawn_location(map_data)
    final = choose_final_location(map_data)
    heading = compute_heading_from_location(spawn, map_data)

    return {
        "spawn_pos": spawn,
        "current_pos": spawn,  # Plane starts at spawn
        "final_pos": final,
        "current_heading": heading,
        "current_speed": 0.0,
    }


def choose_spawn_location(map_data: AirportMapData) -> LocationInfo:
    if map_data["parking"]: # first spawning on parkings if available on airport map data (should be)
        pos = random.choice(map_data["parking"])
        return {
            "name": pos["name"],
            "type": "parking",
            "coord": pos["location"]
        }
    elif map_data["taxiways"]:
        twy = random.choice(map_data["taxiways"])
        return {
            "name": twy["name"],
            "type": "taxiway",
            "coord": twy["start"]
        }
    else:
        raise ValueError("No valid spawn location in airport map.")


def choose_final_location(map_data: AirportMapData) -> LocationInfo:
    if not map_data["runways"]: # plane final location always should be on runways
        raise ValueError("No runway found in airport map.")
    
    rwy = random.choice(map_data["runways"])
    return {
        "name": rwy["name"],
        "type": "runway",
        "coord": rwy["start"]
    }


def compute_heading_from_location(location: LocationInfo, map_data: AirportMapData) -> float:
    spawn = location["coord"]
    candidates = []

    for twy in map_data["taxiways"]:
        candidates.append((twy["start"], twy["end"]))

    for rwy in map_data["runways"]:
        candidates.append((rwy["start"], rwy["end"]))

    if not candidates:
        return 0.0

    def distance(a: LonLat, b: LonLat) -> float:
        return (a[0] - b[0])**2 + (a[1] - b[1])**2

    closest_seg = min(candidates, key=lambda seg: distance(spawn, seg[0]))
    return compute_heading(*closest_seg)


def compute_heading(from_pt: LonLat, to_pt: LonLat) -> float:
    dx = to_pt[0] - from_pt[0]
    dy = to_pt[1] - from_pt[1]
    return (degrees(atan2(dy, dx)) + 360) % 360
