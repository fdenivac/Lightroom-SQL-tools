import os
import pytz
from tzlocal import get_localzone


# work around on cygwin problem :
#
env_tz = os.getenv(
    "TZ"
)  # exists on cygwin and cause exception on tzlocal.get_localzone()
localzone = pytz.timezone(env_tz) if env_tz else get_localzone()
utczone = pytz.utc

VERSION = "2025-12-12"
