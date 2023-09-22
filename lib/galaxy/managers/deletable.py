"""
Many models in Galaxy are not meant to be removed from the database but only
marked as deleted. These models have the boolean attribute 'deleted'.

Other models are deletable and also may be purged. Most often these are
models have some backing/supporting resources that can be removed as well
(e.g. Datasets have data files on a drive). Purging these models removes
the supporting resources as well. These models also have the boolean
attribute 'purged'.
"""
from typing import (
    Any,
    Dict,
    Set,
)

from galaxy.model import Base
from .base import (
    Deserializer,
    ModelValidator,
    OrmFilterParsersType,
    parse_bool,
)


class DeletableManagerMixin:
    """
    A mixin/interface for a model that is deletable (i.e. has a 'deleted' attr).

    Many resources in Galaxy can be marked as deleted - meaning (in most cases)
    that they are no longer needed, should not be displayed, or may be actually
    removed by an admin/script.
    """

    def _session_setattr(self, item: Base, attr: str, val: Any, flush: bool = True):
        ...

    def delete(self, item, flush=True, **kwargs):
        """
        Mark as deleted and return.
        """
        return self._session_setattr(item, "deleted", True, flush=flush)

    def undelete(self, item, flush=True, **kwargs):
        """
        Mark as not deleted and return.
        """
        return self._session_setattr(item, "deleted", False, flush=flush)


class DeletableSerializerMixin:
    serializable_keyset: Set[str]

    def add_serializers(self):
        self.serializable_keyset.add("deleted")


# TODO: these are of questionable value if we don't want to enable users to delete/purge via update
class DeletableDeserializerMixin:
    deserializers: Dict[str, Deserializer]

    def add_deserializers(self):
        self.deserializers["deleted"] = self.deserialize_deleted

    def deserialize_deleted(self, item, key, val, **context):
        """
        Delete or undelete `item` based on `val` then return `item.deleted`.
        """
        new_deleted = ModelValidator.bool(key, val)
        if new_deleted == item.deleted:
            return item.deleted
        # TODO:?? flush=False?
        if new_deleted:
            self.manager.delete(item, flush=False)
        else:
            self.manager.undelete(item, flush=False)
        return item.deleted


class DeletableFiltersMixin:
    orm_filter_parsers: OrmFilterParsersType

    def _add_parsers(self):
        self.orm_filter_parsers.update({"deleted": {"op": ("eq"), "val": parse_bool}})


class PurgableManagerMixin(DeletableManagerMixin):
    """
    A manager interface/mixin for a resource that allows deleting and purging where
    purging is often removal of some additional, non-db resource (e.g. a dataset's
    file).
    """

    def _session_setattr(self, item: Base, attr: str, val: Any, flush: bool = True):
        ...

    def purge(self, item, flush=True, **kwargs):
        """
        Mark as purged and return.

        Override this in subclasses to do the additional resource removal.
        """
        self.delete(item, flush=False)
        return self._session_setattr(item, "purged", True, flush=flush)


class PurgableSerializerMixin(DeletableSerializerMixin):
    serializable_keyset: Set[str]

    def add_serializers(self):
        DeletableSerializerMixin.add_serializers(self)
        self.serializable_keyset.add("purged")


class PurgableDeserializerMixin(DeletableDeserializerMixin):
    deserializers: Dict[str, Deserializer] = {}

    def add_deserializers(self):
        DeletableDeserializerMixin.add_deserializers(self)
        self.deserializers["purged"] = self.deserialize_purged

    def deserialize_purged(self, item, key, val, **context):
        """
        If `val` is True, purge `item` and return `item.purged`.
        """
        new_purged = ModelValidator.bool(key, val)
        if new_purged == item.purged:
            return item.purged
        # do we want to error if something attempts to 'unpurge'?
        if new_purged:
            self.manager.purge(item, flush=False)
        return item.purged


class PurgableFiltersMixin(DeletableFiltersMixin):
    def _add_parsers(self):
        DeletableFiltersMixin._add_parsers(self)
        self.orm_filter_parsers.update({"purged": {"op": ("eq"), "val": parse_bool}})
