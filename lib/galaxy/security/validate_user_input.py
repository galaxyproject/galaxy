import re

VALID_USERNAME_RE = re.compile( "^[a-z0-9\-]+$" )

def validate_email( trans, email, user=None ):
    message = ''
    if user and user.email == email:
        return message 
    if len( email ) == 0 or "@" not in email or "." not in email:
        message = "Enter a real email address"
    elif len( email ) > 255:
        message = "Email address exceeds maximum allowable length"
    elif trans.sa_session.query( trans.app.model.User ).filter_by( email=email ).first():
        message = "User with that email already exists"
    return message

def validate_username( trans, username, user=None ):
    # User names must be at least four characters in length and contain only lower-case
    # letters, numbers, and the '-' character.
    if username in [ 'None', None, '' ]:
        return ''
    if user and user.username == username:
        return ''
    if len( username ) < 4:
        return "User name must be at least 4 characters in length"
    if len( username ) > 255:
        return "User name cannot be more than 255 characters in length"
    if not( VALID_USERNAME_RE.match( username ) ):
        return "User name must contain only lower-case letters, numbers and '-'"
    if trans.sa_session.query( trans.app.model.User ).filter_by( username=username ).first():
        return "This user name is not available"
    return ''

def validate_password( trans, password, confirm ):
    if len( password ) < 6:
        return "Use a password of at least 6 characters"
    elif password != confirm:
        return "Passwords do not match"
    return ''