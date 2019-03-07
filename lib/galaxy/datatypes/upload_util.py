import os

from galaxy.datatypes import sniff
from galaxy.util.checkers import (
    check_binary,
    is_single_file_zip,
    is_zip,
)


class UploadProblemException(Exception):
    pass


def handle_upload(
    registry,
    path,  # dataset.path
    requested_ext,  # dataset.file_type
    name,  # dataset.name,
    tmp_prefix,
    tmp_dir,
    check_content,
    link_data_only,
    in_place,
    auto_decompress,
    convert_to_posix_lines,
    convert_spaces_to_tabs,
):
    stdout = None
    converted_path = None
    multi_file_zip = False

    # Does the first 1K contain a null?
    is_binary = check_binary(path)

    # Decompress if needed/desired and determine/validate filetype. If a keep-compressed datatype is explicitly selected
    # or if autodetection is selected and the file sniffs as a keep-compressed datatype, it will not be decompressed.
    if not link_data_only:
        if auto_decompress and is_zip(path) and not is_single_file_zip(path):
            multi_file_zip = True
        try:
            ext, converted_path, compression_type = sniff.handle_uploaded_dataset_file_internal(
                path,
                registry,
                ext=requested_ext,
                tmp_prefix=tmp_prefix,
                tmp_dir=tmp_dir,
                in_place=in_place,
                check_content=check_content,
                is_binary=is_binary,
                auto_decompress=auto_decompress,
                uploaded_file_ext=os.path.splitext(name)[1].lower().lstrip('.'),
                convert_to_posix_lines=convert_to_posix_lines,
                convert_spaces_to_tabs=convert_spaces_to_tabs,
            )
        except sniff.InappropriateDatasetContentError as exc:
            raise UploadProblemException(str(exc))
    elif requested_ext == 'auto':
        ext = sniff.guess_ext(path, registry.sniff_order, is_binary=is_binary)
    else:
        ext = requested_ext

    # The converted path will be the same as the input path if no conversion was done (or in-place conversion is used)
    converted_path = None if converted_path == path else converted_path

    # Validate datasets where the filetype was explicitly set using the filetype's sniffer (if any)
    if requested_ext != 'auto':
        datatype = registry.get_datatype_by_extension(requested_ext)
        # Enable sniffer "validate mode" (prevents certain sniffers from disabling themselves)
        if check_content and hasattr(datatype, 'sniff') and not datatype.sniff(path):
            stdout = ("Warning: The file 'Type' was set to '{ext}' but the file does not appear to be of that"
                      " type".format(ext=requested_ext))

    # Handle unsniffable binaries
    if is_binary and ext == 'binary':
        upload_ext = os.path.splitext(name)[1].lower().lstrip('.')
        if registry.is_extension_unsniffable_binary(upload_ext):
            stdout = ("Warning: The file's datatype cannot be determined from its contents and was guessed based on"
                     " its extension, to avoid this warning, manually set the file 'Type' to '{ext}' when uploading"
                     " this type of file".format(ext=upload_ext))
            ext = upload_ext
        else:
            stdout = ("The uploaded binary file format cannot be determined automatically, please set the file 'Type'"
                      " manually")

    datatype = registry.get_datatype_by_extension(ext)
    if multi_file_zip and not getattr(datatype, 'compressed', False):
        stdout = 'ZIP file contained more than one file, only the first file was added to Galaxy.'

    return stdout, ext, datatype, is_binary, converted_path
