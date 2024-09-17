from enum import Enum
from typing import (
    List,
    Optional,
)

from pydantic import (
    Field,
    RootModel,
)

from galaxy.schema.fields import EncodedDatabaseIdField, DecodedDatabaseIdField, LibraryFolderDatabaseIdField
from galaxy.schema.schema import Model


class UploadOption(str, Enum):
    upload_file = "upload_file"
    upload_paths = "upload_paths"
    upload_directory = "upload_directory"


class CreateType(str, Enum):
    file = "file"
    folder = "folder"
    collection = "collection"


class LinkDataOnly(str, Enum):
    copy_files = "copy_files"
    link_to_files = "link_to_files"


class LibraryContentsCreatePayload(Model):
    create_type: CreateType = Field(
        ...,
        title="the type of item to create",
    )
    upload_option: Optional[UploadOption] = Field(
        UploadOption.upload_file,
        title="the method to use for uploading files",
    )
    folder_id: LibraryFolderDatabaseIdField = Field(
        ...,
        title="the encoded id of the parent folder of the new item",
    )
    tag_using_filenames: Optional[bool] = Field(
        False,
        title="create tags on datasets using the file's original name",
    )
    tags: Optional[List[str]] = Field(
        [],
        title="create the given list of tags on datasets",
    )
    from_hda_id: Optional[DecodedDatabaseIdField] = Field(
        None,
        title="(only if create_type is 'file') the encoded id of an accessible HDA to copy into the library",
    )
    from_hdca_id: Optional[DecodedDatabaseIdField] = Field(
        None,
        title="(only if create_type is 'file') the encoded id of an accessible HDCA to copy into the library",
    )
    ldda_message: Optional[str] = Field(
        "",
        title="the new message attribute of the LDDA created",
    )
    extended_metadata: Optional[str] = Field(
        None,
        title="sub-dictionary containing any extended metadata to associate with the item",
    )


class LibraryContentsFileCreatePayload(LibraryContentsCreatePayload):
    dbkey: Optional[str] = Field(
        "?",
        title="database key",
    )
    roles: Optional[str] = Field(
        "",
        title="user selected roles",
    )
    file_type: str = Field(
        ...,
        title="file type",
    )
    server_dir: Optional[str] = Field(
        "",
        title="(only if upload_option is 'upload_directory') relative path of the "
        "subdirectory of Galaxy ``library_import_dir`` (if admin) or "
        "``user_library_import_dir`` (if non-admin) to upload. "
        "All and only the files (i.e. no subdirectories) contained "
        "in the specified directory will be uploaded.",
    )
    filesystem_paths: Optional[str] = Field(
        "",
        title="(only if upload_option is 'upload_paths' and the user is an admin) "
        "file paths on the Galaxy server to upload to the library, one file per line",
    )
    link_data_only: Optional[LinkDataOnly] = Field(
        LinkDataOnly.copy_files,
        title="(only when upload_option is 'upload_directory' or 'upload_paths')."
        "Setting to 'link_to_files' symlinks instead of copying the files",
    )


class LibraryContentsFolderCreatePayload(LibraryContentsCreatePayload):
    name: Optional[str] = Field(
        "",
        title="(only if create_type is 'folder') name of the folder to create",
    )
    description: Optional[str] = Field(
        "",
        title="(only if create_type is 'folder') description of the folder to create",
    )


class LibraryContentsDeletePayload(Model):
    purge: Optional[bool] = Field(
        False,
        title="if True, purge the library dataset",
    )
