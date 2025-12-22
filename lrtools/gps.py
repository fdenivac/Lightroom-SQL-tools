#!python3
# # -*- coding: utf-8 -*-
# pylint: disable=too-many-lines,line-too-long,invalid-name
"""
GPS functions

"""
import math
import geopy
from geopy.exc import GeocoderTimedOut

# config is loaded on import
from .lrtoolconfig import lrt_config

from .lrselectgeneric import LRSelectException


def square_around_location(lat, lon, width):
    """
    Return square region around GPS point
    """
    lat = float(lat)
    lon = float(lon)
    width = float(width)
    delta_lat = (width / 6378.0) * (180 / math.pi)
    delta_lon = (
        (width / 6378.0) * (180 / math.pi) / math.cos(lat * math.pi / 180)
    )
    return (lat - delta_lat, lon - delta_lon), (
        lat + delta_lat,
        lon + delta_lon,
    )


def geocodage(address):
    """
    Simple call to geo.api.gouv.fr to retrieve coordinates from address
    """
    try:
        details = ""
        if lrt_config.geocoder.lower() == "banfrance":
            location = geopy.geocoders.BANFrance().geocode(address, timeout=5)
            details = f" ({location.raw['properties']['postcode']}), {location.raw['properties']['context']}"
        elif lrt_config.geocoder.lower() == "nominatim":
            location = geopy.geocoders.Nominatim(user_agent="lrtools").geocode(
                address, timeout=5
            )
        else:
            raise LRSelectException("None Geocoder")
        return (
            location.latitude,
            location.longitude,
        ), location.address + details
    except (AttributeError, GeocoderTimedOut):
        return None
