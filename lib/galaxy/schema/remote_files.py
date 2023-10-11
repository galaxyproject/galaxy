from enum import Enum
from typing import (
    Any,
    List,
    Optional,
    Union,
)

from pydantic import (
    Field,
    Required,
)
from typing_extensions import (
    Annotated,
    Literal,
)

from galaxy.schema.schema import Model


class RemoteFilesTarget(str, Enum):
    ftpdir = "ftpdir"
    userdir = "userdir"
    importdir = "importdir"


class RemoteFilesFormat(str, Enum):
    flat = "flat"
    jstree = "jstree"
    uri = "uri"


class RemoteFilesDisableMode(str, Enum):
    folders = "folders"
    files = "files"


class FilesSourcePlugin(Model):
    id: str = Field(
        Required,
        title="ID",
        description="The `FilesSource` plugin identifier",
        example="_import",
    )
    type: str = Field(
        Required,
        title="Type",
        description="The type of the plugin.",
        example="gximport",
    )
    label: str = Field(
        Required,
        title="Label",
        description="The display label for this plugin.",
        example="Library Import Directory",
    )
    doc: str = Field(
        Required,
        title="Documentation",
        description="Documentation or extended description for this plugin.",
        example="Galaxy's library import directory",
    )
    browsable: bool = Field(
        Required,
        title="Browsable",
        description="Whether this file source plugin can list items.",
    )
    writable: bool = Field(
        Required,
        title="Writeable",
        description="Whether this files source plugin allows write access.",
        example=False,
    )
    requires_roles: Optional[str] = Field(
        None,
        title="Requires roles",
        description="Only users with the roles specified here can access this files source.",
    )
    requires_groups: Optional[str] = Field(
        None,
        title="Requires groups",
        description="Only users belonging to the groups specified here can access this files source.",
    )


class BrowsableFilesSourcePlugin(FilesSourcePlugin):
    browsable: Literal[True]
    uri_root: str = Field(
        Required,
        title="URI root",
        description="The URI root used by this type of plugin.",
        example="gximport://",
    )


class FilesSourcePluginList(Model):
    __root__: List[Union[BrowsableFilesSourcePlugin, FilesSourcePlugin]] = Field(
        default=[],
        title="List of files source plugins",
        example=[
            {
                "id": "_import",
                "type": "gximport",
                "uri_root": "gximport://",
                "label": "Library Import Directory",
                "doc": "Galaxy's library import directory",
                "writable": False,
                "browsable": True,
            }
        ],
    )


class RemoteEntry(Model):
    name: str = Field(Required, title="Name", description="The name of the entry.")
    uri: str = Field(Required, title="URI", description="The URI of the entry.")
    path: str = Field(Required, title="Path", description="The path of the entry.")


class RemoteDirectory(RemoteEntry):
    class_: Literal["Directory"] = Field(Required, alias="class", const=True)


class RemoteFile(RemoteEntry):
    class_: Literal["File"] = Field(Required, alias="class", const=True)
    size: int = Field(Required, title="Size", description="The size of the file in bytes.")
    ctime: str = Field(Required, title="Creation time", description="The creation time of the file.")


class ListJstreeResponse(Model):
    __root__: List[Any] = Field(
        default=[],
        title="List of files",
        description="List of files in Jstree format.",
        deprecated=True,
    )


AnyRemoteEntry = Annotated[
    Union[RemoteFile, RemoteDirectory],
    Field(discriminator="class_"),
]


class ListUriResponse(Model):
    __root__: List[AnyRemoteEntry] = Field(
        default=[],
        title="List of remote entries",
        description="List of directories and files.",
    )


AnyRemoteFilesListResponse = Union[ListUriResponse, ListJstreeResponse]


class CreateEntryPayload(Model):
    target: str = Field(
        Required,
        title="Target",
        description="The target file source to create the entry in.",
    )
    name: str = Field(
        Required,
        title="Name",
        description="The name of the entry to create.",
        example="my_new_entry",
    )


class CreatedEntryResponse(Model):
    name: str = Field(
        Required,
        title="Name",
        description="The name of the created entry.",
        example="my_new_entry",
    )
    uri: str = Field(
        Required,
        title="URI",
        description="The URI of the created entry.",
        example="gxfiles://my_new_entry",
    )
    external_link: Optional[str] = Field(
        default=None,
        title="External link",
        description="An optional external link to the created entry if available.",
    )
