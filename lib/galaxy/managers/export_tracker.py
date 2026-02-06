import json
from datetime import (
    datetime,
    timedelta,
)
from typing import (
    Optional,
)

from pydantic import BaseModel
from sqlalchemy import (
    and_,
    select,
)
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm.scoping import scoped_session

from galaxy.exceptions import ObjectNotFound
from galaxy.model import StoreExportAssociation
from galaxy.schema.fields import Security
from galaxy.schema.schema import ExportObjectType
from galaxy.structured_app import MinimalManagerApp


class StoreExportTracker:
    """
    Manages export-related metadata association of different types of exportable objects
    to remote file sources or repositories.
    """

    def __init__(self, app: MinimalManagerApp):
        self.app = app

    @property
    def session(self) -> scoped_session:
        return self.app.model.context

    def create_export_association(self, object_id: int, object_type: ExportObjectType) -> StoreExportAssociation:
        export_association = StoreExportAssociation(object_id=object_id, object_type=object_type)
        self.session.add(export_association)
        self.session.commit()
        return export_association

    def set_export_association_metadata(self, export_association_id: int, export_metadata: BaseModel):
        try:
            stmt = select(StoreExportAssociation).where(StoreExportAssociation.id == export_association_id)
            export_association: StoreExportAssociation = self.session.execute(stmt).scalars().one()
        except NoResultFound:
            raise ObjectNotFound("Cannot set export metadata. Reason: Export association not found")
        export_association.export_metadata = export_metadata.model_dump(mode="json")
        self.session.commit()

    def get_export_association(self, export_association_id: int) -> StoreExportAssociation:
        try:
            stmt = select(StoreExportAssociation).where(StoreExportAssociation.id == export_association_id)
            export_association: StoreExportAssociation = self.session.execute(stmt).scalars().one()
        except NoResultFound:
            raise ObjectNotFound("Cannot get export association. Reason: Export association not found")
        return export_association

    def get_object_exports(
        self, object_id: int, object_type: ExportObjectType, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> list[StoreExportAssociation]:
        stmt = (
            select(
                StoreExportAssociation,
            )
            .where(
                and_(
                    StoreExportAssociation.object_type == object_type,
                    StoreExportAssociation.object_id == object_id,
                    StoreExportAssociation.task_uuid.is_not(None),
                )
            )
            .order_by(StoreExportAssociation.create_time.desc())
        )
        if offset:
            stmt = stmt.offset(offset)
        if limit:
            stmt = stmt.limit(limit)
        return self.session.execute(stmt).scalars()  # type: ignore[return-value]

    def get_user_exports(
        self,
        user_id: int,
        limit: Optional[int] = None,
        days: int = 30,
    ) -> list[StoreExportAssociation]:
        """
        Get all exports initiated by a user within a time window.

        Args:
            user_id: The user ID to filter by.
            limit: Maximum number of exports to return.
            days: Number of days to look back (default 30).

        Returns:
            List of export associations for the user.
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        stmt = (
            select(StoreExportAssociation)
            .where(
                and_(
                    StoreExportAssociation.task_uuid.is_not(None),
                    StoreExportAssociation.create_time >= cutoff_date,
                )
            )
            .order_by(StoreExportAssociation.create_time.desc())
        )

        # Get all recent exports and filter by user_id from metadata
        all_exports = self.session.execute(stmt).scalars().all()

        # Encode the user_id to match the format stored in metadata
        # (EncodedDatabaseIdField stores as encoded string)
        encoded_user_id = Security.security.encode_id(user_id)

        user_exports = []
        for export in all_exports:
            if export.export_metadata:
                # Access dict directly - JSONType handles deserialization
                # however old records might be JSON strings.
                export_metadata = (
                    json.loads(export.export_metadata)
                    if isinstance(export.export_metadata, str)  # type: ignore[unreachable]
                    else export.export_metadata
                )
                stored_user_id = export_metadata.get("request_data", {}).get("user_id")
                if stored_user_id == encoded_user_id:
                    user_exports.append(export)
                    if limit and len(user_exports) >= limit:
                        break

        return user_exports
