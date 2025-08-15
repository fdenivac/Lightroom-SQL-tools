# Lightroom-SQL-tools
Python library and scripts to retrieve and displays photos data from an Adobe Lightroom catalog

* Execute SQL queries outside of Lightroom
* The catalog is opened in read-only mode, so scripts can be executed while Lightroom is still running.
* 2 scripts available : **lrselect** for generic selection based on various criteria, and **lrsmart** for executing smart collections
* Helper functions for displaying sql queries, result counts, and full results


## Tested environment
* OS: Windows 10 (64 bit)
* Lightroom: 6.x, Classic CC
* Python" >= 3.7
* Terminals: Windows console or cygwin


## Installation
* run "``pip install git+https://github.com/fdenivac/Lightroom-SQL-tools``"
  
<br>OR<br>

* download *[zip file project ](https://github.com/fdenivac/Lightroom-SQL-tools/archive/master.zip)*
* extract the zip file
* execute in the main directory: ``python setup.py install``

Scripts (``lrselect.py`` and ``lrsmart.py``) are installed in *Scripts* directory of Python.

## Configuration
Modify the config file *lrtools.ini*:
* LRCatalog : the default Lightroom catalog to use
* DayFirst :  parsing date format ("DD-MM-YY" if True, else  "YY-MM-DD")

## Using lrtools library

    import sys
    from lrtools.lrcat import LRCatDB, LRCatException
    from lrtools.lrselectgeneric import LRSelectException
    from lrtools.display import display_results

    # open Lightroom catalog
    try:
        lrdb = LRCatDB("D:\Lightroom\Mycatalog.lrcat")
    except LRCatException as _e:
        sys.exit(' ==> FAILED: %s' % _e)

    # select photos
    columns = "name,datecapt, keywords"
    criteria = "datecapt=>=2016-5-15, datecapt=<=2018-1-31, keyword=beach, keyword=family, rating=>3"
    try:
        rows = lrdb.lrphoto.select_generic(columns, criteria).fetchall()
    except LRSelectException as _e:
        sys.exit(' ==> FAILED: %s' % _e)

    # and display results
    display_results(rows, columns, header=True)

</br>
</br>

## Using **lrselect** script
Retrieves and displays data about photos or collections

It builds an SQL SELECT query from two strings describing informations to display, and criteria to search

    ``usage: lrselect.py [OPTIONS] columns criteria``

* Options for display sql query, result count, partial results
* Wildcards "%" can be used in criterion of type string (ex:name=%ab%)
* Criteria are combined with AND (the comma character ","), OR (the vertical line character "|" ) and parenthesis operators
* Allows repeats of the same criterion (ex: "datecapt=>=1-5-2016, datecapt=<=1-9-2018, keyword=sea, keyword=tree")


### Some examples

* photos taken around Paris, with camera RX100, between May and August 2018, and modified in Lightroom since August 2019:

        lrselect.py "name, focal, speed, aperture, keywords" "gps=paris+10, camera=%rx100%, datecapt=>=1-5-2018, datecapt=<=1-7-2018, datemod=>=1-8-2019"
        * Photo results (2 photos) :
            name                 | focal |  speed  | apert | keywords
            ===========================================================
            RX100_01399.tif      |  10.89 |  1/160 |  F5.6 | family,paris
            RX100_01598.DNG      |    8.8 |   1/80 |  F5.0 | museum,paris

* photos with specific name, iso > 1600, focal > 200mm and aperture > F/8 :

        lrselect.py "name,datecapt,iso,focal,aperture,speed,lens" "name=D7K_%,iso=>=1600,focal=>=200,aperture=>8" --max_lines 2
        * Photo results (first 2 photos on 8) :
            name                 |            datecapt |   iso |  focal | apert |  speed | lens
            ===========================================================================================================
            D7K_01977.JPG        | 2013-09-04T15:55:01 |  1600 |  280.0 | F20.0 |  1/500 | 55.0-300.0 mm f/4.5-5.6
            D7K_13025.DNG        | 2014-12-07T14:46:08 |  3200 |  300.0 |  F9.0 |  1/500 | 55.0-300.0 mm f/4.5-5.6

* list of 70mm lenses used with Nikon cameras :

        lrselect.py  "camera,lens"  "camera=nikon D8%, lens=%70%, distinct, sort=-1" --results --sql
        * SQL query =  SELECT DISTINCT  cm.value, el.value FROM Adobe_images i LEFT JOIN AgHarvestedExifMetadata em on i.id_local = em.image LEFT JOIN AgInternedExifCameraModel cm on cm.id_local = em.cameraModelRef LEFT JOIN AgInternedExifLens el on el.id_local = em.lensRef WHERE cm.value LIKE "nikon D8%" AND el.value LIKE "%70%" ORDER BY 1 ASC
        * Photo results (2 photos) :
            camera          | lens
            ==============================================
            NIKON D80       | 17.0-70.0 mm f/2.8-4.0
            NIKON D800E     | 24.0-70.0 mm f/2.8

* list of Canon cameras used :

        lrselect.py "camera" "camera=canon%, distinct" -r
        * Photo results (4 photos) :
            camera
            =====================
            Canon PowerShot G2
            Canon DIGITAL IXUS
            Canon PowerShot G10
            Canon EOS 5D

* Photos number for Canon cameras :

        lrselect.py  "camera, countby(camera)" "camera=canon%, sort=2" -Nr
            Canon PowerShot G2 |  10843
            Canon EOS 5D |   1234
            Canon DIGITAL IXUS 40 |    346
            Canon PowerShot G10 |    140

* duplicates photo name (name with virtual copies)

        lrselect.py "name=basext_vc, countby(name=basext_vc)", "count=name>1" -r
        * Photo results (2 photos) :
            name=b | countb
            ===============
            IMG_102.jpg |      2
            DSC_2038.jpg |      4

* number of photos with "boat" and "family" keywords :

        lrselect.py  ""  "keyword=Boat,keyword=family" --count
        * Count results: 65


### Complete Help :

    usage: lrselect.py [-h] [-b LRCAT] [-s] [-c] [-r] [-z] [-n MAX_LINES] [-f FILE] [-t {photo,collection}] [-N] [-w WIDTHS] [-S SEPARATOR] [-I INDENT] [--raw-print] [--log LOG]
                    [columns] [criteria]

    Select elements from SQL table from Lightroom catalog.

    For photo : specify the "columns" to display and the "criteria of selection in :
        columns :
            - 'name'='base'|'basext'|'full' : base name, basename + extension, full name (path,name, extension)
                With 'base_vc', 'basext_vc', 'full_vc' names for virtual copies are completed with copy name.
            - 'id'         : id photo (Adobe_images.id_local)
            - 'uuid'       : UUID photo (Adobe_images.id_global)
            - 'rating'     : rating/note
            - 'colorlabel' : color and label
            - 'datemod'    : modificaton date
            - 'datecapt'   : capture date
            - 'modcount'   : number of modifications
            - 'master'     : master image of virtual copy
            - 'xmp'        : all xmp metadatas
            - 'vname'      : virtual copy name
            - 'stackpos'   : position in stack
            - 'stack'      : stack identifier
            - 'keywords'   : keywords list
            - 'collections': collections list
            - 'exif'       : 'var:SQLCOLUMN' : display column in table AgHarvestedExifMetadata. Ex: "exif=var:hasgps"
            - 'extfile'    : extension of an external/extension file (jpg,xmp,...)
            - 'dims'       : image dimensions in form <WIDTH>x<HEIGHT>
            - 'aspectratio': aspect ratio (width/height)
            - 'camera'     : camera name
            - 'lens'       : lens name
            - 'iso'        : ISO value
            - 'focal'      : focal lens
            - 'aperture'   : aperture lens
            - 'speed'      : speed shutter
            - 'latitude'   : GPS latitude
            - 'longitude'  : GPS longitude
            - 'creator'    : photo creator
            - 'caption'    : photo caption
            - 'pubname'    : remote path and name of published photo
            - 'pubcollection' : name of publish collection
            - 'pubtime'    : published datetime in seconds from 2001-1-1
            - 'pubposition': order number (float) in collection
            - 'count(NAME)' : count not NULL value for column NAME (ex: "count(master)")
            - 'countby(NAME)' : count aggregated not NULL value for column NAME
        criterias :
            - 'name'       : (str) filename without extension
            - 'exactname'  : (str) filename insensitive without extension
            - 'ext'        : (str) file extension
            - 'id'         : (int) photo id (Adobe_images.id_local)
            - 'uuid'       : (string) photo UUID (Adobe_images.id_global)
            - 'rating'     : (str) [operator (<,<=,>,=, ...)] and rating/note (ex: "rating==5")
            - 'colorlabel' : (str) color and label. Color names are localized (Bleu, Rouge,...)
            - 'flag'       : (str) flag status : 'flagged', 'unflagged', 'rejected'. (ex: "flag=flagged")
            - 'creator'    : (str) photo creator
            - 'caption'    : (true/false/str) photo caption
            - 'datecapt'   : (str) operator (<,<=,>, >=) and capture date
            - 'datemod'    : (str) operator (<,<=,>, >=) and lightroom modification date
            - 'modcount'   : (int) number of modifications
            - 'iso'        : (int) ISO value with operators <,<=,>,>=,= (ex: "iso=>=1600")
            - 'focal'      : (int) focal lens with operators <,<=,>,>=,= (ex: "iso=>135")
            - 'aperture'   : (float) aperture lens with operators <,<=,>,>=,= (ex: "aperture=<8")
            - 'speed'      : (float) speed shutter with operators <,<=,>,>=,= (ex: "speed=>=8")
            - 'camera'     : (str) camera name (ex:"camera=canon%")
            - 'lens'       : (str) lens name (ex:"lens=%300%")
            - 'width'      : (int) cropped image width. Need to include column "dims"
            - 'height      : (int) cropped image height. Need to include column "dims"
            - 'aspectratio': (float) aspect ratio (width/height)
            - 'hasgps'     : (bool) has GPS datas
            - 'gps'        : (str) GPS rectangle defined by :
                                - town or coordinates, and bound in kilometer (ex:"paris+20", "45.7578;4.8320+10"),
                                - 2 towns or coordinates (ex: "grenoble/lyon", "44.84;-0.58/43.63;1.38")
                                - a geolocalized Lightroom photo name (ex:"photo:NIK_10312")
            - 'videos'     : (bool) type videos
            - 'exifindex'  : search words in exif (AgMetadataSearchIndex). Use '&' for AND words '|' for OR. ex: "exifindex=%Lowy%&%blanko%"
            - 'vcopies'    : 'NULL'|'!NULL'|'<NUM>' : all, none virtual copies or copies for a master image NUM
            - 'keyword'    : (str) keyword name. Only one keyword can be specified in request
            - 'haskeywords': (bool) photos with or without keywords
            - 'import'     : (int) import id
            - 'stacks'     : operation on stacks in :
                    'yes'    = photos in a stack
                    'no'     = excludes photos in a stack
                    'top'    = photos at the top of stacks
                    'no+top' = excludes photos in a stack not at first position
                    <NUM>    = photos in the stack identifier NUM
            - 'metastatus' :  metadatas status
                    'conflict' = metadatas different on disk from db
                    'changedondisk' = metadata changed externally on disk
                    'hasbeenchanged' = to be save on disk
                    'conflict' = metadatas different on disk from db
                    'uptodate' = uptodate, in error, or to write on disk
                    'unknown' = write error, phot missing ...
            - 'idcollection' : (int) collection id
            - 'collection' : (str) collection name
            - 'pubcollection: (str) publish collection name
            - 'pubtime     : (str) publish time,  operator (<,<=,>, >=)
            - 'extfile'    : (str) has external file with <value> extension as jpg,xmp... (field AgLibraryFile.sidecarExtensions)

            - 'count(NAME) : (str) criter for column countby(NAME)
            - 'sort'       : (int|str) sort result: column index (one based) or column name 
            - 'distinct'   : suppress similar lines of results

    For collection : specify the "columns" to display and the "criteria" of selection in :
            columns :
                - 'name'      : collection name
                - 'id'        : id collection
                - 'type'      : collection type
                - 'parent'    : id of parent collection
                - 'smart'     : data of smart collection. For a specfic collection use criteria "id4content" or "name4content"
            criteria :
                - 'name'      : (str) collection name
                - 'id'        : (int) collection id
                - 'type'      : (str) collection type (creationId) : "standard", "smart", "all", or explicit creationId content (as com.adobe.ag.library.group)
                - 'id4smart  ': (int) id smart collection. To be used with column "smart"
                - 'name4smart': (str) name of smart collection. To be used with column "smart"

    File sizes can be computed/displayed via the pseudo column "filesize", or option "--filesize".

    Examples:
            lrselect.py --sql --results "basename,datecapt" "rating=>4,video=0"
            lrselect.py  "name,datecapt,latitude,longitude,keywords" "rating=>4,videos=0" --results --count
            lrselect.py  "datecapt,filesize" "rating=>4,videos=0" --results

    positional arguments:
    columns               Columns to display
    criteria              Criteria of select

    options:
    -h, --help            show this help message and exit
    -b LRCAT, --lrcat LRCAT
                            Ligthroom catalog file for database request (default:"C:\Lightroom\La Totale\La Totale.lrcat"), or INI file (lrtools.ini form)
    -s, --sql             Display SQL request
    -c, --count           Display count of results
    -r, --results         Display datas results
    -z, --filesize        Compute and display files size selection. Alternative: add a column "filesize"
    -n MAX_LINES, --max-lines MAX_LINES
                            Max number of results to display (-1 means all results)
    -f FILE, --file FILE  UUIDs photos file : replace the criteria parameter which is ignored
    -t {photo,collection}, --table {photo,collection}
                            table to work on : photo or collection
    -N, --no-header       don't print header (photos count ans columns names)
    -w WIDTHS, --widths WIDTHS
                            Widths of columns to display widths (ex:30,-50,10)
    -S SEPARATOR, --separator SEPARATOR
                            separator string between columns (default:" | ")
    -I INDENT, --indent INDENT
                            space indentation in output (default:"4")
    --raw-print           print raw value (for speed, aperture columns)
    --log LOG             log on file




</br>
</br>
</br>


## Using **lrsmart** script
Retrieve smart collections stored in catalog, process SQL queries and displays results</br>
Smart files, exported from Lightroom or modified by hand, can be specified too.</br>
Unfortunately :
 * some criteria or operations are not implemented
 * some operations on criteria don't give the exact same results as Lightroom (as: all, touchtime ...)
</br>
=> ... TODO improvements !

### Supported criteria
* all
* aperture
* aspectRatio
* camera
* captureTime
* collection
* colorMode
* creator
* exif
* fileFormat
* filename
* flashFired
* focalLength
* hasAdjustments
* hadsGPSData
* heightCropped
* iptc
* isoSpeedRating
* keywords
* labelColor
* labelText
* lens
* metadata
* metadataStatus
* rating
* shutterSpeed
* touchTime
* treatment
* widthCropped

### Some examples

* display short definition for smart collections which name contains "mil"

        lrsmart.py --list --dict "%mil%"
           Smart Collection "Family smart photos"
           * Definition as python dictionnary :
                   0 = {'criteria': 'rating', 'operation': '>=', 'value': 3}
                   1 = {'criteria': 'keywords', 'operation': 'any', 'value': 'family', 'value2': ''}
                   combine = intersect
           ....


* display smart collection "Holidays no GPS" with specific columns

        lrsmart.py "Holidays no GPS" --sql --max_lines 2 --columns "name, datecapt"
          Smart Collection "Holidays no GPS"
           * Definition as python dictionnary :
                0 = {'criteria': 'collection', 'operation': 'beginsWith', 'value': 'Ballades', 'value2': ''}
                1 = {'criteria': 'hasGPSData', 'operation': '==', 'value': False}
                combine = intersect
           * SQL query:  SELECT DISTINCT  fi.baseName || "." || fi.extension AS name, i.captureTime AS datecapt FROM Adobe_images i LEFT JOIN AgLibraryFile fi ON i.rootFile = fi.id_local  LEFT JOIN  AgLibraryCollectionimage ci0 ON ci0.image = i.id_local LEFT JOIN AgLibraryCollection col0 ON col0.id_local = ci0.Collection WHERE col0.name LIKE "Holidays%" INTERSECT SELECT  fi.baseName || "." || fi.extension AS name, i.captureTime AS datecapt FROM Adobe_images i  JOIN AgLibraryFile fi ON i.rootFile = fi.id_local LEFT JOIN AgHarvestedExifMetadata em on i.id_local = em.image  WHERE em.hasGps == 0
           * Count results: 1880
           * Photo results (first 2 photos on 1880) :
             name                 |            datecapt
             =============================================
             103-0332_IMG.JPG     | 2002-03-07T17:53:03
             112-1248.jpg         | 2002-04-14T16:57:08




### Complete help

        usage: lrsmart.py [-h] [-b LRCAT] [-f] [-l] [--raw] [-d] [-s] [-c] [-r]
                        [-n MAX_LINES] [-C COLUMNS] [-N] [--raw_print] [--log LOG]
                        [smart_name [smart_name ...]]

        Execute smart collections from an Adobe Lightroom catalog or from an exported file
        Supported criteria are : all, aperture, aspectRatio, camera, captureTime,
          collection, colorMode, creator, exif, fileFormat, filename, flashFired,
          focalLength, hasAdjustments, hasGPSData, heightCropped, iptc, isoSpeedRating,
          keywords, labelColor, labelText, lens, metadata, metadataStatus, rating,
          shutterSpeed, touchTime, treatment, widthCropped

        positional arguments:
        smart_name            Name of smart(s) collection

        optional arguments:
        -h, --help            show this help message and exit
        -b LRCAT, --lrcat LRCAT
                                Lightroom catalog file for database query
                                (default:"I:\Lightroom\La Totale\La Totale.lrcat")
        -f, --file            positional parameters are files, not smart collection
                                names
        -l, --list            List smart collections of name "smart_name" from
                                Lightroom catalog. "smart_name" can include jokers
                                "%". Leave empty for list all collections
        --raw                 Display description of smart collection as stored
        -d, --dict            Display description of smart collection as python
                                dictionnary
        -s, --sql             Display SQL query
        -c, --count           Display count of results
        -r, --results         Display query results
        -n MAX_LINES, --max_lines MAX_LINES
                                Max number of results to display
        -C COLUMNS, --columns COLUMNS
                                Columns names to print (default:"uuid,name"). For
                                column names, see help of lrselect.py
        -N, --no_header       don't print header (columns names)
        --raw_print           print raw value (for speed, aperture columns)
        --log LOG             log to file

