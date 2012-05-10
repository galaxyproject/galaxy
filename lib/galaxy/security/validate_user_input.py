import re

VALID_PUBLICNAME_RE = re.compile( "^[a-z0-9\-]+$" )
VALID_PUBLICNAME_SUB = re.compile( "[^a-z0-9\-]" )
FILL_CHAR = '-'

def validate_email( trans, email, user=None, check_dup=True ):
    message = ''
    if user and user.email == email:
        return message 
    if len( email ) == 0 or "@" not in email or "." not in email:
        message = "Enter a real email address"
    elif len( email ) > 255:
        message = "Email address exceeds maximum allowable length"
    elif check_dup and trans.sa_session.query( trans.app.model.User ).filter_by( email=email ).first():
        message = "User with that email already exists"
    return message

def validate_publicname( trans, publicname, user=None ):
    # User names must be at least four characters in length and contain only lower-case
    # letters, numbers, and the '-' character.
    if publicname in [ 'None', None, '' ]:
        return ''
    if user and user.username == publicname:
        return ''
    if len( publicname ) < 4:
        return "Public name must be at least 4 characters in length"
    if len( publicname ) > 255:
        return "Public name cannot be more than 255 characters in length"
    if not( VALID_PUBLICNAME_RE.match( publicname ) ):
        return "Public name must contain only lower-case letters, numbers and '-'"
    if trans.sa_session.query( trans.app.model.User ).filter_by( username=publicname ).first():
        return "Public name is taken; please choose another"
    return ''

def transform_publicname( trans, publicname, user=None ):
    # User names must be at least four characters in length and contain only lower-case
    # letters, numbers, and the '-' character.
    #TODO: Enhance to allow generation of semi-random publicnnames e.g., when valid but taken
    if user and user.username == publicname:
        return publicname
    elif publicname not in [ 'None', None, '' ]:
        publicname = publicname.lower()
        publicname = re.sub( VALID_PUBLICNAME_SUB, FILL_CHAR, publicname )
        publicname = publicname.ljust( 4, FILL_CHAR )[:255]
        if not trans.sa_session.query( trans.app.model.User ).filter_by( username=publicname ).first():
            return publicname
    return ''

def validate_password( trans, password, confirm ):
    if len( password ) < 6:
        return "Use a password of at least 6 characters"
    elif password != confirm:
        return "Passwords do not match"
    return ''