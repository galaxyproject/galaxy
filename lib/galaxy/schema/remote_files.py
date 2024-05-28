from enum import Enum
from typing import (
    Any,
    List,
    Optional,
    Union,
)

from pydantic import (
    Field,
    RootModel,
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


class FilesSourceSupports(Model):
    pagination: Annotated[bool, Field(description="Whether this file source supports server-side pagination.")] = False
    search: Annotated[bool, Field(description="Whether this file source supports server-side search.")] = False
    sorting: Annotated[bool, Field(description="Whether this file source supports server-side sorting.")] = False


class FilesSourcePlugin(Model):
    id: str = Field(
        ...,
        title="ID",
        description="The `FilesSource` plugin identifier",
        examples=["_import"],
    )
    type: str = Field(
        ...,
        title="Type",
        description="The type of the plugin.",
        examples=["gximport"],
    )
    label: str = Field(
        ...,
        title="Label",
        description="The display label for this plugin.",
        examples=["Library Import Directory"],
    )
    doc: Optional[str] = Field(
        None,
        title="Documentation",
        description="Documentation or extended description for this plugin.",
        examples=["Galaxy's library import directory"],
    )
    browsable: bool = Field(
        ...,
        title="Browsable",
        description="Whether this file source plugin can list items.",
    )
    writable: bool = Field(
        ...,
        title="Writeable",
        description="Whether this files source plugin allows write access.",
        examples=[False],
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
    url: Optional[str] = Field(
        None,
        title="URL",
        description="Optional URL that might be provided by some plugins to link to the remote source.",
    )
    supports: Annotated[
        FilesSourceSupports,
        Field(default=..., description="Features supported by this file source."),
    ] = FilesSourceSupports()


class BrowsableFilesSourcePlugin(FilesSourcePlugin):
    browsable: Literal[True]
    uri_root: str = Field(
        ...,
        title="URI root",
        description="The URI root used by this type of plugin.",
        examples=["gximport://"],
    )


class FilesSourcePluginList(RootModel):
    root: List[Union[BrowsableFilesSourcePlugin, FilesSourcePlugin]] = Field(
        default=[],
        title="List of files source plugins",
        examples=[
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
    name: str = Field(..., title="Name", description="The name of the entry.")
    uri: str = Field(..., title="URI", description="The URI of the entry.")
    path: str = Field(..., title="Path", description="The path of the entry.")


class RemoteDirectory(RemoteEntry):
    class_: Literal["Directory"] = Field(..., alias="class")


class RemoteFile(RemoteEntry):
    class_: Literal["File"] = Field(..., alias="class")
    size: int = Field(..., title="Size", description="The size of the file in bytes.")
    ctime: str = Field(..., title="Creation time", description="The creation time of the file.")


class ListJstreeResponse(RootModel):
    root: List[Any] = Field(
        default=[],
        title="List of files",
        description="List of files in Jstree format.",
        # TODO: also deprecate on python side, https://github.com/pydantic/pydantic/issues/2255
        json_schema_extra={"deprecated": True},
    )


AnyRemoteEntry = Annotated[
    Union[RemoteFile, RemoteDirectory],
    Field(discriminator="class_"),
]


class ListUriResponse(RootModel):
    root: List[AnyRemoteEntry] = Field(
        default=[],
        title="List of remote entries",
        description="List of directories and files.",
    )


AnyRemoteFilesListResponse = Union[ListUriResponse, ListJstreeResponse]


class CreateEntryPayload(Model):
    target: str = Field(
        ...,
        title="Target",
        description="The target file source to create the entry in.",
    )
    name: str = Field(
        ...,
        title="Name",
        description="The name of the entry to create.",
        examples=["my_new_entry"],
    )


class CreatedEntryResponse(Model):
    name: str = Field(
        ...,
        title="Name",
        description="The name of the created entry.",
        examples=["my_new_entry"],
    )
    uri: str = Field(
        ...,
        title="URI",
        description="The URI of the created entry.",
        examples=["gxfiles://my_new_entry"],
    )
    external_link: Optional[str] = Field(
        default=None,
        title="External link",
        description="An optional external link to the created entry if available.",
    )
