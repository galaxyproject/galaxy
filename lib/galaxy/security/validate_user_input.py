"""
Utilities for validating inputs related to user objects.

The validate_* methods in this file return simple messages that do not contain
user inputs - so these methods do not need to be escaped.
"""

import logging
import re
from typing import Optional

import dns.resolver
from dns.exception import DNSException
from sqlalchemy import (
    func,
    select,
)
from typing_extensions import LiteralString

from galaxy.objectstore import ObjectStore

log = logging.getLogger(__name__)

# Email validity parameters
#
# Many words (and regexes) have been written about validating email addresses and there is no perfect answer on how it
# should be done. We choose to use the HTML5 spec (and corresponding regex) that engages in a "willful violation" of RFC
# 5322 to provide a reasonably good validation. Additionally, we allow Unicode characters in both the user and domain
# parts of the email by using re's '\w' character. Note that \w includes "word" characters but appears to exclude emoji
# characters, which should in fact be valid.
#
# https://html.spec.whatwg.org/multipage/input.html#e-mail-state-(type%3Demail)
VALID_EMAIL_RE = re.compile(r"^[\w.!#$%&'*+\/=?^_`{|}~-]+@[\w](?:[\w-]{0,61}[\w])?(?:\.[\w](?:[\w-]{0,61}[\w])?)*$")
EMAIL_MAX_LEN = 255

# Public name validity parameters
PUBLICNAME_MAX_LEN = 255
VALID_PUBLICNAME_RE = re.compile(r"^[a-z0-9._\-]+$")
VALID_PUBLICNAME_SUB = re.compile(r"[^a-z0-9._\-]")
FILL_CHAR = "-"

# Password validity parameters
PASSWORD_MIN_LEN = 6


def validate_email_str(email):
    """Validates a string containing an email address."""
    if not email:
        return "No email address was provided."
    if not (VALID_EMAIL_RE.match(email)):
        return "The format of the email address is not correct."
    elif len(email) > EMAIL_MAX_LEN:
        return "Email address cannot be more than %d characters in length." % EMAIL_MAX_LEN
    return ""


def validate_password_str(password):
    if not password or len(password) < PASSWORD_MIN_LEN:
        return "Use a password of at least %d characters." % PASSWORD_MIN_LEN
    return ""


def validate_publicname_str(publicname):
    """Validates a string containing a public username."""
    if not publicname:
        return "Public name cannot be empty"
    if len(publicname) > PUBLICNAME_MAX_LEN:
        return "Public name cannot be more than %d characters in length." % (PUBLICNAME_MAX_LEN)
    if not (VALID_PUBLICNAME_RE.match(publicname)):
        return "Public name must contain only lower-case letters, numbers, '.', '_' and '-'."
    return ""


def validate_email(trans, email, user=None, check_dup=True, allow_empty=False, validate_domain=False):
    """
    Validates the email format, also checks whether the domain is blocklisted in the disposable domains configuration.
    """
    if (user and user.email == email) or (email == "" and allow_empty):
        return ""
    message = validate_email_str(email)
    if not message and validate_domain:
        domain = extract_domain(email)
        message = validate_email_domain_name(domain)

    stmt = select(trans.app.model.User).filter(func.lower(trans.app.model.User.email) == email.lower()).limit(1)
    if not message and check_dup and trans.sa_session.scalars(stmt).first():
        message = f"User with email '{email}' already exists."

    if not message:
        # If the allowlist is not empty filter out any domain not in the list and ignore blocklist.
        if trans.app.config.email_domain_allowlist_content is not None:
            domain = extract_domain(email)
            if domain not in trans.app.config.email_domain_allowlist_content:
                message = "Please enter an allowed domain email address for this server."
        # If the blocklist is not empty filter out the disposable domains.
        elif trans.app.config.email_domain_blocklist_content is not None:
            domain = extract_domain(email, base_only=True)
            if domain in trans.app.config.email_domain_blocklist_content:
                message = "Please enter your permanent email address."

    return message


def validate_email_domain_name(domain: str) -> LiteralString:
    message = ""
    try:
        dns.resolver.resolve(domain, "MX")
    except DNSException:
        try:
            # Per RFC 5321, try to fall back to the A record (implicit MX) for
            # the domain, see https://www.rfc-editor.org/rfc/rfc5321#section-5.1
            dns.resolver.resolve(domain, "A")
        except DNSException:
            message = "The email domain cannot be resolved."
    return message


def extract_domain(email, base_only=False):
    domain = email.rsplit("@", 1)[-1]
    parts = domain.split(".")
    if len(parts) > 2 and base_only:
        return (".").join(parts[-2:])
    return domain


def validate_publicname(trans, publicname, user=None):
    """
    Check that publicname respects the minimum and maximum string length, the
    allowed characters, and that the username is not taken already.
    """
    if user and user.username == publicname:
        return ""
    if message := validate_publicname_str(publicname):
        return message

    stmt = select(trans.app.model.User).filter_by(username=publicname).limit(1)
    if trans.sa_session.scalars(stmt).first():
        return "Public name is taken; please choose another."
    return ""


def transform_publicname(publicname):
    """
    Transform publicname to respect the minimum and maximum string length, and
    the allowed characters.
    FILL_CHAR is used to extend or replace characters.
    """
    # TODO: Enhance to allow generation of semi-random publicnnames e.g., when valid but taken
    if not publicname:
        raise ValueError("Public name cannot be empty")
    publicname = publicname.lower()
    publicname = re.sub(VALID_PUBLICNAME_SUB, FILL_CHAR, publicname)
    publicname = publicname[:PUBLICNAME_MAX_LEN]
    return publicname


def validate_password(trans, password, confirm):
    if password != confirm:
        return "Passwords do not match."
    return validate_password_str(password)


def validate_preferred_object_store_id(
    trans, object_store: ObjectStore, preferred_object_store_id: Optional[str]
) -> str:
    return object_store.validate_selected_object_store_id(trans.user, preferred_object_store_id) or ""
