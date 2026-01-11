# -*- coding: utf-8 -*-
# pylint: disable=invalid-name

"""

Configuration for LRTool

"""

import sys
import os
from configparser import ConfigParser

# sections
CONFIG_MAIN = "Main"


class LRConfigException(Exception):
    """lrtools config exception"""


class LRToolConfig:
    """
    Singleton class for LRTools config
    """

    def __init__(self, config_filename="lrtools.ini"):
        """load default config

            If config_filename has a full path, it will be used.
            If it only has a filename, it will be searched for in the directory
            the script is stored.
            If it is None, defaults will be used.
        """
        self.default_lrcat = (
            "C:\\Users\\Default\\Documents\\My Lightroom Catalog.lrcat"
        )
        self.dayfirst = True
        self.geocoder = "nominatim"

        if config_filename:
            try:
                self.load(config_filename)
            except LRConfigException:
                print(
                    "WARNING: failed to read config file",
                    config_filename,
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

        # config file is located in directory where main script is launched
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
