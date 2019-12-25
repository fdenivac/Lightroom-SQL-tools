#!python3
# # -*- coding: utf-8 -*-
# pylint: disable=line-too-long, bad-continuation
'''

Base class for building simple SQL select from a table

'''

import logging
from datetime import datetime
from dateutil import parser

# config is loaded on import
from .lrtoolconfig import lrt_config

from .lrcat import date_to_lrstamp


class LRSelectException(Exception):
    ''' LRSelect Exception '''



def parsedate(date):
    ''' return datetime from string '''
    if isinstance(date, str):
        return parser.parse(date, dayfirst=lrt_config.dayfirst)
    elif isinstance(date, datetime):
        return date
    else:
        return None

def to_bool(value):
    ''' convert value to bool (true, false, 1, 0) '''
    if isinstance(value, str):
        if value.lower() == 'true' or value == '1' or value == 'yes':
            return True
        if  value.lower() == 'false' or value == '0' or value == 'no':
            return False
    raise LRSelectException('Invalid bool value')




class LRSelectGeneric():
    '''
    Build select SQL requests for a specific table from columns and criteria strings
    This a base class not intended to be used directly.

    Exemple:
        lrdb = LRCatDB('holidays.lrcat')
        lrphoto = LRSelecPhoto(lrdb)
        results = lrphoto.select_generic("name=full, uuid," "rating=2, datecapt<2012-05-18")

    '''


     # specific key for column specification
    _VAR_FIELD = 'var:'


    def __init__(self, lrdb, main_table, columns, criteria):
        '''
        * param lrdb : LRCatDB instance
        * param main_table: string,
        * param columns: dictionnary for convert to SQL.
          structure :
            column_name (the key) :  {
                value1 : [ SQL_COLUMNS,  [SQL_FROM_TABLE_LIST] ],
                value2 : [ SQL_COLUMNS,  [SQL_FROM_TABLE_LIST] ],
                ...
                }
            example :
                'name' : {
                    'full':
                        [   'rf.absolutePath || fo.pathFromRoot || fi.baseName || "." || fi.extension AS name',
                            [
                                ' JOIN AgLibraryRootFolder rf ON fo.rootFolder = rf.id_local',
                                'JOIN AgLibraryFolder fo ON fi.folder = fo.id_local', 'JOIN AgLibraryFile fi ON i.rootFile = fi.id_local'
                            ],
                        ],
                    True:  [ 'fi.baseName || "." || fi.extension AS name', [ 'JOIN AgLibraryFile fi ON i.rootFile = fi.id_local' ] ],
                }

        * params criteria :  dictionnary where :
          structure :
            criter_name : [ SQL_JOIN_TABLES, SQL_WHERES, parse_value_funtion ]
            ...
            example :
            'collection' : [
                'JOIN AgLibraryCollection col ON col.id_local = ci.Collection JOIN  AgLibraryCollectionimage ci ON ci.image = i.id_local',
                'col.name = "%s"' ]                   ]
        '''
        self.lrdb = lrdb
        self.from_table = 'FROM %s' % main_table
        self.column_description = columns
        self.criteria_description = criteria


    #
    # Some general functions called for convert value key in value sql
    #

    def func_parsedate(self, value):
        ''' parse a date value '''
        date = parsedate(value)
        if not date:
            raise LRSelectException('Incorrect date')
        return date

    def func_oper_parsedate(self, value):
        ''' parse opration and date value '''
        for index, char in enumerate(value):
            if char.isnumeric():
                oper = value[:index]
                value = value[index:]
                break
        date = parsedate(value)
        if not date:
            raise LRSelectException('Incorrect date')
        return oper, date

    def func_oper_date_to_lrstamp(self, value):
        ''' value is a lightrom timestamp '''
        for index, char in enumerate(value):
            if char.isnumeric():
                oper = value[:index]
                value = value[index:]
                break
        dtmod = date_to_lrstamp(value)
        if not dtmod:
            raise LRSelectException('invalid date value on "fromdatemod"')
        return oper, dtmod

    def func_date_to_lrstamp(self, value):
        ''' value is a lightrom timestamp '''
        dtmod = date_to_lrstamp(value)
        if not dtmod:
            raise LRSelectException('invalid date value on "fromdatemod"')
        return dtmod

    def func_bool_to_equal(self, value):
        ''' value is boolean '''
        return '=' if to_bool(value) else '!='

    def func_0_1(self, value):
        ''' value is a null condition '''
        value = value.lower()
        if value in ['0', 'false']:
            value = '0'
        elif value in ['1', 'true']:
            value = '1'
        else:
            raise LRSelectException('invalid gps criterion value')
        return value

    def func_value_or_null(self, value):
        ''' value is a null condition '''
        value = value.lower()
        if value in ['null', 'false']:
            value = 'IS NULL'
        elif value in ['!null', 'true']:
            value = "NOT NULL"
        else:
            value = '= "%s"' % value
        return value

    def func_like_value_or_null(self, value):
        ''' value is a null condition '''
        value = value.lower()
        if value in ['null', 'false']:
            value = 'IS NULL'
        elif value in ['!null', 'true']:
            value = "NOT NULL"
        else:
            value = 'LIKE "%s"' % value
        return value

    def func_value_or_not_equal(self, value):
        ''' value is parameter or comparaison '''
        try:
            value = to_bool(value)
            if value:
                return ('<>', '""')
            else:
                return ('==', '""')
        except LRSelectException:
            return ('=', '"%s"' % value)




    def _to_keys(self, strlist):
        '''
        convert string of key=value in list of dict
        '''
        pairs = list()
        if not strlist:
            return pairs
        try:
            for keyval in strlist.split(','):
                if not keyval:
                    continue    # skip double commas
                keyval = keyval.strip()
                _kv = keyval.split('=', 1)
                if len(_kv) == 2:
                    _k, _v = _kv
                else:
                    if len(_kv) == 1:
                        # support key without value => value if True
                        _k = keyval
                        _v = 'True'
                    else:
                        raise LRSelectException('No value after = on %s' % keyval)
                pairs.append({_k : _v})
        except Exception:
            raise LRSelectException('Invalid key/value syntax (%s in %s)' % (keyval, strlist))
        return pairs


    def _add_from(self, sql, froms):
        ''' add from to final FROM statement (internal function)'''
        if isinstance(sql, str):
            sql = [sql]
        for sqlfrom in sql:
            sqlfrom = sqlfrom.strip()
            if sqlfrom in froms:
                continue
            froms.append(sqlfrom)


    def remove_quotes(self, value):
        ''' Remove quotes from string '''
        if not value:
            return
        if (value[0] == '"' and value[-1] == '"') or (value[0] == "'" and value[-1] == "'"):
            value = value[1:-1]
        return value


    def columns_to_sql(self, columns, sqlcols, sqlfroms):
        '''
        Convert string of column names comman separated to sql string
        '''
        for keyval in self._to_keys(columns):
            key, value = list(keyval.items())[0]
            try:
                dvalues = self.column_description[key]
                if self._VAR_FIELD in dvalues and value.startswith(self._VAR_FIELD):
                    # _VAR_FIELD introduces process for columns name specification
                    _, from_sql = dvalues[self._VAR_FIELD]
                    col_sql = self.remove_quotes(value[len(self._VAR_FIELD):])
                else:
                    if value not in list(dvalues.keys()):
                        value = bool(value)
                        if value not in list(dvalues.keys()):
                            raise LRSelectException('Invalid value "%s" on column "%s"' % (value, key))
                    col_sql, from_sql = dvalues[value]
                sqlcols.append(col_sql)
                if from_sql:
                    self._add_from(from_sql, sqlfroms)
            except KeyError:
                raise LRSelectException('invalid column key "%s"' % key)


    def select_generic(self, columns, criters, **kwargs):
        '''
        Build SQL request from key/value pairs
        columns :
            - 'NAME1'='VALUE1'
            - ...
        criteria :
            - 'CRITERION' = 'OPERATION+VALUE'
            - ....
        kwargs :
            - distinct : request SELECT DISTINCT
            - debug : print sql
            - print : print sql and return None
            - sql : return SQL string only
        '''


        # logging
        log = logging.getLogger()
        log.info('select_generic("%s" "%s")', columns, criters)

        fields = []
        froms = [self.from_table]
        wheres = []
        sort = ''
        nb_wheres = {}
        select_type = None

        #
        # process criteria :
        #
        for keyval in self._to_keys(criters):
            key, value = list(keyval.items())[0]
            value = self.remove_quotes(value)
            if not key in nb_wheres:
                nb_wheres[key] = 1
            else:
                nb_wheres[key] += 1
            if not key in self.criteria_description:
                raise LRSelectException('No existent criterion "%s"' %  key)
            criter_desc = self.criteria_description[key]
            if len(criter_desc) == 2:
                _from, _where = criter_desc
            else:
                _from, _where, func = criter_desc
                value = func(value)
            # some specific keywords for SQL
            if key == 'sort':       # specific key 'sort' for sql 'ORDER BY'
                way = 'DESC'
                if value[0] == '-':
                    way = 'ASC'
                    value = value[1:]
                sort = 'ORDER BY %s %s' % (value, way)
                continue
            if key == 'distinct':      # specific key 'sort' for sql 'SELECT DISTINCT'
                select_type = _where
                continue

            if _from:
                if isinstance(_from, str):
                    _from = [_from]
                _from = [_f.replace('<NUM>', '%s' % nb_wheres[key]) for  _f in _from]
                self._add_from(_from, froms)
            _where = _where.replace('<NUM>', '%s' % nb_wheres[key])
            if '%s' in _where:
                _where = _where % value
            wheres.append(_where)

        #
        # process columns :
        #
        self.columns_to_sql(columns, fields, froms)

        #
        # finalize request
        #
        if fields:
            fields = ', '.join(fields)
        else:
            fields = 'rf.absolutePath || fo.pathFromRoot || fi.baseName || "." || fi.extension '
        froms = ' '.join(froms)
        if wheres:
            wheres = 'WHERE %s' % ' AND '.join(wheres)
        else:
            wheres = ''

        if kwargs.get('distinct'):
            select_type = 'SELECT DISTINCT'
        elif not select_type:
            select_type = 'SELECT'

        sql = '%s  %s %s %s %s' % (select_type, fields, froms, wheres, sort)
        log.info('SQL = %s', sql)
        if kwargs.get('debug') or kwargs.get('print'):
            print('SQL =', sql)
        if kwargs.get('print'):
            return None
        if kwargs.get('sql'):
            return sql
        self.lrdb.cursor.execute(sql)
        return self.lrdb.cursor
