#!python3
# # -*- coding: utf-8 -*-
# pylint: disable=line-too-long,invalid-name

'''
SQLSmartColl Class for Lightroom Smart Collection manipulations


'''
from datetime import datetime, timedelta

from .lrselectgeneric import date_to_lrstamp
from .lrkeyword import LRKeywords
from .lrselectcollection import LRSelectCollection

class SmartException(Exception):
    ''' SQLSmartColl Exception '''


class SQLSmartColl():
    '''
    Build self.sql request from structure returned by LRCatDB.get_smartcoll_data

    Supported criteria :
        all
        aperture
        aspectRatio
        camera
        captureTime
        collection
        colorMode
        exif
        fileFormat
        filename
        flashFired
        focalLength
        hasAdjustments
        hadsGPSData
        iptc
        isoSpeedRating
        keywords
        labelColor
        labelText
        lens
        metadata
        metadataStatus
        rating
        shutterSpeed
        touchTime
        treatment
    '''

    _SELECT_DIMS = ', (SELECT CASE '\
                ' WHEN ids.croppedWidth <> "uncropped" AND i.orientation IN ("AB", "BA", "CD", "DC") THEN CAST(ids.croppedWidth AS int) || "x" || CAST(ids.croppedHeight AS int)'\
                ' WHEN ids.croppedWidth <> "uncropped" AND i.orientation IN ("AD", "DA", "BC", "CB") THEN CAST(ids.croppedHeight AS int) || "x" || CAST(ids.croppedWidth AS int)'\
                ' WHEN ids.croppedWidth = "uncropped" AND i.orientation IN ("AB", "BA", "CD", "DC") THEN CAST(i.filewidth AS int) || "x" || CAST(i.fileHeight AS int)'\
                ' WHEN ids.croppedWidth = "uncropped" AND i.orientation IN ("AD", "DA", "BC", "CB") THEN CAST(i.fileHeight AS int) || "x" || CAST(i.filewidth AS int)'\
                ' ELSE CAST(i.filewidth AS int) || "x" || CAST(i.fileHeight AS int) END) AS dims '


    def __init__(self, lrdb, smart, verbose=False):
        '''
        Initialize from :
        - lrdb : LRCatDB instance
        - smart : (str) smart collection as stored in database
            example :
                "s = {
                        {
                                criteria = "collection",
                                operation = "beginsWith",
                                value = "Ballades",
                                value2 = "",
                        },
                        {
                                criteria = "hasGPSData",
                                operation = "==",
                                value = false,
                        },
                        combine = "intersect",
                }"

        '''
        self.lrdb = lrdb
        self.smart = smart
        self.verbose = verbose
        # will be set latter
        self.base_sql_select = self.base_select = self.base_sql = self.sql = self.func = self.joins = ''



    def criteria_aspectRatio(self):
        ''' criteria aspectRatio '''
        what = {'square' : ('=', '!='), 'portrait' : ('<', '>='), 'landscape' : ('>', '<=')}
        if self.func['value'] not in what:
            raise SmartException('value unsupported: %s' %  self.func['value'])
        if self.func['operation'] not in ('==', '!='):
            raise SmartException('operation unsupported: %s on criteria %s' % (self.func['operation'], self.func['criteria']))
        oper_eq, oper_neq = what[self.func['value']]
        oper = oper_eq if self.func['operation'] == '==' else oper_neq
        self.sql += self._complete_sql('', 'WHERE i.aspectRatioCache %s 1' % oper)


    def criteria_widthCropped(self):
        ''' criteria widthCropped '''
        if self.func['operation'] == 'in':
            _sql = self._complete_sql('LEFT JOIN Adobe_imageDevelopSettings ids ON ids.image = i.id_local',\
                                'WHERE  i.fileFormat <> "VIDEO" AND '\
                                'CAST(substr(dims, 1, instr(dims, "x")-1) AS int) >= %s AND '\
                                'CAST(substr(dims, 1, instr(dims, "x")-1) AS int) <= %s' %  (self.func['value'], self.func['value2']))
        else:
            _sql = self._complete_sql('LEFT JOIN Adobe_imageDevelopSettings ids ON ids.image = i.id_local',\
                                'WHERE  i.fileFormat <> "VIDEO" AND '\
                                'CAST(substr(dims, 1, instr(dims, "x")-1) AS int) %s %s' %  (self.func['operation'], self.func['value']))
        _parts = _sql.split(' FROM ')
        _parts[0] += self._SELECT_DIMS
        self.sql += ' FROM '.join(_parts)


    def criteria_heightCropped(self):
        ''' criteria heightCropped '''
        if self.func['operation'] == 'in':
            _sql = self._complete_sql('LEFT JOIN Adobe_imageDevelopSettings ids ON ids.image = i.id_local',\
                                'WHERE  i.fileFormat <> "VIDEO" AND '\
                                'CAST(substr(dims, instr(dims, "x")+1) AS int) >= %s AND '\
                                'CAST(substr(dims, instr(dims, "x")+1) AS int) <= %s' %  (self.func['value'], self.func['value2']))
        else:
            _sql = self._complete_sql('LEFT JOIN Adobe_imageDevelopSettings ids ON ids.image = i.id_local',\
                                'WHERE  i.fileFormat <> "VIDEO" AND '\
                                'CAST(substr(dims, instr(dims, "x")+1) AS int) %s %s' %  (self.func['operation'], self.func['value']))
        _parts = _sql.split(' FROM ')
        _parts[0] += self._SELECT_DIMS
        self.sql += ' FROM '.join(_parts)


    def criteria_captureTime(self):
        ''' criteria captureTime '''
        if self.func['operation'] == 'in':
            # shift of 24 h for end of day :
            endtime = (datetime.strptime(self.func['value2'], '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')
            self.sql += self._complete_sql('', 'WHERE i.captureTime >= "%s" AND  i.captureTime < "%s"' % (self.func['value'], endtime))
        elif self.func['operation'] == 'inLast':
            self.sql += self._complete_sql('', 'WHERE i.captureTime >= date("now", "-%s %s")' % (self.func['value'], self.func['_units']))
        elif self.func['operation'] in ['==', '!=', '>', '<']:
            self.sql += self._complete_sql('', ' WHERE i.captureTime %s "%s"' % (self.func['operation'], self.func['value']))
        else:
            raise SmartException('operation unsupported: %s on criteria %s' % (self.func['operation'], self.func['criteria']))


    def criteria_touchTime(self):
        ''' criteria touchTime '''
        # convert and shift of 24 hours for end of day
        touchtime1 = date_to_lrstamp(self.func['value']) + (24 * 3600)
        touchtime2 = date_to_lrstamp(self.func['value2']) + (24 * 3600)
        if self.func['operation'] == 'in':
            self.sql += self._complete_sql('', ' WHERE i.touchTime >= %s AND  i.touchTime <= %s' % (touchtime1, touchtime2))
        elif self.func['operation'] == 'inLast':
            self.sql += self._complete_sql('', ' WHERE i.touchTime >= date("now", "-%s %s")' % (self.func['value'], self.func['_units']))
        elif self.func['operation'] == '<':
            self.sql += self._complete_sql('', ' WHERE i.touchTime < %s AND  i.touchTime > 0' % (touchtime1))
        elif self.func['operation'] in ['==', '!=', '>']:
            self.sql += self._complete_sql('', ' WHERE i.touchTime %s %s' % (self.func['operation'], touchtime1))
        else:
            raise SmartException('operation unsupported: %s on criteria %s' % (self.func['operation'], self.func['criteria']))


    def criteria_filename(self):
        ''' criteria filename '''
        self.build_string_value('', 'name')


    def criteria_fileFormat(self):
        ''' criteria file format (dng, video...). Operation "==" or "!=" '''
        self.sql += self._complete_sql('', ' WHERE i.fileFormat %s "%s"' % (self.func['operation'], self.func['value']))


    def criteria_collection(self):
        ''' criteria collection '''
        lrcollection = LRSelectCollection(self.lrdb)
        if self.func['operation'] in ['all', 'beginsWith', 'endsWith']:
            what = {'all' : '"%%%s%%"', 'beginsWith' : '"%s%%"', 'endsWith' : '"%%%s"'}
            values = self.func['value'].split()
            self.build_all_values_with_join(' LEFT JOIN AgLibraryCollectionimage ci%s ON ci%s.image = i.id_local'\
                                            ' LEFT JOIN AgLibraryCollection col%s ON col%s.id_local = ci%s.Collection ', \
                                            ' col%s.name ' +  'LIKE %s' % (what[self.func['operation']]), values)
        elif self.func['operation'] == 'noneOf':
            idscoll = list()
            for coll in self.func['value'].split():
                idscoll += [id for id, in lrcollection.select_generic('id', 'name="%%%s%%"' % coll).fetchall()]
            idscoll = ','.join([str(id) for id in idscoll])
            self.sql += self.base_sql + ' EXCEPT '+ self.base_sql + \
                ' LEFT JOIN  AgLibraryCollectionimage ci ON ci.image = i.id_local WHERE ci.collection IN (%s)' % idscoll
        else:
            raise SmartException('operation unsupported: %s on criteria %s' % (self.func['operation'], self.func['criteria']))



    def criteria_keywords(self):
        ''' criteria keyword '''
        _base_sql = self.lrdb.lrphoto.select_generic(self.base_select, 'keyword', distinct=True, sql=True)
        _base_sql = _base_sql[:_base_sql.find(' WHERE ')]
        if self.func['operation'] == 'noneOf':
            lrk = LRKeywords(self.lrdb)
            indexes = list()
            for keyword in self.func['value'].split():
                indexes += lrk.hierachical_indexes(keyword, self.func['operation'])
            indexes = ','.join([str(index) for index in indexes])
            self.sql += _base_sql + ' EXCEPT '+ _base_sql + ' WHERE kw1.id_local IN (%s)' % indexes

        elif self.func['operation'] == 'any':
            lrk = LRKeywords(self.lrdb)
            indexes = list()
            for keyword in self.func['value'].split():
                indexes += lrk.hierachical_indexes(keyword, self.func['operation'])
            indexes = ','.join([str(index) for index in indexes])
            self.sql += _base_sql  + ' WHERE kw1.id_local IN (%s)' % indexes

        elif self.func['operation']  in ['all', 'words', 'beginsWith', 'endsWith']:
            lrk = LRKeywords(self.lrdb)
            values = []
            for keyword in self.func['value'].split():
                indexes = lrk.hierachical_indexes(keyword, self.func['operation'])
                values.append(','.join([str(index) for index in indexes]))
            self.build_all_values_with_join(' LEFT JOIN AgLibraryKeywordImage kwi%s ON i.id_local = kwi%s.image '\
                                            ' LEFT JOIN AgLibraryKeyword kw%s ON kw%s.id_local = kwi%s.tag ', \
                                            ' kw%s.id_local IN (%s) ', values)

        elif self.func['operation'] == 'empty':
            _sql = _base_sql.replace(' LEFT JOIN AgLibraryKeyword kw1 ON kw1.id_local = kwi1.tag', '')
            self.sql += _sql + ' WHERE kwi1.image IS NULL'
        elif self.func['operation'] == 'notEmpty':
            _sql = self.lrdb.lrphoto.select_generic(self.base_select, '', sql=True)
            self.sql += _sql + '  WHERE  i.id_local IN (SELECT DISTINCT kwi.image FROM AgLibraryKeywordImage kwi) '
        else:
            raise SmartException('operation unsupported: %s on criteria %s' % (self.func['operation'], self.func['criteria']))


    def criteria_labelColor(self):
        ''' criteria color or text label (criteria labelText) '''
        value = self.func['value']
        if value == 'none':
            value = ''
        self.sql += self._complete_sql('', ' WHERE i.colorLabels %s "%s"' % (self.func['operation'], value))

    def criteria_labelText(self):
        ''' criteria label Text, same as  criteria color label '''
        self.criteria_labelColor()


    def criteria_colorMode(self):
        ''' criteria color mode '''
        self.sql += self._complete_sql('', ' WHERE i.colorMode %s %s' % (self.func['operation'], self.func['value']))


    def criteria_treatment(self):
        ''' criteria treatment '''
        if self.func['value'] == 'grayscale':
            self.sql += self._complete_sql('LEFT JOIN Adobe_ImageDevelopSettings ids ON ids.image = i.id_local', 'WHERE ids.grayscale %s 1.0' % (self.func['operation']))
        else:
            raise SmartException('operation unsupported: %s on criteria %s' % (self.func['operation'], self.func['criteria']))


    def criteria_hasAdjustments(self):
        '''
        criteria adjustment
        note: 3 possible values : -1, 0, 1
        '''
        if self.func['operation'] == 'isFalse':
            oper = '!= 1'
        else:
            oper = '= 1'
        self.sql += self._complete_sql('LEFT JOIN Adobe_ImageDevelopSettings ids ON ids.image = i.id_local', 'WHERE hasDevelopAdjustmentsEx %s' % oper)


    def criteria_rating(self):
        ''' criteria rating'''
        _sql = 'WHERE '
        if self.func['operation'].startswith('<') or (self.func['operation'].startswith('=') and self.func['value'] == '0'):
            _sql += 'i.rating is NULL OR '
        if self.func['operation'] in ['==', '!=', '>', '<', '>=', '<=']:
            _sql += 'i.rating %s %s' % (self.func['operation'], self.func['value'])
            self.sql += self._complete_sql('', _sql)
        else:
            raise SmartException('operation unsupported: %s on criteria %s' % (self.func['operation'], self.func['criteria']))


    def criteria_camera(self):
        ''' criteria camera : operations on strings + "==' or "!=" '''
        if self.func['operation'] == '!=':
            column = 'em.cameraModelRef IS NULL OR cm.value'
        elif self.func['operation'] == '==':
            column = 'cm.value'
        else:
            column = 'cm.searchIndex'
        self.build_string_value('LEFT JOIN AgHarvestedExifMetadata em on i.id_local = em.image ' \
                                'LEFT JOIN AgInternedExifCameraModel cm on cm.id_local = em.cameraModelRef',\
                                column)


    def criteria_lens(self):
        ''' criteria camera : operations on strings + "==' or "!=" '''
        if self.func['operation'] == '!=':
            column = 'em.lensRef IS NULL OR el.value'
        elif self.func['operation'] == '==':
            column = 'el.value'
        else:
            column = 'el.searchIndex'
        self.build_string_value('LEFT JOIN AgHarvestedExifMetadata em on i.id_local = em.image ' \
                                'LEFT JOIN AgInternedExifLens el on el.id_local = em.lensRef',\
                                column)


    def criteria_isoSpeedRating(self):
        ''' criteria iso '''
        self.build_numeric_value('LEFT JOIN AgHarvestedExifMetadata em on i.id_local = em.image', 'em.isoSpeedRating')


    def criteria_focalLength(self):
        ''' criteria focal length '''
        self.build_numeric_value('LEFT JOIN AgHarvestedExifMetadata em on i.id_local = em.image', 'em.focalLength')


    def criteria_aperture(self):
        ''' criteria aperture
            2 * ( log base 2 of F number)
            value = 2 * log(F/x], 2) and  [F/x] = 2**(value/2)
            f/1.0    : 0
            f/1.4    : 0.997085365434048
            f/2.0    : 2
            f/2.8    : 2.99708536543405
            ...
            f/8     : 6
        '''
        self.build_numeric_value('LEFT JOIN AgHarvestedExifMetadata em on i.id_local = em.image', 'em.aperture')

    def criteria_shutterSpeed(self):
        '''
        criteria shutterSpeed
        note : operator '>' < must be inverted !
        value = log base 2 of Nth of speed
        1/8s    : 3
        1/128s  : 7
        1/256s  : 8
        ...
        '''
        if '>' in self.func['operation']:
            self.func['operation'] = self.func['operation'].replace('>', '<')
        elif '<' in self.func['operation']:
            self.func['operation'] = self.func['operation'].replace('<', '>')
        self.build_numeric_value('LEFT JOIN AgHarvestedExifMetadata em on i.id_local = em.image', 'em.shutterSpeed')

    def criteria_hasGPSData(self):
        ''' criteria GPS'''
        self.build_boolean_value('LEFT JOIN AgHarvestedExifMetadata em on i.id_local = em.image', 'em.hasGps')


    def criteria_flashFired(self):
        ''' criteria flash fired '''
        self.build_boolean_value('LEFT JOIN AgHarvestedExifMetadata em on i.id_local = em.image', 'em.flashFired')


    def criteria_exif(self):
        ''' criteria exif '''
        self.build_string_value('LEFT JOIN AgMetadataSearchIndex msi ON i.id_local = msi.image', 'msi.exifSearchIndex')

    def criteria_iptc(self):
        ''' criteria IPTC '''
        self.build_string_value('LEFT JOIN AgMetadataSearchIndex msi ON i.id_local = msi.image', 'msi.iptcSearchIndex')


    def criteria_all(self):
        ''' criteria all text searchable :

        Find in earchindex, keywords, collections, creator, coptright, caption, colorprofile, full pathname
        '''
        rules = {\
            'any': (' OR '),\
            'all': (' AND '),\
        }
        if self.func['operation'] not in rules:
            raise SmartException('operation unsupported: %s on criteria %s' % (self.func['operation'], self.func['criteria']))
        combine = rules[self.func['operation']]
        lrk = LRKeywords(self.lrdb)
        wheres = [' WHERE ']
        joins = [' LEFT JOIN AgMetadataSearchIndex msi ON i.id_local = msi.image ',\
                ' LEFT JOIN AgLibraryFile fi ON i.rootFile = fi.id_local ',\
                ' LEFT JOIN AgLibraryFolder fo ON fi.folder = fo.id_local ',\
                ' LEFT JOIN AgLibraryRootFolder rf ON fo.rootFolder = rf.id_local ', \
                ' LEFT JOIN AgHarvestedIptcMetadata im on i.id_local = im.image ',\
                ' LEFT JOIN AgInternedIptcCreator iic on im.creatorRef = iic.id_local ',\
                ' LEFT JOIN AgLibraryIptc liptc on liptc.image = i.id_local ',\
                ' LEFT JOIN AgSourceColorProfileConstants scpc on scpc.image = i.id_local',\
                ]
        for num_value, value in enumerate(self.func['value'].split()):
            indexes = lrk.hierachical_indexes(value, self.func['operation'])
            joins.append(' LEFT JOIN AgLibraryKeywordImage kwi%s ON i.id_local = kwi%s.image'\
                         ' LEFT JOIN AgLibraryKeyword kw%s ON kw%s.id_local = kwi%s.tag '.replace('%s', str(num_value)))
            joins.append(' LEFT JOIN AgLibraryCollectionimage ci%s ON ci%s.image = i.id_local'\
                         ' LEFT JOIN AgLibraryCollection col%s ON col%s.id_local = ci%s.Collection '.replace('%s', str(num_value)))
            if num_value > 0:
                wheres += [combine]
            wheres.append('(msi.searchIndex LIKE "%%s%" '\
                        ' OR fi.lc_idx_filename LIKE "%%s%" '\
                        ' OR fo.pathFromRoot LIKE "%%s%"'\
                        ' OR rf.absolutePath LIKE "%%s%"'.replace('%s', str(value)))
            wheres.append(' OR iic.value LIKE "%%%s%%" ' % value)
            wheres.append(' OR liptc.caption LIKE "%%%s%%" ' % value)
            wheres.append(' OR liptc.copyright LIKE "%%%s%%" ' % value)
            wheres.append(' OR scpc.profileName LIKE "%%%s%%" ' % value)
            wheres.append(' OR  col%s.name LIKE "%%%s%%"' % (num_value, value))
            wheres.append(' OR  kw%s.id_local IN (%s)) ' % (num_value, ','.join([str(index) for index in indexes])))

        # the base 'select columns from' :
        self.base_sql_select = self._add_joins_from_select(self.lrdb.lrphoto.select_generic(self.base_select, '', distinct=True, sql=True))
        # final sql
        self._add_joins(joins)
        self.sql += ''.join([self.base_sql_select] +  [' LEFT JOIN '] + [' LEFT JOIN '.join(self.joins)] +  wheres)


    def criteria_metadata(self):
        '''
        criteria metadata : find in metadatas (AgMetadataSearchIndex.searchindex) and keywords
        TODO
        '''
        rules = {\
            'any': ('OR'),\
            'all': ('AND'),\
        }
        if self.func['operation'] not in rules:
            raise SmartException('operation unsupported: %s on criteria %s' % (self.func['operation'], self.func['criteria']))
        combine = rules[self.func['operation']]
        lrk = LRKeywords(self.lrdb)
        wheres = [' WHERE ']
        joins = [' LEFT JOIN AgMetadataSearchIndex msi ON i.id_local = msi.image ']
        for num_value, value in enumerate(self.func['value'].split()):
            indexes = lrk.hierachical_indexes(value, self.func['operation'])
            joins.append(' LEFT JOIN AgLibraryKeywordImage kwi%s ON i.id_local = kwi%s.image'\
                         ' LEFT JOIN AgLibraryKeyword kw%s ON kw%s.id_local = kwi%s.tag '.replace('%s', str(num_value)))
            if num_value > 0:
                wheres += [combine]
            wheres.append('(msi.searchIndex LIKE "%%%s%%" '.replace('%s', str(value)))
            wheres.append(' OR  kw%s.id_local IN (%s)) ' % (num_value, ','.join([str(index) for index in indexes])))
        # the base 'select columns from' :
        self.base_sql_select = self._add_joins_from_select(self.lrdb.lrphoto.select_generic(self.base_select, '', distinct=True, sql=True))
        # final sql
        self._add_joins(joins)
        self.sql += ''.join([self.base_sql_select] +  [' LEFT JOIN '] + [' LEFT JOIN '.join(self.joins)] +  wheres)


    def criteria_metadataStatus(self):
        '''
        criteria metadata status
        '''
        self.base_sql_select = self._add_joins_from_select(self.lrdb.lrphoto.select_generic(self.base_select, '', distinct=True, sql=True))
        self._add_joins(['LEFT JOIN Adobe_AdditionalMetadata am on i.id_local = am.image'])
        if self.func['value'] == 'unknown':
            where = 'am.externalXmpIsDirty=0 and i.sidecarStatus = 2.0'
        elif self.func['value'] == 'changedOnDisk':
            where = 'am.externalXmpIsDirty=1 and (i.sidecarStatus = 2.0 or i.sidecarStatus = 0.0)'
        elif self.func['value'] == 'hasBeenChanged':
            where = 'am.externalXmpIsDirty=0 and i.sidecarStatus = 1.0'
        elif self.func['value'] == 'conflict':
            where = 'am.externalXmpIsDirty=1 and i.sidecarStatus = 1.0'
        elif self.func['value'] == 'upToDate':
            where = 'am.externalXmpIsDirty=0 and i.sidecarStatus = 0.0'
        else:
            raise SmartException('value unsupported: %s on criteria %s' % (self.func['operation'], self.func['value']))
        self.sql += ''.join([self.base_sql_select] +  [' LEFT JOIN '] + [' LEFT JOIN '.join(self.joins)] + [' WHERE '] + [where])


    def criteria_creator(self):
        '''
        criteria creator
        '''
        self.build_string_value('LEFT JOIN AgHarvestedIptcMetadata im on i.id_local = im.image ' \
                    'LEFT JOIN AgInternedIptcCreator iic on im.creatorRef = iic.id_local',\
                    'iic.value')


    def build_string_value(self, tables_join, where_column):
        '''
        build SQL for string values
        TODO: operation "!=" not directly supported (bad count). See comment in criteria_camera
        '''
        rules = {\
            'any': ('"%%%s%%"', 'OR', 'LIKE'),\
            'all': ('"%%%s%%"', 'AND', 'LIKE'),\
            'beginsWith': ('"%%/t%s%%"', 'AND', 'LIKE'), \
            'endsWith': ('"%%%s/t%%"', 'AND', 'LIKE'), \
            'words': ('"%%/t%s/t%%"', 'AND', 'LIKE'), \
            'noneOf': ('"%%%s%%"', 'AND', 'NOT LIKE'),\
            '==': ('"%s"', 'AND', '=='),\
            '!=': ('"%s"', 'AND', '!='),\
            }
        if not self.func['operation'] in rules:
            raise SmartException('operation unsupported: %s on criteria %s' % (self.func['operation'], self.func['criteria']))
        what, combine, test = rules[self.func['operation']]
        _sql = ''
        if self.func['operation'] in ['==', '!=']:
            values = [self.func['value']]
        else:
            # character '+' force an AND combination
            self.func['value'] = self.func['value'].lower().replace('+', ' +')
            values = self.func['value'].split()
        for value in values:
            if value[0] == '+':      # force AND
                _sql += ' AND '
                value = value[1:]
            elif _sql:
                _sql += ' %s ' % combine   # "AND" or "OR"
            modifier = ''
            if value[0] == '!':
                modifier = 'NOT'
                value = value[1:]
            _sql += ' %s %s %s %s' % (where_column, modifier, test, what % value)
        self.sql += self._complete_sql(tables_join, ' WHERE %s' % _sql)



    def build_numeric_value(self, tables_join, where_column, where_complement=''):
        '''
        build SQL for numeric values (==, !=, >, <, >=, <=, in)
        '''
        if self.func['operation'] == 'in':
            self.sql += self._complete_sql(tables_join, ' WHERE %s >= %s AND %s <= %s %s' % \
                                (where_column, self.func['value'], where_column, self.func['value2'], where_complement))
        else:
            self.sql += self._complete_sql(tables_join, 'WHERE %s %s %s %s' % \
                                (where_column, self.func['operation'], self.func['value'], where_complement))


    def build_boolean_value(self, tables_join, where_column):
        '''
        build SQL for boolean values ()
        '''
        value = 1 if self.func['value'] else 0
        self.sql += self._complete_sql(tables_join, ' WHERE %s == %s' % (where_column, value))



    def build_all_values_with_join(self, base_join, base_where, values):
        ''' generic "all" function when values needs to use join tables (collection, keywords)'''
        joins = []
        wheres = []
        for num_value, value in enumerate(values):
            joins.append(base_join.replace('%s', str(num_value)))
            if num_value == 0:
                wheres.append(' WHERE ')
            else:
                wheres.append(' AND ')
            wheres.append(base_where % (num_value, value))
        # the base 'select columns from' :
        _sql = self.lrdb.lrphoto.select_generic(self.base_select, '', distinct=True, sql=True)
        ijoin = _sql.find('WHERE ')
        # final sql
        self.sql += ''.join([_sql[:ijoin]] + joins + wheres)



    def _add_joins_from_select(self, basesql):
        '''
        add join tables from a sql select request to self.joins
        Return select part
        basesql doesnt contains WHERE statement
        '''
        ijoin = basesql.find('LEFT JOIN ')
        sjoins = basesql[ijoin:]
        for join_table in sjoins.split('LEFT JOIN'):
            join_table = join_table.strip()
            if join_table and join_table not in  self.joins:
                self.joins.append(join_table)
        return basesql[:ijoin]


    def _add_joins(self, tables):
        '''
        add join tables list to self.joins
        '''
        for table in tables:
            for ajoin in table.split('LEFT JOIN'):
                ajoin = ajoin.strip()
                if ajoin and ajoin not in self.joins:
                    self.joins.append(ajoin)


    def _complete_sql(self, join_part, where_part):
        '''
        Return complete SQl from :
            - self.base_sql ('select columns from table' part),
            - self.joins (tables to join)
            - join_part (tables to join for where_part parameter)
            - where_part
        '''
        parts = [self.base_sql_select]
        if join_part:
            self._add_joins_from_select(join_part)
        if self.joins:
            parts.append('JOIN')
            parts.append(' LEFT JOIN '.join(self.joins))
        if where_part:
            parts.append(where_part)
        return ' '.join(parts)


    def build_sql(self, base_select):
        '''
        Return self.sql command from data returned by get_smartcoll_data
        '''
        self.base_select = base_select
        self.base_sql = self.lrdb.lrphoto.select_generic(base_select, '', sql=True)
        self.joins = []
        self.base_sql_select = self._add_joins_from_select(self.lrdb.lrphoto.select_generic(base_select, '', sql=True))
        self.sql = ''

        fid = 0
        while True:
            if fid not in self.smart:
                break
            if fid > 0:
                if self.smart['combine'] == 'union':
                    self.sql += ' UNION '
                elif self.smart['combine'] == 'intersect':
                    self.sql += ' INTERSECT '
                else:
                    raise SmartException('"combine" operation unsupported: %s' %  self.smart['combine'])

            self.func = self.smart[fid]
            if self.verbose:
                print('    FUNC', fid, self.func)

            # build criteria function name ...
            try:
                func_criteria = getattr(self, 'criteria_%s' % self.func['criteria'])
            except AttributeError:
                raise SmartException('criteria unsupported: %s' % self.func['criteria'])
            # ... and call it
            func_criteria()

            # next function
            fid += 1

        return self.sql



    def to_string(self):
        ''' convert smart collection to string '''
        smart_str = ''
        for _k, _v in list(self.smart.items()):
            smart_str += '%s = %s\n' % (_k, _v)
        return smart_str
