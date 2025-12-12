#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""

SQL results display functions

"""

import sys
import os
import re
from datetime import datetime, timedelta
import pytz

from . import localzone



def smart_unit(value, unit):
    """convert number in smart form : KB, MB, GB, TB"""
    if value is None:
        return f"- K{unit}"
    if isinstance(value, str):
        value = int(value)
    if value > 1000 * 1000 * 1000 * 1000:
        return f"{(value / (1000 * 1000 * 1000 * 1000.0)):.2f} T{unit}"
    if value > 1000 * 1000 * 1000:
        return f"{(value / (1000 * 1000 * 1000.0)):.2f} G{unit}"
    if value > 1000 * 1000:
        return f"{(value / (1000 * 1000.0)):.2f} M{unit}"
    if value > 1000:
        return f"{(value / (1000.0)):.2f} K{unit}"


#
# specific functions for display datas
#

def display_keywords(value):
    ''' remove None from keywords '''
    if value is None:
        value = ''
    return value

def display_aperture(value):
    ''' format aperture in F value '''
    return f'F{2**((float(value)/2)):.1f}'

def display_iso(value):
    ''' format iso value '''
    return f'{value:.0f}'

def display_speed(value):
    ''' format shutter speed value '''
    value = 2**(float(value))
    if value > 1:
        return f'1/{value:.0f}'
    return f'{1/value:.0f}'

def display_boolean(value):
    ''' format boolean value '''
    if value == 0:
        return 'no'
    if value == 1:
        return 'yes'
    return '?'

def display_date(value):
    ''' format date : remove sub-seconds '''
    return value[:19]

def display_lrtimestamp(value):
    ''' format LR timestamp (2001 based) '''
    utc = pytz.utc.localize(datetime(2001, 1, 1, 0, 0, 0) + timedelta(seconds=float(value)))
    return utc.astimezone(localzone).strftime("%Y-%m-%d %H:%M:%S")

def display_duration(value):
    ''' format video duration '''
    num, den = value.split('/')
    return seconds_tostring(int(num, 16) / int(den, 16), fract=1)

def display_flag(value):
    ''' format flag (pick) value'''
    dflags = {0: 'unflagged', 1: 'flagged', -1: 'rejected'}
    return dflags[int(value)]

def seconds_tostring(seconds, **kwargs):
    """
    convert seconds to string
    format returned :
        [H:]MM:SS[.pp]
    kwargs :
        fract : control decimals number
    """
    stime = []
    seconds = float(seconds)
    if seconds // 3600 > 0:
        stime.append(f"{int(seconds // 3600)}:")
    stime.append(f"{int((seconds // 60) % 60):02}:")
    stime.append(f"{int(seconds % 60):02}")
    if kwargs.get("fract", 0):
        fmt = f"%.{kwargs.get('fract', 0)}f"
        fract = fmt % (seconds % 1)
        fract = fract[1:]
        stime.append(fract)
    return "".join(stime)


#
# default columns width and display functions
#
DEFAULT_SPEC = ('%6s', None)
DEFAULT_SPECS = {
    'name'      : ('%-20s', None),
    'name=full' : ('%-80s', None),
    'name=base' : ('%-20s', None),
    'name=basext' : ('%-25s', None),
    'id'        : ('%8s', None),
    'uuid'      : ('%38s', None),
    'rating'    : ('%1s', None),
    'colorlabel': ('%8s', None),
    'flag'      : ('%6s', display_flag),
    'datemod'   : ('%19s', display_lrtimestamp),
    'datehist'  : ('%19s', display_lrtimestamp),
    'datecapt'  : ('%19s', display_date),
    'modcount'  : ('%2s', None),
    'master'    : ('%10s', None),
    'vname'     : ('%10s', None),
    'stackpos'  : ('%3s', None),
    'keywords'  : ('%-30s', display_keywords),
    'collections' : ('%-30s', None),
    'camera'    : ('%-15s', None),
    'camerasn'  : ('%-8s', None),
    'lens'      : ('%-25s', None),
    'iso'       : ('%5s', display_iso),
    'focal'     : ('%6s', None),
    'aperture'  : ('%5s', display_aperture),
    'speed'     : ('%6s', display_speed),
    'flash'     : ('%3s', display_boolean),
    'monochrome': ('%3s', display_boolean),
    'creator'   : ('%-18s', None),
    'caption'   : ('%-30s', None),
    'dims'      : ('%-10s', None),
    'pubcollection'   : ('%30s', None),
    'pubname'   : ('%30s', None),
    'pubtime'   : ('%19s', display_lrtimestamp),
    'latitude'  : ('%-18s', None),
    'longitude' : ('%-18s', None),
    'duration'  : ('%5s', display_duration),
    'filesize'  : ('%8s', None),            # pseudo column
}
DEFAULT_SEPARATOR = ' | '


def prepare_display_columns(columns, widths):
    '''
    Prepare columns to display : set width and specific display functions
    - columns : ([str]) columns names as defined by LRSelectPhotos
    - widths : ([str]) width of each column, comma separated (ex: "15,-50")
    '''
    column_spec = {}
    for num_col, name in enumerate(columns):
        name = name.strip()
        if not name:
            continue
        if name in DEFAULT_SPECS:
            width, func = DEFAULT_SPECS[name]
        else:
            width, func = DEFAULT_SPEC
        # chance to change widths from outside
        if num_col < len(widths):
            width = f'%{widths[num_col].strip()}s'
        column_spec[num_col] = (name, width, func)
    return column_spec


def display_results(rows, columns, **kwargs):
    '''
    Display SQL results
    - rows : SQL colummns
    - columns : column names to display ("filesize" column can be specified for compute filesize )
    - kwargs :
       * max_lines : max lines to display
       * header : display header (columns names)
       * indent : number of indentation space on each line
       * widths : widths of columns
       * separator : characters separator between columns
       * raw_print : print raw value (for columns aperture, shutter speed, ido, dates)
       * filesize : compute and add column filesize
    '''
    if not rows:
        if kwargs.get('header', True):
            print(' * None data result')
        return

    if isinstance(columns, str):
        columns = [a.strip() for a in columns.split(',')]
    widths = kwargs.get('widths', [])
    if widths is None:
        widths = []
    if isinstance(widths, str):
        widths = [a.strip() for a in widths.split(',')]
    indent = kwargs.get('indent', 4)
    separator = kwargs.get('separator', DEFAULT_SEPARATOR)
    wanted_lines = kwargs.get('max_lines', sys.maxsize)
    if wanted_lines < 0:
        wanted_lines = sys.maxsize
    if wanted_lines >= len(rows):
        max_lines = len(rows)
        if  kwargs.get('header', True):
            print(f' * Photo results ({len(rows)} photos) :')
    else:
        max_lines = wanted_lines
        if  kwargs.get('header', True):
            print(f' * Photo results (first {wanted_lines} photos on {len(rows)}) :')

    column_spec = prepare_display_columns(columns, widths)

    # basic check : detect if suffisant column
    for i in range(len(rows[0])):
        if i < len(column_spec):
            continue
        column_spec[i] = (f'column{i}', DEFAULT_SPEC[0], DEFAULT_SPEC[1])

    # display header
    if kwargs.get('header', True):
        total_width = 0
        line = []

        for _, num_col in enumerate(column_spec):
            name, width, _ = column_spec[num_col]
            match = re.search(r'(\d+)s', width)
            if match:
                val_width = int(match.group(1))
            else:
                val_width = 8
            total_width += val_width
            name = name[:val_width]
            line.append(width % name)
        print(indent * ' ', separator.join(line), sep='')
        print(indent * ' ', (total_width + (len(column_spec) - 1) * len(separator)) * '=', sep='')

    # display datas
    total_filesize = 0
    if  kwargs.get('filesize', False):
        # compute columns index
        columns_lr = list(columns)
        columns_lr.remove('filesize')
        id_fname = columns_lr.index('name=full')
        id_filesize = columns.index('filesize')
    for num in range(0, max_lines):
        if num == len(rows):
            break
        line = []
        row = rows[num]
        if  kwargs.get('filesize', False):
            fname = row[id_fname]
            try:
                size = os.path.getsize(fname)
                total_filesize += size
            except OSError:
                size = 0
            row = list(row)
            row.insert(id_filesize, size)
        for num_col, value in enumerate(row):
            try:
                _, width, func_format = column_spec[num_col]
            except KeyError:
                # invisible column (ex: criteria width/heightCropped)
                continue
            if not kwargs.get('raw_print', False):
                if value is None:
                    value = ''
                elif func_format:
                    value = func_format(value)
            line.append(width % value)
        print(indent * ' ', separator.join(line), sep='')

    # datas displayed, but maybe still filesize to compute
    if  kwargs.get('filesize', False):
        for num in range(max_lines, len(rows)):
            row = rows[num]
            fname = row[id_fname]
            try:
                size = os.path.getsize(fname)
                total_filesize += size
            except OSError:
                pass
        print(f' * Total filesize : {smart_unit(total_filesize, "B")} ({total_filesize} bytes)')
