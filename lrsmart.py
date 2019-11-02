#!python3
# -*- coding: utf-8 -*-
# pylint: disable=line-too-long
"""

Execute Lightroom smart collections from catalog or file

"""

import logging
import argparse
from argparse import RawDescriptionHelpFormatter

# config is loaded on import
from lrtools.lrtoolconfig import lrt_config

from lrtools.lrcat import LRCatDB
from lrtools.lrselectgeneric import LRSelectException
from lrtools.lrsmartcoll import SQLSmartColl, SmartException
from lrtools.slpp import SLPP
from lrtools.display import display_results


def main():
    ''' Main entry from command line  '''

    #
    # commands parser
    #
    parser = argparse.ArgumentParser(description='Execute smart collections from Lightroom catalog or from a exported file',
                                     formatter_class=RawDescriptionHelpFormatter)
    parser.add_argument('smart_name', help='Name of smart(s) collection', nargs='*')
    parser.add_argument('-b', '--lrcat', default=lrt_config.default_lrcat, help='Ligthroom catalog file for database request (default:"%(default)s")')
    parser.add_argument('-f', '--file', action='store_true', help='positionnal parameters are files, not smart collection names')
    parser.add_argument('-l', '--list', action='store_true', help='List smart collections of name "smart_name" from Lightroom catalog.'\
                        ' "smart_name" can include jokers "%%". Leave empty for list all collections')
    parser.add_argument('--raw', action='store_true', help='Display description of smart collection as stored')
    parser.add_argument('-d', '--dict', action='store_true', help='Display description of smart collection as python dictionnary')
    parser.add_argument('-s', '--sql', action='store_true', help='Display SQL request')
    parser.add_argument('-c', '--count', action='store_true', help='Display count of results')
    parser.add_argument('-r', '--results', action='store_true', help='Display datas results')
    parser.add_argument('-n', '--max_lines', type=int, default=0, help='Max number of results to display')
    parser.add_argument('-C', '--columns', default='uuid,name', help='Columns names to print (default:"%(default)s"). For column names, see help of lrselect.py')
    parser.add_argument('-N', '--no_header', action='store_true', help='don\'t print header (columns names)')
    parser.add_argument('-w', '--widths', help='Widths of columns to display widths (ex:30,-50,10)')
    parser.add_argument('--raw_print', action='store_true', help='print raw value (for speed, aperture columns)')
    parser.add_argument('--log', help='log on file')

    args = parser.parse_args()
    # --max_lines option implies --results
    if args.max_lines > 0:
        args.results = True

    # logging
    if args.log:
        # basicConfig doesn't support utf-8 encoding yet (?)
        #   logging.basicConfig(filename=args.log, level=logging.INFO, encoding='utf-8')
        # use work-around :
        log = logging.getLogger()
        log.setLevel(logging.INFO)
        handler = logging.FileHandler(args.log, 'a', 'utf-8')
        handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
        log.addHandler(handler)
    log = logging.getLogger()
    log.info('lrsmart start')

    #
    # for lrsmart validation :
    #  a file containing photos number by smart collection, extracted  from Lightrrom (via specific plugin)
    #  can be loaded :
    #
    count_smart = {}
    try:
        lines = open('I:/Lightroom/SmartsCountFromLR.txt', encoding='utf8').read().splitlines()
        for line in lines:
            values = line.split('==>')
            if not len(values) == 2:
                continue
            count_smart[values[0].strip()] = int(values[1].strip())
    except IOError:
        pass


    # open catalog
    lrdb = LRCatDB(args.lrcat)

    if args.list:
        colls = list()
        if not args.smart_name:
            args.smart_name = '%'
        for name in args.smart_name:
            colls += lrdb.select_collections(lrdb.SMART_COLL, name)
        args.smart_name = [name for  _, name, _ in colls]


    for smart_name in args.smart_name:
        if not args.file:
            print('Smart Collection "%s"' % smart_name)
        if args.raw:
            if args.file:
                try:
                    for line in open(smart_name).read().splitlines():
                        print(line)
                except OSError:
                    print("  ==> FAILED : Not found")
                    continue
            else:
                print(' * Raw definition as stored :')
                smart = lrdb.get_smartcoll_data(smart_name, True)
                if not smart:
                    print('  ==> FAILED : Not found')
                    return
                for _s in smart.splitlines():
                    print('\t', _s)

        try:
            if args.file:
                print('Smart Collection filename "%s"' % (smart_name))
                try:
                    smart = open(smart_name, 'r').read()
                    smart = smart[smart.find('{'):]
                    # smart = smart[4:]
                    lua = SLPP()
                    smart = lua.decode(smart)
                    if not smart or 'value' not in smart:
                        raise TypeError
                    if 'title' in smart:
                        smart_title = smart['title']
                    else:
                        smart_title = smart_name
                    print(' * Collection name : "%s"' % (smart_title))
                    smart = smart['value']
                except OSError:
                    print('  ==> FAILED : Not found')
                    continue
                except (KeyError, TypeError):
                    print('  ==> FAILED : Invalid syntax')
                    continue

            else:
                smart = lrdb.get_smartcoll_data(smart_name)
                if not smart:
                    raise OSError
        except OSError as _e:
            print('  ==> FAILED : Not found')
            continue

        builder = SQLSmartColl(lrdb, smart)

        if args.dict:
            print(' * Definition as python dictionnary :')
            for _s in builder.to_string().splitlines():
                print('\t', _s)

        if not (args.results or args.count or args.sql):
            continue

        try:
            sql = builder.build_sql(args.columns)
        except (LRSelectException, SmartException) as _e:
            print(' ==> FAILED : ', _e)
            continue

        if args.sql:
            print(' * SQL Request: ', sql)

        if not (args.results or args.count):
            continue

        log.info('start smart "%s"', smart_name)
        lrdb.cursor.execute(sql)
        rows = lrdb.cursor.fetchall()
        log.info('end smart : %s rows', len(rows))

        if args.count:
            print(' * Count results:', len(rows), end='  ')
            if smart_name in count_smart:
                if count_smart[smart_name] == len(rows):
                    print('=> conform to LR', end='')
                else:
                    print('=> NOT_CONFORM to LR : %s' % count_smart[smart_name], end='')
            print()

        if args.results:
            display_results(rows, args.columns, \
                max_lines=args.max_lines, header=not args.no_header, raw_print=args.raw_print)

    log.info('lrsmart end')



if __name__ == '__main__':
    # protect main from IOError occuring with a pipe command
    try:
        main()
    except IOError as _e:
        if _e.errno not in [22, 32]:
            raise _e
