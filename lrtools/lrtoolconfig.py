# -*- coding: utf-8 -*-
# pylint: disable=invalid-name

"""

Configuration for LRTool

"""

import sys
import os
from configparser import SafeConfigParser, Error
from dateutil import parser as dateparser

class Singleton(type):
    '''
    For unique instance of a class
    Usage:
        class Logger(object):
            __metaclass__ = Singleton
            ...

        log = Logger()

    '''
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]




# config file
CONFIG_FILENAME = 'lrtools.ini'
# sections
CONFIG_MAIN = 'Main'
CONFIG_ARCHVOL = 'ArchiveVolume'



class LRConfigException(Exception):
    ''' lrtools config exception '''



class LRToolConfig(metaclass=Singleton):
    '''
    Singleton class for LRTools config
    '''

    def __init__(self):
        ''' load default config '''
        self.default_lrcat = 'C:\\Users\\Default\\Documents\\My Lightroom Catalog.lrcat'
        self.default_prod_directory = 'C:\\Users\\Default\\Documents\\Photos\\Production'
        self.rsync_exe = 'C:\\cygwin64\\bin\\rsync.exe'
        self.rsync_max_len_line = 4092
        self.archive_date_fmt = '%%Y/%%m'
        self.production_date_fmt = '%%Y/%%m'
        self.fs_encoding = 'cp1252'
        self.dayfirst = True
        self.geocoder = 'nominatim'
        self.archive_volumes = []

        try:
            self.load(CONFIG_FILENAME)
        except LRConfigException:
            print('WARNING: failed to read config file', CONFIG_FILENAME, file=sys.stderr)


    def load(self, filename):
        ''' load a config file '''

        # parser and default value
        parser = SafeConfigParser({ \
                    'LRCatalog' : self.default_lrcat, \
                    'ProdDirectory' : self.default_prod_directory, \
                    'RSyncExe' : self.rsync_exe, \
                    'RsyncMaxLenLine' : self.rsync_max_len_line, \
                    'FSEncoding' : self.fs_encoding, \
                    'ArchiveDateFmt' : self.archive_date_fmt, \
                    'ProductionDateFmt' : self.production_date_fmt, \
                    'DayFirst' : self.dayfirst, \
                    'GeoCoder' : self.geocoder, \
                })

        # config file is located in directory where main script is lauched
        _dir, _ = os.path.split(filename)
        if _dir:
            config_file = filename
        else:
            config_file = os.path.join(os.path.dirname(sys.argv[0]), filename)

        parser.read(config_file)
        try:
            self.default_lrcat = parser.get(CONFIG_MAIN, 'LRCatalog')
            self.default_prod_directory = parser.get(CONFIG_MAIN, 'ProdDirectory')

            self.rsync_exe = parser.get(CONFIG_MAIN, 'RSyncExe')
            self.rsync_max_len_line = parser.getint(CONFIG_MAIN, 'RsyncMaxLenLine')

            self.archive_date_fmt = parser.get(CONFIG_MAIN, 'ArchiveDateFmt')
            self.production_date_fmt = parser.get(CONFIG_MAIN, 'ProductionDateFmt')

            self.fs_encoding = parser.get(CONFIG_MAIN, 'FSEncoding')

            self.dayfirst = parser.get(CONFIG_MAIN, 'DayFirst')

            self.geocoder = parser.get(CONFIG_MAIN, 'GeoCoder')


            if parser.has_section(CONFIG_ARCHVOL):
                self.archive_volumes = []
                idvol = 1
                while True:
                    if not parser.has_option(CONFIG_ARCHVOL, 'VOLUME%s' % idvol):
                        break
                    archvol = parser.get(CONFIG_ARCHVOL, 'VOLUME%s' % idvol)
                    #print archvol
                    try:
                        volname, dirname, datestart, dateend = archvol.split(',')
                        volname = volname.strip()
                        dirname = dirname.strip()
                        datestart = dateparser.parse(datestart)
                        dateend = dateparser.parse(dateend)
                    except ValueError:
                        print('ERROR section %s invalid' % CONFIG_ARCHVOL)
                        sys.exit(0)
                    self.archive_volumes.append((volname, dirname, datestart, dateend))
                    idvol += 1


        except Error as _e:
            raise LRConfigException('Failed to read config file %s' % filename)


lrt_config = LRToolConfig()
