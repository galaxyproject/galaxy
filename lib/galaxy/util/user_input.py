"""
Rules for user account fields that depend on nothing but the value.

galaxy.schema validates API payloads with these and the managers apply them for
every other caller, so a field has one rule however its value arrives. As in
galaxy.security.validate_user_input, the validate_* functions return a
user-facing message, or "" for a valid value, and never echo the input.
"""

import re
import unicodedata

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

# Display name validity parameters
#
# Display names are free-form and may be in any script, so the rule rejects
# what cannot be seen rather than listing what may be used. Bidirectional
# formatting characters are the main reason the check exists: U+202E and
# friends let a name render as text entirely unrelated to what is stored, which
# makes a display name a viable impersonation vector wherever it is shown. The
# other control, format, line and paragraph separator, private-use, surrogate
# and unassigned code points go with them, as do the letters and marks that
# render as blank space.
#
# The zero-width joiner and non-joiner are the exception. Persian, the Indic
# scripts and emoji sequences need them, so they are allowed where they can do
# that job: between two visible characters.
DISPLAY_NAME_MAX_LEN = 255
DISPLAY_NAME_REJECTED_CATEGORIES = frozenset({"Cc", "Cf", "Cn", "Co", "Cs", "Zl", "Zp"})
DISPLAY_NAME_BLANK_CHARACTERS = frozenset("\u034f\u115f\u1160\u17b4\u17b5\u2800\u3164\uffa0")
DISPLAY_NAME_JOINERS = frozenset("\u200c\u200d")


def canonicalize_email(email: str | None) -> str:
    """Return the form of an email address that is validated and stored.

    Surrounding whitespace is stripped; None becomes "", which validate_email_str reports as missing.
    """
    return (email or "").strip()


def is_valid_email_str(email: str | None) -> bool:
    """Validates a string containing an email address and returns a boolean result."""
    return validate_email_str(email) == ""


def validate_email_str(email: str | None) -> str:
    """Validates a string containing an email address."""
    if not email:
        return "No email address was provided."
    if not (VALID_EMAIL_RE.match(email)):
        return "The format of the email address is not correct."
    elif len(email) > EMAIL_MAX_LEN:
        return f"Email address cannot be more than {EMAIL_MAX_LEN} characters in length."
    return ""


def canonicalize_display_name(display_name: str | None) -> str | None:
    """Return the form of a display name that is validated and stored.

    The name is NFC-normalized so that composed and decomposed spellings are
    stored (and measured) alike, and surrounding whitespace is stripped rather
    than rejected. A name that is empty once stripped becomes None, which
    clears the field - an invisible difference is a poor reason to fail a save.
    """
    return unicodedata.normalize("NFC", display_name or "").strip() or None


def validate_display_name_str(display_name: str | None) -> str:
    """Validates a string containing a user's display name.

    Callers are expected to have passed the value through
    canonicalize_display_name; an empty display name means "unset" and is
    accepted here so that clearing the field is not an error.
    """
    if not display_name:
        return ""
    if len(display_name) > DISPLAY_NAME_MAX_LEN:
        return f"Display name cannot be more than {DISPLAY_NAME_MAX_LEN} characters in length."
    last = len(display_name) - 1
    for i, char in enumerate(display_name):
        if char in DISPLAY_NAME_JOINERS:
            if not (0 < i < last and _is_joinable(display_name[i - 1]) and _is_joinable(display_name[i + 1])):
                return "Display name cannot contain control, formatting or invisible characters."
        elif unicodedata.category(char) in DISPLAY_NAME_REJECTED_CATEGORIES or char in DISPLAY_NAME_BLANK_CHARACTERS:
            return "Display name cannot contain control, formatting or invisible characters."
    if not any(_is_visible(char) for char in display_name):
        return "Display name must contain at least one visible character."
    return ""


def _is_visible(char: str) -> bool:
    # Letters, numbers, punctuation and symbols; not marks, separators or other.
    return unicodedata.category(char)[0] in "LNPS" and char not in DISPLAY_NAME_BLANK_CHARACTERS


def _is_joinable(char: str) -> bool:
    # A joiner may follow or precede a combining mark (a virama, an emoji
    # variation selector) but not a space, a format character or another joiner.
    return unicodedata.category(char)[0] not in "CZ" and char not in DISPLAY_NAME_BLANK_CHARACTERS
