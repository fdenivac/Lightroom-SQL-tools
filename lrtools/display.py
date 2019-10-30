#!python3
# -*- coding: utf-8 -*-

"""

SQL results display functions

"""

#
# specific functions for display datas
#

def display_aperture(value):
    ''' format aperture in F value '''
    return 'F%.1f' % 2**((float(value)/2))

def display_iso(value):
    ''' format iso value '''
    return '%.0f' % value

def display_speed(value):
    ''' format shutter speed value '''
    value = 2**(float(value))
    if value > 1:
        return '1/%.0f'  % value
    return '%.0f' % (1/value)

def display_date(value):
    ''' format date : remove sub-seconds '''
    return value[:19]



#
# default columns width and display functions
#
DEFAULT_SPEC = ('%6s', None)
DEFAULT_SPECS = {
    'name' : ('%-20s', None),
    'name=full' : ('%-60s', None),
    'name=base' : ('%-20s', None),
    'name=basext' : ('%-25s', None),
    'id' : ('%8s', None),
    'uuid' : ('%38s', None),
    'rating' : ('%1s', None),
    'colorlabel': ('%8s', None),
    'datemod' : ('%19s', None),
    'datecapt' : ('%19s', display_date),
    'modcount' : ('%2s', None),
    'master'    :('%10s', None),
    'vname'     : ('%10s', None),
    'stackpos'  :('%3s', None),
    'camera'    : ('%-15s', None),
    'lens'      : ('%-25s', None),
    'iso'       : ('%5s', display_iso),
    'focal'     : ('%6s', None),
    'aperture'  : ('%5s', display_aperture),
    'speed'     : ('%6s', display_speed),
}
SEPARATOR = ' | '


def prepare_display_columns(columns):
    '''
    Prepare columns to display : set width and specific display functions
    '''
    # column names and default widths
    column_spec = {}
    for num_col, name in enumerate(columns.split(',')):
        name = name.strip()
        if not name:
            continue
        if name in DEFAULT_SPECS:
            width, func = DEFAULT_SPECS[name]
        else:
            width, func = DEFAULT_SPEC
        column_spec[num_col] = (name, width, func)
    return column_spec


def display_results(rows, columns, **kwargs):
    '''
    Display SQL results
    - rows : SQL colummns to print
    - columns : column names string selected
    - kwargs :
       * max_lines : max lines to display
       * header : display header (columns names)
       * indent : number of indentation space on each line
       * raw_print : print raw value (for columns aperture, shutter speed, ido, dates)
    '''
    if not rows:
        print(' * None data result')
        return

    indent = kwargs.get('indent', 4)
    wanted_lines = kwargs.get('max_lines', 0)
    if wanted_lines == 0 or wanted_lines >= len(rows):
        max_lines = len(rows)
        print(' * Photo results (%s photos) :' % (len(rows)))
    else:
        max_lines = wanted_lines
        print(' * Photo results (first %s photos on %s) :' % (wanted_lines, len(rows)))

    column_spec = prepare_display_columns(columns)

    # display header
    if kwargs.get('header', True):
        total_width = 0
        print(end=indent * ' ')
        for num_col in range(0, len(column_spec)):
            name, width, _ = column_spec[num_col]
            val_width = int(''.join([char for char in width if char.isdigit()]))
            total_width += val_width + len(SEPARATOR)
            name = name[:val_width]
            print(width % name, end=SEPARATOR)
        print()
        print(end=indent * ' ')
        print(total_width * "=")

    # display datas
    for num in range(0, max_lines):
        if num == len(rows):
            break
        print(end=indent * ' ')
        for num_col, value in enumerate(rows[num]):
            _, width, func_format = column_spec[num_col]
            if not kwargs.get('raw_print', False) and value is not None and func_format:
                value = func_format(value)
            print(width % value, end=SEPARATOR)
        print()
    print()
