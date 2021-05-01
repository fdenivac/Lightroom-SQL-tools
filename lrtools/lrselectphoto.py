#!python3
# # -*- coding: utf-8 -*-
# pylint: disable=line-too-long,bad-continuation, bad-whitespace

'''
LRSelectPhoto class for building SQL select for table Adobe_images
'''

import math
import re
import logging
from datetime import datetime

from .lrselectgeneric import LRSelectGeneric, LRSelectException
from .gps import geocodage, square_around_location

class LRSelectPhoto(LRSelectGeneric):
    '''
    Build select request for photo table Adobe_images
    '''

    def __init__(self, lrdb):
        '''
        '''
        super().__init__(lrdb, \
            #
            # Table source
            #
            'Adobe_images i',

            #
            # Column description
            #
            { \
            'all' :  {
                'True' : [ '*',  None ] }, \
            'name' : {
                'full' : \
                    [   'rf.absolutePath || fo.pathFromRoot || fi.baseName || "." || fi.extension AS name', \
                        [ 'LEFT JOIN AgLibraryFile fi ON i.rootFile = fi.id_local', 'LEFT JOIN AgLibraryFolder fo ON fi.folder = fo.id_local', 'LEFT JOIN AgLibraryRootFolder rf ON fo.rootFolder = rf.id_local' ],
                    ],\
                'full_vc' : \
                    [   'rf.absolutePath || fo.pathFromRoot || fi.baseName || COALESCE(i.copyName, "") || "." || fi.extension AS name', \
                        [ 'LEFT JOIN AgLibraryFile fi ON i.rootFile = fi.id_local', 'LEFT JOIN AgLibraryFolder fo ON fi.folder = fo.id_local', 'LEFT JOIN AgLibraryRootFolder rf ON fo.rootFolder = rf.id_local' ],
                    ],\
                'base': [ 'fi.baseName AS name', ['LEFT JOIN AgLibraryFile fi ON i.rootFile = fi.id_local' ] ], \
                'base_vc': [ 'fi.baseName || COALESCE(i.copyName, "") AS name', ['LEFT JOIN AgLibraryFile fi ON i.rootFile = fi.id_local' ] ], \
                'True' :  [ 'fi.baseName || "." || fi.extension AS name', [ 'LEFT JOIN AgLibraryFile fi ON i.rootFile = fi.id_local' ] ], \
                'basext': ['fi.baseName || "." || fi.extension AS name', [ 'LEFT JOIN AgLibraryFile fi ON i.rootFile = fi.id_local'] ], \
                'basext_vc': ['fi.baseName || COALESCE(i.copyName, "") || "." || fi.extension AS name', [ 'LEFT JOIN AgLibraryFile fi ON i.rootFile = fi.id_local'] ], \
                }, \
            'vname' : { \
                'True' : [ 'i.copyName AS vname',  None ] }, \
            'uuid' : { \
                'True' : [ 'i.id_global AS uuid',  None ] }, \
            'master' : { \
                'True' : [ 'i.masterImage AS master',  None ] }, \
            'id' : { \
                'True' : [ 'i.id_local AS id',  None ] }, \
            'rating' : { \
                'True' : [ 'i.rating AS rating',  None ] }, \
            'colorlabel' : { \
                'True' : [ 'i.colorlabels AS colorlabel',  None ] }, \
            'datemod' : { \
                # modif date (including keywords changes)
                'True' : [ 'i.touchtime AS datemod',  None ], }, \
            'datehist' : { \
                # modif date based on history developement steps, ignoring exportations and publications (TODO: strings need to be localized )
                'True' : [ '(SELECT max(ids2.datecreated) '\
                            'FROM Adobe_libraryImageDevelopHistoryStep ids2 WHERE ids2.image =i.id_local AND substr(name,1,4) NOT IN ("Expo", "Publ")) AS datehist',  None ], }, \
            'modcount' : { \
                'True' : [ 'i.touchCount AS modcount',  None ] }, \
            'datecapt' : { \
                'True' : [ 'i.captureTime AS datecapt',  None ] }, \
            'xmp' : { \
                'True' : \
                    [   'am.xmp AS xmp', \
                        [ 'LEFT JOIN Adobe_AdditionalMetadata am on i.id_local = am.image' ] \
                    ] \
                }, \
            'count': { \
                'name' : [ 'count(name) AS countname' ,  None ], \
                'master' : [ 'count(masterimage) AS countmaster' ,  None ], \
                }, \
            'stackpos' : { \
                'True' :  \
                    [   'fsi.position AS stackpos', \
                        [ 'LEFT JOIN AgLibraryFolderStackImage fsi ON i.id_local = fsi.image' ] \
                    ] \
                }, \
            'keywords': { \
                'True' :  \
                    [   '(SELECT GROUP_CONCAT(kwdef.name) FROM AgLibraryKeywordImage kwimg JOIN AgLibraryKeyword kwdef ON kwdef.id_local = kwimg.tag'\
                        ' WHERE kwimg.image=i.id_local) AS keywords', \
                        None \
                    ] \
                }, \
            'collections': { \
                'True' :  \
                    [   '(SELECT GROUP_CONCAT(col.name) FROM AgLibraryCollection col JOIN AgLibraryCollectionimage ci ON ci.collection = col.id_local'\
                        ' WHERE ci.image = i.id_local) AS Collections' \
                        '', \
                        None \
                    ] \
                }, \

            'camera' : { \
                'True' : [ 'cm.value AS camera', \
                        ['LEFT JOIN AgHarvestedExifMetadata em on i.id_local = em.image',
                        'LEFT JOIN AgInternedExifCameraModel cm on cm.id_local = em.cameraModelRef'] ] },
            'lens' : { \
                'True' : [ 'el.value AS lens', \
                        ['LEFT JOIN AgHarvestedExifMetadata em on i.id_local = em.image',
                        'LEFT JOIN AgInternedExifLens el on el.id_local = em.lensRef'] ] },
            'iso' : { \
                'True' : [ 'em.isoSpeedRating AS iso',  ['LEFT JOIN AgHarvestedExifMetadata em on i.id_local = em.image'] ] }, \
            'focal' : { \
                'True' : [ 'em.focalLength AS focal',  ['LEFT JOIN AgHarvestedExifMetadata em on i.id_local = em.image'] ] }, \
            'aperture' : { \
                'True' : [ 'em.aperture AS aperture',  ['LEFT JOIN AgHarvestedExifMetadata em on i.id_local = em.image'] ] }, \
            'speed' : { \
                'True' : [ 'em.shutterSpeed AS speed',  ['LEFT JOIN AgHarvestedExifMetadata em on i.id_local = em.image'] ] }, \
            'dims' : { \
                'True' : [ '(SELECT CASE '\
                            'WHEN ids.croppedWidth <> "uncropped" AND i.orientation IN ("AB", "BA", "CD", "DC") THEN CAST(ids.croppedWidth AS int) || "x" || CAST(ids.croppedHeight AS int) '\
                            'WHEN ids.croppedWidth <> "uncropped" AND i.orientation IN ("AD", "DA", "BC", "CB") THEN CAST(ids.croppedHeight AS int) || "x" || CAST(ids.croppedWidth AS int) '\
                            'WHEN ids.croppedWidth = "uncropped" AND i.orientation IN ("AB", "BA", "CD", "DC") THEN CAST(i.filewidth AS int) || "x" || CAST(i.fileHeight AS int) '\
                            'WHEN ids.croppedWidth = "uncropped" AND i.orientation IN ("AD", "DA", "BC", "CB") THEN CAST(i.fileHeight AS int) || "x" || CAST(i.filewidth AS int) '\
                            'ELSE CAST(i.filewidth AS int) || "x" || CAST(i.fileHeight AS int) END) AS dims ',
                      ['LEFT JOIN Adobe_imageDevelopSettings ids ON ids.image = i.id_local'] ] }, \
            'aspectratio' : { \
                'True' : [ 'i.aspectRatioCache AS aspectRatio',  None ] }, \
            'creator' : { \
                'True' : [ 'iic.value AS creator',
                        ['LEFT JOIN AgHarvestedIptcMetadata im on i.id_local = im.image',\
                         'LEFT JOIN AgInternedIptcCreator iic on im.creatorRef = iic.id_local'] ] }, \
            'caption' : { \
                'True' : [ 'iptc.caption AS caption',\
                        ['LEFT JOIN AgLibraryIPTC iptc on i.id_local = iptc.image'] ] }, \
            'latitude' : { \
                'True' : [ 'em.GpsLatitude AS latitude',  ['LEFT JOIN AgHarvestedExifMetadata em on i.id_local = em.image'] ] }, \
            'longitude' : { \
                'True' : [ 'em.GpsLongitude AS longitude',  ['LEFT JOIN AgHarvestedExifMetadata em on i.id_local = em.image'] ] }, \
            'exif' : { \
                LRSelectGeneric._VAR_FIELD: \
                    [   None,
                        [ 'LEFT JOIN AgHarvestedExifMetadata em on i.id_local = em.image' ] \
                    ] \
                }, \
            'pubcollection': { \
                'True' : ['pc.name AS pubcollection', ['LEFT JOIN AgLibraryPublishedCollectionImage pci ON pci.image = i.id_local',
                     'LEFT JOIN AgLibraryPublishedCollection pc ON pc.id_local = pci.collection', ]], \
                },\
            'pubname' : { \
                'True' : [ 'rm.remoteId AS pubname',  ['LEFT JOIN AgRemotePhoto rm on i.id_local = rm.photo'] ] }, \
            'pubtime' : { \
                'True' : [ '(select substr(rm.url, pos+1) from (select instr(rm.url, "/") as pos)) AS pubtime', \
                        ['LEFT JOIN AgRemotePhoto rm on i.id_local = rm.photo'] ] }, \
            'extfile' : { \
                'True' :  \
                    [   'fi.sidecarExtensions AS extfile', None  ] \
                }, \
            },


            #
            # Criteria description
            #
            { \
                'name' : [ \
                    'LEFT JOIN AgLibraryFile fi ON i.rootFile = fi.id_local', \
                    ' UPPER(fi.baseName) LIKE "%s"', \
                    ],
                'exactname' : [ \
                    'LEFT JOIN AgLibraryFile fi ON i.rootFile = fi.id_local', \
                    ' UPPER(fi.baseName) = "%s"', \
                    ],
                'ext' : [ \
                    'LEFT JOIN AgLibraryFile fi ON i.rootFile = fi.id_local',
                    ' UPPER(fi.extension) LIKE "%s"', \
                    ],
                'exact_ext' : [ \
                    'LEFT JOIN AgLibraryFile fi ON i.rootFile = fi.id_local',
                    'UPPER(fi.extension) = "%s"'
                    ],
                'id' : [ \
                    '', \
                    'i.id_local = %s', \
                    ],
                'uuid' : [ \
                    '', \
                    'i.id_global = "%s"', \
                    ],
                'datecapt' : [ \
                    '', \
                    '%s', self.func_oper_parsedate,
                    ],
                'datemod' : [ \
                    '', \
                    'i.touchtime %s %s', self.func_oper_dateloc_to_lrstamp, \
                    ],
                'modcount' : [ \
                    '', \
                    'i.touchcount %s', \
                    ],
                'videos' : [ \
                    '', \
                    'i.fileFormat %s "VIDEO"', self.func_bool_to_equal, \
                    ],
                'vcopies' : [ \
                    '', \
                    'i.masterImage %s', self.func_value_or_null, \
                    ],
                'rating' : [ \
                    '', \
                    '%s', self.func_rating, \
                    ],
                'colorlabel' : [ \
                    '', \
                    'i.colorlabels %s %s', self.func_value_or_not_equal,
                    ],
                'title' : [ \
                    'LEFT JOIN AgMetadataSearchIndex msi ON i.id_local = msi.image', \
                    '%s', self.func_titleindex \
                    ],
                'caption' : [ \
                    'LEFT JOIN AgLibraryIPTC iptc on i.id_local = iptc.image', \
                    'iptc.caption %s', self.func_like_value_or_null
                    ],
                'creator' : [ \
                    ['LEFT JOIN AgHarvestedIptcMetadata im on i.id_local = im.image', \
                    'LEFT JOIN AgInternedIptcCreator iic on im.creatorRef = iic.id_local'], \
                    'iic.value LIKE "%s"',
                    ],
                'iso' : [ \
                    'LEFT JOIN AgHarvestedExifMetadata em on i.id_local = em.image', \
                    'em.isoSpeedRating %s',
                    ],
                'focal' : [ \
                    'LEFT JOIN AgHarvestedExifMetadata em on i.id_local = em.image', \
                    'em.focalLength %s',
                    ],
                'aperture' : [ \
                    'LEFT JOIN AgHarvestedExifMetadata em on i.id_local = em.image', \
                    'em.aperture %s', self.func_aperture,
                    ],
                'speed' : [ \
                    'LEFT JOIN AgHarvestedExifMetadata em on i.id_local = em.image', \
                    'em.shutterSpeed %s', self.func_speed,
                    ],
                'camera' : [ \
                    ['LEFT JOIN AgHarvestedExifMetadata em on i.id_local = em.image', \
                    ' LEFT JOIN AgInternedExifCameraModel cm on cm.id_local = em.cameraModelRef'], \
                    'cm.value LIKE "%s"',
                    ],
                'lens' : [ \
                    ['LEFT JOIN AgHarvestedExifMetadata em on i.id_local = em.image', \
                    ' LEFT JOIN AgInternedExifLens el on el.id_local = em.lensRef'], \
                    'el.value LIKE "%s"',
                    ],
                # TODO: width and height criteria works on 'virtual' column dims ! So, the 'dims' column dims MUST to be included in the query
                'width' : [ \
                    ['LEFT JOIN Adobe_imageDevelopSettings ids ON ids.image = i.id_local'], \
                    'CAST(substr(dims, 1, instr(dims, "x")-1) AS int) %s',
                    ],
                'height' : [ \
                    ['LEFT JOIN Adobe_imageDevelopSettings ids ON ids.image = i.id_local'], \
                    'CAST(substr(dims, instr(dims, "x")+1) AS int) %s',
                    ],
                'aspectratio' : [ \
                    '', \
                    'i.aspectRatioCache %s', \
                    ],
                'hasgps' : [ \
                    ['LEFT JOIN AgHarvestedExifMetadata em on i.id_local = em.image'], \
                    'em.hasGps = %s', self.func_0_1,
                    ],
                'gps' : [ \
                    ['LEFT JOIN AgHarvestedExifMetadata em on i.id_local = em.image'], \
                    '%s', self.func_gps,
                    ],
                'import' : [ \
                    ['LEFT JOIN AgLibraryImportImage impim on  i.id_local = impim.image', \
                    ' LEFT JOIN AgLibraryImport imp on impim.import = imp.id_local'], \
                    'imp.id_local = %s',
                    ],
                'idcollection' : [ \
                    ['LEFT JOIN AgLibraryCollectionimage ci ON ci.image = i.id_local', \
                    ' LEFT JOIN AgLibraryCollection col ON col.id_local = ci.Collection'],\
                    'col.id_local = %s', \
                    ],
                'collection' : [ \
                    ['LEFT JOIN AgLibraryCollectionimage ci<NUM> ON ci<NUM>.image = i.id_local',
                     'LEFT JOIN AgLibraryCollection col<NUM> ON col<NUM>.id_local = ci<NUM>.Collection'],\
                    'col<NUM>.name LIKE "%s"', \
                    ],
                'pubcollection' : [ \
                    ['LEFT JOIN AgLibraryPublishedCollectionImage pci ON pci.image = i.id_local',
                     'LEFT JOIN AgLibraryPublishedCollection pc ON pc.id_local = pci.collection'],\
                    '%s', self.func_published, \
                    ],
                'pubtime' : [ \
                    ['LEFT JOIN AgRemotePhoto rm on i.id_local = rm.photo'], \
                    'CAST((select substr(rm.url, pos+1) from (select instr(rm.url, "/") as pos)) AS INTEGER) %s %s', self.func_oper_dateutc_to_lrstamp, \
                    ],
                'metastatus' : [ \
                    ['LEFT JOIN Adobe_AdditionalMetadata am on i.id_local = am.image'], \
                    '%s', self.func_metastatus, \
                    ],
                'extfile' : [ \
                    'LEFT JOIN AgLibraryFile fi ON i.rootFile = fi.id_local', \
                    ' UPPER(fi.sidecarExtensions) LIKE "%s"', \
                    ],
                'stacks' : [ \
                    'LEFT JOIN AgLibraryFolderStackImage fsi ON i.id_local = fsi.image', \
                    '%s', self.func_stacks,
                    ],
                'keyword' : [ \
                    ['LEFT JOIN AgLibraryKeywordImage kwi<NUM> ON i.id_local = kwi<NUM>.image', \
                    ' LEFT JOIN AgLibraryKeyword kw<NUM> ON kw<NUM>.id_local = kwi<NUM>.tag'], \
                    'kw<NUM>.name LIKE "%s"',
                    ],
                'haskeywords' : [ \
                    '', \
                    '%s', self.func_haskeywords, \
                    ],
                'exifindex' : [ \
                    'LEFT JOIN AgMetadataSearchIndex msi ON i.id_local = msi.image', \
                    '%s', self.func_exifindex \
                    ],

                'sort' : [ \
                    '', \
                    'ORDER BY %s', \
                    ],
                'distinct' : [ \
                    '', \
                    'SELECT DISTINCT', \
                    ],
                'groupby' : [ \
                    '', \
                    'GROUP BY %s', \
                    ],               }
        )


    def func_metastatus(self, value):
        ''' specific value for metastatus '''
        if value == 'unknown':
            return 'am.externalXmpIsDirty = 0 AND i.sidecarStatus = 2.0'
        if value == 'changedondisk':
            return 'am.externalXmpIsDirty=1 and (i.sidecarStatus = 2.0 or i.sidecarStatus = 0.0)'
        if value == 'hasbeenchanged':
            return 'am.externalXmpIsDirty=0 and i.sidecarStatus = 1.0'
        if value == 'conflict':
            return 'am.externalXmpIsDirty=1 and i.sidecarStatus = 1.0'
        if value == 'uptodate':
            return 'am.externalXmpIsDirty=0 and i.sidecarStatus = 0.0'
        raise LRSelectException('invalid "metastatus" value "%s"' % value)

    def func_stacks(self, value):
        ''' specific value for photos stack '''
        if value == 'only':
            return 'fsi.position=1.0'
        if value == 'none':
            return 'fsi.image is NULL'
        if value == 'one':
            return '(fsi.image is NULL OR fsi.position=1.0)'
        else:
            raise LRSelectException('invalid "stacks" value "%s"' % value)

    def func_exifindex(self, value):
        '''  specific value for search exif '''
        if '&' in value:
            action = (' AND ', '&')
        elif '|' in value:
            action = (' OR ', '|')
        else:
            action = (' ', '__')
        return action[0].join([ 'msi.exifSearchIndex LIKE "%%/t%s/t%%"' % val for val in value.split(action[1])])

    def func_titleindex(self, value):
        '''  specific value for title : in otherSearchIndex column '''
        if '&' in value:
            action = (' AND ', '&')
        elif '|' in value:
            action = (' OR ', '|')
        else:
            action = (' ', '__')
        return action[0].join([ 'msi.otherSearchIndex LIKE "%%/t%s/t%%"' % val for val in value.split(action[1])])

    def func_aperture(self, value):
        '''
        convert aperture value (as 5.6, F8) to LR value : 2 * ( log base 2 of F number)
        take care with operator '=' because it works on float
        '''
        for index, char in enumerate(value):
            if char.isnumeric():
                oper = value[:index]
                if oper[-1].upper() == 'F':
                    oper = oper[:-1]
                value = value[index:]
                break
        if re.match(r'[F]*-?\d+(?:\.\d+)?', value) is None:
            raise LRSelectException('invalid aperture value')
        if not oper:
            oper = '='
        return '%s %s' % (oper, 2 * math.log(float(value), 2))

    def func_speed(self, value):
        '''
        convert speed value in seconds to LR value : log base 2 of Nth of speed
        ex: ">1/1000" for 1/1000s, "<5" for 5 seconds
        '''
        for index, char in enumerate(value):
            if char.isnumeric():
                oper = value[:index]
                value = value[index:]
                break
        try:
            value = eval(value)
            value = '%s %s' % (oper, math.log(float(1/value), 2))
        except ValueError as _e:
            raise LRSelectException(_e)
        return value

    def func_haskeywords(self, value):
        '''
        select photos with or without keywords
        '''
        if value in ['True', '1']:
            return 'i.id_local IN (SELECT DISTINCT kwi.image FROM AgLibraryKeywordImage kwi)'
        if value in ['False', '0']:
            self._add_from(['LEFT JOIN AgLibraryKeywordImage kwi1 ON i.id_local = kwi1.image'], self.froms)
            return 'kwi1.image IS NULL'
        raise LRSelectException('invalid haskeywords value')

    def func_gps(self, value):
        '''
        select photos within gps values
            ex: value=paris/lyon
        '''
        def reorder(val1, val2):
            return min(val1, val2), max(val1, val2)

        log = logging.getLogger()
        re_gpsw = re.compile(r'([\d\-\.]+);([\d\-\.]+)\+([\d\.]+)')                 # 45.78;-2.54+100
        re_2gps = re.compile(r'([\d\-\.]+);([\d\-\.]+)/([\d\-\.]+);([\d\-\.]+)')    # 45.78;-2.51/46.01;1.05
        re_townw = re.compile(r'([\w\'\ -;]+)\+([\d\.]+)')                          # paris+50
        re_2town = re.compile(r'([\w\'\ -]+)/([\w\'\ -]+)')                         # paris/geneve
        re_photo = re.compile(r'photo:([\w\'\ _-]+)\+([\d\.]+)')                    # photo_000151+2 (2km around photo)

        if re_photo.match(value):
            name_photo, width = re_photo.match(value).groups()
            lrphoto = LRSelectPhoto(self.lrdb)
            coords = lrphoto.select_generic('latitude, longitude', f'name={name_photo}').fetchone()
            if not coords:
                raise LRSelectException(f'Photo "{name_photo}" not in Lightroom')
            lat, lon = coords
            if not lat or not lon:
                raise LRSelectException(f'Photo "{name_photo}" is not geolocalized')
            (lat1, lon1), (lat2, lon2) = square_around_location(lat, lon, width)
        elif re_gpsw.match(value):
            lat, lon, width = re_gpsw.match(value).groups()
            (lat1, lon1), (lat2, lon2) = square_around_location(lat, lon, width)
        elif re_2gps.match(value):
            lat1, lon1, lat2, lon2 = re_2gps.match(value).groups()
        elif re_townw.match(value):
            town, width = re_townw.match(value).groups()
            try:
                (lat, lon), address = geocodage(town)
                log.info('Geocodage for %s : %s, %s (%s)', town, lat, lon, address)
            except TypeError:
                raise LRSelectException('Town coordinates not found')
            (lat1, lon1), (lat2, lon2) = square_around_location(lat, lon, width)
        elif re_2town.match(value):
            town1, town2 = re_2town.match(value).groups()
            try:
                (lat1, lon1), address1 = geocodage(town1)
                (lat2, lon2), address2 = geocodage(town2)
                log.info('Geocodage for %s : %s, %s (%s)', town1, lat1, lon1, address1)
                log.info('Geocodage for %s : %s, %s (%s)', town2, lat2, lon2, address2)
            except TypeError:
                raise LRSelectException('Town coordinates not found')
        else:
            raise LRSelectException('GPS coordinates malformed')

        lat1, lat2 = reorder(lat1, lat2)
        lon1, lon2 = reorder(lon1, lon2)
        return '(em.hasGps = 1 AND em.gpsLatitude BETWEEN %s AND %s AND em.gpsLongitude BETWEEN %s AND %s)' % \
                (lat1, lat2, lon1, lon2)

    def func_published(self, value):
        '''
        select photos published
        '''
        if value == 'True':
            return 'i.id_local = pci.image'
        return '(i.id_local = pci.image AND pc.name = "%s" COLLATE NOCASE)' % value

    def func_pubtime(self, value):
        '''
        select publish time
        '''
        if value == 'True':
            return 'i.id_local = pci.image'
        return '(i.id_local = pci.image AND pc.name = "%s" COLLATE NOCASE)' % value

    def func_rating(self, value):
        '''
        select rating
        '''
        if value[0] == '<' or value == '>=0':
            return '(i.rating IS NULL OR i.rating %s)' % value
        if value == "=0":
            return 'i.rating IS NULL'
        return 'i.rating %s' % value


    def select_predefined(self, columns, _criters):
        '''
        SQL functions support
        '''
        def _todt(date):
            parts = re.findall(r'\d+', date)
            if len(parts) == 1:
                return 'by_year', datetime(int(parts[0]), 1, 1,)
            if len(parts) == 2:
                return 'by_month', datetime(int(parts[0]), int(parts[1]), 1)
            if  len(parts) == 3:
                return 'by_day', datetime(int(parts[0]), int(parts[1]), int(parts[3]))
            raise LRSelectException('Incorrect date')

        match = re.match(r'count_by_date\((.+)\)', columns)
        if match:
            mode = 'by_year'
            dt_from = datetime(2010, 1, 1)
            dt_to = None
            dates = match.group(1).split(',')
            if len(dates) > 0:
                mode, dt_from = _todt(dates[0])
            if len(dates) > 1:
                _, dt_to = _todt(dates[1])
            return self.lrdb.select_count_by_date(mode, dt_from, dt_to, sql=True)
        match = re.match(r'duplicated_names(.+)', columns)
        if match:
            return self.lrdb.select_duplicates(sql=True)


    def select_generic(self, columns, criters='', **kwargs):
        '''
        Build SQL request for photo table (Adobe_images) from key/value pair
        columns :
            - 'name'='base'|'basext'|'full' : base name, basename + extension, full name (path,name, extension)
                With 'base_vc', 'basext_vc', 'full_vc' names for virtual copies are completed with copy name.
            - 'id'         : id photo (Adobe_images.id_local)
            - 'uuid'       : UUID photo (Adobe_images.id_global)
            - 'rating'     : rating/note
            - 'colorlabel' : color and label
            - 'datemod'    : modificaton date
            - 'datecapt'   : capture date
            - 'modcount'   : number of modifications
            - 'master'     : master image of virtual copy
            - 'xmp'        : all xmp metadatas
            - 'vname'      : virtual copy name
            - 'stackpos'   : position in stack
            - 'keywords'   : keywords list
            - 'collections': collections list
            - 'exif'       : 'var:SQLCOLUMN' : display column in table AgHarvestedExifMetadata. Ex: "exif=var:hasgps"
            - 'extfile'    : extension of an external/extension file (jpg,xmp,...)
            - 'dims'       : image dimensions in form <WIDTH>x<HEIGHT>
            - 'aspectratio': aspect ratio (width/height)
            - 'camera'     : camera name
            - 'lens'       : lens name
            - 'iso'        : ISO value
            - 'focal'      : focal lens
            - 'aperture'   : aperture lens
            - 'speed'      : speed shutter
            - 'latitude'   : GPS latitude
            - 'longitude'  : GPS longitude
            - 'creator'    : photo creator
            - 'caption'    : photo caption
            - 'pubname'    : remote path and name of published photo
            - 'pubcollection' : name of publish collection
            - 'pubtime'    : published datetime in seconds from 2001-1-1
        criterias :
            - 'name'       : (str) filename without extension
            - 'exactname'  : (str) filename insensitive without extension
            - 'ext'        : (str) file extension
            - 'id'         : (int) photo id (Adobe_images.id_local)
            - 'uuid'       : (string) photo UUID (Adobe_images.id_global)
            - 'rating'     : (str) [operator (<,<=,>,=, ...)] and rating/note. ex: "rating==5"
            - 'colorlabel' : (str) color and label. Color names are localized (Bleu, Rouge,...)
            - 'creator'    : (str) photo creator
            - 'caption'    : (true/false/str) photo caption
            - 'datecapt'   : (str) operator (<,<=,>, >=) and capture date
            - 'datemod'    : (str) operator (<,<=,>, >=) and lightroom modification date
            - 'modcount'   : (int) number of modifications
            - 'iso'        : (int) ISO value with operators <,<=,>,>=,= (ex: "iso=>=1600")
            - 'focal'      : (int) focal lens with operators <,<=,>,>=,= (ex: "iso=>135")
            - 'aperture'   : (float) aperture lens with operators <,<=,>,>=,= (ex: "aperture=<8")
            - 'speed'      : (float) speed shutter with operators <,<=,>,>=,= (ex: "speed=>=8")
            - 'width'      : (int) cropped image width. Need to include column "dims"
            - 'height      : (int) cropped image height. Need to include column "dims"
            - 'aspectratio': (float) aspect ratio (width/height)
            - 'hasgps'     : (bool) has GPS datas
            - 'gps'        : (str) GPS rectangle defined by :
                                - town or coordinates, and bound in kilometer (ex:"paris+20", "45.7578;4.8320+10"),
                                - 2 towns or coordinates (ex: "grenoble/lyon", "44.84;-0.58/43.63;1.38")
                                - a geolocalized Lightroom photo name (ex:"photo:NIK_10312")
            - 'videos'     : (bool) type videos
            - 'exifindex'  : search words in exif (AgMetadataSearchIndex). Use '&' for AND words '|' for OR. ex: "exifindex=%Lowy%&%blanko%"
            - 'vcopies'    : 'NULL'|'!NULL'|'<NUM>' : all, none virtual copies or copies for a master image NUM
            - 'keyword'    : (str) keyword name. Only one keyword can be specified in request
            - 'haskeywords': (bool) photos with or without keywords
            - 'import'     : (int) import id
            - 'stacks'     : operation on stacks in :
                    'only' = selects only the photos in stacks
                    'none' = excludes the photos in stacks
                    'one'  = excludes the photos in stacks not at first position
            - 'metastatus' :  metadatas status
                    'conflict' = metadatas different on disk from db
                    'changedondisk' = metadata changed externally on disk
                    'hasbeenchanged' = to be save on disk
                    'conflict' = metadatas different on disk from db
                    'uptodate' = uptodate, in error, or to write on disk
                    'unknown' = write error, phot missing ...
            - 'idcollection' : (int) collection id
            - 'collection' : (str) collection name
            - 'pubcollection: (str) publish collection name
            - 'pubtime     : (str) publish time,  operator (<,<=,>, >=)
            - 'extfile'    : (str) has external file with <value> extension as jpg,xmp... (field AgLibraryFile.sidecarExtensions)
            - 'sort'       : sql sort string
            - 'distinct'   : suppress similar lines of results
        kwargs :
            - distinct : request SELECT DISTINCT
            - debug : print sql
            - print : print sql and return None
            - sql : return SQL string only
        '''

        if not columns:
            columns = 'name=basext'
        return super().select_generic(columns, criters, **kwargs)
