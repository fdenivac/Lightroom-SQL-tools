
import os
from datetime import datetime, timedelta, timezone
import pytz
from tzlocal import get_localzone


# date reference of lightroom (at least for timestamp of photos modified)
DATE_REF = datetime(2001, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

# unix timestamp for LR date reference (2001,1,1,0,0,0)
TIMESTAMP_LRBASE = 978307200


# work around on cygwin problem :
#
env_tz = os.getenv("TZ")    # exists on cygwin and cause exception on tzlocal.get_localzone()
localzone = pytz.timezone(env_tz) if env_tz else get_localzone()
