from datetime import datetime

# NOTE REGARDING TIMESTAMPS:
#   It is currently difficult to have the timestamps calculated by the
#   database in a portable way, so we're doing it in the client. This
#   also saves us from needing to postfetch on postgres. HOWEVER: it
#   relies on the client's clock being set correctly, so if clustering
#   web servers, use a time server to ensure synchronization

# Return the current time in UTC without any timezone information
now = datetime.utcnow

__all__ = ('now', )
