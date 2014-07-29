import logging
import re

log = logging.getLogger( __name__ )

VALID_PUBLICNAME_RE = re.compile( "^[a-z0-9\-]+$" )
VALID_PUBLICNAME_SUB = re.compile( "[^a-z0-9\-]" )
#  Basic regular expression to check email validity.
VALID_EMAIL_RE = re.compile( "[^@]+@[^@]+\.[^@]+" )
FILL_CHAR = '-'


def validate_email( trans, email, user=None, check_dup=True ):
    """
    Validates the email format, also checks whether the domain is blacklisted in the disposable domains configuration.
    """
    message = ''
    if user and user.email == email:
        return message
    if not( VALID_EMAIL_RE.match( email ) ):
        message = "Please enter your real email address."
    elif len( email ) > 255:
        message = "Email address exceeds maximum allowable length."
    elif check_dup and trans.sa_session.query( trans.app.model.User ).filter_by( email=email ).first():
        message = "User with that email already exists."
    #  If the blacklist is not empty filter out the disposable domains.
    elif trans.app.config.blacklist_content is not None:
        if email.split('@')[1] in trans.app.config.blacklist_content:
            message = "Please enter your permanent email address."
    return message


def validate_publicname( trans, publicname, user=None ):
    # User names must be at least four characters in length and contain only lower-case
    # letters, numbers, and the '-' character.
    if user and user.username == publicname:
        return ''
    if trans.webapp.name == 'tool_shed':
        if len( publicname ) < 3:
            return "Public name must be at least 3 characters in length"
    else:
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
    # TODO: Enhance to allow generation of semi-random publicnnames e.g., when valid but taken
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
