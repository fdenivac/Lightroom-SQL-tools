#!/usr/bin/env python
# # # -*- coding: utf-8 -*-
# pylint: disable=line-too-long, bad-continuation
"""

Base class for building simple SQL select from a table

"""

import re
import logging
from datetime import datetime
from dateutil import parser

# config is loaded on import
from .lrtoolconfig import lrt_config

from .lrcat import date_to_lrstamp
from .criterlexer import CriterLexer


class LRSelectException(Exception):
    """LRSelect Exception"""


# sqlite date modifiers accordigf parts of date string
STARTS_OF_DATE = {
    1: "start of year",
    2: "start of month",
    3: "start of day",
}


def parsedate(date):
    """return datetime from string"""
    if isinstance(date, str):
        return parser.parse(
            date,
            default=datetime(1900, 1, 1, 0, 0, 0),
            dayfirst=lrt_config.dayfirst,
        )
    if isinstance(date, datetime):
        return date
    return None


def to_bool(value):
    """convert value to bool (true, false, 1, 0)"""
    if isinstance(value, str):
        if value.lower() == "true" or value == "1" or value == "yes":
            return True
        if value.lower() == "false" or value == "0" or value == "no":
            return False
    raise LRSelectException("Invalid bool value")


class LRSelectGeneric:
    """
    Build select SQL requests for a specific table from columns and criteria strings
    This a base class not intended to be used directly.

    Exemple:
        lrdb = LRCatDB('holidays.lrcat')
        lrphoto = LRSelecPhoto(lrdb)
        results = lrphoto.select_generic("name=full, uuid," "rating=2, datecapt<2012-05-18")

    """

    # specific key for column specification
    _VAR_FIELD = "var:"

    def __init__(self, lrdb, main_table, columns, criteria):
        """
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
            criter_name : [ SQL_JOIN_TABLES, SQL_WHERES, parser_value_function ]
            ...
            example :
            'collection' : [
                'JOIN AgLibraryCollection col ON col.id_local = ci.Collection JOIN  AgLibraryCollectionimage ci ON ci.image = i.id_local',
                'col.name = "%s"' ]                   ]
        """
        self.lrdb = lrdb
        self.from_table = f"FROM {main_table}"
        self.froms = None
        self.column_description = columns
        self.criteria_description = criteria
        self.groupby = ""
        self.having_criters = []
        self.sql_column_names = []
        self.raw_column_names = []

    def selected_column_names(self):
        """column names from SQL statement executed"""
        return self.raw_column_names

    #
    # Some general functions called for convert value key in value sql
    #

    def func_oper_parsedate(self, value):
        """parse opration and date value"""
        oper = False
        for index, char in enumerate(value):
            if char.isnumeric():
                oper = value[:index]
                value = value[index:]
                break
        if not oper:
            raise LRSelectException("None operator for date")
        date = parsedate(value)
        if not date:
            raise LRSelectException("Incorrect date")
        # value is it year, month/year or day/month/year ?
        nparts = len(re.findall(r"\d+", value))
        if nparts <= 3:
            sql = f'DATE(i.captureTime, "{STARTS_OF_DATE[nparts]}") {oper} DATE("{date}", "{STARTS_OF_DATE[nparts]}")'
        else:
            sql = f'i.captureTime {oper} "{date.strftime("""%Y-%m-%dT%H:%M:%S""")}"'
        return sql

    def func_oper_dateloc_to_lrstamp(self, value):
        """value is a lightrom timestamp"""
        for index, char in enumerate(value):
            if char.isnumeric():
                oper = value[:index]
                value = value[index:]
                break
        dtmod = date_to_lrstamp(value)
        if dtmod is None:
            raise LRSelectException('invalid date value on "datemod"')
        return oper, dtmod

    def func_oper_dateutc_to_lrstamp(self, value):
        """value is a lightrom timestamp"""
        oper = None
        for index, char in enumerate(value):
            if char.isnumeric():
                oper = value[:index]
                value = value[index:]
                break
        dtmod = date_to_lrstamp(value, False)
        if not dtmod:
            raise LRSelectException('invalid date value on "datemod"')
        return oper, dtmod

    def func_oper_value(self, value):
        """optional operand and numeric value"""
        oper = None
        for index, char in enumerate(value):
            if char.isalnum():
                oper = value[:index] if value[:index] else "="
                value = value[index:]
                break
        if oper is None:
            raise LRSelectException("operator without value")
        return oper, value

    def func_bool_to_equal(self, value):
        """value is boolean"""
        return "=" if to_bool(value) else "!="

    def func_0_1(self, value):
        """value is a null condition"""
        value = value.lower()
        if value in ["0", "false"]:
            value = "0"
        elif value in ["1", "true"]:
            value = "1"
        else:
            raise LRSelectException("invalid hasgps criterion value")
        return value

    def func_value_or_null(self, value):
        """value is a null condition"""
        value = value.lower()
        if value in ["null", "false"]:
            value = "IS NULL"
        elif value in ["!null", "true"]:
            value = "NOT NULL"
        else:
            value = f'= "{value}"'
        return value

    def func_like_value_or_null(self, value):
        """value is a null condition"""
        value = value.lower()
        if value in ["null", "false"]:
            value = "IS NULL"
        elif value in ["!null", "true"]:
            value = "NOT NULL"
        else:
            value = f'LIKE "{value}"'
        return value

    def func_value_or_not_equal(self, value):
        """value is parameter or comparaison"""
        try:
            value = to_bool(value)
            if value:
                return ("<>", '""')
            return ("==", '""')
        except LRSelectException:
            return ("=", f'"{value}"')

    def _keyval_to_keys(self, strlist):
        """
        convert string of key=value in list of dict
        """
        pairs = list()
        if not strlist:
            return pairs
        for keyval in strlist.split(","):
            try:
                if not keyval:
                    continue  # skip double commas
                keyval = keyval.strip()
                if keyval.startswith("count(") or keyval.startswith("countby("):
                    pairs.append({keyval: "True"})
                    continue
                _kv = keyval.split("=", 1)
                if len(_kv) == 2:
                    _k, _v = _kv
                else:
                    if len(_kv) == 1:
                        # support key without value => value if True
                        _k = keyval
                        _v = "True"
                    else:
                        raise LRSelectException(f"No value after = on {keyval}")
                pairs.append({_k: _v})
            except Exception as _e:
                raise LRSelectException(
                    f"Invalid key/value syntax ({keyval} in {strlist})"
                ) from _e
        return pairs

    def _add_from(self, sql, froms):
        """add from to final FROM statement (internal function)"""
        if isinstance(sql, str):
            sql = [sql]
        for sqlfrom in sql:
            sqlfrom = sqlfrom.strip()
            if sqlfrom in froms:
                continue
            froms.append(sqlfrom)

    def remove_quotes(self, value):
        """Remove quotes from string"""
        if not value:
            return ""
        if (value[0] == '"' and value[-1] == '"') or (
            value[0] == "'" and value[-1] == "'"
        ):
            value = value[1:-1]
        return value

    def columns_to_sql(self, columns, sqlcols, sqlfroms):
        """
        Convert string of column names comman separated to sql string
        """

        def _column_to_sql(column, case=""):
            """process on column"""
            key, value = list(column.items())[0]
            try:
                dvalues = self.column_description[key]
                if self._VAR_FIELD in dvalues and value.startswith(
                    self._VAR_FIELD
                ):
                    # _VAR_FIELD introduces process for columns name specification
                    _, from_sql = dvalues[self._VAR_FIELD]
                    col_sql = self.remove_quotes(value[len(self._VAR_FIELD) :])
                else:
                    if value not in dvalues.keys():
                        raise LRSelectException(
                            f'Invalid value "{value}" on column "{key}"'
                        )
                    col_sql, from_sql = dvalues[value]
                if case in ["count", "countby"]:
                    parts = col_sql.split(" ")
                    if parts[-2].upper() == "AS":
                        sqlcols.append(
                            f"count({''.join(parts[:-2])}) AS count_{parts[-1]}"
                        )
                        if case == "countby":
                            self.groupby = f"GROUP BY {parts[-1]}"
                    else:
                        raise LRSelectException("Error in count definition")
                else:
                    sqlcols.append(col_sql)
                if from_sql:
                    self._add_from(from_sql, sqlfroms)
            except KeyError as _e:
                raise LRSelectException(f'invalid column key "{key}"') from _e

        # ENTRY columns_to_sql(self, ...)
        self.raw_column_names = []
        for keyval in self._keyval_to_keys(columns):
            key, value = list(keyval.items())[0]
            if key == "name":
                self.raw_column_names.append(f"{key}={value}")
            else:
                self.raw_column_names.append(f"{key}")
            match = re.match(r"(count|countby)\(([\w=]+)\)", key)
            if match:
                if match.group(1) == "count":
                    _column_to_sql({match.group(2): value}, "count")
                    continue
                # countby :
                lkv = self._keyval_to_keys(match.group(2))
                _column_to_sql(lkv[0], "countby")
                continue
            _column_to_sql(keyval)

    def select_predefined(self, _columns, _criters):
        """
        To be redefined in derived class
        Must return SQL statement if columns or criters is a keyword (a function) supported, else empty string
        """
        return None

    def select_generic(self, columns, criters, **kwargs):
        """
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
        """

        def _finalize(sql):
            if kwargs.get("debug") or kwargs.get("print"):
                print("SQL =", sql)
            if kwargs.get("print"):
                return None
            if kwargs.get("sql"):
                return sql
            log.info("SQL = %s", sql)
            self.lrdb.cursor.execute(sql)
            # retrieve columns names as detected by sqlite
            self.sql_column_names = [d[0] for d in self.lrdb.cursor.description]
            return self.lrdb.cursor

        # logging
        log = logging.getLogger(__name__)
        log.info('select_generic("%s" "%s")', columns, criters)

        # init
        fields = []
        self.froms = [self.from_table]
        wheres = []
        sort = ""
        nb_wheres = {}
        select_type = None
        self.groupby = ""
        self.having_criters = []
        self.sql_column_names = []
        self.raw_column_names = []

        #
        # process predefined sql functions
        #
        # pylint: disable=assignment-from-none
        sql = self.select_predefined(columns, criters)
        if sql:
            return _finalize(sql)

        #
        # process criteria :
        #

        lex = CriterLexer(criters)
        if criters and not lex.parse():
            raise LRSelectException(f"Criteria syntax error : {lex.last_error}")
        token2sql = {"LPAR": "(", "RPAR": ")", "AND": "AND", "OR": "OR"}

        # process tokens
        prev_optoken = None
        has_where = False
        for token, data in lex.tokens:
            if token in token2sql:
                # add previous token if any
                if prev_optoken:
                    wheres.append(token2sql[prev_optoken])
                prev_optoken = token
                continue

            if token != "KEYVAL":
                raise LRSelectException(f'Invalid Token : "{token}"')
            key, value = data
            value = self.remove_quotes(value)
            if key not in nb_wheres:
                nb_wheres[key] = 1
            else:
                nb_wheres[key] += 1
            if key not in self.criteria_description:
                raise LRSelectException(f'No existent criterion "{key}"')
            criter_desc = self.criteria_description[key]
            if len(criter_desc) == 2:
                _from, _where = criter_desc
            else:
                _from, _where, func = criter_desc
                try:
                    value = func(value)
                except TypeError as _e:
                    raise LRSelectException(
                        f'Syntax error on criterion "{key}"'
                    ) from _e
            # some specific keywords for SQL
            if key == "sort":  # specific key for sql 'ORDER BY'
                way = "DESC"
                if value[0] == "-":
                    way = "ASC"
                    value = value[1:]
                sort = f"ORDER BY {value} {way}"
                prev_optoken = None
                continue
            if key == "distinct":  # specific key for sql 'SELECT DISTINCT'
                select_type = _where
                prev_optoken = None
                continue
            if key == "count":  # key for sql 'COUNT (*) ... HAVING'
                self.having_criters.append(f"count_{value}")
                prev_optoken = None
                continue

            if _from:
                if isinstance(_from, str):
                    _from = [_from]
                _from = [
                    _f.replace("<NUM>", f"{nb_wheres[key]}") for _f in _from
                ]
                self._add_from(_from, self.froms)
            _where = _where.replace("<NUM>", f"{nb_wheres[key]}")
            if "%s" in _where:
                _where = _where % value

            # append the operation token if any
            if prev_optoken:
                if prev_optoken == "LPAR" or has_where:
                    wheres.append(token2sql[prev_optoken])
                prev_optoken = None
            # and the "where" string
            wheres.append(_where)
            has_where = True

        # finally: last operation token (a parenthesis)
        if prev_optoken:
            wheres.append(token2sql[prev_optoken])

        #
        # process columns :
        #
        self.columns_to_sql(columns, fields, self.froms)

        #
        # finalize request
        #
        if fields:
            fields = ", ".join(fields)
        else:
            fields = 'rf.absolutePath || fo.pathFromRoot || fi.baseName || "." || fi.extension '
        self.froms = " ".join(self.froms)
        if wheres:
            wheres = f'WHERE {" ".join(wheres)}'
        else:
            wheres = ""

        if kwargs.get("distinct"):
            select_type = "SELECT DISTINCT"
        elif not select_type:
            select_type = "SELECT"

        having = (
            f"HAVING {' AND '.join(self.having_criters)}"
            if self.having_criters
            else ""
        )

        sql = f"{select_type}  {fields} {self.froms} {wheres} {self.groupby} {having} {sort}"
        return _finalize(sql)
