import wchartype


def is_multi_byte( chars ):
    for char in chars:
        try:
            char = unicode( char )
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
