#!python3
# # -*- coding: utf-8 -*-
# pylint: disable=line-too-long,bad-continuation, bad-whitespace

'''
LRSelectPhoto class for building SQL select for table Adobe_images
'''

from math import log
from .lrselectgeneric import LRSelectGeneric, LRSelectException

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
                True :  '*' },
            'name' : {
                'full' : \
                    [   'rf.absolutePath || fo.pathFromRoot || fi.baseName || "." || fi.extension AS name', \
                        [ 'LEFT JOIN AgLibraryFile fi ON i.rootFile = fi.id_local', 'LEFT JOIN AgLibraryFolder fo ON fi.folder = fo.id_local', 'LEFT JOIN AgLibraryRootFolder rf ON fo.rootFolder = rf.id_local' ],
                    ],\
                'base': [ 'fi.baseName AS name', ['LEFT JOIN AgLibraryFile fi ON i.rootFile = fi.id_local' ] ], \
                True :  [ 'fi.baseName || "." || fi.extension AS name', [ 'LEFT JOIN AgLibraryFile fi ON i.rootFile = fi.id_local' ] ], \
                'basext': ['fi.baseName || "." || fi.extension AS name', [ 'LEFT JOIN AgLibraryFile fi ON i.rootFile = fi.id_local'] ], \
        #            'basextcopy': ['fi.baseName || i.copyName || "." || fi.extension AS name', [ 'JOIN AgLibraryFile fi ON i.rootFile = fi.id_local'] ], \
                }, \
            'vname' : { \
                True : [ 'i.copyName AS vname',  None ] }, \
            'uuid' : { \
                True : [ 'i.id_global AS uuid',  None ] }, \
            'master' : { \
                True : [ 'i.masterImage AS master',  None ] }, \
            'id' : { \
                True : [ 'i.id_local AS id',  None ] }, \
            'rating' : { \
                True : [ 'i.rating',  None ] }, \
            'colorlabel' : { \
                True : [ 'i.colorlabels AS colorlabel',  None ] }, \
            'datemod' : { \
                True : [ 'strftime("%Y-%m-%dT%H:%M:%S", datetime("2001-01-01",  "+" || i.touchtime || " seconds")) AS datemod',  None ], }, \
            'modcount' : { \
                True : [ 'i.touchCount AS modcount',  None ] }, \
            'datecapt' : { \
                True : [ 'i.captureTime AS datecapt',  None ] }, \
            'xmp' : { \
                True : \
                    [   'am.xmp AS xmp', \
                        [ 'LEFT JOIN Adobe_AdditionalMetadata am on i.id_local = am.image' ] \
                    ] \
                }, \
            'count': { \
                'name' : [ 'count(name) AS countname' ,  None ], \
                'master' : [ 'count(masterimage) AS countmaster' ,  None ], \
                }, \
            'stackpos' : { \
                True :  \
                    [   'fsi.position AS stackpos', \
                        [ 'LEFT JOIN AgLibraryFolderStackImage fsi ON i.id_local = fsi.image' ] \
                    ] \
                }, \
            'keywords': { \
                True :  \
                    [   'kw.name', \
                        [ 'LEFT JOIN AgLibraryKeywordImage kwi ON i.id_local = kwi.image',
                          'LEFT JOIN AgLibraryKeyword kw ON kw.id_local = kwi.tag'  ] \
                    ] \
                }, \

            'camera' : { \
                True : [ 'cm.value', \
                        ['LEFT JOIN AgHarvestedExifMetadata em on i.id_local = em.image',
                        'LEFT JOIN AgInternedExifCameraModel cm on cm.id_local = em.cameraModelRef'] ] },
            'lens' : { \
                True : [ 'el.value', \
                        ['LEFT JOIN AgHarvestedExifMetadata em on i.id_local = em.image',
                        'LEFT JOIN AgInternedExifLens el on el.id_local = em.lensRef'] ] },
            'iso' : { \
                True : [ 'em.isoSpeedRating',  ['LEFT JOIN AgHarvestedExifMetadata em on i.id_local = em.image'] ] }, \
            'focal' : { \
                True : [ 'em.focalLength',  ['LEFT JOIN AgHarvestedExifMetadata em on i.id_local = em.image'] ] }, \
            'aperture' : { \
                True : [ 'em.aperture',  ['LEFT JOIN AgHarvestedExifMetadata em on i.id_local = em.image'] ] }, \
            'speed' : { \
                True : [ 'em.shutterSpeed',  ['LEFT JOIN AgHarvestedExifMetadata em on i.id_local = em.image'] ] }, \

            'exif' : { \
                LRSelectGeneric._VAR_FIELD: \
                    [   None,
                        [ 'LEFT JOIN AgHarvestedExifMetadata em on i.id_local = em.image' ] \
                    ] \
                }, \
            'extfile' : { \
                True :  \
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
                    'i.id_global= %s', \
                    ],
                'datecapt' : [ \
                    '', \
                    'i.captureTime %s "%s"', self.func_oper_parsedate, \
                    ],
                # fromdatecapt obsolete replaced by datecapt
                'fromdatecapt' : [ \
                    '', \
                    'i.captureTime >= "%s"', self.func_parsedate, \
                    ],
                # todatecapt obsolete replaced by datecapt
                'todatecapt' : [ \
                    '', \
                    'i.captureTime <= "%s"', self.func_parsedate, \
                    ],
                'datemod' : [ \
                    '', \
                    'i.touchtime %s %s', self.func_oper_date_to_lrstamp, \
                    ],
                # fromdatemod obsolete replaced by datemod
                'fromdatemod' : [ \
                    '', \
                    'i.touchtime >= %s', self.func_date_to_lrstamp, \
                    ],
                # todatemod obsolete replaced by datemod
                'todatemod' : [ \
                    '', \
                    'i.touchtime <= %s', self.func_date_to_lrstamp, \
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
                    'i.rating %s', \
                    ],
                'colorlabel' : [ \
                    '', \
                    'i.colorlabels %s %s', self.func_value_or_not_equal,
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
                'import' : [ \
                    ['LEFT JOIN AgLibraryImportImage impim on  i.id_local = impim.image', \
                    ' LEFT JOIN AgLibraryImport imp on impim.import = imp.id_local'], \
                    'imp.id_local = %s',
                    ],
                'idcollection' : [ \
                    ['LEFT JOIN  AgLibraryCollectionimage ci ON ci.image = i.id_local', \
                    ' LEFT JOIN AgLibraryCollection col ON col.id_local = ci.Collection'],\
                    'col.id_local = %s', \
                    ],
                'collection' : [ \
                    ['LEFT JOIN  AgLibraryCollectionimage ci ON ci.image = i.id_local',
                     'LEFT JOIN AgLibraryCollection col ON col.id_local = ci.Collection'],\
                    'col.name = "%s"', \
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
                    'fsi.position %s', self.func_stacks,
                    ],
                'keyword' : [ \
                    ['LEFT JOIN AgLibraryKeywordImage kwi ON i.id_local = kwi.image', \
                    ' LEFT JOIN AgLibraryKeyword kw ON kw.id_local = kwi.tag'], \
                    'kw.name="%s"',
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
               }
        )


    def func_metastatus(self, value):
        ''' specific value for metastatus '''
        if value == 'unknown':
            return 'am.externalXmpIsDirty = 0 AND i.sidecarStatus = 2.0'
        elif value == 'changedondisk':
            return 'am.externalXmpIsDirty=1 and (i.sidecarStatus = 2.0 or i.sidecarStatus = 0.0)'
        elif value == 'hasbeenchanged':
            return 'am.externalXmpIsDirty=0 and i.sidecarStatus = 1.0'
        elif value == 'conflict':
            return 'am.externalXmpIsDirty=1 and i.sidecarStatus = 1.0'
        elif value == 'uptodate':
            return 'am.externalXmpIsDirty=0 and i.sidecarStatus = 0.0'
        else:
            raise LRSelectException('invalid "metastatus" value "%s"' % value)

    def func_stacks(self, value):
        ''' specific value for photos stack '''
        if value == 'only':
            return 'fsi.position=1.0'
        elif value == 'none':
            return 'fsi.image is NULL'
        elif value == 'one':
            return 'fsi.image is NULL OR fsi.position=1.0'
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

    def func_aperture(self, value):
        '''
        convert aperture value to LR value : 2 * ( log base 2 of F number)
        take care with operator '=' because it works on float
        '''
        for index, char in enumerate(value):
            if char.isnumeric():
                oper = value[:index]
                value = value[index:]
                break
        if not value.isnumeric():
            raise LRSelectException('invalid aperture value')
        if not oper:
            oper = '='
        return '%s %s' % (oper, 2 * log(int(value), 2))

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
            value = '%s %s' % (oper, log(float(1/value), 2))
        except ValueError as _e:
            raise LRSelectException(_e)
        return value


    def select_generic(self, columns, criters, **kwargs):
        '''
        Build SQL request for photo table (Adobe_images) from key/value pair
        columns :
            - 'name'='base'|'basext'|'full' : base name, basename + extension, full name (path,name, extension)
            - 'id'        : id photo (Adobe_images.id_local)
            - 'uuid'      : UUID photo (Adobe_images.id_global)
            - 'rating'    : rating/note
            - 'colorlabel': color and label
            - 'datemod'   : modificaton date
            - 'datecapt'  : capture date
            - 'modcount'  : number of modifications
            - 'master'    : master image of virtual copy
            - 'xmp'       : all xmp metadatas
            - 'vname'     : virtual copy name
            - 'stackpos'  : position in stack
            - 'keywords'  : keyword names (AgLibraryKeyword via AgLibraryKeywordImage)
            - 'exif'      : 'var:"COL1 COL2 ..." : exif metadatas (AgHarvestedExifMetadata). Ex: "exif=var:hasgps"
            - 'extfile'   : extension of an external/extension file (jpg,xmp,...)
            - 'camera'    : camera name
            - 'lens'      : lens name
            - 'iso'       : ISO value
            - 'focal'     : focal lens
            - 'aperture'  : aperture lens
            - 'speed'     : speed shutter
        criterias :
            - 'name'      : (str) filename without extension
            - 'exactname' : (str) filename insensitive without extension
            - 'ext'       : (str) file extension
            - 'id'        : (int) photo id (Adobe_images.id_local)
            - 'uuid'      : (string) photo UUID (Adobe_images.id_global)
            - 'rating'    : (str) [operator (<,<=,>,=, ...)] and rating/note. ex: "rating==5"
            - 'colorlabel': (str) color and label. Color names are localized (Bleu, Rouge,...)
            - 'datecapt'  : (str) operator (<,<=,>, >=) and capture date
            - 'datemod'   : (str) operator (<,<=,>, >=) and lightroom modification date
            - 'exifindex' : search words in exif (AgMetadataSearchIndex). Use '&' for AND words '|' for OR. ex: "exifindex=%Lowy%&%blanko%"
            - 'videos'    : (bool) type videos
            - 'vcopies'   : 'NULL'|'!NULL'|'<NUM>' : all, none virtual copies or copies for a master image NUM
            - 'keyword'   : (str) keyword name. Only one keyword can be specified in request
            - 'import'    : (int) import id
            - 'stacks'    : operation on stacks in :
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
            return 'am.externalXmpIsDirty = 0 AND i.sidecarStatus = 2.0'
        elif value == 'changedondisk':
            return 'am.externalXmpIsDirty=1 and (i.sidecarStatus = 2.0 or i.sidecarStatus = 0.0)'
        elif value == 'hasbeenchanged':
            return 'am.externalXmpIsDirty=0 and i.sidecarStatus = 1.0'
        elif value == 'conflict':
            return 'am.externalXmpIsDirty=1 and i.sidecarStatus = 1.0'
        elif value == 'uptodate':
            return 'am.externalXmpIsDirty=0 and i.sidecarStatus = 0.0'
        else:
            raise LRSelectException('invalid "metastatus" value "%s"' % value)

            - 'idcollection' : (int) collection id
            - 'collection': (str) collection name
            - 'extfile'   : (str) has external file with <value> extension as jpg,xmp... (field AgLibraryFile.sidecarExtensions)
            - 'iso'       : ISO value with operators <,<=,>,>=,= (ex: "iso=>=1600")
            - 'focal'     : focal lens with operators <,<=,>,>=,= (ex: "iso=>135")
            - 'aperture'  : aperture lens with operators <,<=,>,>=,= (ex: "aperture=<8")
            - 'speed'     : speed shutter with operators <,<=,>,>=,= (ex: "speed=>=8")
            - 'sort'      : sql sort string
            - 'distinct'  : suppress similar lines of results
        kwargs :
            - distinct : request SELECT DISTINCT
            - debug : print sql
            - print : print sql and return None
            - sql : return SQL string only
        '''

        if not columns:
            columns = 'name=basext'
        return super().select_generic(columns, criters, **kwargs)
