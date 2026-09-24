"""Models describing Admin panel extensions.

An admin extension is a directory containing a ``config.yml`` that declares a
section for the Admin panel and the items shown under it. Extensions are
declarative: they ship no JavaScript, and the client renders them from these
models alone.
"""

from typing import (
    Annotated,
    Literal,
)

from pydantic import (
    Field,
    StringConstraints,
)

from galaxy.schema.schema import Model

IdentifierStr = Annotated[str, StringConstraints(pattern=r"^[A-Za-z][A-Za-z0-9_-]*$", max_length=64)]


class AdminExtensionLinkItem(Model):
    """A panel entry that opens a URL, either framed inside Galaxy or in a new tab."""

    id: IdentifierStr = Field(..., description="Identifier of the item, unique within its extension.")
    type: Literal["link"] = Field("link", description="Item type.")
    title: str = Field(..., min_length=1, max_length=255, description="Text shown in the Admin panel.")
    url: str = Field(..., min_length=1, description="URL to open. Relative URLs are resolved against Galaxy's root.")
    target: Literal["iframe", "new_tab"] = Field(
        "iframe", description="Whether to show the URL inside the Galaxy center panel or open it in a new tab."
    )


class AdminExtension(Model):
    """One extension: a titled section of the Admin panel and its items."""

    id: IdentifierStr = Field(..., description="Identifier of the extension, unique across all loaded extensions.")
    section: str = Field(..., min_length=1, max_length=255, description="Section title shown in the Admin panel.")
    items: list[AdminExtensionLinkItem] = Field(..., min_length=1, description="Items shown under the section.")
