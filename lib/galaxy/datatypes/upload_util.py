from galaxy.datatypes import sniff
from galaxy.datatypes.binary import Binary


class UploadProblemException(Exception):

    def __init__(self, message):
        self.message = message


def handle_unsniffable_binary_check(data_type, ext, path, name, is_binary, requested_ext, check_content, registry):
    """Return modified values of data_type and ext if unsniffable binary encountered.

    Throw UploadProblemException if content problems or extension mismatches occur.

    Precondition: check_binary called returned True.
    """
    if is_binary or registry.is_extension_unsniffable_binary(requested_ext):
        # We have a binary dataset, but it is not Bam, Sff or Pdf
        data_type = 'binary'
        parts = name.split(".")
        if len(parts) > 1:
            ext = parts[-1].strip().lower()
            is_ext_unsniffable_binary = registry.is_extension_unsniffable_binary(ext)
            if check_content and not is_ext_unsniffable_binary:
                raise UploadProblemException('The uploaded binary file contains inappropriate content')

            elif is_ext_unsniffable_binary and requested_ext != ext:
                err_msg = "You must manually set the 'File Format' to '%s' when uploading %s files." % (ext, ext)
                raise UploadProblemException(err_msg)
    return data_type, ext


def handle_sniffable_binary_check(data_type, ext, path, registry):
    """Return modified values of data_type and ext if sniffable binary encountered.

    Precondition: check_binary called returned True.
    """
    # Sniff the data type
    guessed_ext = sniff.guess_ext(path, registry.sniff_order)
    # Set data_type only if guessed_ext is a binary datatype
    datatype = registry.get_datatype_by_extension(guessed_ext)
    if isinstance(datatype, Binary):
        data_type = guessed_ext
        ext = guessed_ext

    return data_type, ext
