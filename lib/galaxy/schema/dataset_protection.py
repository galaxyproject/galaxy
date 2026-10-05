from datetime import datetime
from typing import (
    Annotated,
    Literal,
)

from pydantic import Field

from galaxy.schema.schema import Model


class Crypt4GHGrantPayload(Model):
    scheme: Annotated[
        Literal["crypt4gh"],
        Field(description="The protection scheme of the dataset."),
    ]
    crypt4gh_compute_header: Annotated[
        str,
        Field(
            min_length=1,
            max_length=65536,
            description=(
                "Base64-encoded Crypt4GH header of the dataset, re-encrypted by the user-side recryptor "
                "service to the compute keypair."
            ),
        ),
    ]
    crypt4gh_compute_keypair_id: Annotated[
        str,
        Field(
            min_length=1,
            max_length=255,
            pattern=r"^[A-Za-z0-9:._-]+$",
            description="Identifier of the compute keypair the header was re-encrypted to.",
        ),
    ]
    crypt4gh_compute_keypair_expiration_date: Annotated[
        datetime,
        Field(description="Expiration date of the compute keypair, including the timezone."),
    ]


class DatasetProtectionStatus(Model):
    protected: Annotated[
        bool,
        Field(description="Whether the dataset is encrypted with a supported protection scheme."),
    ]
    scheme: Annotated[
        str | None,
        Field(description="The protection scheme of the dataset, if protected."),
    ] = None
    ready: Annotated[
        bool,
        Field(description="Whether the current user holds a valid grant to compute on this dataset."),
    ] = False
    expires_at: Annotated[
        datetime | None,
        Field(description="Expiration (UTC) of the current user's grant, if any."),
    ] = None
