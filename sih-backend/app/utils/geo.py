import math


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two points, in kilometers."""
    R = 6371.0088
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def grid_key(lat: float, lon: float, cell_km: float) -> str:
    """
    Bucket a lat/lon into a coarse grid cell so repeat detections "at the
    same place" (within ~cell_km) share a key, without needing PostGIS.
    """
    # ~111 km per degree latitude; longitude scaled by cos(lat) for accuracy.
    lat_step = cell_km / 111.0
    lon_step = cell_km / (111.320 * max(math.cos(math.radians(lat)), 0.1))

    lat_bucket = round(lat / lat_step)
    lon_bucket = round(lon / lon_step)
    return f"{lat_bucket}:{lon_bucket}"
