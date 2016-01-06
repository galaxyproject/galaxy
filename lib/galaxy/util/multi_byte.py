try:
    import wchartype
except ImportError:
    wchartype = None

from six import text_type


def is_multi_byte( chars ):
    if wchartype is None:
        message = "Attempted to use galaxy.util.multi_byte but dependency wchartype is unavailable."
        raise Exception(message)
    for char in chars:
        try:
            char = text_type( char )
        except UnicodeDecodeError:
            # Probably binary
            return False
        if ( wchartype.is_asian( char ) or wchartype.is_full_width( char ) or
                wchartype.is_kanji( char ) or wchartype.is_hiragana( char ) or
                wchartype.is_katakana( char ) or wchartype.is_half_katakana( char ) or
                wchartype.is_hangul( char ) or wchartype.is_full_digit( char ) or
                wchartype.is_full_letter( char )):
            return True
    return False
