"""
Superclass Manager and Serializers for Sharable objects.

A sharable Galaxy object:
    has an owner/creator User
    is sharable with other, specific Users
    is importable (copyable) by users that have access
    has a slug which can be used as a link to view the resource
    can be published effectively making it available to all other Users
    can be rated
"""

import logging
import re
from typing import (
    Any,
    List,
    Optional,
    Set,
    Type,
)

from slugify import slugify
from sqlalchemy import (
    exists,
    false,
    select,
    true,
)

from galaxy import (
    exceptions,
    model,
)
from galaxy.managers import (
    annotatable,
    base,
    ratable,
    secured,
    taggable,
    users,
)
from galaxy.managers.base import combine_lists
from galaxy.model import (
    User,
    UserShareAssociation,
)
from galaxy.model.base import transaction
from galaxy.model.tags import GalaxyTagHandler
from galaxy.schema.schema import (
    ShareWithExtra,
    SharingOptions,
)
from galaxy.structured_app import MinimalManagerApp
from galaxy.util import ready_name_for_url
from galaxy.util.hash_util import md5_hash_str

log = logging.getLogger(__name__)


class SharableModelManager(
    base.ModelManager,
    secured.OwnableManagerMixin,
    secured.AccessibleManagerMixin,
    annotatable.AnnotatableManagerMixin,
    ratable.RatableManagerMixin,
):
    # e.g. histories, pages, stored workflows, visualizations
    # base.DeleteableModelMixin? (all four are deletable)

    #: the model used for UserShareAssociations with this model
    user_share_model: Type[UserShareAssociation]

    #: the single character abbreviation used in username_and_slug: e.g. 'h' for histories: u/user/h/slug
    SINGLE_CHAR_ABBR: Optional[str] = None

    def __init__(self, app: MinimalManagerApp):
        super().__init__(app)
        # user manager is needed to check access/ownership/admin
        self.user_manager = users.UserManager(app)
        self.tag_handler = app[GalaxyTagHandler]

    # .... has a user
    def by_user(self, user: User, **kwargs: Any) -> List[Any]:
        """
        Return list for all items (of model_class type) associated with the given
        `user`.
        """
        user_filter = self.model_class.table.c.user_id == user.id
        filters = combine_lists(user_filter, kwargs.get("filters", None))
        return self.list(filters=filters, **kwargs)

    # .... owned/accessible interfaces
    def is_owner(self, item: model.Base, user: Optional[User], **kwargs: Any) -> bool:
        """
        Return true if this sharable belongs to `user` (or `user` is an admin).
        """
        # ... effectively a good fit to have this here, but not semantically
        if self.user_manager.is_admin(user, trans=kwargs.get("trans", None)):
            return True
        return item.user == user  # type:ignore[attr-defined]

    def is_accessible(self, item, user: Optional[User], **kwargs: Any) -> bool:
        """
        If the item is importable, is owned by `user`, or (the valid) `user`
        is in 'users shared with' list for the item: return True.
        """
        if item.importable:
            return True
        # note: owners always have access - checking for accessible implicitly checks for ownership
        if self.is_owner(item, user, **kwargs):
            return True
        if self.user_manager.is_anonymous(user):
            return False
        if user in item.users_shared_with_dot_users:
            return True
        return False

    # .... importable
    def make_importable(self, item, flush=True):
        """
        Makes item accessible--viewable and importable--and sets item's slug.
        Does not flush/commit changes, however. Item must have name, user,
        importable, and slug attributes.
        """
        self.create_unique_slug(item, flush=False)
        return self._session_setattr(item, "importable", True, flush=flush)

    def make_non_importable(self, item, flush=True):
        """
        Makes item accessible--viewable and importable--and sets item's slug.
        Does not flush/commit changes, however. Item must have name, user,
        importable, and slug attributes.
        """
        # item must be unpublished if non-importable
        if item.published:
            self.unpublish(item, flush=False)
        return self._session_setattr(item, "importable", False, flush=flush)

    # .... published
    def publish(self, item, flush=True):
        """
        Set both the importable and published flags on `item` to True.
        """
        # item must be importable to be published
        if not item.importable:
            self.make_importable(item, flush=False)
        return self._session_setattr(item, "published", True, flush=flush)

    def unpublish(self, item, flush=True):
        """
        Set the published flag on `item` to False.
        """
        return self._session_setattr(item, "published", False, flush=flush)

    def list_published(self, filters=None, **kwargs):
        """
        Return a list of all published items.
        """
        published_filter = self.model_class.table.c.published == true()
        filters = combine_lists(published_filter, filters)
        return self.list(filters=filters, **kwargs)

    # .... user sharing
    # sharing is often done via a 3rd table btwn a User and an item -> a <Item>UserShareAssociation
    def get_share_assocs(self, item, user=None):
        """
        Get the UserShareAssociations for the `item`.

        Optionally send in `user` to test for a single match.
        """
        query = self.query_associated(self.user_share_model, item)
        if user is not None:
            query = query.filter_by(user=user)
        return query.all()

    def share_with(self, item, user: User, flush: bool = True):
        """
        Get or create a share for the given user.
        """
        # precondition: user has been validated
        # get or create
        existing = self.get_share_assocs(item, user=user)
        if existing:
            return existing.pop(0)
        return self._create_user_share_assoc(item, user, flush=flush)

    def _create_user_share_assoc(self, item, user, flush=True):
        """
        Create a share for the given user.
        """
        user_share_assoc = self.user_share_model()
        self.session().add(user_share_assoc)
        self.associate(user_share_assoc, item)
        user_share_assoc.user = user

        # ensure an item slug so shared users can access
        if not item.slug:
            self.create_unique_slug(item)

        if flush:
            session = self.session()
            with transaction(session):
                session.commit()
        return user_share_assoc

    def unshare_with(self, item, user: User, flush: bool = True):
        """
        Delete a user share from the database.
        """
        # Look for and delete sharing relation for user.
        user_share_assoc = self.get_share_assocs(item, user=user)[0]
        self.session().delete(user_share_assoc)
        if flush:
            session = self.session()
            with transaction(session):
                session.commit()
        return user_share_assoc

    def _query_shared_with(self, user, eagerloads=True, **kwargs):
        """
        Return a query for this model already filtered to models shared
        with a particular user.
        """
        query = self.session().query(self.model_class).join(self.model_class.users_shared_with)
        if eagerloads is False:
            query = query.enable_eagerloads(False)
        # TODO: as filter in FilterParser also
        query = query.filter(self.user_share_model.user == user)
        return self._filter_and_order_query(query, **kwargs)

    def list_shared_with(self, user, filters=None, order_by=None, limit=None, offset=None, **kwargs):
        """
        Return a list of those models shared with a particular user.
        """
        # TODO: refactor out dupl-code btwn base.list
        orm_filters, fn_filters = self._split_filters(filters)
        if not fn_filters:
            # if no fn_filtering required, we can use the 'all orm' version with limit offset
            query = self._query_shared_with(
                user, filters=orm_filters, order_by=order_by, limit=limit, offset=offset, **kwargs
            )
            return self._orm_list(query=query, **kwargs)

        # fn filters will change the number of items returnable by limit/offset - remove them here from the orm query
        query = self._query_shared_with(user, filters=orm_filters, order_by=order_by, limit=None, offset=None, **kwargs)
        # apply limit and offset afterwards
        items = self._apply_fn_filters_gen(query.all(), fn_filters)
        return list(self._apply_fn_limit_offset_gen(items, limit, offset))

    def get_sharing_extra_information(
        self, trans, item, users: Set[User], errors: Set[str], option: Optional[SharingOptions] = None
    ) -> Optional[ShareWithExtra]:
        """Returns optional extra information about the shareability of the given item.

        This function should be overridden in the particular manager class that wants
        to provide the extra information, otherwise, it will be None by default."""
        return None

    def make_members_public(self, trans, item):
        """Make potential elements of this item public.

        This method must be overridden in managers that need to change permissions of internal elements
        contained associated with the given item.
        """

    def update_current_sharing_with_users(self, item, new_users_shared_with: Set[User], flush=True):
        """Updates the currently list of users this item is shared with by adding new
        users and removing missing ones."""
        current_shares = self.get_share_assocs(item)
        currently_shared_with = {share.user for share in current_shares}

        needs_adding = new_users_shared_with - currently_shared_with
        for user in needs_adding:
            current_shares.append(self.share_with(item, user, flush=False))

        needs_removing = currently_shared_with - new_users_shared_with
        for user in needs_removing:
            current_shares.remove(self.unshare_with(item, user, flush=False))

        if flush:
            session = self.session()
            with transaction(session):
                session.commit()
        return current_shares, needs_adding, needs_removing

    # .... slugs
    # slugs are human readable strings often used to link to sharable resources (replacing ids)
    # TODO: as validator, deserializer, etc. (maybe another object entirely?)
    def set_slug(self, item, new_slug, user, flush=True):
        """
        Validate and set the new slug for `item`.
        """
        # precondition: has been validated
        if not base.is_valid_slug(new_slug):
            raise exceptions.RequestParameterInvalidException("Invalid slug", slug=new_slug)

        if item.slug == new_slug:
            return item

        session = self.session()

        # error if slug is already in use
        if slug_exists(session, item.__class__, user, new_slug):
            raise exceptions.Conflict("Slug already exists", slug=new_slug)

        item.slug = new_slug
        if flush:
            with transaction(session):
                session.commit()
        return item

    def _default_slug_base(self, item):
        # override in subclasses
        if hasattr(item, "title"):
            return item.title.lower()
        return item.name.lower()

    def get_unique_slug(self, item):
        """
        Returns a slug that is unique among user's importable items
        for item's class.
        """
        cur_slug = item.slug

        # Setup slug base.
        if cur_slug is None or cur_slug == "":
            slug_base = slugify(self._default_slug_base(item), allow_unicode=True)
        else:
            slug_base = cur_slug

        # Using slug base, find a slug that is not taken. If slug is taken,
        # add integer to end.
        new_slug = slug_base
        count = 1
        while importable_item_slug_exists(self.session(), item.__class__, item.user, new_slug):
            # Slug taken; choose a new slug based on count. This approach can
            # handle numerous items with the same name gracefully.
            new_slug = "%s-%i" % (slug_base, count)
            count += 1

        return new_slug

    def create_unique_slug(self, item, flush=True):
        """
        Set a new, unique slug on the item.
        """
        item.slug = self.get_unique_slug(item)
        self.session().add(item)
        if flush:
            session = self.session()
            with transaction(session):
                session.commit()
        return item

    # TODO: def by_slug( self, user, **kwargs ):


class SharableModelSerializer(
    base.ModelSerializer,
    taggable.TaggableSerializerMixin,
    annotatable.AnnotatableSerializerMixin,
    ratable.RatableSerializerMixin,
):
    # TODO: stub
    SINGLE_CHAR_ABBR: Optional[str] = None

    def __init__(self, app, **kwargs):
        super().__init__(app, **kwargs)
        self.add_view(
            "sharing",
            [
                "id",
                "title",
                "email_hash",
                "importable",
                "published",
                "username",
                "username_and_slug",
                "users_shared_with",
            ],
        )

    def add_serializers(self):
        super().add_serializers()
        taggable.TaggableSerializerMixin.add_serializers(self)
        annotatable.AnnotatableSerializerMixin.add_serializers(self)
        ratable.RatableSerializerMixin.add_serializers(self)
        self.serializers.update(
            {
                "id": self.serialize_id,
                "title": self.serialize_title,
                "username": self.serialize_username,
                "username_and_slug": self.serialize_username_and_slug,
                "users_shared_with": self.serialize_users_shared_with,
                "email_hash": self.serialize_email_hash,
            }
        )
        # these use the default serializer but must still be white-listed
        self.serializable_keyset.update(["importable", "published", "slug"])

    def serialize_email_hash(self, item, key, **context):
        if not (item.user and item.user.email):
            return None
        return md5_hash_str(item.user.email)

    def serialize_title(self, item, key, **context):
        if hasattr(item, "title"):
            return item.title
        elif hasattr(item, "name"):
            return item.name

    def serialize_username(self, item, key, **context):
        return item.user and item.user.username

    def serialize_username_and_slug(self, item, key, **context):
        if not (item.user and item.user.username and item.slug and self.SINGLE_CHAR_ABBR):
            return None
        return ("/").join(("u", item.user.username, self.SINGLE_CHAR_ABBR, item.slug))

    # the only ones that needs any fns:
    #   user/user_id
    #   username_and_slug?

    def serialize_users_shared_with(self, item, key, user=None, **context):
        """
        Returns a list of encoded ids for users the item has been shared.

        Skipped if the requesting user is not the owner.
        """
        # TODO: still an open question as to whether key removal based on user
        # should be handled here or at a higher level (even if we didn't have to pass user (via thread context, etc.))
        if not self.manager.is_owner(item, user):
            self.skip()

        share_assocs = self.manager.get_share_assocs(item)
        return [self.serialize_id(share, "user_id") for share in share_assocs]


class SharableModelDeserializer(
    base.ModelDeserializer,
    taggable.TaggableDeserializerMixin,
    annotatable.AnnotatableDeserializerMixin,
    ratable.RatableDeserializerMixin,
):
    def __init__(self, app: MinimalManagerApp, **kwargs):
        super().__init__(app, **kwargs)
        self.tag_handler = app.tag_handler

    def add_deserializers(self):
        super().add_deserializers()
        taggable.TaggableDeserializerMixin.add_deserializers(self)
        annotatable.AnnotatableDeserializerMixin.add_deserializers(self)
        ratable.RatableDeserializerMixin.add_deserializers(self)

        self.deserializers.update(
            {
                "published": self.deserialize_published,
                "importable": self.deserialize_importable,
                "users_shared_with": self.deserialize_users_shared_with,
            }
        )

    def deserialize_published(self, item, key, val, **context):
        """ """
        val = self.validate.bool(key, val)
        if item.published == val:
            return val

        if val:
            self.manager.publish(item, flush=False)
        else:
            self.manager.unpublish(item, flush=False)
        return item.published

    def deserialize_importable(self, item, key, val, **context):
        """ """
        val = self.validate.bool(key, val)
        if item.importable == val:
            return val

        if val:
            self.manager.make_importable(item, flush=False)
        else:
            self.manager.make_non_importable(item, flush=False)
        return item.importable

    # TODO: def deserialize_slug( self, item, val, **context ):

    def deserialize_users_shared_with(self, item, key, val, **context):
        """
        Accept a list of encoded user_ids, validate them as users, and then
        add or remove user shares in order to update the users_shared_with to
        match the given list finally returning the new list of shares.
        """
        unencoded_ids = [self.app.security.decode_id(id_) for id_ in val]
        new_users_shared_with = set(self.manager.user_manager.by_ids(unencoded_ids))
        current_shares, _, _ = self.manager.update_current_sharing_with_users(item, new_users_shared_with)
        # TODO: or should this return the list of ids?
        return current_shares


class SharableModelFilters(
    base.ModelFilterParser, taggable.TaggableFilterMixin, annotatable.AnnotatableFilterMixin, ratable.RatableFilterMixin
):
    def _add_parsers(self):
        super()._add_parsers()
        taggable.TaggableFilterMixin._add_parsers(self)
        annotatable.AnnotatableFilterMixin._add_parsers(self)
        ratable.RatableFilterMixin._add_parsers(self)

        self.orm_filter_parsers.update(
            {
                "importable": {"op": ("eq"), "val": base.parse_bool},
                "published": {"op": ("eq"), "val": base.parse_bool},
                "slug": {"op": ("eq", "contains", "like")},
                # chose by user should prob. only be available for admin? (most often we'll only need trans.user)
                # 'user'          : { 'op': ( 'eq' ), 'val': self.parse_id_list },
            }
        )


class SlugBuilder:
    """Builder for creating slugs out of items."""

    def create_item_slug(self, sa_session, item) -> bool:
        """Create/set item slug.

        Slug is unique among user's importable items for item's class.

        :param sa_session: Database session context.
        :param item: The item to create/update its slug.
        :type item: [type]
        :return: Returns true if item's slug was set/changed; false otherwise.
        :rtype: bool
        """
        cur_slug = item.slug

        # Setup slug base.
        if cur_slug is None or cur_slug == "":
            # Item can have either a name or a title.
            item_name = ""
            if hasattr(item, "name"):
                item_name = item.name
            elif hasattr(item, "title"):
                item_name = item.title
            slug_base = ready_name_for_url(item_name.lower())
        else:
            slug_base = cur_slug

        # Using slug base, find a slug that is not taken. If slug is taken,
        # add integer to end.
        new_slug = slug_base
        count = 1
        # Ensure unique across model class and user and don't include this item
        # in the check in case it has previously been assigned a valid slug.
        while another_slug_exists(sa_session, item.__class__, item.user, new_slug, item.id):
            # Slug taken; choose a new slug based on count. This approach can
            # handle numerous items with the same name gracefully.
            new_slug = f"{slug_base}-{count}"
            count += 1

        # Set slug and return.
        item.slug = new_slug
        return item.slug == cur_slug


def slug_exists(session, model_class, user, slug, ignore_deleted=False):
    stmt = select(exists().where(model_class.user == user).where(model_class.slug == slug))
    if ignore_deleted:  # Only check items that are NOT marked as deleted
        stmt = stmt.where(model_class.deleted == false())
    return session.scalar(stmt)


def importable_item_slug_exists(session, model_class, user, slug):
    stmt = select(
        exists().where(model_class.user == user).where(model_class.slug == slug).where(model_class.importable == true())
    )
    return session.scalar(stmt)


def another_slug_exists(session, model_class, user, slug, id):
    stmt = select(exists().where(model_class.user == user).where(model_class.slug == slug).where(model_class.id != id))
    return session.scalar(stmt)


__all__ = (
    "SharableModelDeserializer",
    "SharableModelFilters",
    "SharableModelManager",
    "SharableModelSerializer",
    "SharingOptions",
    "ShareWithExtra",
    "SlugBuilder",
)
