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

from lrtools import __version__ as LR_VERSION

from lrtools.lrtoolconfig import LRToolConfig, LRConfigException

from lrtools.lrcat import LRCatDB, LRCatException
from lrtools.lrselectgeneric import LRSelectException
from lrtools.lrselectphoto import LRSelectPhoto
from lrtools.lrselectcollection import LRSelectCollection
from lrtools.display import display_results


DEFAULT_COLUMNS = "name,datecapt"

# pylint: disable=invalid-name
log = logging.getLogger()


def main():
    """Main entry from command line"""

    config = LRToolConfig()

    #
    # command parser
    #

    # prepare help based on doc strings
    description = (
        "Select elements from SQL table from Lightroom catalog.\n\n"
        'For photo : specify the "columns" to display and the "criteria of selection in :'
    )
    # add part of help for function LRSelectPhoto.select_generic
    doc_func = LRSelectPhoto.select_generic.__doc__
    start = doc_func.find("columns :")
    start = doc_func.rfind("\n", 0, start)
    end = doc_func.find("kwargs :")
    description += doc_func[start:end]
    # add part of help for function LRSelectCollection.select_generic
    description += '\nFor collection (use "-t collection") : specify the "columns" to display and the "criteria" of selection in :'
    doc_func = LRSelectCollection.select_generic.__doc__
    start = doc_func.find("columns :")
    start = doc_func.rfind("\n", 0, start)
    end = doc_func.find("kwargs :")
    description += doc_func[start:end]
    # complete help
    description += '\nFile sizes can be computed/displayed via the pseudo column "filesize", or option "--filesize".\n'
    description += (
        "\nExamples:\n"
        '\tlrselect.py --sql --results "name=basext,datecapt" "rating=>4,videos=0"\n'
        '\tlrselect.py  "name,datecapt,latitude,longitude,keywords" "rating=>4,videos=0" --results --count\n'
        '\tlrselect.py  "datecapt,filesize" "rating=>4,videos=0" --results'
    )

    parser = argparse.ArgumentParser(
        description=description, formatter_class=RawTextHelpFormatter
    )
    parser.add_argument(
        "columns", help="Columns to display", default=DEFAULT_COLUMNS, nargs="?"
    )
    parser.add_argument("criteria", help="Criteria of select", nargs="?")
    parser.add_argument(
        "-b",
        "--lrcat",
        default=config.default_lrcat,
        help='Ligthroom catalog file for database request (default:"%(default)s"), or INI file (lrtools.ini form)',
    )
    parser.add_argument(
        "-s", "--sql", action="store_true", help="Display SQL request"
    )
    parser.add_argument(
        "-c", "--count", action="store_true", help="Display count of results"
    )
    parser.add_argument(
        "-r", "--results", action="store_true", help="Display datas results"
    )
    parser.add_argument(
        "-z",
        "--filesize",
        action="store_true",
        help='Compute and display files size selection. Alternative: add a column "filesize"',
    )
    parser.add_argument(
        "-n",
        "--max-lines",
        type=int,
        default=-1,
        help="Max number of results to display (-1 means all results)",
    )
    parser.add_argument(
        "-f",
        "--file",
        help="UUIDs photos file : replace the criteria parameter which is ignored",
    )
    parser.add_argument(
        "-t",
        "--table",
        choices=["photo", "collection"],
        default="photo",
        help="table to work on : photo or collection",
    )
    parser.add_argument(
        "-N",
        "--no-header",
        action="store_true",
        help="don't print header (photos count ans columns names)",
    )
    parser.add_argument(
        "-w",
        "--widths",
        help="Widths of columns to display widths (ex:30,-50,10)",
    )
    parser.add_argument(
        "-S",
        "--separator",
        default=" | ",
        help='separator string between columns (default:"%(default)s")',
    )
    parser.add_argument(
        "-I",
        "--indent",
        type=int,
        default=4,
        help='space indentation in output (default:"%(default)s")',
    )
    parser.add_argument(
        "--raw-print",
        action="store_true",
        help="print raw value (for speed, aperture columns)",
    )
    parser.add_argument("--log", help="log on file")
    parser.add_argument(
        "--version", "-V", action="store_true", help="show version and exit"
    )

    args = parser.parse_args()

    if args.version:
        print(
            f"lrselect version : {LR_VERSION} , using python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        )
        return

    # logging
    if args.log:
        # basicConfig doesn't support utf-8 encoding yet (?)
        #   logging.basicConfig(filename=args.log, level=logging.INFO, encoding='utf-8')
        # use work-around :
        log.setLevel(logging.INFO)
        handler = logging.FileHandler(args.log, "a", "utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s - %(message)s"))
        log.addHandler(handler)
    log.info("lrselect start")
    log.info("lrtools version : %s", LR_VERSION)
    log.info("arguments: %s", " ".join(sys.argv[1:]))

    # --max_lines option implies --results
    if args.max_lines > 0:
        args.results = True
    # default columns if empty
    if not args.columns:
        if args.filesize:
            args.columns = "name=full,filesize"
        else:
            args.columns = DEFAULT_COLUMNS
    # prepare stuff when filesize wanted
    columns = [col.strip() for col in args.columns.split(",")]
    if "filesize" in columns:
        args.filesize = True
    if args.filesize:
        if "filesize" not in columns:
            columns.append("filesize")
        if "name=full" not in columns:
            columns.append("name=full")
    columns_lr = list(columns)
    if "filesize" in columns_lr:
        columns_lr.remove("filesize")

    # open database
    if not args.lrcat.endswith("lrcat"):
        # not a catalog but an INI file
        config.load(args.lrcat)
        args.lrcat = config.default_lrcat
    lrdb = LRCatDB(config, args.lrcat)

    # select on which table to work
    if args.table == "photo":
        lrobj = lrdb.lrphoto
    else:
        lrobj = LRSelectCollection(config, lrdb)

    if not (args.sql or args.count or args.results):
        print('WARNING: option "--count" forced')
        args.count = True

    if args.sql:
        print(
            " * SQL request = ",
            lrobj.select_generic(",".join(columns_lr), args.criteria, sql=True),
        )

    if not (args.count or args.results):
        return

    if args.file:
        # option file containing photo uuids
        try:
            uuids = open(args.file, encoding="utf-8").read().splitlines()
        except FileNotFoundError as _e:
            print(
                f' ==> Failed to open input file "{_e.filename}"',
                file=sys.stderr,
            )
            return
        # build rows ...
        bad_uuids = []
        rows = []
        for uuid in uuids:
            try:
                row = lrobj.select_generic(
                    ",".join(columns_lr), f'uuid="{uuid}"'
                ).fetchone()
                if row is None:
                    # failed to get uuid fromm db
                    bad_uuids.append(uuid)
                    continue
                rows.append(row)
            except LRSelectException as _e:
                print(" ==> FAILED:", _e, file=sys.stderr)
                return
            except sqlite3.OperationalError as _e:
                print(" ==> FAILED SQL :", _e, file=sys.stderr)
                return
        if bad_uuids:
            print(
                f"=> WARNING found uuids invalid ({len(bad_uuids)}/{len(uuids)}) : {', '.join(bad_uuids)}"
            )
    else:
        try:
            rows = lrobj.select_generic(
                ",".join(columns_lr), args.criteria
            ).fetchall()
        except LRSelectException as _e:
            # convert specific error caused by a limitation on build SQL with criteria width or height
            if _e.args[0] == "no such column: dims":
                _e.args = ('Try to add column "dims"',)
            print(" ==> FAILED:", _e, file=sys.stderr)
            return

    if args.count:
        print(" * Count results:", len(rows))

    if args.results:
        display_results(
            rows,
            columns,
            max_lines=args.max_lines,
            header=not args.no_header,
            widths=args.widths,
            raw_print=args.raw_print,
            separator=args.separator,
            filesize=args.filesize,
            indent=args.indent,
        )
    else:
        if args.filesize:
            # only compute total filesize
            display_results(
                rows,
                columns,
                max_lines=0,
                header=False,
                filesize=args.filesize,
            )


if __name__ == "__main__":
    # protect main from IOError occuring with a pipe command
    try:
        main()
    except IOError as _e:
        if _e.errno not in [22, 32]:
            raise _e
    except (LRConfigException, LRSelectException, LRCatException) as _e:
        print(" ==> FAILED:", _e, file=sys.stderr)
    except sqlite3.OperationalError as _e:
        print(" ==> FAILED SQL :", _e, file=sys.stderr)

    log.info("lrselect end")
