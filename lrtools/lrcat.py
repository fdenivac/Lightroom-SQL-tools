#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=line-too-long, C0326, unused-variable, invalid-name, too-many-lines
'''
Main class LRCatDB for Lightroom database manipulations

'''
import os
import sys
import sqlite3
import logging
from datetime import datetime
from dateutil import parser

from . import DATE_REF, localzone, utczone
# config is loaded on import
from .lrtoolconfig import lrt_config

from .slpp import SLPP



def date_to_lrstamp(mydate, localtz=True):
    '''
    convert localized time string or datetime date to a lightroom timestamp : seconds (float) from 1/1/2001
    '''
    if isinstance(mydate, str):
        dtdate = parser.parse(mydate, dayfirst=lrt_config.dayfirst)
        # set locale timezone
        if localtz:
            dtdate = dtdate.astimezone(localzone)
        else:
            dtdate = dtdate.astimezone(utczone)
    elif isinstance(mydate, datetime):
        # TODO check tzinfo
        dtdate = mydate
    else:
        return None
    ts = (dtdate - DATE_REF).total_seconds()
    return ts if ts >= 0 else 0



def lr_strptime(lrdate):
    '''
    Convert LR date string to datetime
    '''
    if  '.' in lrdate:
        if '+' in lrdate:
            # format 2019-08-13T19:47:33.022+02:00
            return datetime.strptime(lrdate, '%Y-%m-%dT%H:%M:%S.%f%z')
        # format 2019-08-13T19:47:33.269
        return datetime.strptime(lrdate, '%Y-%m-%dT%H:%M:%S.%f')
    if '+' in lrdate or 'Z' in lrdate:
        # format 2019-08-13T19:47:33+02:00
        try:
            return datetime.strptime(lrdate, '%Y-%m-%dT%H:%M:%S%z')
        except ValueError:
            pass
        return datetime.strptime(lrdate, '%Y-%m-%dT%H:%M%z')
    # format 2019-08-13T19:47:33
    try:
        return datetime.strptime(lrdate, '%Y-%m-%dT%H:%M:%S')
    except ValueError:
        pass
    return datetime.strptime(lrdate, '%Y-%m-%dT%H:%M')


# import here for avoid import circular error :
# pylint: disable=wrong-import-position
from .lrselectphoto import LRSelectPhoto



class LRCatException(Exception):
    ''' LRCatDB Exception '''



class LRCatDB():
    '''
    Build SQL requests for a Lightroom database

    The database is opened by default in read-only, with cache local and as immutable (needed by Lightroom >= version 8).
    So Lightroom can be opened while running python scripts using this module.

    '''

    ALL_COLL = 1
    STND_COLL = 2
    SMART_COLL = 3


    def __init__(self, lrcat_file, open_options="mode=ro&cache=private&immutable=1"):
        self.conn = self.cursor = self.lrdb_version = None
        def open_db(uri):
            try:
                self.conn = sqlite3.connect(uri, uri='?' in  uri)
                self.cursor = self.conn.cursor()
                self.lrdb_version, = self.cursor.execute('SELECT value FROM Adobe_variablesTable WHERE name="Adobe_DBVersion"').fetchone()
                log.info('LR database "%s" opened with uri "%s"', self.lrcat_file, uri)
                log.info('Adobe_DBVersion : %s', self.lrdb_version)
                return True
            except sqlite3.OperationalError:
                self.conn.close()
                return False
        self.lrcat_file = lrcat_file
        if not os.path.exists(self.lrcat_file):
            raise LRCatException('LR catalog doesn\'t exist')
        log = logging.getLogger()
        log.info('sqlite3 binding version : %s , sqlite3 version : %s', sqlite3.version, sqlite3.sqlite_version)
        modes = "?%s" % open_options if open_options else ""
        if not open_db('file:%s%s' % (self.lrcat_file, modes)):
            log.info('Failed to open "%s" with uri "%s"', self.lrcat_file, open_options)
            raise LRCatException('Unable to open LR catalog')
        self.lrphoto = LRSelectPhoto(self)


    def has_basename(self, name):
        '''
        Check if basename exists
        '''
        # COLLATE NOCASE for case insensitive
        self.cursor.execute('SELECT baseName FROM AgLibraryFile WHERE baseName = ? COLLATE NOCASE', (name, ))
        return len(self.cursor.fetchall()) > 0



    def select_vcopies_master(self, master, columns):
        '''
        Select master image and the copies
            default return columns : name=basext , vname, stackpos, datemod, uuid, xmp, master, id
        '''
        sqlcols = []
        sqlfroms = ['Adobe_images i']
        self.lrphoto.columns_to_sql(columns, sqlcols, sqlfroms)
        sql = 'SELECT %s FROM %s WHERE i.masterImage=%s OR i.id_local=%s ORDER BY i.id_local' % \
                     (', '.join(sqlcols), ' '.join(sqlfroms), master, master)
        self.cursor.execute(sql)
        return self.cursor


    def select_duplicates(self, **kwargs):
        '''
        Returns duplicates photos name (same basename) :
            ( (fullname, number_copies), ...)
        '''
        sql = 'SELECT * FROM ( \
            SELECT rf.absolutePath || fo.pathFromRoot || fi.baseName || "." || fi.extension as name, count( fi.baseName) AS duplicates \
            FROM Adobe_images i \
            JOIN AgLibraryFile fi on i.rootFile = fi.id_local \
            JOIN AgLibraryFolder fo on fi.folder = fo.id_local \
            JOIN AgLibraryRootFolder rf on fo.rootFolder = rf.id_local \
            WHERE i.MasterImage IS NULL \
            AND i.fileFormat != "VIDEO" \
            GROUP BY UPPER(fi.baseName)) \
            WHERE duplicates >1'
        if kwargs.get('sql'):
            return sql
        self.cursor.execute(sql)
        return self.cursor.fetchall()


    def select_imports(self, import_id=None):
        '''
        Select details on imports (date, count)
        Parameter:
            - import_id: import detor None for all imports
        '''
        if import_id:
            sql = 'SELECT id_local, importDate,' \
                ' (SELECT COUNT(ii.import) FROM AgLibraryImport i JOIN AgLibraryImportImage ii ON i.id_local = ii.import' \
                ' WHERE i.id_local = %s) AS count' \
                ' FROM AgLibraryImport WHERE id_local = %s' % (import_id, import_id)
        else:
            sql = 'SELECT id_local, importDate ,' \
                ' (SELECT COUNT(ii.import) FROM AgLibraryImport i ' \
                ' JOIN AgLibraryImportImage ii ON i.id_local = ii.import WHERE i0.id_local = i.id_local) AS Count' \
                ' FROM AgLibraryImport i0 ORDER BY importDate ASC'
        self.cursor.execute(sql)
        return self.cursor


    def get_smartcoll_data(self, name_or_id, raw_value=False):
        '''
        Return smart collection lua request in a python structure
        '''
        try:
            pid = int(name_or_id)
            self.cursor.execute(
                'SELECT cont.content FROM AgLibraryCollectionContent cont \
                JOIN AgLibraryCollection  col on col.id_local = cont.collection\
                WHERE col.id_local=? AND cont.owningModule = "ag.library.smart_collection"', (pid, )
            )
        except ValueError:
            name = name_or_id
            self.cursor.execute(
                'SELECT cont.content FROM AgLibraryCollectionContent cont \
                JOIN AgLibraryCollection  col on col.id_local = cont.collection\
                WHERE  col.name LIKE ? AND cont.owningModule = "ag.library.smart_collection"', (name, )
            )
        try:
            smart = self.cursor.fetchone()[0]
            if raw_value:
                return smart
            smart = smart[4:]
            lua = SLPP()
            data = lua.decode(smart)
            return data
        except TypeError:
            return None


    def select_count_by_date(self, mode, date_start, date_end=None, **kwargs):
        '''
        Returns photos number by year or month

        - mode : "by_year", "by_month" or "by_day"
        - date_start
        - date_end
        '''
        # valid too : SELECT COUNT(captureTime),  DATE(captureTime, 'start of month') FROM Adobe_images  GROUP BY DATE(captureTime, 'start of month')
        if not date_end:
            date_end = datetime.now()
        if mode == 'by_day':
            sql = 'SELECT strftime("%%Y-%%m-%%d", DATE(captureTime, "start of day")) as day, COUNT(captureTime) AS count' \
                ' FROM Adobe_images WHERE captureTime >= "%s" AND captureTime < "%s" GROUP BY DATE(captureTime, "start of day")' % (date_start, date_end)
        elif mode == 'by_month':
            sql = 'SELECT strftime("%%Y-%%m", DATE(captureTime, "start of month")) as month, COUNT(captureTime) AS count'\
                ' FROM Adobe_images WHERE captureTime >= "%s" AND captureTime < "%s" GROUP BY DATE(captureTime, "start of month")' % (date_start, date_end)
        elif mode == 'by_year':
            sql = 'SELECT strftime("%%Y", DATE(captureTime, "start of year")) as year, COUNT(captureTime) AS count'\
                ' FROM Adobe_images WHERE captureTime >= "%s" AND captureTime <= "%s" GROUP BY DATE(captureTime, "start of year")' % (date_start, date_end)
        else:
            print('BUG')
            sys.exit(0)
        if kwargs.get('sql'):
            return sql
        self.cursor.execute(sql)
        return self.cursor.fetchall()


    def select_collections(self, what, collname=""):
        '''
        Select collections name for standard and dynamic type)
          what = [ALL_COLL, STND_COLL, SMART_COLL] : collections type to retrieve
          collname : partial (including a %) or complete name of collection, or empty for all collections
        '''
        if what == self.STND_COLL:
            where = 'creationId="com.adobe.ag.library.collection"'
        elif what == self.SMART_COLL:
            where = 'creationId="com.adobe.ag.library.smart_collection"'
        else:
            where = 'creationId="com.adobe.ag.library.smart_collection" OR creationId="com.adobe.ag.library.collection"'
        if collname:
            oper = 'LIKE' if '%' in collname else '='
            where += ' AND name %s "%s" COLLATE NOCASE' % (oper, collname)
        self.cursor.execute('SELECT id_local, name, creationId FROM AgLibraryCollection WHERE %s ORDER BY name ASC' % where)
        return self.cursor.fetchall()


    def select_metadatas_to_archive(self):
        '''
        Returns photos as LR smart collection : métadatas "conflit détecté" OU "a été modifié"
        '''
        return self.lrphoto.select_generic('name=full', 'metastatus=conflict, sort=capturetime')


    def get_xmp(self, name_or_id):
        '''
        Returns Adobe_AdditionalMetadata.xmp (list of tuple)
            id :  photo basename or id (Adobe_images.id_local)
        '''
        try:
            name_or_id = int(name_or_id)
            self.lrphoto.select_generic('xmp', 'id="%s"' % name_or_id)
        except ValueError:
            self.lrphoto.select_generic('xmp', 'name="%s"' % name_or_id)
        return self.cursor.fetchall()


    def get_exif_metadata(self, name_or_id, fields):
        '''
        Returns elements of table AgHarvestedExifMetadata for a photo basename
            name_or_id : photo basename or id
            fields: (string) sql fields to retrieve (ex:'hasgps,focallength')
        NOTA: also possible: acces to GPS infos via self.get_xmp (field exif:GPS<KEY>)
        TODO : WARNING : if photo has name as "numerical" (1235.jpg) ... LOST
        '''
        try:
            name_or_id = int(name_or_id)
            self.cursor.execute('\
                SELECT %s FROM AgHarvestedExifMetadata \
                WHERE image = ? ' % fields, (name_or_id, ))
        except ValueError:
            self.cursor.execute('\
                SELECT %s  FROM Adobe_images i \
                JOIN AgHarvestedExifMetadata em on i.id_local = em.image \
                JOIN AgLibraryFile fi on i.rootFile = fi.id_local \
                WHERE fi.baseName = ? ' % fields, (name_or_id, ))
        return self.cursor.fetchall()


    def get_rowfield(self, field=None):
        '''
        Get next row and returns specific field
        '''
        row = self.cursor.fetchone()
        if not row:
            return None
        if field is None:
            return row
        return row[field]


    def prodpath_from_xmp(self, xmp, prod_basepath, date_fmt):
        '''
        Returns production path and capture time from xmp

        Parameters
            xmp  : XMP datas from LR
            prod_basepath : production directory base path
            date_fmt : date format for subdirectories in production dir

        Returns
            (str) production path, (datetime) capture_time
        '''
        # image.captureTime always exists (with and without exif date) :
        #   so, we need to read xmp for exif:DateTimeOriginal ou exif:DateTimeDigitized
        # date capture is DateTimeOriginal or DateTimeDigitized else None
        datecapt = self.xtract_prop_key(xmp, 'exif:DateTimeOriginal')
        if not datecapt:
            datecapt = self.xtract_prop_key(xmp, 'exif:DateTimeDigitized')
        if not datecapt:    # last chance !
            datecapt = self.xtract_prop_key(xmp, 'xmp:CreateDate')
        if datecapt:
            capturetime = lr_strptime(datecapt)
        else:
            capturetime = datetime.strptime('1900-01-01T00:00:00', '%Y-%m-%dT%H:%M:%S')
        prodpath = os.path.normpath(os.path.join(str(prod_basepath), capturetime.strftime(date_fmt)))
        return prodpath, capturetime


    def xtract_prop_key(self, xmp, key):
        '''
        Extract value for key in xmp string (exif:DateTimeOriginal='VALUE')
        '''
        i = xmp.find(key + '="')
        if i == -1:
            return None
        beg = i + len(key) + 2
        end = xmp.find('"', beg)
        if end == -1:
            return None
        return xmp[beg:end]
