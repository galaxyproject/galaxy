"""
Qualityscore class
"""
import logging

from . import (
    data,
    sniff
)

log = logging.getLogger(__name__)


class QualityScore(data.Text):
    """
    until we know more about quality score formats
    """
    edam_data = "data_2048"
    edam_format = "format_3606"
    file_ext = "qual"


@sniff.build_sniff_from_prefix
class QualityScoreSOLiD(QualityScore):
    """
    until we know more about quality score formats
    """
    edam_format = "format_3610"
    file_ext = "qualsolid"

    def sniff_prefix(self, file_prefix):
        """
        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname( 'sequence.fasta' )
        >>> QualityScoreSOLiD().sniff( fname )
        False
        >>> fname = get_test_fname( 'sequence.qualsolid' )
        >>> QualityScoreSOLiD().sniff( fname )
        True
        """
        fh = file_prefix.string_io()
        readlen = None
        goodblock = 0
        while True:
            line = fh.readline()
            if not line:
                if goodblock > 0:
                    return True
                else:
                    break  # EOF
            line = line.strip()
            if line and not line.startswith('#'):  # first non-empty non-comment line
                if line.startswith('>'):
                    line = fh.readline().strip()
                    if line == '' or line.startswith('>'):
                        break
                    try:
                        [int(x) for x in line.split()]
                        if not(readlen):
                            readlen = len(line.split())
                        assert len(line.split()) == readlen  # SOLiD reads should be of the same length
                    except Exception:
                        break
                    goodblock += 1
                    if goodblock > 10:
                        return True
                else:
                    break  # we found a non-empty line, but it's not a header
        return False

    def set_meta(self, dataset, **kwd):
        if self.max_optional_metadata_filesize >= 0 and dataset.get_size() > self.max_optional_metadata_filesize:
            dataset.metadata.data_lines = None
            return
        return QualityScore.set_meta(self, dataset, **kwd)


@sniff.build_sniff_from_prefix
class QualityScore454(QualityScore):
    """
    until we know more about quality score formats
    """
    edam_format = "format_3611"
    file_ext = "qual454"

    def sniff_prefix(self, file_prefix):
        """
        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname( 'sequence.fasta' )
        >>> QualityScore454().sniff( fname )
        False
        >>> fname = get_test_fname( 'sequence.qual454' )
        >>> QualityScore454().sniff( fname )
        True
        """
        fh = file_prefix.string_io()
        while True:
            line = fh.readline()
            if not line:
                break  # EOF
            line = line.strip()
            if line and not line.startswith('#'):  # first non-empty non-comment line
                if line.startswith('>'):
                    line = fh.readline().strip()
                    if line == '' or line.startswith('>'):
                        break
                    try:
                        [int(x) for x in line.split()]
                    except Exception:
                        break
                    return True
                else:
                    break  # we found a non-empty line, but it's not a header
        return False


class QualityScoreSolexa(QualityScore):
    """
    until we know more about quality score formats
    """
    edam_format = "format_3608"
    file_ext = "qualsolexa"


class QualityScoreIllumina(QualityScore):
    """
    until we know more about quality score formats
    """
    edam_format = "format_3609"
    file_ext = "qualillumina"
