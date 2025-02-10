import logging

from sqlalchemy import select
from sqlalchemy.sql.expression import func

# Cannot import galaxy.model b/c it creates a circular import graph.
import galaxy

log = logging.getLogger(__name__)


class UsesItemRatings:
    """
    Mixin for getting and setting item ratings.

    Class makes two assumptions:
    (1) item-rating association table is named <item_class>RatingAssocation
    (2) item-rating association table has a column with a foreign key referencing
    item table that contains the item's id.
    """

    def get_ave_item_rating_data(self, db_session, item, webapp_model=None):
        """Returns the average rating for an item."""
        if webapp_model is None:
            webapp_model = galaxy.model
        item_rating_assoc_class = self._get_item_rating_assoc_class(item, webapp_model=webapp_model)
        if not item_rating_assoc_class:
            raise Exception(f"Item does not have ratings: {item.__class__.__name__}")
        item_id_filter = self._get_item_id_filter_str(item, item_rating_assoc_class)
        ave_rating = db_session.scalar(select(func.avg(item_rating_assoc_class.rating)).where(item_id_filter))
        # Convert ave_rating to float; note: if there are no item ratings, ave rating is None.
        if ave_rating:
            ave_rating = float(ave_rating)
        else:
            ave_rating = 0
        num_ratings = db_session.scalar(select(func.count(item_rating_assoc_class.rating)).where(item_id_filter))
        return (ave_rating, num_ratings)

    def rate_item(self, db_session, user, item, rating, webapp_model=None):
        """Rate an item. Return type is <item_class>RatingAssociation."""
        if webapp_model is None:
            webapp_model = galaxy.model
        item_rating = self.get_user_item_rating(db_session, user, item, webapp_model=webapp_model)
        if not item_rating:
            # User has not yet rated item; create rating.
            item_rating_assoc_class = self._get_item_rating_assoc_class(item, webapp_model=webapp_model)
            item_rating = item_rating_assoc_class(user, item, rating)
            db_session.add(item_rating)
            db_session.commit()
        elif item_rating.rating != rating:
            # User has rated item; update rating.
            item_rating.rating = rating
            db_session.commit()
        return item_rating

    def get_user_item_rating(self, db_session, user, item, webapp_model=None):
        """Returns user's rating for an item. Return type is <item_class>RatingAssociation."""
        if webapp_model is None:
            webapp_model = galaxy.model
        item_rating_assoc_class = self._get_item_rating_assoc_class(item, webapp_model=webapp_model)
        if not item_rating_assoc_class:
            raise Exception(f"Item does not have ratings: {item.__class__.__name__}")

        # Query rating table by user and item id.
        item_id_filter = self._get_item_id_filter_str(item, item_rating_assoc_class)
        return db_session.scalars(
            select(item_rating_assoc_class).filter_by(user=user).where(item_id_filter).limit(1)
        ).first()

    def _get_item_rating_assoc_class(self, item, webapp_model=None):
        """Returns an item's item-rating association class."""
        if webapp_model is None:
            webapp_model = galaxy.model
        item_rating_assoc_class = f"{item.__class__.__name__}RatingAssociation"
        return getattr(webapp_model, item_rating_assoc_class, None)

    def _get_item_id_filter_str(self, item, item_rating_assoc_class):
        # Get foreign key in item-rating association table that references item table.
        item_fk = get_foreign_key(item_rating_assoc_class, item)
        return item_fk.parent == item.id


class UsesAnnotations:
    """Mixin for getting and setting item annotations."""

    def get_item_annotation_str(self, db_session, user, item):
        return get_item_annotation_str(db_session, user, item)

    def get_item_annotation_obj(self, db_session, user, item):
        return get_item_annotation_obj(db_session, user, item)

    def add_item_annotation(self, db_session, user, item, annotation):
        return add_item_annotation(db_session, user, item, annotation)

    def delete_item_annotation(self, db_session, user, item):
        if annotation_assoc := get_item_annotation_obj(db_session, user, item):
            db_session.delete(annotation_assoc)
            db_session.commit()

    def copy_item_annotation(self, db_session, source_user, source_item, target_user, target_item):
        """Copy an annotation from a user/item source to a user/item target."""
        if source_user and target_user:
            annotation_str = self.get_item_annotation_str(db_session, source_user, source_item)
            if annotation_str:
                annotation = self.add_item_annotation(db_session, target_user, target_item, annotation_str)
                return annotation
        return None


def get_item_annotation_obj(db_session, user, item):
    """Returns a user's annotation object for an item."""

    # Get annotation association class.
    annotation_assoc_class = _get_annotation_assoc_class(item)
    if not annotation_assoc_class or item.id is None:
        return None

    # Get annotation association object.
    annotation_assoc = select(annotation_assoc_class).filter_by(user=user)

    if item.__class__ == galaxy.model.History:
        annotation_assoc = annotation_assoc.filter_by(history=item)
    elif item.__class__ == galaxy.model.HistoryDatasetAssociation:
        annotation_assoc = annotation_assoc.filter_by(hda=item)
    elif item.__class__ == galaxy.model.HistoryDatasetCollectionAssociation:
        annotation_assoc = annotation_assoc.filter_by(history_dataset_collection=item)
    elif item.__class__ == galaxy.model.StoredWorkflow:
        annotation_assoc = annotation_assoc.filter_by(stored_workflow=item)
    elif item.__class__ == galaxy.model.WorkflowStep:
        annotation_assoc = annotation_assoc.filter_by(workflow_step=item)
    elif item.__class__ == galaxy.model.Page:
        annotation_assoc = annotation_assoc.filter_by(page=item)
    elif item.__class__ == galaxy.model.Visualization:
        annotation_assoc = annotation_assoc.filter_by(visualization=item)
    return db_session.scalars(annotation_assoc.limit(1)).first()


def get_item_annotation_str(db_session, user, item):
    """Returns a user's annotation string for an item."""
    if hasattr(item, "annotations"):
        # If we already have an annotations object we use it.
        annotation_obj = None
        for annotation in item.annotations:
            if annotation.user == user:
                annotation_obj = annotation
                break
    else:
        annotation_obj = get_item_annotation_obj(db_session, user, item)
    if annotation_obj:
        return galaxy.util.unicodify(annotation_obj.annotation)
    return None


def add_item_annotation(db_session, user, item, annotation):
    """Add or update an item's annotation; a user can only have a single annotation for an item."""
    # Get/create annotation association object.
    annotation_assoc = get_item_annotation_obj(db_session, user, item)
    if not annotation_assoc:
        annotation_assoc_class = _get_annotation_assoc_class(item)
        if not annotation_assoc_class:
            return None
        annotation_assoc = annotation_assoc_class()
        item.annotations.append(annotation_assoc)
        annotation_assoc.user = user
    # Set annotation.
    annotation_assoc.annotation = annotation
    return annotation_assoc


def _get_annotation_assoc_class(item):
    """Returns an item's item-annotation association class."""
    class_name = f"{item.__class__.__name__}AnnotationAssociation"
    return getattr(galaxy.model, class_name, None)


def get_foreign_key(source_class, target_class):
    """Returns foreign key in source class that references target class."""
    target_fk = None
    for fk in source_class.__table__.foreign_keys:
        if fk.references(target_class.__table__):
            target_fk = fk
            break
    if not target_fk:
        raise Exception(f"No foreign key found between objects: {source_class.__table__}, {target_class.__table__}")
    return target_fk


__all__ = (
    "get_foreign_key",
    "UsesAnnotations",
    "UsesItemRatings",
)
