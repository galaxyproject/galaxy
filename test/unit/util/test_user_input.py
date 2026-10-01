import pytest

from galaxy.util.user_input import (
    canonicalize_display_name,
    validate_display_name_str,
    validate_email_str,
    validate_publicname_str,
)


def test_validate_username():
    assert validate_publicname_str("testuser") == ""
    assert validate_publicname_str("test.user") == ""
    assert validate_publicname_str("test-user") == ""
    assert validate_publicname_str("test@user") != ""
    assert validate_publicname_str("test user") != ""


@pytest.mark.parametrize(
    "display_name",
    [
        pytest.param("Ada Lovelace", id="latin"),
        pytest.param("Zoë Müller", id="latin composed"),
        pytest.param("Zoe\u0308 Mu\u0308ller", id="latin decomposed"),
        pytest.param("O'Brien-Smith", id="apostrophe and hyphen"),
        pytest.param("Αλέξανδρος", id="greek"),
        pytest.param("Пётр Ильич", id="cyrillic"),
        pytest.param("محمد", id="arabic"),
        pytest.param("\u0645\u06cc\u200c\u062e\u0648\u0627\u0647\u0645", id="persian with zero width non-joiner"),
        pytest.param("张伟", id="chinese"),
        pytest.param("山田\u3000太郎", id="japanese with ideographic space"),
        pytest.param("\u0915\u094d\u200d\u0937", id="devanagari with zero width joiner"),
        pytest.param("\u0915\u094d\u200c\u0937", id="devanagari with zero width non-joiner"),
        pytest.param("Ada 🧬", id="emoji"),
        pytest.param("\U0001f469\u200d\U0001f4bb", id="emoji zero width joiner sequence"),
        pytest.param("\U0001f3f3\ufe0f\u200d\U0001f308", id="emoji sequence with variation selector"),
        pytest.param("admin", id="reserved word"),
        pytest.param("", id="empty"),
        pytest.param(None, id="none"),
    ],
)
def test_validate_display_name_str_accepts(display_name):
    assert validate_display_name_str(display_name) == ""


@pytest.mark.parametrize(
    "display_name",
    [
        pytest.param("Ada\nLovelace", id="line feed"),
        pytest.param("Ada\x7fLovelace", id="delete"),
        pytest.param("Ada\u0085Lovelace", id="next line"),
        pytest.param("Ada\u009fLovelace", id="c1 control"),
        pytest.param("Ada\u00adLovelace", id="soft hyphen"),
        pytest.param("Ada\u034fLovelace", id="combining grapheme joiner"),
        pytest.param("Ada\u061cLovelace", id="arabic letter mark"),
        pytest.param("Ada\u115fLovelace", id="hangul choseong filler"),
        pytest.param("Ada\u1160Lovelace", id="hangul jungseong filler"),
        pytest.param("Ada\u180eLovelace", id="mongolian vowel separator"),
        pytest.param("Ada\u200bLovelace", id="zero width space"),
        pytest.param("Ada\u2028Lovelace", id="line separator"),
        pytest.param("Ada\u2029Lovelace", id="paragraph separator"),
        pytest.param("Ada\u202eLovelace", id="right-to-left override"),
        pytest.param("Ada\u2060Lovelace", id="word joiner"),
        pytest.param("Ada\u2066Lovelace", id="left-to-right isolate"),
        pytest.param("Ada\u2800Lovelace", id="braille pattern blank"),
        pytest.param("Ada\u3164Lovelace", id="hangul filler"),
        pytest.param("Ada\ue000Lovelace", id="private use"),
        pytest.param("Ada\ud800Lovelace", id="lone surrogate"),
        pytest.param("Ada\ufeffLovelace", id="zero width no-break space"),
        pytest.param("Ada\uffa0Lovelace", id="halfwidth hangul filler"),
        pytest.param("Ada\U000e0000Lovelace", id="unassigned tag block code point"),
        pytest.param("Ada\U000e0001Lovelace", id="language tag"),
        pytest.param("Ada\U000e0041Lovelace", id="tag latin capital letter a"),
        pytest.param("Ada\U000e007fLovelace", id="cancel tag"),
        pytest.param("Ada\U0010ffffLovelace", id="noncharacter"),
        pytest.param("\u3164", id="only hangul filler"),
        pytest.param("\u3164\u3164", id="only hangul fillers"),
        pytest.param("\u2800", id="only braille pattern blank"),
        pytest.param("\u200dAda", id="leading zero width joiner"),
        pytest.param("Ada\u200d", id="trailing zero width joiner"),
        pytest.param("\u200cAda", id="leading zero width non-joiner"),
        pytest.param("Ada\u200c", id="trailing zero width non-joiner"),
        pytest.param("Ada\u200d\u200dLovelace", id="doubled zero width joiner"),
        pytest.param("Ada\u200c\u200dLovelace", id="adjacent joiners"),
        pytest.param("Ada \u200dLovelace", id="zero width joiner after space"),
        pytest.param("Ada\u200d Lovelace", id="zero width joiner before space"),
        pytest.param("Ada\u200d\u2060Lovelace", id="zero width joiner before word joiner"),
        pytest.param("\u200d", id="only zero width joiner"),
        pytest.param("\u0301", id="only combining mark"),
        pytest.param("\ufe0f", id="only variation selector"),
        pytest.param("   ", id="only spaces"),
    ],
)
def test_validate_display_name_str_rejects(display_name):
    assert validate_display_name_str(display_name) != ""


def test_validate_display_name_str_length():
    assert validate_display_name_str("N" * 255) == ""
    assert validate_display_name_str("N" * 256) != ""


@pytest.mark.parametrize(
    "display_name, canonical",
    [
        ("Ada Lovelace", "Ada Lovelace"),
        ("  Ada Lovelace  ", "Ada Lovelace"),
        ("\u3000山田\u3000太郎\u3000", "山田\u3000太郎"),
        ("Zoe\u0308 Mu\u0308ller", "Zoë Müller"),
        ("Zoë Müller", "Zoë Müller"),
        ("", None),
        ("   ", None),
        (" " * 256, None),
        (None, None),
    ],
)
def test_canonicalize_display_name(display_name, canonical):
    assert canonicalize_display_name(display_name) == canonical


def test_validate_email_str():
    assert validate_email_str("test@foo.com") == ""
    assert validate_email_str("test-dot.user@foo.com") == ""
    assert validate_email_str("test-plus+user@foo.com") == ""
    assert validate_email_str("test-ünicode-user@foo.com") == ""
    assert validate_email_str("test@ünicode-domain.com") == ""
    assert validate_email_str("test-missing-domain@") != ""
    assert validate_email_str("@test-missing-local") != ""
    assert validate_email_str("test-invalid-local\\character@foo.com") != ""
    assert validate_email_str("test@invalid-domain-character!com") != ""
    assert validate_email_str("test@newlines.in.address.are.invalid\n\n.com") != ""
    assert validate_email_str('"i-like-to-break-email-valid@tors"@foo.com') != ""
    too_long_email = "N" * 255 + "@foo.com"
    assert validate_email_str(too_long_email) != ""
