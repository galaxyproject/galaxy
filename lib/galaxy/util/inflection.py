#!/usr/bin/env python

# Copyright (c) 2006 Bermi Ferrer Martinez
#
# bermi a-t bermilabs - com
# See the end of this file for the free software, open source license (BSD-style).
#
# Modified by the Galaxy team.

import re


class Inflector:
    """
    Inflector for pluralizing and singularizing English nouns.
    """

    # This is a small subset of words that either have the same singular and plural form, or have no singular form
    NONCHANGING_WORDS = {
        "equipment",
        "information",
        "rice",
        "money",
        "species",
        "series",
        "sheep",
        "sms",
    }

    IRREGULAR_WORDS = {
        "person": "people",
        "man": "men",
        "child": "children",
        "sex": "sexes",
        "move": "moves",
        "octopus": "octopi",
    }

    PLURALIZE_RULES = (
        ("(?i)(quiz)$", "\\1zes"),
        ("(?i)^(ox)$", "\\1en"),
        ("(?i)([m|l])ouse$", "\\1ice"),
        ("(?i)(matr|vert|ind)ix|ex$", "\\1ices"),
        ("(?i)(x|ch|ss|sh)$", "\\1es"),
        ("(?i)([^aeiouy]|qu)ies$", "\\1y"),
        ("(?i)([^aeiouy]|qu)y$", "\\1ies"),
        ("(?i)(hive)$", "\\1s"),
        ("(?i)(?:([^f])fe|([lr])f)$", "\\1\\2ves"),
        ("(?i)sis$", "ses"),
        ("(?i)([ti])um$", "\\1a"),
        ("(?i)(buffal|tomat)o$", "\\1oes"),
        ("(?i)(bu)s$", "\\1ses"),
        ("(?i)(alias|status|virus)", "\\1es"),
        ("(?i)(ax|test)is$", "\\1es"),
        ("(?i)s$", "s"),
        ("(?i)$", "s"),
    )

    SINGULARIZE_RULES = (
        ("(?i)(quiz)zes$", "\\1"),
        ("(?i)(matr)ices$", "\\1ix"),
        ("(?i)(vert|ind)ices$", "\\1ex"),
        ("(?i)^(ox)en", "\\1"),
        ("(?i)(alias|status|virus)es$", "\\1"),
        ("(?i)(cris|ax|test)es$", "\\1is"),
        ("(?i)(shoe)s$", "\\1"),
        ("(?i)(o)es$", "\\1"),
        ("(?i)(bus)es$", "\\1"),
        ("(?i)([m|l])ice$", "\\1ouse"),
        ("(?i)(x|ch|ss|sh)es$", "\\1"),
        ("(?i)(m)ovies$", "\\1ovie"),
        ("(?i)(s)eries$", "\\1eries"),
        ("(?i)([^aeiouy]|qu)ies$", "\\1y"),
        ("(?i)([lr])ves$", "\\1f"),
        ("(?i)(tive)s$", "\\1"),
        ("(?i)(hive)s$", "\\1"),
        ("(?i)([^f])ves$", "\\1fe"),
        ("(?i)(^analy)ses$", "\\1sis"),
        ("(?i)((a)naly|(b)a|(d)iagno|(p)arenthe|(p)rogno|(s)ynop|(t)he)ses$", "\\1\\2sis"),
        ("(?i)([ti])a$", "\\1um"),
        ("(?i)(n)ews$", "\\1ews"),
        ("(?i)s$", ""),
    )

    def pluralize(self, word):
        """Pluralizes nouns."""
        return self._transform(self.PLURALIZE_RULES, word)

    def singularize(self, word):
        """Singularizes nouns."""
        return self._transform(self.SINGULARIZE_RULES, word, pluralize=False)

    def cond_plural(self, number_of_records, word):
        """Returns the plural form of a word if first parameter is greater than 1"""
        if number_of_records != 1:
            return self.pluralize(word)
        return word

    def _transform(self, rules, word, pluralize=True):
        return (
            self._handle_nonchanging(word)
            or self._handle_irregular(word, pluralize=pluralize)
            or self._apply_rules(rules, word)
            or word
        )

    def _handle_nonchanging(self, word):
        lower_cased_word = word.lower()
        # Check if word is an item or the suffix of any item in NONCHANGING_WORDS
        for nonchanging_word in self.NONCHANGING_WORDS:
            if lower_cased_word.endswith(nonchanging_word):
                return word

    def _handle_irregular(self, word, pluralize=True):
        for form_a, form_b in self.IRREGULAR_WORDS.items():
            if not pluralize:
                form_a, form_b = form_b, form_a
            match = re.search(f"({form_a})$", word, re.IGNORECASE)
            if match:
                return re.sub(f"(?i){form_a}$", match.expand("\\1")[0] + form_b[1:], word)

    def _apply_rules(self, rules, word):
        for pattern, replacement in rules:
            if re.search(pattern, word):
                return re.sub(pattern, replacement, word)


# Copyright (c) 2006 Bermi Ferrer Martinez
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software to deal in this software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of this software, and to permit
# persons to whom this software is furnished to do so, subject to the following
# condition:
#
# THIS SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THIS SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THIS SOFTWARE.
