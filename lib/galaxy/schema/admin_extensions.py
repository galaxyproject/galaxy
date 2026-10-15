"""Models describing Admin panel extensions.

An admin extension is a directory containing a ``config.yml`` that declares a
section for the Admin panel and the items shown under it. Extensions are
declarative: they ship no JavaScript, and the client renders them from these
models alone.
"""

from collections import Counter
from typing import (
    Annotated,
    Literal,
)

from pydantic import (
    ConfigDict,
    Field,
    model_validator,
    StringConstraints,
)

from galaxy.schema.schema import Model

IdentifierStr = Annotated[str, StringConstraints(pattern=r"^[A-Za-z][A-Za-z0-9_-]*$", max_length=64)]
# An absolute http(s) URL or a path from Galaxy's root; protocol-relative URLs are rejected.
UrlStr = Annotated[str, StringConstraints(pattern=r"^(https?://|/[^/]|/$)")]


class AdminExtensionLinkItem(Model):
    """A panel entry that opens a URL, either framed inside Galaxy or in a new tab."""

    model_config = ConfigDict(extra="forbid")

    id: IdentifierStr = Field(..., description="Identifier of the item, unique within its extension.")
    type: Literal["link"] = Field("link", description="Item type.")
    title: str = Field(..., min_length=1, max_length=255, description="Text shown in the Admin panel.")
    url: UrlStr = Field(
        ..., description="URL to open: an absolute http(s) URL, or a path starting with '/' that is served by Galaxy."
    )
    target: Literal["iframe", "new_tab"] = Field(
        "iframe", description="Whether to show the URL inside the Galaxy center panel or open it in a new tab."
    )


class AdminExtension(Model):
    """One extension: a titled section of the Admin panel and its items."""

    model_config = ConfigDict(extra="forbid")

    id: IdentifierStr = Field(..., description="Identifier of the extension, unique across all loaded extensions.")
    section: str = Field(..., min_length=1, max_length=255, description="Section title shown in the Admin panel.")
    items: list[AdminExtensionLinkItem] = Field(..., min_length=1, description="Items shown under the section.")

    @model_validator(mode="after")
    def check_unique_item_ids(self) -> "AdminExtension":
        counts = Counter(item.id for item in self.items)
        duplicates = sorted(item_id for item_id, count in counts.items() if count > 1)
        if duplicates:
            raise ValueError(f"Duplicate item ids in admin extension '{self.id}': {', '.join(duplicates)}")
        return self
