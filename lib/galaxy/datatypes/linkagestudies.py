"""
LinkageStudies datatypes

Defines input formats for Alohomora, including pre-Makeped LINKAGE formats and format-variants:
http://www.medgen.de/ped/imex4.html

Also defines seperate output formats ({Allegro, Genehunter, Merlin, Simwalk, Swiftlink}), of:
  - LOD scores generated via linkage
  - Haplotypes generated via haplotype reconstruction
  - Descent data generated via haplotype reconstruction
"""

import logging
import os
import re
import sys
#from cgi import escape

#from six.moves.urllib.parse import quote_plus

from galaxy.datatypes import metadata
from galaxy.datatypes.metadata import MetadataElement
#from galaxy.datatypes.tabular import Tabular
from galaxy.datatypes.text import Text
#from galaxy.util import nice_size
#from galaxy.web import url_for

verbose = True

class Genotypes(Text):
    """
    Column of Marker IDs followed by sample genotypes
    """
    def __init__(self):
        # blah

    def set_meta(self):
        # blah

    def sniff(self):
        # blah

    def get_mime(self):
        #blah


### Alohomora input classes
class MarkerMap(Text)
class MAF(Text)
class Pedigree(Text)
#
### Linkage input classes
class RecFreqs(Text)
class PedigreeGT(Text)
class Map(MarkerMap)      # <-- literally truncated
#
### Linkage output classes
class AllegroHaplo(Text)
class AllegroDescent(Text)
class AllegroLOD(Text)
#
class GHMHaplo(Text)
class GHMDescent(Text)
class GHMLOD(Text)
#
class MerlinHaplo(Text)
class MerlinDescent(Text)
class MerlinLOD(Text)
#
class Mega2Descent(Text)
class Mega2LOD(Text)
#
class SwiftLOD(Text)  # <- May be the same format as genehuner
