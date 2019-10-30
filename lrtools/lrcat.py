#!python3
# # -*- coding: utf-8 -*-
# pylint: disable=too-many-lines,line-too-long
'''
Classes for Lightroom database manipulations
    - LRCatDB
    - LRNames

'''
import os
import sys
import sqlite3
import logging
from datetime import datetime
from dateutil import parser

# config is loaded on import
from .lrtoolconfig import lrt_config

# for avoid import circular error, move next import after date_to_lrstamp and lr_strptime :
#   from .lrselectphoto import LRSelectPhoto

from .slpp import SLPP

# date reference of lightroom (at least for timestamp of photos modified)
# (TODO : using select based on touchtime, compararing with count results in LR, needs sometimes to shift of 6h hours ! localization problems ?)
DATE_REF = datetime(2001, 1, 1, 0, 0, 0)



def date_to_lrstamp(mydate):
    '''
    convert string or datetime date to a lightroom timestamp : seconds (float) from 1/1/2001
    '''
    if isinstance(mydate, str):
        dtdate = parser.parse(mydate, dayfirst=lrt_config.dayfirst)
    elif isinstance(mydate, datetime):
        dtdate = mydate
    else:
        return None
    return (dtdate - DATE_REF).total_seconds()



def lr_strptime(lrdate):
    '''
    Convert LR date string to datetime
    '''
    if '.' in lrdate and '+' in lrdate:
        # format 2019-08-13T19:47:33.022+02:00
        return datetime.strptime(lrdate, '%Y-%m-%dT%H:%M:%S.%f%z')
    if  '.' in lrdate:
        # format 2019-08-13T19:47:33.269
        return datetime.strptime(lrdate, '%Y-%m-%dT%H:%M:%S.%f')
    if '+' in lrdate:
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
from .lrselectphoto import LRSelectPhoto



class LRCatException(Exception):
    ''' LRCatDB Exception '''



class LRCatDB():
    '''
    Build SQL requests for a Lightroom database

    The database is opened in read-only, with cache local and without lock.
    So Lightroom can be opened while running python scripts using this module

    '''

    ALL_COLL = 1
    STND_COLL = 2
    SMART_COLL = 3


    def __init__(self, lrcat_file):
        self.lrcat_file = lrcat_file
        if not os.path.exists(self.lrcat_file):
            raise LRCatException('LR catalog doesn\'t exist')
        log = logging.getLogger()
        log.info('sqlite3 binding version : %s , sqlite3 version : %s', sqlite3.version, sqlite3.sqlite_version)
        # try to open DB in readonly in python 3
        try:
            lrcat_file = 'file:%s?mode=ro&cache=private&nolock=1' % self.lrcat_file
            self.conn = sqlite3.connect(lrcat_file, uri=True)
            log.info('Database "%s" opened in readonly,cacheprivate,nolock', self.lrcat_file)
        except sqlite3.OperationalError:
            self.conn = sqlite3.connect(self.lrcat_file)
            log.info('Database "%s" opened', self.lrcat_file)
        self.cursor = self.conn.cursor()
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


    def select_duplicates(self):
        '''
        Returns duplicates photos (with same basename) :
            ( (fullname, number_copies), ...)
        '''
        self.cursor.execute('\
        SELECT * FROM ( \
            SELECT rf.absolutePath || fo.pathFromRoot || fi.baseName || "." || fi.extension as FullName, count( fi.baseName) AS Nombre \
            FROM Adobe_images i \
            JOIN AgLibraryFile fi on i.rootFile = fi.id_local \
            JOIN AgLibraryFolder fo on fi.folder = fo.id_local \
            JOIN AgLibraryRootFolder rf on fo.rootFolder = rf.id_local \
            WHERE i.MasterImage IS NULL \
            AND i.fileFormat != "VIDEO" \
            GROUP BY UPPER(fi.baseName)) \
            WHERE Nombre >1 ')
        return self.cursor


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


    def select_count_by_date(self, mode, date_start, date_end=None):
        '''
        Returns photos number by year or month
        with :
            - mode : "dates_by_month" or "dates_by_year"
            - date_start :
            - date_end :
        '''
        # valid too : SELECT COUNT(captureTime),  DATE(captureTime, 'start of month') FROM Adobe_images  GROUP BY DATE(captureTime, 'start of month')
        if mode == 'dates_by_day':
            self.cursor.execute('SELECT strftime("%%Y-%%m-%%d", DATE(captureTime, "start of day")) as d, COUNT(captureTime)\
                FROM Adobe_images WHERE d >= "%s" AND d < "%s" GROUP BY DATE(captureTime, "start of day")' % (date_start, date_end))
        elif mode == 'dates_by_month':
            self.cursor.execute('SELECT strftime("%%Y-%%m", DATE(captureTime, "start of month")) as d, COUNT(captureTime)\
                FROM Adobe_images WHERE d >= "%s" AND d < "%s" GROUP BY DATE(captureTime, "start of month")' % (date_start, date_end))
        elif mode == 'dates_by_year':
            self.cursor.execute('SELECT strftime("%%Y", DATE(captureTime, "start of year")) as d, COUNT(captureTime)\
                FROM Adobe_images WHERE d >= "%s" AND d < "%s" GROUP BY DATE(captureTime, "start of year")' % (date_start, date_end))
        else:
            print('BUG')
            sys.exit(0)
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
            where += ' AND name %s "%s"' % (oper, collname)
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






class LRNames(object):
    '''
    LRNames is the Lightroom photo names of  catalog

    lrphotos is a dictionnary with Adobe_images.id_local as key
        It contains a list = (lrname, uuid, stackpos, master, vname, datemod, idlocal, groupvcopies, prodname, prodpath)
        In addition,  when production path if wanted, field xmp is added (needed for build path from capture date)
        'groupcopies' contains the id of master photo when virtual copy. None if not virtual

    Usage :

    '''

    def __init__(self, lrcat, **kwargs):
        ''' init with a LRCat instance and populates '''
        self.lrdb = lrcat
        self.lrphotos = dict()
        self._populate(**kwargs)


    def _populate(self, **kwargs):
        '''
        Build all base names conform to Lightroom export
        Names are in key in self.lrphotos. Contains :
            (lrname, uuid, stackpos, master, vname, datemod, idlocal, _master, prodname, prodpath)

        kwargs :
            - date :    criter capture date(s)
            - datemod : criter modification date(s)
            - dir :     production directory
            - fmtdate : date format for build subdirectories in production dir

        '''
        log = logging.getLogger()
        datecapt = kwargs.pop('date', None)
        datemod = kwargs.pop('datemod', None)
        prod_basepath = kwargs.pop('dir', None)
        date_fmt = kwargs.pop('fmtdate', None)

        criters = 'sort=name, videos=False'
        if datecapt:
            dates = datecapt.split('-')
            try:
                if len(dates) == 2:
                    if dates[0]:
                        criters += ', fromdatecapt=%s' % dates[0]
                    if dates[1]:
                        criters += ', todatecapt=%s' % dates[1]
                else:
                    criters += ', fromdatecapt=%s' % dates[0]
            except:
                raise LRCatException('Invalid capture date')
        if datemod:
            dates = datemod.split('-')
            try:
                if len(dates) == 2:
                    if dates[0]:
                        criters += ', fromdatemod=%s' % dates[0]
                    if dates[1]:
                        criters += ', todatemod=%s' % dates[1]
                else:
                    criters += ', fromdatemod=%s' % dates[0]
            except:
                raise LRCatException('Invalid modification date')

        # load all photos infos
        masters_vcopies = dict()    # for memorize the master photos having virtual copies
        columns = 'id, name=basext, uuid, vname, stackpos, master, datemod'
        if prod_basepath:
            columns += ', xmp'
        log.info('LRNames criters %s', criters)
        for row in self.lrdb.lrphoto.select_generic(columns, criters).fetchall():
            if prod_basepath:
                idlocal, lrname, uuid, vname, stackpos, master, datemod, xmp = row
            else:
                idlocal, lrname, uuid, vname, stackpos, master, datemod = row
            groupvcopies = None
            prodname = os.path.splitext(lrname)[0].lower()
            # convert virtual copy name to export name (suffix : '-<NUMCOPY> starting to 2)
            if master:
                log.info('### Load virtual copies: %s %s', master, lrname)
                rows = self.lrdb.select_vcopies_master(master, 'id, name=basext, vname, stackpos, uuid, master').fetchall()
                numcopy = 0
                for _id, _lrname, _vname, _stack_pos, _uuid, _master in rows:
                    if not _master: # identify the master photo
                        # this master is in a group of virtual copies
                        masters_vcopies[_id] = master
                        log.info('Marked as copy group : %s = %s', lrname, prodname)
                    numcopy += 1
                    if idlocal == _id:
                        break
                prodname = '%s-%s' % (prodname, numcopy)
                groupvcopies = master
            if prod_basepath:
                prodpath, _ = self.lrdb.prodpath_from_xmp(xmp, prod_basepath, date_fmt)
            else:
                prodpath = None
            # and append
            self.lrphotos[idlocal] = (lrname, uuid, stackpos, master, vname, datemod, idlocal, groupvcopies, prodname, prodpath)

        # in second phase : update masters having virtual copies
        for _id, _master in masters_vcopies.items():
            try:
                lrname, uuid, stackpos, master, vname, datemod, idlocal, groupvcopies, prodname, prodpath = self.lrphotos[_id]
                log.info('Set groupvcopies to %s %s %s %s %s %s %s %s', lrname, uuid, stackpos, master, vname, idlocal, groupvcopies, prodname)
            except KeyError:
                # when using criter datemod, all photos are not present in self.lrphotos
                row = self.lrdb.lrphoto.select_generic('id, name=basext, uuid, vname, stackpos, master, datemod, xmp', 'id=%s' % _id).fetchone()
                idlocal, lrname, uuid, vname, stackpos, master, datemod, xmp = row
                prodname = os.path.splitext(lrname)[0].lower()
                if prod_basepath:
                    prodpath, _ = self.lrdb.prodpath_from_xmp(xmp, prod_basepath, date_fmt)
                else:
                    prodpath = None
                log.info('Add missing master %s %s %s %s %s %s %s %s %s %s', lrname, uuid, stackpos, master, vname, datemod, idlocal, _master, prodname, prodpath)
            self.lrphotos[_id] = (lrname, uuid, stackpos, master, vname, datemod, idlocal, _master, prodname, prodpath)


    def get_prodnames(self, want_vcopies, want_stack1):
        '''
        Returns final production names considering options virtual copies and photos stacked
            It is a dictionnary with full production name as key
            Contains (lrname, uuid, stackpos, master, vname, datemod, idlocal, groupvcopies, prodname, prodpath)
        '''
        prodnames = dict()
        for lrname, uuid, stackpos, master, vname, datemod, idlocal, groupvcopies, prodname, prodpath in list(self.lrphotos.values()):
            if groupvcopies and not want_vcopies:
                continue
            if  stackpos and stackpos > 1 and want_stack1 and not groupvcopies:
                continue
            prodnames[prodname] = (lrname, uuid, stackpos, master, vname, datemod, idlocal, groupvcopies, prodname, prodpath)
        return prodnames
