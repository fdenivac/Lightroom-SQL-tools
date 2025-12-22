# -*- coding: utf-8 -*-
# pylint: disable=invalid-name

"""

Configuration for LRTool

"""

import sys
import os
from configparser import ConfigParser


class Singleton(type):
    """
    For unique instance of a class
    Usage:
        class Logger(object):
            __metaclass__ = Singleton
            ...

        log = Logger()

    """

    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(
                *args, **kwargs
            )
        return cls._instances[cls]


# config file
CONFIG_FILENAME = "lrtools.ini"
# sections
CONFIG_MAIN = "Main"
CONFIG_ARCHVOL = "ArchiveVolume"


class LRConfigException(Exception):
    """lrtools config exception"""


class LRToolConfig(metaclass=Singleton):
    """
    Singleton class for LRTools config
    """

    def __init__(self):
        """load default config"""
        self.default_lrcat = (
            "C:\\Users\\Default\\Documents\\My Lightroom Catalog.lrcat"
        )
        self.dayfirst = True
        self.geocoder = "nominatim"

        try:
            self.load(CONFIG_FILENAME)
        except LRConfigException:
            print(
                "WARNING: failed to read config file",
                CONFIG_FILENAME,
                file=sys.stderr,
            )

    def load(self, filename):
        """load a config file"""

        # parser and default value
        parser = ConfigParser(
            {
                "LRCatalog": self.default_lrcat,
                "DayFirst": self.dayfirst,
                "GeoCoder": self.geocoder,
            }
        )

        # config file is located in directory where main script is lauched
        _dir, _ = os.path.split(filename)
        if _dir:
            config_file = filename
        else:
            config_file = os.path.join(os.path.dirname(sys.argv[0]), filename)

        parser.read(config_file)
        try:
            self.default_lrcat = parser.get(CONFIG_MAIN, "LRCatalog")
            self.dayfirst = parser.getboolean(CONFIG_MAIN, "DayFirst")
            self.geocoder = parser.get(CONFIG_MAIN, "GeoCoder")

        except Exception as _e:
            raise LRConfigException(
                f'Failed to read config file "{filename}"'
            ) from _e


lrt_config = LRToolConfig()
