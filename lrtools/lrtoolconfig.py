# -*- coding: utf-8 -*-
# pylint: disable=line-too-long, C0326, unused-variable
"""

Configuration for LRTool

"""

import sys
import os
from configparser import SafeConfigParser, Error
from datetime import datetime
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


# defaults volumes for archive : mine
ARCHIVE_VOLUMES = [ \
    ( 'PhotosArch1', 'Photos Archives', datetime(1, 1, 1), datetime(2015, 7, 31, 23, 59, 59, 999999)), \
    ( 'PhotosArch2', 'Photos Archives', datetime(2015, 8, 1), datetime(9999, 1, 1) ), \
#    ( 'BackupL1', 'phot_2', datetime(1, 1, 1), datetime(2015, 9, 20) ),
#    ( 'LR', 'phot_3', datetime(2015, 9, 21), datetime(9999, 1, 1) ),
    ]



class LRToolConfig(metaclass=Singleton):
    '''
    Singleton class for LRTools config
    '''

    def __init__(self):

        parser = SafeConfigParser({ \
                    'LRCatalog' :'C:\\Users\\Default\\Documents\\My Lightroom Catalog.lrcat', \
                    'ProdDirectory' : 'C:\\Users\\Default\\Documents\\Photos\\Production', \
                    'RSyncExe' : 'C:\\cygwin64\\bin\\rsync.exe', \
                    'RsyncMaxLenLine' : '4092', \
                    'FSEncoding' : 'cp1252', \
                    'ArchiveDateFmt' : '%%Y/%%m', \
                    'ProductionDateFmt' : '%%Y/%%m', \
                    'DayFirst' : True, \
                })

        # config file is located in directory where main script is lauched
        config_file = os.path.join(os.path.dirname(sys.argv[0]), CONFIG_FILENAME)      
        dataset = parser.read(config_file)
        try:
            self.default_lrcat = parser.get(CONFIG_MAIN, 'LRCatalog')
            self.default_prod_directory = parser.get(CONFIG_MAIN, 'ProdDirectory')

            self.rsync_exe = parser.get(CONFIG_MAIN, 'RSyncExe')
            self.rsync_max_len_line = parser.getint(CONFIG_MAIN, 'RsyncMaxLenLine')

            self.archive_date_fmt = parser.get(CONFIG_MAIN, 'ArchiveDateFmt')
            self.production_date_fmt = parser.get(CONFIG_MAIN, 'ProductionDateFmt')

            self.fs_encoding = parser.get(CONFIG_MAIN, 'FSEncoding')

            self.dayfirst = parser.get(CONFIG_MAIN, 'DayFirst')


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
            print("ERROR Reading config file %s (%s)"  % (CONFIG_FILENAME, _e))


lrt_config = LRToolConfig()
