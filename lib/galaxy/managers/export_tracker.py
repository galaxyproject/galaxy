from typing import (
    List,
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
from galaxy.model.base import transaction
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
        with transaction(self.session):
            self.session.commit()
        return export_association

    def set_export_association_metadata(self, export_association_id: int, export_metadata: BaseModel):
        try:
            stmt = select(StoreExportAssociation).where(StoreExportAssociation.id == export_association_id)
            export_association: StoreExportAssociation = self.session.execute(stmt).scalars().one()
        except NoResultFound:
            raise ObjectNotFound("Cannot set export metadata. Reason: Export association not found")
        export_association.export_metadata = export_metadata.model_dump_json()  # type:ignore[assignment]
        with transaction(self.session):
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
    ) -> List[StoreExportAssociation]:
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
        return self.session.execute(stmt).scalars()  # type:ignore[return-value]
