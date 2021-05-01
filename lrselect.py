#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=line-too-long
"""

Select photos from Lightroom catalog

"""

import sys
import logging
import argparse
from argparse import RawTextHelpFormatter
import sqlite3

# config is loaded on import
from lrtools.lrtoolconfig import lrt_config

from lrtools.lrcat import LRCatDB, LRCatException
from lrtools.lrselectgeneric import LRSelectException
from lrtools.lrselectphoto import LRSelectPhoto
from lrtools.lrselectcollection import LRSelectCollection
from lrtools.display import display_results


DEFAULT_COLUMNS = 'name,datecapt'

# pylint: disable=invalid-name
log = logging.getLogger()


def main():
    ''' Main entry from command line  '''

    #
    # command parser
    #

    # prepare help based on doc strings
    description = 'Select elements from SQL table from Lightroom catalog.\n\n' \
                    'For photo : specify the "columns" to display and the "criteria of selection in :'
    # add part of help for function LRSelectPhoto.select_generic
    doc_func = LRSelectPhoto.select_generic.__doc__
    start = doc_func.find('columns :')
    start = doc_func.rfind('\n', 0, start)
    end = doc_func.find('kwargs :')
    description += doc_func[start:end]
    # add part of help for function LRSelectCollection.select_generic
    description += '\nFor collection : specify the "columns" to display and the "criteria" of selection in :'
    doc_func = LRSelectCollection.select_generic.__doc__
    start = doc_func.find('columns :')
    start = doc_func.rfind('\n', 0, start)
    end = doc_func.find('kwargs :')
    description += doc_func[start:end]
    # add examples
    description += '\nExamples:\n' \
            '\tlrselect.py --sql --results "basename,datecapt" "rating=>4,video=0"\n' \
            '\tlrselect.py  "name,datecapt,latitude,longitude,keywords" "rating=>4,videos=0" --results --count'

    parser = argparse.ArgumentParser(description=description,
                                     formatter_class=RawTextHelpFormatter)
    parser.add_argument('columns', help='Columns to display', default=DEFAULT_COLUMNS, nargs='?')
    parser.add_argument('criteria', help='Criteria of select', nargs='?')
    parser.add_argument('-b', '--lrcat', default=lrt_config.default_lrcat, help='Ligthroom catalog file for database request (default:"%(default)s")')
    parser.add_argument('-s', '--sql', action='store_true', help='Display SQL request')
    parser.add_argument('-c', '--count', action='store_true', help='Display count of results')
    parser.add_argument('-r', '--results', action='store_true', help='Display datas results')
    parser.add_argument('-n', '--max_lines', type=int, default=0, help='Max number of results to display')
    parser.add_argument('-f', '--file', help='UUIDs photos file : replace the criteria parameter which is ignored. All parameters are ignored')
    parser.add_argument('-t', '--table', choices=['photo', 'collection'], default='photo', help='table to work on : photo or collection')
    parser.add_argument('-N', '--no-header', action='store_true', help='don\'t print header (photos count ans columns names)')
    parser.add_argument('-w', '--widths', help='Widths of columns to display widths (ex:30,-50,10)')
    parser.add_argument('-S', '--separator', default=' | ', help='separator string between columns (default:"%(default)s")')
    parser.add_argument('-I', '--indent', type=int, default=4, help='space indentation in output (default:"%(default)s")')
    parser.add_argument('--raw_print', action='store_true', help='print raw value (for speed, aperture columns)')
    parser.add_argument('--log', help='log on file')

    args = parser.parse_args()
    # --max_lines option implies --results
    if args.max_lines > 0:
        args.results = True
    # default columns if empty
    if not args.columns:
        args.columns = DEFAULT_COLUMNS

    # logging
    if args.log:
        # basicConfig doesn't support utf-8 encoding yet (?)
        #   logging.basicConfig(filename=args.log, level=logging.INFO, encoding='utf-8')
        # use work-around :
        log.setLevel(logging.INFO)
        handler = logging.FileHandler(args.log, 'a', 'utf-8')
        handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
        log.addHandler(handler)
    log.info('lrselect start')
    log.info('arguments: %s', ' '.join(sys.argv[1:]))

    # open database
    lrdb = LRCatDB(args.lrcat)

    # select on which table to work
    if args.table == 'photo':
        lrobj = lrdb.lrphoto
    elif args.table == 'collection':
        lrobj = LRSelectCollection(lrdb)

    if args.file:
        # option file : all parameters other than "columns" are ignored
        try:
            uuids = open(args.file).read().splitlines()
        except OSError:
            print(' ==> Failed to open file', file=sys.stderr)
            return
        # build rows ...
        num_uuid = 1
        rows = []
        for uuid in uuids:
            try:
                rows.append(lrobj.select_generic(args.columns, 'uuid="%s"' % uuid).fetchone())
            except LRSelectException as _e:
                print(' ==> FAILED:', _e, file=sys.stderr)
                return
            except sqlite3.OperationalError as _e:
                print(' ==> FAILED SQL :', _e, file=sys.stderr)
                return
            num_uuid += 1
        # ... and displays
        display_results(rows, \
            lrobj.selected_column_names(), \
            max_lines=args.max_lines, \
            header=not args.no_header, \
            widths=args.widths,\
            raw_print=args.raw_print, \
            separator=args.separator)
        return


    if not (args.sql or args.count or args.results):
        print('WARNING: option "--count" forced')
        args.count = True

    if args.sql:
        print(' * SQL request = ', lrobj.select_generic(args.columns, args.criteria, sql=True))


    if not (args.count or args.results):
        return

    try:
        rows = lrobj.select_generic(args.columns, args.criteria).fetchall()
    except (LRSelectException)  as _e:
        # TODO: convert specific error caused by a limitation on build SQL with criteria width or height
        if _e.args[0] == 'no such column: dims':
            _e.args = ('Try to add column "dims"',)
        print(' ==> FAILED:', _e, file=sys.stderr)
        return

    if args.count:
        print(' * Count results:', len(rows))

    if args.results:
        display_results(rows, \
            lrobj.selected_column_names(), \
            max_lines=args.max_lines, \
            header=not args.no_header, \
            widths=args.widths,\
            raw_print=args.raw_print, \
            separator=args.separator, \
            indent=args.indent)




if __name__ == '__main__':
    # protect main from IOError occuring with a pipe command
    try:
        main()
    except IOError as _e:
        if _e.errno not in [22, 32]:
            raise _e
    except (LRSelectException, LRCatException) as _e:
        print(' ==> FAILED:', _e, file=sys.stderr)
    except sqlite3.OperationalError as _e:
        print(' ==> FAILED SQL :', _e, file=sys.stderr)

    log.info('lrselect end')
