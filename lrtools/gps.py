#!python3
# # -*- coding: utf-8 -*-
# pylint: disable=too-many-lines,line-too-long,invalid-name
'''
GPS functions

'''
import math
import fractions
import json
import requests
import geopy
from geopy.exc import GeocoderTimedOut

# config is loaded on import
from .lrtoolconfig import lrt_config

from .lrselectgeneric import LRSelectException


class Fraction(fractions.Fraction):
    """Only create Fractions from floats.

    >>> Fraction(0.3)
    Fraction(3, 10)
    >>> Fraction(1.1)
    Fraction(11, 10)
    """

    def __new__(cls, value):
        """Should be compatible with Python 2.6, though untested."""
        return fractions.Fraction.from_float(value).limit_denominator(99999)

def dms_to_decimal(degrees, minutes, seconds, sign=' '):
    """Convert degrees, minutes, seconds into decimal degrees.

    >>> dms_to_decimal(10, 10, 10)
    10.169444444444444
    >>> dms_to_decimal(8, 9, 10, 'S')
    -8.152777777777779
    """
    return (-1 if sign[0] in 'SWsw' else 1) * (
        float(degrees)        +
        float(minutes) / 60   +
        float(seconds) / 3600
    )

def decimal_to_dms(decimal):
    """Convert decimal degrees into degrees, minutes, seconds.

    >>> decimal_to_dms(50.445891)
    [Fraction(50, 1), Fraction(26, 1), Fraction(113019, 2500)]
    >>> decimal_to_dms(-125.976893)
    [Fraction(125, 1), Fraction(58, 1), Fraction(92037, 2500)]
    """
    remainder, degrees = math.modf(abs(decimal))
    remainder, minutes = math.modf(remainder * 60)
    return [Fraction(n) for n in (degrees, minutes, remainder * 60)]


def lambert932WGPS(lambertE, lambertN):
    '''
    Convert a "Coordonnées géographique en projection légale" to GPS

    Code OK, not used because geo.api.gouv.fr returns GPS infos in fields geometry
    '''
    class constantes:
        ''' GPS contants '''
        GRS80E = 0.081819191042816
        LONG_0 = 3
        XS = 700000
        YS = 12655612.0499
        n = 0.7256077650532670
        C = 11754255.4261

    delX = lambertE - constantes.XS
    delY = lambertN - constantes.YS

    gamma = math.atan(-delX / delY)
    R = math.sqrt(delX * delX + delY * delY)
    latiso = math.log(constantes.C / R) / constantes.n
    sinPhiit0 = math.tanh(latiso + constantes.GRS80E * math.atanh(constantes.GRS80E * math.sin(1)))
    sinPhiit1 = math.tanh(latiso + constantes.GRS80E * math.atanh(constantes.GRS80E * sinPhiit0))
    sinPhiit2 = math.tanh(latiso + constantes.GRS80E * math.atanh(constantes.GRS80E * sinPhiit1))
    sinPhiit3 = math.tanh(latiso + constantes.GRS80E * math.atanh(constantes.GRS80E * sinPhiit2))
    sinPhiit4 = math.tanh(latiso + constantes.GRS80E * math.atanh(constantes.GRS80E * sinPhiit3))
    sinPhiit5 = math.tanh(latiso + constantes.GRS80E * math.atanh(constantes.GRS80E * sinPhiit4))
    sinPhiit6 = math.tanh(latiso + constantes.GRS80E * math.atanh(constantes.GRS80E * sinPhiit5))

    longRad = math.asin(sinPhiit6)
    latRad = gamma / constantes.n + constantes.LONG_0 / 180 * math.pi

    longitude = latRad / math.pi * 180
    latitude = longRad / math.pi * 180

    return longitude, latitude


def square_around_location(lat, lon, width):
    '''
    Return square region around GPS point
    '''
    lat = float(lat)
    lon = float(lon)
    width = float(width)
    delta_lat = (width / 6378.) * (180 / math.pi)
    delta_lon = (width / 6378.) * (180 / math.pi) / math.cos(lat * math.pi/180)
    return (lat - delta_lat, lon - delta_lon), (lat + delta_lat, lon + delta_lon)


def geocodage(address):
    '''
    Simple call to geo.api.gouv.fr to retrieve coordinates from address
    '''
    try:
        details = ''
        if lrt_config.geocoder.lower() == 'banfrance':
            location = geopy.geocoders.BANFrance().geocode(address, timeout=5)
            details = ' (%s), %s' % (location.raw['properties']['postcode'], location.raw['properties']['context'])
        elif lrt_config.geocoder.lower() == 'nominatim':
            location = geopy.geocoders.Nominatim(user_agent='lrtools').geocode(address, timeout=5)
        else:
            raise LRSelectException('None Geocoder')
        return (location.latitude, location.longitude), location.address + details
    except (AttributeError, GeocoderTimedOut):
        return None


