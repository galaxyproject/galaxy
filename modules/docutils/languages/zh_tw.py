# Author: Joe YS Jaw
# Contact: joeysj@users.sourceforge.net
# Revision: $Revision: 2608 $
# Date: $Date: 2004-09-13 21:09:56 +0200 (Mon, 13 Sep 2004) $
# Copyright: This module has been placed in the public domain.

# New language mappings are welcome.  Before doing a new translation, please
# read <http://docutils.sf.net/docs/howto/i18n.html>.  Two files must be
# translated for each language: one in docutils/languages, the other in
# docutils/parsers/rst/languages.

"""
Traditional Chinese language mappings for language-dependent features of Docutils.
"""

__docformat__ = 'reStructuredText'

labels = {
      # fixed: language-dependent
      'author': u'\u4f5c\u8005', # 'Author',
      'authors': u'\u4f5c\u8005\u7fa4', # 'Authors',
      'organization': u'\u7d44\u7e54', # 'Organization',
      'address': u'\u5730\u5740', # 'Address',
      'contact': u'\u9023\u7d61', # 'Contact',
      'version': u'\u7248\u672c', # 'Version',
      'revision': u'\u4fee\u8a02', # 'Revision',
      'status': u'\u72c0\u614b', # 'Status',
      'date': u'\u65e5\u671f', # 'Date',
      'copyright': u'\u7248\u6b0a', # 'Copyright',
      'dedication': u'\u984c\u737b', # 'Dedication',
      'abstract': u'\u6458\u8981', # 'Abstract',
      'attention': u'\u6ce8\u610f\uff01', # 'Attention!',
      'caution': u'\u5c0f\u5fc3\uff01', # 'Caution!',
      'danger': u'\uff01\u5371\u96aa\uff01', # '!DANGER!',
      'error': u'\u932f\u8aa4', # 'Error',
      'hint': u'\u63d0\u793a', # 'Hint',
      'important': u'\u91cd\u8981', # 'Important',
      'note': u'\u8a3b\u89e3', # 'Note',
      'tip': u'\u79d8\u8a23', # 'Tip',
      'warning': u'\u8b66\u544a', # 'Warning',
      'contents': u'\u76ee\u9304' # 'Contents'
} 
"""Mapping of node class name to label text."""

bibliographic_fields = {
      # language-dependent: fixed
      'author': 'author',
      'authors': 'authors',
      'organization': 'organization',
      'address': 'address',
      'contact': 'contact',
      'version': 'version',
      'revision': 'revision',
      'status': 'status',
      'date': 'date',
      'copyright': 'copyright',
      'dedication': 'dedication',
      'abstract': 'abstract'}
"""Traditional Chinese to canonical name mapping for bibliographic fields."""

author_separators = [u'\uff1b', u'\uff0c', u'\u3001',
                     ';', ',']
"""List of separator strings for the 'Authors' bibliographic field. Tried in
order."""
