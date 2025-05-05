"""
Mixins for Annotatable model managers and serializers.
"""

import abc
import logging
from typing import (
    Dict,
    Optional,
)

from sqlalchemy.orm import scoped_session

from .base import (
    Deserializer,
    FunctionFilterParsersType,
    ModelValidator,
    Serializer,
)

log = logging.getLogger(__name__)


# needed to extract this for use in manager *and* serializer, ideally, would use self.manager.annotation
# from serializer, but history_contents has no self.manager
# TODO: fix
def _match_by_user(item, user) -> Optional[str]:
    if not user:
        return None
    for annotation in item.annotations:
        if annotation.user_id == user.id:
            return annotation.annotation
    return None


class AnnotatableManagerMixin:
    #: class of AnnotationAssociation (e.g. HistoryAnnotationAssociation)
    annotation_assoc: type

    @abc.abstractmethod
    def session(self) -> scoped_session: ...

    def annotation(self, item) -> Optional[str]:
        """
        Return the annotation string made by the `item`'s owner or `None` if there
        is no annotation.
        """
        # NOTE: only works with sharable (.user)
        return self._user_annotation(item, item.user)

    # TODO: should/do we support multiple, non-owner annotation of items?
    def annotate(self, item, annotation, user=None, flush=True):
        """
        Create a new annotation on `item` or delete the existing if annotation
        is `None`.
        """
        if not user:
            return None
        if annotation is None:
            self._delete_annotation(item, user, flush=flush)
            return None

        annotation_obj = item.add_item_annotation(self.session(), user, item, annotation)
        if flush:
            session = self.session()
            session.commit()
        return annotation_obj

    def _user_annotation(self, item, user):
        return _match_by_user(item, user)

    def _delete_annotation(self, item, user, flush=True):
        returned = item.delete_item_annotation(self.session(), user, item)
        if flush:
            session = self.session()
            session.commit()
        return returned


class AnnotatableSerializerMixin:
    serializers: Dict[str, Serializer]

    def add_serializers(self):
        self.serializers["annotation"] = self.serialize_annotation

    def serialize_annotation(self, item, key, user=None, **context):
        """
        Get and serialize an `item`'s annotation.
        """
        annotation = _match_by_user(item, user)
        return annotation.strip() if annotation else None


class AnnotatableDeserializerMixin:
    deserializers: Dict[str, Deserializer]

    def add_deserializers(self):
        self.deserializers["annotation"] = self.deserialize_annotation

    def deserialize_annotation(self, item, key, val, user=None, **context):
        """
        Make sure `val` is a valid annotation and assign it, deleting any existing
        if `val` is None.
        """
        val = ModelValidator.nullable_basestring(key, val)
        return self.manager.annotate(item, val, user=user, flush=False)


# TODO: I'm not entirely convinced this (or tags) are a good idea for filters since they involve a/the user
class AnnotatableFilterMixin:
    fn_filter_parsers: FunctionFilterParsersType

    def _owner_annotation(self, item) -> Optional[str]:
        """
        Get the annotation by the item's owner.
        """
        return _match_by_user(item, item.user)

    def filter_annotation_contains(self, item, val: str) -> bool:
        """
        Test whether `val` is in the owner's annotation.
        """
        owner_annotation = self._owner_annotation(item)
        if owner_annotation is None:
            return False
        return val.lower() in owner_annotation.lower()

    def _add_parsers(self):
        self.fn_filter_parsers.update(
            {
                "annotation": {
                    "op": {
                        "has": self.filter_annotation_contains,
                        "contains": self.filter_annotation_contains,
                    },
                },
            }
        )
