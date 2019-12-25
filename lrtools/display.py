#!python3
# -*- coding: utf-8 -*-

"""

SQL results display functions

"""

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
    'name'      : ('%-20s', None),
    'name=full' : ('%-60s', None),
    'name=base' : ('%-20s', None),
    'name=basext' : ('%-25s', None),
    'id'        : ('%8s', None),
    'uuid'      : ('%38s', None),
    'rating'    : ('%1s', None),
    'colorlabel': ('%8s', None),
    'datemod'   : ('%19s', None),
    'datecapt'  : ('%19s', display_date),
    'modcount'  : ('%2s', None),
    'master'    : ('%10s', None),
    'vname'     : ('%10s', None),
    'stackpos'  : ('%3s', None),
    'keywords'  : ('%-30s', display_keywords),
    'collections' : ('%-30s', None),
    'camera'    : ('%-15s', None),
    'lens'      : ('%-25s', None),
    'iso'       : ('%5s', display_iso),
    'focal'     : ('%6s', None),
    'aperture'  : ('%5s', display_aperture),
    'speed'     : ('%6s', display_speed),
    'creator'   : ('%18s', None),
    'caption'   : ('%-30s', None),
    'dims'      : ('%-10s', None),
}
DEFAULT_SEPARATOR = ' | '


def prepare_display_columns(columns, widths):
    '''
    Prepare columns to display : set width and specific display functions
    - columns : (str) columns names as defined by LRSelectPhotos
    - widths : (str) width of each column, comma separated (ex: "15,-50")
    '''
    widths = widths.split(',') if widths else []
    column_spec = {}
    for num_col, name in enumerate(columns.split(',')):
        name = name.strip()
        if not name:
            continue
        if name in DEFAULT_SPECS:
            width, func = DEFAULT_SPECS[name]
        else:
            width, func = DEFAULT_SPEC
        # chance to change widths from outside
        if num_col < len(widths):
            width = '%%%ss' % widths[num_col].strip()
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
       * widths : widths of columns
       * separator : characters separator between columns
       * raw_print : print raw value (for columns aperture, shutter speed, ido, dates)
    '''
    if not rows and kwargs.get('header', True):
        print(' * None data result')
        return

    indent = kwargs.get('indent', 4)
    separator = kwargs.get('separator', DEFAULT_SEPARATOR)
    wanted_lines = kwargs.get('max_lines', 0)
    if wanted_lines == 0 or wanted_lines >= len(rows):
        max_lines = len(rows)
        if  kwargs.get('header', True):
            print(' * Photo results (%s photos) :' % (len(rows)))
    else:
        max_lines = wanted_lines
        if  kwargs.get('header', True):
            print(' * Photo results (first %s photos on %s) :' % (wanted_lines, len(rows)))

    column_spec = prepare_display_columns(columns, kwargs.get('widths', ''))

    # display header
    if kwargs.get('header', True):
        total_width = 0
        line = []

        for num_col in range(0, len(column_spec)):
            name, width, _ = column_spec[num_col]
            val_width = int(''.join([char for char in width if char.isdigit()]))
            total_width += val_width
            name = name[:val_width]
            line.append(width % name)
        print(indent * ' ', separator.join(line), sep='')
        print(indent * ' ', (total_width + (len(column_spec) - 1) * len(separator)) * '=', sep='')

    # display datas
    for num in range(0, max_lines):
        if num == len(rows):
            break
        line = []
        for num_col, value in enumerate(rows[num]):
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
    print()
