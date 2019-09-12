"""
Utilities for validating inputs related to user objects.

The validate_* methods in this file return simple messages that do not contain
user inputs - so these methods do not need to be escaped.
"""
import logging
import re

log = logging.getLogger(__name__)

# Email validity parameters
VALID_EMAIL_RE = re.compile(r"[^@]+@[^@]+\.[^@]+")
EMAIL_MAX_LEN = 255

# Public name validity parameters
PUBLICNAME_MIN_LEN = 3
PUBLICNAME_MAX_LEN = 255
VALID_PUBLICNAME_RE = re.compile(r"^[a-z0-9._\-]+$")
VALID_PUBLICNAME_SUB = re.compile(r"[^a-z0-9._\-]")
FILL_CHAR = '-'

# Password validity parameters
PASSWORD_MIN_LEN = 6


def validate_email(trans, email, user=None, check_dup=True, allow_empty=False):
    """
    Validates the email format, also checks whether the domain is blacklisted in the disposable domains configuration.
    """
    message = ''
    if (user and user.email == email) or (email == "" and allow_empty):
        return message
    if not(VALID_EMAIL_RE.match(email)):
        message = "The format of the email address is not correct."
    elif len(email) > EMAIL_MAX_LEN:
        message = "Email address cannot be more than %d characters in length." % EMAIL_MAX_LEN
    elif check_dup and trans.sa_session.query(trans.app.model.User).filter_by(email=email).first():
        message = "User with that email already exists."
    #  If the blacklist is not empty filter out the disposable domains.
    elif trans.app.config.blacklist_content is not None:
        domain = email.split('@')[1]
        if len(domain.split('.')) > 2:
            domain = ('.').join(domain.split('.')[-2:])
        if domain in trans.app.config.blacklist_content:
            message = "Please enter your permanent email address."
    return message


def validate_publicname(trans, publicname, user=None):
    # User names must be at least three characters in length and contain only lower-case
    # letters, numbers, and the '-' character.
    if user and user.username == publicname:
        return ''
    if len(publicname) < PUBLICNAME_MIN_LEN:
        return "Public name must be at least %d characters in length." % (PUBLICNAME_MIN_LEN)
    if len(publicname) > PUBLICNAME_MAX_LEN:
        return "Public name cannot be more than %d characters in length." % (PUBLICNAME_MAX_LEN)
    if not(VALID_PUBLICNAME_RE.match(publicname)):
        return "Public name must contain only lower-case letters, numbers, '.', '_' and '-'."
    if trans.sa_session.query(trans.app.model.User).filter_by(username=publicname).first():
        return "Public name is taken; please choose another."
    return ''


def transform_publicname(trans, publicname, user=None):
    # User names must be at least four characters in length and contain only lower-case
    # letters, numbers, and the '-' character.
    # TODO: Enhance to allow generation of semi-random publicnnames e.g., when valid but taken
    if user and user.username == publicname:
        return publicname
    elif publicname not in ['None', None, '']:
        publicname = publicname.lower()
        publicname = re.sub(VALID_PUBLICNAME_SUB, FILL_CHAR, publicname)
        publicname = publicname.ljust(PUBLICNAME_MIN_LEN + 1, FILL_CHAR)[:PUBLICNAME_MAX_LEN]
        if not trans.sa_session.query(trans.app.model.User).filter_by(username=publicname).first():
            return publicname
    return ''


def validate_password(trans, password, confirm):
    if len(password) < PASSWORD_MIN_LEN:
        return "Use a password of at least %d characters." % PASSWORD_MIN_LEN
    elif password != confirm:
        return "Passwords do not match."
    return ""
