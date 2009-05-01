from webhelpers import *

from datetime import datetime

def time_ago( x ):
    return date.distance_of_time_in_words( x, datetime.utcnow() )
    
def iff( a, b, c ):
    if a:
        return b
    else:
        return c