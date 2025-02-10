import logging
import re
from typing import (
    Dict,
    List,
    Optional,
    Tuple,
    TYPE_CHECKING,
)

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import select
from sqlalchemy.sql.expression import func

import galaxy.model
from galaxy.exceptions import ItemOwnershipException
from galaxy.model.scoped_session import galaxy_scoped_session
from galaxy.util import (
    strip_control_characters,
    unicodify,
)

if TYPE_CHECKING:
    from galaxy.model import (
        GalaxySession,
        Tag,
        User,
    )

log = logging.getLogger(__name__)


# Item-specific information needed to perform tagging.
class ItemTagAssocInfo:
    def __init__(self, item_class, tag_assoc_class, item_id_col):
        self.item_class = item_class
        self.tag_assoc_class = tag_assoc_class
        self.item_id_col = item_id_col


class TagHandler:
    """
    Manages CRUD operations related to tagging objects.
    """

    def __init__(self, sa_session: galaxy_scoped_session, galaxy_session=None) -> None:
        self.sa_session = sa_session
        # Minimum tag length.
        self.min_tag_len = 1
        # Maximum tag length.
        self.max_tag_len = 255
        # Tag separator.
        self.tag_separators = ",;"
        # Hierarchy separator.
        self.hierarchy_separator = "."
        # Key-value separator.
        self.key_value_separators = "=:"
        # Initialize with known classes - add to this in subclasses.
        self.item_tag_assoc_info: Dict[str, ItemTagAssocInfo] = {}
        # Can't include type annotation in signature, because lagom will attempt to look up
        # GalaxySession, but can't find it due to the circular import
        self.galaxy_session: Optional[GalaxySession] = galaxy_session

    def create_tag_handler_session(self, galaxy_session: Optional["GalaxySession"]):
        # Creates a transient tag handler that avoids repeated flushes
        return GalaxyTagHandlerSession(self.sa_session, galaxy_session=galaxy_session)

    def add_tags_from_list(self, user, item, new_tags_list, flush=True):
        new_tags_set = set(new_tags_list)
        if item.tags:
            new_tags_set.update(self.get_tags_str(item.tags).split(","))
        return self.set_tags_from_list(user, item, new_tags_set, flush=flush)

    def remove_tags_from_list(self, user, item, tag_to_remove_list, flush=True):
        tag_to_remove_set = set(tag_to_remove_list)
        tags_set = {_.strip() for _ in self.get_tags_str(item.tags).split(",")}
        if item.tags:
            tags_set -= tag_to_remove_set
        return self.set_tags_from_list(user, item, tags_set, flush=flush)

    def set_tags_from_list(
        self,
        user,
        item,
        new_tags_list,
        flush=True,
    ):
        # precondition: item is already security checked against user
        # precondition: incoming tags is a list of sanitized/formatted strings
        self.delete_item_tags(user, item)
        new_tags_str = ",".join(new_tags_list)
        self.apply_item_tags(user, item, unicodify(new_tags_str, "utf-8"), flush=flush)
        if flush:
            self.sa_session.commit()
        item.update()
        return item.tags

    def get_tag_assoc_class(self, item_class):
        """Returns tag association class for item class."""
        return self.item_tag_assoc_info[item_class.__name__].tag_assoc_class

    def get_id_col_in_item_tag_assoc_table(self, item_class):
        """Returns item id column in class' item-tag association table."""
        return self.item_tag_assoc_info[item_class.__name__].item_id_col

    def get_community_tags(self, item=None, limit=None):
        """Returns community tags for an item."""
        # Get item-tag association class.
        item_class = item.__class__
        item_tag_assoc_class = self.get_tag_assoc_class(item_class)
        if not item_tag_assoc_class:
            return []
        # Build select statement.
        from_obj = item_tag_assoc_class.table.join(item_class.table).join(galaxy.model.Tag.table)
        where_clause = self.get_id_col_in_item_tag_assoc_table(item_class) == item.id
        group_by = item_tag_assoc_class.table.c.tag_id
        # Do query and get result set.
        query = (
            select(item_tag_assoc_class.table.c.tag_id, func.count())
            .select_from(from_obj)
            .where(where_clause)
            .group_by(group_by)
            .order_by(func.count().desc())
            .limit(limit)
        )
        result_set = self.sa_session.execute(query)
        # Return community tags.
        community_tags = []
        for row in result_set:
            tag_id = row[0]
            community_tags.append(self.get_tag_by_id(tag_id))
        return community_tags

    def get_tool_tags(self):
        query = select(galaxy.model.ToolTagAssociation.table.c.tag_id).distinct()
        result_set = self.sa_session.execute(query)

        tags = []
        for row in result_set:
            tag_id = row[0]
            tags.append(self.get_tag_by_id(tag_id))
        return tags

    def remove_item_tag(self, user: "User", item, tag_name: str):
        """Remove a tag from an item."""
        self._ensure_user_owns_item(user, item)
        # Get item tag association.
        # Remove association.
        if item_tag_assoc := self._get_item_tag_assoc(user, item, tag_name):
            # Delete association.
            self.sa_session.delete(item_tag_assoc)
            item.tags.remove(item_tag_assoc)
            return True
        return False

    def delete_item_tags(self, user: Optional["User"], item):
        """Delete tags from an item."""
        self._ensure_user_owns_item(user, item)
        # Delete item-tag associations.
        for tag in item.tags:
            if tag.id:
                # Only can and need to delete tag if tag is persisted
                self.sa_session.delete(tag)
        # Delete tags from item.
        del item.tags[:]

    def _ensure_user_owns_item(self, user: Optional["User"], item):
        """Raises exception if user does not own item.
        Notice that even admin users cannot directly modify tags on items they do not own.
        To modify tags on items they don't own, admin users must impersonate the item's owner.
        """
        if getattr(item, "id", None) is None:
            # Item is not persisted, likely it is being copied from an existing, so no need
            # to check ownership at this point.
            return
        # Prefer checking ownership via history (or associated history).
        # When checking multiple items in batch this should save a few lazy-loads
        is_owner = False
        history = item if isinstance(item, galaxy.model.History) else getattr(item, "history", None)
        if not user:
            if self.galaxy_session and history:
                # anon users can only tag histories and history items,
                # and should only have a single history
                if history == self.galaxy_session.current_history:
                    return
            raise ItemOwnershipException("User does not own item.")
        user_id = history.user_id if history else getattr(item, "user_id", None)
        is_owner = user_id == user.id
        if not is_owner:
            raise ItemOwnershipException("User does not own item.")

    def item_has_tag(self, user, item, tag):
        """Returns true if item is has a given tag."""
        # Get tag name.
        tag_name = None
        if isinstance(tag, str):
            tag_name = tag
        elif isinstance(tag, galaxy.model.Tag):
            tag_name = tag.name
        elif isinstance(tag, galaxy.model.ItemTagAssociation):
            tag_name = tag.user_tname
        # Check for an item-tag association to see if item has a given tag.
        item_tag_assoc = self._get_item_tag_assoc(user, item, tag_name)
        if item_tag_assoc:
            return True
        return False

    def apply_item_tag(
        self,
        user: Optional["User"],
        item,
        name,
        value=None,
        flush=True,
    ):
        self._ensure_user_owns_item(user, item)
        # Use lowercase name for searching/creating tag.
        if name is None:
            return
        lc_name = name.lower()
        # Get or create item-tag association.
        item_tag_assoc = self._get_item_tag_assoc(user, item, lc_name)
        # If the association does not exist, or if it has a different value, add another.
        # We do allow multiple associations with different values.
        if not item_tag_assoc or (item_tag_assoc and item_tag_assoc.value != value):
            # Create item-tag association.
            # Create tag; if None, skip the tag (and log error).
            tag = self._get_or_create_tag(lc_name)
            if not tag:
                log.warning(f"Failed to create tag with name {lc_name}")
                return
            # Create tag association based on item class.
            item_tag_assoc_class = self.get_tag_assoc_class(item.__class__)
            item_tag_assoc = item_tag_assoc_class()
            # Add tag to association.
            item.tags.append(item_tag_assoc)
            item_tag_assoc.tag = tag
            item_tag_assoc.user = user
        # Apply attributes to item-tag association. Strip whitespace from user name and tag.
        lc_value = None
        if value:
            lc_value = value.lower()
        item_tag_assoc.user_tname = name
        item_tag_assoc.user_value = value
        item_tag_assoc.value = lc_value
        if flush:
            self.sa_session.commit()
        return item_tag_assoc

    def apply_item_tags(
        self,
        user: Optional["User"],
        item,
        tags_str: Optional[str],
        flush=True,
    ):
        """Apply tags to an item."""
        self._ensure_user_owns_item(user, item)
        # Parse tags.
        parsed_tags = self.parse_tags(tags_str)
        # Apply each tag.
        for name, value in parsed_tags:
            self.apply_item_tag(user, item, name, value, flush=flush)

    def get_tags_list(self, tags) -> List[str]:
        """Build a list of tags from an item's tags."""
        # Return empty list if there are no tags.
        if not tags:
            return []
        # Create list of tags.
        tags_list: List[str] = []
        for tag in tags:
            tag_str = tag.user_tname
            if tag.value is not None:
                tag_str += f":{tag.user_value}"
            tags_list.append(tag_str)
        return tags_list

    def get_tags_str(self, tags):
        """Build a string from an item's tags."""
        tags_list = self.get_tags_list(tags)
        # Return empty string if there are no tags.
        return ", ".join(tags_list)

    def get_tag_by_id(self, tag_id):
        """Get a Tag object from a tag id."""
        return self.sa_session.get(galaxy.model.Tag, tag_id)

    def get_tag_by_name(self, tag_name):
        """Get a Tag object from a tag name (string)."""
        if tag_name:
            return self.sa_session.scalars(select(galaxy.model.Tag).filter_by(name=tag_name.lower()).limit(1)).first()
        return None

    def _create_tag(self, tag_str: str):
        """
        Create or retrieve one or more Tag objects from a tag string. If there are multiple
        hierarchical tags in the tag string, the string will be split along `self.hierarchy_separator` chars.
        A Tag instance will be created for each non-empty prefix. If a prefix corresponds to the
        name of an existing tag, that tag will be retrieved; otherwise, a new Tag object will be created.
        For example, for the tag string `a.b.c` 3 Tag instances will be created: `a`, `a.b`, `a.b.c`.
        Return the last tag created (`a.b.c`).
        """
        tag_hierarchy = tag_str.split(self.hierarchy_separator)
        tag_prefix = ""
        parent_tag = None
        tag = None
        for sub_tag in tag_hierarchy:
            # Get or create subtag.
            sub_tag_name = self._scrub_tag_name(sub_tag)
            if sub_tag_name:
                tag_name = tag_prefix + sub_tag_name
                tag = self._get_tag(tag_name)
                if not tag:
                    tag = self._create_tag_instance(tag_name)
                # Set tag parent.
                tag.parent = parent_tag
                # Update parent and tag prefix.
                parent_tag = tag
                tag_prefix = tag.name + self.hierarchy_separator
        return tag

    def _get_tag(self, tag_name):
        return self.sa_session.scalars(select(galaxy.model.Tag).filter_by(name=tag_name).limit(1)).first()

    def _create_tag_instance(self, tag_name):
        # For good performance caller should first check if there's already an appropriate tag
        tag = galaxy.model.Tag(type=0, name=tag_name)
        if not self.sa_session:
            return tag
        Session = sessionmaker(self.sa_session.bind)
        with Session() as separate_session:
            separate_session.add(tag)
            try:
                separate_session.commit()
            except IntegrityError:
                # tag already exists, get from database
                separate_session.rollback()
        return self._get_tag(tag_name)

    def _get_or_create_tag(self, tag_str):
        """Get or create a Tag object from a tag string."""
        # Scrub tag; if tag is None after being scrubbed, return None.
        scrubbed_tag_str = self._scrub_tag_name(tag_str)
        if not scrubbed_tag_str:
            return None
        # Get item tag.
        tag = self.get_tag_by_name(scrubbed_tag_str)
        # Create tag if necessary.
        if tag is None:
            tag = self._create_tag(scrubbed_tag_str)
        return tag

    def _get_item_tag_assoc(self, user, item, tag_name):
        """
        Return ItemTagAssociation object for a user, item, and tag string; returns None if there is
        no such association.
        """
        scrubbed_tag_name = self._scrub_tag_name(tag_name)
        for item_tag_assoc in item.tags:
            if (item_tag_assoc.user == user) and (item_tag_assoc.user_tname == scrubbed_tag_name):
                return item_tag_assoc
        return None

    def parse_tags(self, tag_str):
        """
        Return a list of tag tuples (name, value) pairs derived from a string.

        >>> th = TagHandler("bridge_of_death")
        >>> assert th.parse_tags("#ARTHUR") == [('name', 'ARTHUR')]
        >>> tags = th.parse_tags("name:Lancelot of Camelot;#Holy Grail;blue")
        >>> assert tags == [('name', 'LancelotofCamelot'), ('name', 'HolyGrail'), ('blue', None)]
        """
        # Gracefully handle None.
        if not tag_str:
            return {}
        # Strip unicode control characters
        tag_str = strip_control_characters(tag_str)
        # Split tags based on separators.
        reg_exp = re.compile(f"[{self.tag_separators}]")
        raw_tags = reg_exp.split(tag_str)
        return self.parse_tags_list(raw_tags)

    def parse_tags_list(self, tags_list: List[str]) -> List[Tuple[str, Optional[str]]]:
        """
        Return a list of tag tuples (name, value) pairs derived from a list.
        Method scrubs tag names and values as well.

        >>> th = TagHandler("bridge_of_death")
        >>> tags = th.parse_tags_list(["name:Lancelot of Camelot", "#Holy Grail", "blue"])
        >>> assert tags == [('name', 'LancelotofCamelot'), ('name', 'HolyGrail'), ('blue', None)]
        """
        name_value_pairs = []
        for raw_tag in tags_list:
            nv_pair = self._get_name_value_pair(raw_tag)
            scrubbed_name = self._scrub_tag_name(nv_pair[0])
            scrubbed_value = self._scrub_tag_value(nv_pair[1])
            # Append tag_name, tag_value tuple -- TODO use NamedTuple
            name_value_pairs.append((scrubbed_name, scrubbed_value))
        return name_value_pairs

    def _scrub_tag_value(self, value):
        """Scrub a tag value."""
        # Gracefully handle None:
        if not value:
            return None
        # Remove whitespace from value.
        reg_exp = re.compile(r"\s")
        scrubbed_value = re.sub(reg_exp, "", value)
        return scrubbed_value

    def _scrub_tag_name(self, name):
        """Scrub a tag name."""
        # Gracefully handle None:
        if not name:
            return None
        # Remove whitespace from name.
        reg_exp = re.compile(r"\s")
        scrubbed_name = re.sub(reg_exp, "", name)
        # Ignore starting ':' char.
        if scrubbed_name.startswith(self.hierarchy_separator):
            scrubbed_name = scrubbed_name[1:]
        # If name is too short or too long, return None.
        if len(scrubbed_name) < self.min_tag_len or len(scrubbed_name) > self.max_tag_len:
            return None
        return scrubbed_name

    def _scrub_tag_name_list(self, tag_name_list):
        """Scrub a tag name list."""
        scrubbed_tag_list = []
        for tag in tag_name_list:
            scrubbed_tag_list.append(self._scrub_tag_name(tag))
        return scrubbed_tag_list

    def _get_name_value_pair(self, tag_str) -> List[Optional[str]]:
        """Get name, value pair from a tag string."""
        # Use regular expression to parse name, value.
        if tag_str.startswith("#"):
            tag_str = f"name:{tag_str[1:]}"
        reg_exp = re.compile(f"[{self.key_value_separators}]")
        name_value_pair: List[Optional[str]] = list(reg_exp.split(tag_str, 1))
        # Add empty slot if tag does not have value.
        if len(name_value_pair) < 2:
            name_value_pair.append(None)
        return name_value_pair


class GalaxyTagHandler(TagHandler):
    _item_tag_assoc_info: Dict[str, ItemTagAssocInfo] = {}

    def __init__(self, sa_session: galaxy_scoped_session, galaxy_session=None):
        TagHandler.__init__(self, sa_session, galaxy_session=galaxy_session)
        if not GalaxyTagHandler._item_tag_assoc_info:
            GalaxyTagHandler.init_tag_associations()
        self.item_tag_assoc_info = GalaxyTagHandler._item_tag_assoc_info

    @classmethod
    def init_tag_associations(cls):
        from galaxy import model

        cls._item_tag_assoc_info = {
            "History": ItemTagAssocInfo(
                model.History, model.HistoryTagAssociation, model.HistoryTagAssociation.history_id
            ),
            "HistoryDatasetAssociation": ItemTagAssocInfo(
                model.HistoryDatasetAssociation,
                model.HistoryDatasetAssociationTagAssociation,
                model.HistoryDatasetAssociationTagAssociation.history_dataset_association_id,
            ),
            "HistoryDatasetCollectionAssociation": ItemTagAssocInfo(
                model.HistoryDatasetCollectionAssociation,
                model.HistoryDatasetCollectionTagAssociation,
                model.HistoryDatasetCollectionTagAssociation.history_dataset_collection_id,
            ),
            "LibraryDatasetDatasetAssociation": ItemTagAssocInfo(
                model.LibraryDatasetDatasetAssociation,
                model.LibraryDatasetDatasetAssociationTagAssociation,
                model.LibraryDatasetDatasetAssociationTagAssociation.library_dataset_dataset_association_id,
            ),
            "Page": ItemTagAssocInfo(model.Page, model.PageTagAssociation, model.PageTagAssociation.page_id),
            "StoredWorkflow": ItemTagAssocInfo(
                model.StoredWorkflow,
                model.StoredWorkflowTagAssociation,
                model.StoredWorkflowTagAssociation.stored_workflow_id,
            ),
            "Visualization": ItemTagAssocInfo(
                model.Visualization,
                model.VisualizationTagAssociation,
                model.VisualizationTagAssociation.visualization_id,
            ),
        }
        return cls._item_tag_assoc_info


class GalaxyTagHandlerSession(GalaxyTagHandler):
    """Like GalaxyTagHandler, but avoids one flush per created tag."""

    def __init__(self, sa_session, galaxy_session: Optional["GalaxySession"]):
        super().__init__(sa_session, galaxy_session)
        self.created_tags: Dict[str, Tag] = {}

    def _get_tag(self, tag_name):
        """Get tag from cache or database."""
        # Avoids creating multiple new tags with the same tag_name, which violates unique key constraint
        return self.created_tags.get(tag_name) or super(GalaxyTagHandler, self)._get_tag(tag_name)

    def _create_tag_instance(self, tag_name):
        """Create tag and and store in cache."""
        tag = super()._create_tag_instance(tag_name)
        self.created_tags[tag_name] = tag
        return tag


class GalaxySessionlessTagHandler(GalaxyTagHandlerSession):
    def _ensure_user_owns_item(self, user: Optional["User"], item):
        # In sessionless mode we don't need to check ownership, we're only exporting
        pass

    def _get_tag(self, tag_name):
        """Get tag from cache or database."""
        # Short-circuit session access
        return self.created_tags.get(tag_name)

    def get_tag_by_name(self, tag_name):
        return self.created_tags.get(tag_name)


class CommunityTagHandler(TagHandler):
    def __init__(self, sa_session):
        TagHandler.__init__(self, sa_session)
