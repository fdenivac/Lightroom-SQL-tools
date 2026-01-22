#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=line-too-long
"""

Execute Lightroom smart collections from catalog or file

"""

import sys
import logging
import argparse
from sqlite3 import OperationalError

from lrtools import __version__ as LR_VERSION

from lrtools.lrtoolconfig import LRToolConfig, LRConfigException

from lrtools.lrcat import LRCatDB, LRCatException
from lrtools.lrselectgeneric import LRSelectException
from lrtools.lrsmartcoll import SQLSmartColl, SmartException
from lrtools.slpp import SLPP
from lrtools.display import display_results


def main():
    """Main entry from command line"""

    config = LRToolConfig()

    #
    # commands parser
    #
    # prepare description
    criteria = ", ".join(
        [
            crit.split("_")[1]
            for crit in dir(SQLSmartColl)
            if crit.startswith("criteria_")
        ]
    )
    description = (
        "Execute smart collections from Lightroom catalog or from a exported file.\n"
        "Supported criteria are : " + criteria
    )
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "smart_name",
        help='name of smart(s) collection. Can be lightroom smart collections (joker "%%"), or filenames (joker "*") with option "--file",',
        nargs="*",
    )
    parser.add_argument(
        "-b",
        "--lrcat",
        default=config.default_lrcat,
        help='Lightroom catalog file for database request (default:"%(default)s")',
    )
    parser.add_argument(
        "-f",
        "--file",
        action="store_true",
        help="positionnal parameters are files, not smart collection names",
    )
    parser.add_argument(
        "-l",
        "--list",
        action="store_true",
        help='list smart collections of name "smart_name" from Lightroom catalog.'
        ' "smart_name" can include jokers "%%". Leave empty for all collections',
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="display description of smart collection as stored",
    )
    parser.add_argument(
        "-d",
        "--dict",
        action="store_true",
        help="display description of smart collection as python dictionnary",
    )
    parser.add_argument(
        "-s", "--sql", action="store_true", help="display SQL request"
    )
    parser.add_argument(
        "-c", "--count", action="store_true", help="display count of results"
    )
    parser.add_argument("--validation-file", default="", help=argparse.SUPPRESS)
    parser.add_argument(
        "-r", "--results", action="store_true", help="display datas results"
    )
    parser.add_argument(
        "-n",
        "--max-lines",
        type=int,
        default=0,
        help="max number of results to display",
    )
    parser.add_argument(
        "-C",
        "--columns",
        default="uuid,name",
        help='columns names to print (default:"%(default)s").'
        " For column names, see help of lrselect.py. "
        "(Note that to obtain a number of results identical to those obtained in LR,"
        " the uuid column must be present)",
    )
    parser.add_argument(
        "-o",
        "--sort-column",
        default="1",
        help='name or number (one based) of column to sort (default:"%(default)s").'
        ' Sort is ascending order by default, add "-" before colum name or number for descending order',
    )
    parser.add_argument(
        "-N",
        "--no-header",
        action="store_true",
        help="don't print header (columns names)",
    )
    parser.add_argument(
        "-w",
        "--widths",
        help="widths of columns to display (ex:30,-50,10)",
    )
    parser.add_argument(
        "-S",
        "--separator",
        default=" | ",
        help='separator string between columns (default:"%(default)s")',
    )
    parser.add_argument(
        "--raw-print",
        action="store_true",
        help="print raw value (for speed, aperture columns)",
    )
    parser.add_argument("--log", help="log to file")

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
        handler = logging.FileHandler(args.log, "a", "utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s - %(message)s"))
        log.addHandler(handler)
    log = logging.getLogger()
    log.info("lrsmart start")
    log.info("lrtools version : %s", LR_VERSION)

    #
    # for lrsmart validation :
    #  a file containing photos number by smart collection, extracted from Lightrrom (via specific plugin)
    #  can be loaded :
    #
    count_smart = {}
    if args.validation_file:
        try:
            lines = (
                open(args.validation_file, encoding="utf8").read().splitlines()
            )
            for line in lines:
                values = line.split("==>")
                if not len(values) == 2:
                    continue
                count_smart[values[0].strip()] = int(values[1].strip())
        except FileNotFoundError:
            sys.exit("Validation file not found")

    # open catalog
    if not args.lrcat.endswith("lrcat"):
        # specify LR catalog or INI file
        config.load(args.lrcat)
        args.lrcat = config.default_lrcat
    lrdb = LRCatDB(config, args.lrcat)

    if args.list:
        if not args.smart_name:
            args.smart_name = "%"

    if not args.file:
        # place for process joker '%'
        colls = []
        for name in args.smart_name:
            colls += lrdb.select_collections(lrdb.SMART_COLL, name)
        args.smart_name = [name for _, name, _ in colls]

    for smart_name in args.smart_name:
        if not args.file:
            print(f'Smart Collection "{smart_name}"')
        if args.raw:
            if args.file:
                try:
                    for line in (
                        open(smart_name, encoding="utf-8").read().splitlines()
                    ):
                        print(line)
                except OSError:
                    print("  ==> FAILED : Not found")
                    continue
            else:
                print(" * Raw definition as stored :")
                smart = lrdb.get_smartcoll_data(smart_name, True)
                if not smart:
                    print("  ==> FAILED : Not found")
                    return
                for _s in smart.splitlines():
                    print("\t", _s)

        try:
            if args.file:
                print(f'Smart Collection filename "{smart_name}"')
                try:
                    smart = open(smart_name, "r", encoding="utf-8").read()
                    smart = smart[smart.find("{") :]
                    lua = SLPP()
                    smart = lua.decode(smart)
                    if not smart or "value" not in smart:
                        raise TypeError
                    if "title" in smart:
                        smart_title = smart["title"]
                    else:
                        smart_title = smart_name
                    print(f' * Collection name : "{smart_title}"')
                    smart = smart["value"]
                except OSError:
                    print("  ==> FAILED : Not found")
                    continue
                except (KeyError, TypeError):
                    print("  ==> FAILED : Invalid syntax")
                    continue

            else:
                smart = lrdb.get_smartcoll_data(smart_name)
                if not smart:
                    raise OSError
        except OSError as _e:
            print("  ==> FAILED : Not found")
            continue

        builder = SQLSmartColl(config, lrdb, smart)

        if args.dict:
            print(" * Definition as python dictionnary :")
            for _s in builder.to_string().splitlines():
                print("\t", _s)

        if not (args.results or args.count or args.sql):
            continue

        try:
            sql = builder.build_sql(args.columns)
        except (LRSelectException, SmartException) as _e:
            print(" ==> FAILED : ", _e)
            continue
        # add sort on column
        sort_column = args.sort_column.strip()
        way = "ASC"
        if sort_column[0] == "-":
            way = "DESC"
            sort_column = sort_column[1:]
        sql += f" ORDER BY {sort_column} {way}"

        if args.sql:
            print(" * SQL Request: ", sql)

        if not (args.results or args.count):
            continue

        log.info('start smart "%s"', smart_name)
        try:
            lrdb.cursor.execute(sql)
            rows = lrdb.cursor.fetchall()
            log.info("end smart : %s rows", len(rows))
        except OperationalError as _e:
            log.info("end smart : FAILED : %s", _e)
            print(" ==> FAILED : ", _e)
            continue

        if args.count:
            print(" * Count results:", len(rows), end="  ")
            if smart_name in count_smart:
                if count_smart[smart_name] == len(rows):
                    print("=> conform to LR", end="")
                else:
                    print(
                        f"=> NOT_CONFORM to LR : {count_smart[smart_name]}",
                        end="",
                    )
            print()

        if args.results:
            display_results(
                rows,
                [d[0] for d in lrdb.cursor.description],
                max_lines=args.max_lines,
                header=not args.no_header,
                raw_print=args.raw_print,
                separator=args.separator,
            )

    log.info("lrsmart end")


if __name__ == "__main__":
    # protect main from IOError occuring with a pipe command
    try:
        main()
    except IOError as _e:
        if _e.errno not in [22, 32]:
            raise _e
    except (LRConfigException, LRSelectException, LRCatException) as _e:
        print(" ==> FAILED:", _e, file=sys.stderr)
