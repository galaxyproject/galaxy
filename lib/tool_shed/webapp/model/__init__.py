import logging
import os
import weakref
from datetime import (
    datetime,
    timedelta,
)
from typing import (
    Any,
    Mapping,
    TYPE_CHECKING,
)

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    desc,
    false,
    ForeignKey,
    Integer,
    not_,
    String,
    Table,
    TEXT,
    true,
    UniqueConstraint,
)
from sqlalchemy.orm import (
    registry,
    relationship,
)
from sqlalchemy.orm.decl_api import DeclarativeMeta

import tool_shed.repository_types.util as rt_util
from galaxy import util
from galaxy.model.custom_types import (
    MutableJSONType,
    TrimmedString,
)
from galaxy.model.orm.now import now
from galaxy.model.orm.util import add_object_to_object_session
from galaxy.security.validate_user_input import validate_password_str
from galaxy.util import unique_id
from galaxy.util.bunch import Bunch
from galaxy.util.dictifiable import Dictifiable
from galaxy.util.hash_util import new_secure_hash
from tool_shed.dependencies.repository import relation_builder
from tool_shed.util import (
    hg_util,
    metadata_util,
)
from tool_shed.util.hgweb_config import hgweb_config_manager

log = logging.getLogger(__name__)

WEAK_HG_REPO_CACHE: Mapping["Repository", Any] = weakref.WeakKeyDictionary()

if TYPE_CHECKING:

    class _HasTable:
        table: Table

else:
    _HasTable = object


mapper_registry = registry()


class Base(metaclass=DeclarativeMeta):
    __abstract__ = True
    registry = mapper_registry
    metadata = mapper_registry.metadata
    __init__ = mapper_registry.constructor

    @classmethod
    def __declare_last__(cls):
        cls.table = cls.__table__


class APIKeys(Base, _HasTable):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True)
    create_time = Column(DateTime, default=now)
    user_id = Column(ForeignKey("galaxy_user.id"), index=True)
    key = Column(TrimmedString(32), index=True, unique=True)
    user = relationship("User", back_populates="api_keys")


class User(Base, Dictifiable, _HasTable):
    __tablename__ = "galaxy_user"

    id = Column(Integer, primary_key=True)
    create_time = Column(DateTime, default=now)
    update_time = Column(DateTime, default=now, onupdate=now)
    email = Column(TrimmedString(255), nullable=False)
    username = Column(String(255), index=True)
    password = Column(TrimmedString(40), nullable=False)
    external = Column(Boolean, default=False)
    new_repo_alert = Column(Boolean, default=False)
    deleted = Column(Boolean, index=True, default=False)
    purged = Column(Boolean, index=True, default=False)
    active_repositories = relationship(
        "Repository",
        primaryjoin=(lambda: (Repository.user_id == User.id) & (not_(Repository.deleted))),  # type: ignore[has-type]
        back_populates="user",
        order_by=lambda: desc(Repository.name),  # type: ignore[has-type]
    )
    galaxy_sessions = relationship(
        "GalaxySession", back_populates="user", order_by=lambda: desc(GalaxySession.update_time)  # type: ignore[has-type]
    )
    api_keys = relationship("APIKeys", back_populates="user", order_by=lambda: desc(APIKeys.create_time))
    reset_tokens = relationship("PasswordResetToken", back_populates="user")
    groups = relationship("UserGroupAssociation", back_populates="user")

    dict_collection_visible_keys = ["id", "username"]
    dict_element_visible_keys = ["id", "username"]
    bootstrap_admin_user = False
    roles = relationship("UserRoleAssociation", back_populates="user")
    non_private_roles = relationship(
        "UserRoleAssociation",
        viewonly=True,
        primaryjoin=(
            lambda: (User.id == UserRoleAssociation.user_id)  # type: ignore[has-type]
            & (UserRoleAssociation.role_id == Role.id)  # type: ignore[has-type]
            & not_(Role.name == User.email)  # type: ignore[has-type]
        ),
    )
    repository_reviews = relationship("RepositoryReview", back_populates="user")

    def __init__(self, email=None, password=None):
        self.email = email
        self.password = password
        self.external = False
        self.deleted = False
        self.purged = False
        self.new_repo_alert = False

    def all_roles(self):
        roles = [ura.role for ura in self.roles]
        for group in [uga.group for uga in self.groups]:
            for role in [gra.role for gra in group.roles]:
                if role not in roles:
                    roles.append(role)
        return roles

    def check_password(self, cleartext):
        """Check if 'cleartext' matches 'self.password' when hashed."""
        return self.password == new_secure_hash(text_type=cleartext)

    def get_disk_usage(self, nice_size=False):
        return 0

    @property
    def nice_total_disk_usage(self):
        return 0

    def set_disk_usage(self, bytes):
        pass

    total_disk_usage = property(get_disk_usage, set_disk_usage)

    def set_password_cleartext(self, cleartext):
        message = validate_password_str(cleartext)
        if message:
            raise Exception(f"Invalid password: {message}")
        # Set 'self.password' to the digest of 'cleartext'.
        self.password = new_secure_hash(text_type=cleartext)


class PasswordResetToken(Base, _HasTable):
    __tablename__ = "password_reset_token"

    token = Column(String(32), primary_key=True, unique=True, index=True)
    expiration_time = Column(DateTime)
    user_id = Column(ForeignKey("galaxy_user.id"), index=True)
    user = relationship("User", back_populates="reset_tokens")

    def __init__(self, user, token=None):
        if token:
            self.token = token
        else:
            self.token = unique_id()
        add_object_to_object_session(self, user)
        self.user = user
        self.expiration_time = now() + timedelta(hours=24)


class Group(Base, Dictifiable, _HasTable):
    __tablename__ = "galaxy_group"

    id = Column(Integer, primary_key=True)
    create_time = Column(DateTime, default=now)
    update_time = Column(DateTime, default=now, onupdate=now)
    name = Column(String(255), index=True, unique=True)
    deleted = Column(Boolean, index=True, default=False)
    roles = relationship("GroupRoleAssociation", back_populates="group")
    users = relationship("UserGroupAssociation", back_populates="group")

    dict_collection_visible_keys = ["id", "name"]
    dict_element_visible_keys = ["id", "name"]

    def __init__(self, name=None):
        self.name = name
        self.deleted = False


class Role(Base, Dictifiable, _HasTable):
    __tablename__ = "role"

    id = Column(Integer, primary_key=True)
    create_time = Column(DateTime, default=now)
    update_time = Column(DateTime, default=now, onupdate=now)
    name = Column(String(255), index=True, unique=True)
    description = Column(TEXT)
    type = Column(String(40), index=True)
    deleted = Column(Boolean, index=True, default=False)
    repositories = relationship("RepositoryRoleAssociation", back_populates="role")
    groups = relationship("GroupRoleAssociation", back_populates="role")
    users = relationship("UserRoleAssociation", back_populates="role")

    dict_collection_visible_keys = ["id", "name"]
    dict_element_visible_keys = ["id", "name", "description", "type"]
    private_id = None
    types = Bunch(PRIVATE="private", SYSTEM="system", USER="user", ADMIN="admin", SHARING="sharing")

    def __init__(self, name=None, description=None, type=types.SYSTEM, deleted=False):
        self.name = name
        self.description = description
        self.type = type
        self.deleted = deleted

    @property
    def is_repository_admin_role(self):
        # A repository admin role must always be associated with a repository. The mapper returns an
        # empty list for those roles that have no repositories.  This method will require changes if
        # new features are introduced that results in more than one role per repository.
        if self.repositories:
            return True
        return False


class UserGroupAssociation(Base, _HasTable):
    __tablename__ = "user_group_association"

    id = Column(Integer, primary_key=True)
    user_id = Column(ForeignKey("galaxy_user.id"), index=True)
    group_id = Column(ForeignKey("galaxy_group.id"), index=True)
    create_time = Column(DateTime, default=now)
    update_time = Column(DateTime, default=now, onupdate=now)
    user = relationship("User", back_populates="groups")
    group = relationship("Group", back_populates="users")

    def __init__(self, user, group):
        add_object_to_object_session(self, user)
        self.user = user
        self.group = group


class UserRoleAssociation(Base, _HasTable):
    __tablename__ = "user_role_association"

    id = Column(Integer, primary_key=True)
    user_id = Column(ForeignKey("galaxy_user.id"), index=True)
    role_id = Column(ForeignKey("role.id"), index=True)
    create_time = Column(DateTime, default=now)
    update_time = Column(DateTime, default=now, onupdate=now)
    user = relationship("User", back_populates="roles")
    role = relationship("Role", back_populates="users")

    def __init__(self, user, role):
        add_object_to_object_session(self, user)
        self.user = user
        add_object_to_object_session(self, role)
        self.role = role


class GroupRoleAssociation(Base, _HasTable):
    __tablename__ = "group_role_association"

    id = Column(Integer, primary_key=True)
    group_id = Column(ForeignKey("galaxy_group.id"), index=True)
    role_id = Column(ForeignKey("role.id"), index=True)
    create_time = Column(DateTime, default=now)
    update_time = Column(DateTime, default=now, onupdate=now)
    group = relationship("Group", back_populates="roles")
    role = relationship("Role", back_populates="groups")

    def __init__(self, group, role):
        self.group = group
        self.role = role


class RepositoryRoleAssociation(Base, _HasTable):
    __tablename__ = "repository_role_association"

    id = Column(Integer, primary_key=True)
    repository_id = Column(ForeignKey("repository.id"), index=True)
    role_id = Column(ForeignKey("role.id"), index=True)
    create_time = Column(DateTime, default=now)
    update_time = Column(DateTime, default=now, onupdate=now)
    repository = relationship("Repository", back_populates="roles")
    role = relationship("Role", back_populates="repositories")

    def __init__(self, repository, role):
        add_object_to_object_session(self, repository)
        self.repository = repository
        self.role = role


class GalaxySession(Base, _HasTable):
    __tablename__ = "galaxy_session"

    id = Column(Integer, primary_key=True)
    create_time = Column(DateTime, default=now)
    update_time = Column(DateTime, default=now, onupdate=now)
    user_id = Column(ForeignKey("galaxy_user.id"), index=True, nullable=True)
    remote_host = Column(String(255))
    remote_addr = Column(String(255))
    referer = Column(TEXT)
    # unique 128 bit random number coerced to a string
    session_key = Column(TrimmedString(255), index=True, unique=True)
    is_valid = Column(Boolean, default=False)
    # saves a reference to the previous session so we have a way to chain them together
    prev_session_id = Column(Integer)
    last_action = Column(DateTime)
    user = relationship("User", back_populates="galaxy_sessions")

    def __init__(self, is_valid=False, **kwd):
        super().__init__(**kwd)
        self.is_valid = is_valid
        self.last_action = self.last_action or datetime.now()


class Repository(Base, Dictifiable, _HasTable):
    __tablename__ = "repository"

    id = Column(Integer, primary_key=True)
    create_time = Column(DateTime, default=now)
    update_time = Column(DateTime, default=now, onupdate=now)
    name = Column(TrimmedString(255), index=True)
    type = Column(TrimmedString(255), index=True)
    remote_repository_url = Column(TrimmedString(255))
    homepage_url = Column(TrimmedString(255))
    description = Column(TEXT)
    long_description = Column(TEXT)
    user_id = Column(ForeignKey("galaxy_user.id"), index=True)
    private = Column(Boolean, default=False)
    deleted = Column(Boolean, index=True, default=False)
    email_alerts = Column(MutableJSONType, nullable=True)
    times_downloaded = Column(Integer)
    deprecated = Column(Boolean, default=False)
    categories = relationship("RepositoryCategoryAssociation", back_populates="repository")
    ratings = relationship(
        "RepositoryRatingAssociation",
        order_by=lambda: desc(RepositoryRatingAssociation.update_time),
        back_populates="repository",
    )
    user = relationship("User", back_populates="active_repositories")
    downloadable_revisions = relationship(
        "RepositoryMetadata",
        primaryjoin=lambda: (Repository.id == RepositoryMetadata.repository_id) & (RepositoryMetadata.downloadable == true()),  # type: ignore[attr-defined,has-type]
        viewonly=True,
        order_by=lambda: desc(RepositoryMetadata.update_time),  # type: ignore[attr-defined]
    )
    metadata_revisions = relationship(
        "RepositoryMetadata",
        order_by=lambda: desc(RepositoryMetadata.update_time),  # type: ignore[attr-defined]
        back_populates="repository",
    )
    roles = relationship("RepositoryRoleAssociation", back_populates="repository")
    reviews = relationship("RepositoryReview", back_populates="repository")
    reviewers = relationship("User", secondary=lambda: RepositoryReview.__table__, viewonly=True)  # type: ignore

    dict_collection_visible_keys = [
        "id",
        "name",
        "type",
        "remote_repository_url",
        "homepage_url",
        "description",
        "user_id",
        "private",
        "deleted",
        "times_downloaded",
        "deprecated",
        "create_time",
    ]
    dict_element_visible_keys = [
        "id",
        "name",
        "type",
        "remote_repository_url",
        "homepage_url",
        "description",
        "long_description",
        "user_id",
        "private",
        "deleted",
        "times_downloaded",
        "deprecated",
        "create_time",
    ]
    file_states = Bunch(NORMAL="n", NEEDS_MERGING="m", MARKED_FOR_REMOVAL="r", MARKED_FOR_ADDITION="a", NOT_TRACKED="?")

    def __init__(self, private=False, times_downloaded=0, deprecated=False, **kwd):
        super().__init__(**kwd)
        self.private = private
        self.times_downloaded = times_downloaded
        self.deprecated = deprecated
        self.name = self.name or "Unnamed repository"

    @property
    def hg_repo(self):
        from mercurial import (
            hg,
            ui,
        )

        if not WEAK_HG_REPO_CACHE.get(self):
            WEAK_HG_REPO_CACHE[self] = hg.cachedlocalrepo(hg.repository(ui.ui(), self.repo_path().encode("utf-8")))
        return WEAK_HG_REPO_CACHE[self].fetch()[0]

    @property
    def admin_role(self):
        admin_role_name = f"{str(self.name)}_{str(self.user.username)}_admin"
        for rra in self.roles:
            role = rra.role
            if str(role.name) == admin_role_name:
                return role
        raise Exception(
            "Repository %s owned by %s is not associated with a required administrative role."
            % (str(self.name), str(self.user.username))
        )

    def allow_push(self):
        hgrc_file = hg_util.get_hgrc_path(self.repo_path())
        with open(hgrc_file) as fh:
            for line in fh.read().splitlines():
                if line.startswith("allow_push = "):
                    return line[len("allow_push = ") :]
        return ""

    def can_change_type(self):
        # Allow changing the type only if the repository has no contents, has never been installed, or has
        # never been changed from the default type.
        if self.is_new():
            return True
        if self.times_downloaded == 0:
            return True
        if self.type == rt_util.UNRESTRICTED:
            return True
        return False

    def can_change_type_to(self, app, new_type_label):
        if self.type == new_type_label:
            return False
        if self.can_change_type():
            new_type = app.repository_types_registry.get_class_by_label(new_type_label)
            if new_type.is_valid_for_type(self):
                return True
        return False

    def get_changesets_for_setting_metadata(self, app):
        type_class = self.get_type_class(app)
        return type_class.get_changesets_for_setting_metadata(app, self)

    def get_repository_dependencies(self, app, changeset, toolshed_url):
        # We aren't concerned with repositories of type tool_dependency_definition here if a
        # repository_metadata record is not returned because repositories of this type will never
        # have repository dependencies. However, if a readme file is uploaded, or some other change
        # is made that does not create a new downloadable changeset revision but updates the existing
        # one, we still want to be able to get repository dependencies.
        repository_metadata = metadata_util.get_current_repository_metadata_for_changeset_revision(app, self, changeset)
        if repository_metadata:
            metadata = repository_metadata.metadata
            if metadata:
                rb = relation_builder.RelationBuilder(app, self, repository_metadata, toolshed_url)
                repository_dependencies = rb.get_repository_dependencies_for_changeset_revision()
                if repository_dependencies:
                    return repository_dependencies
        return None

    def get_type_class(self, app):
        return app.repository_types_registry.get_class_by_label(self.type)

    def get_tool_dependencies(self, app, changeset_revision):
        changeset_revision = metadata_util.get_next_downloadable_changeset_revision(app, self, changeset_revision)
        for downloadable_revision in self.downloadable_revisions:
            if downloadable_revision.changeset_revision == changeset_revision:
                return downloadable_revision.metadata.get("tool_dependencies", {})
        return {}

    def installable_revisions(self, app, sort_revisions=True):
        return metadata_util.get_metadata_revisions(app, self, sort_revisions=sort_revisions)

    def is_new(self):
        tip_rev = self.hg_repo.changelog.tiprev()
        return tip_rev < 0

    def repo_path(self, app=None):
        # Keep app argument for compatibility with tool_shed_install Repository model
        return hgweb_config_manager.get_entry(os.path.join("repos", self.user.username, self.name))

    def revision(self):
        repo = self.hg_repo
        tip_ctx = repo[repo.changelog.tip()]
        return f"{str(tip_ctx.rev())}:{str(tip_ctx)}"

    def set_allow_push(self, usernames, remove_auth=""):
        allow_push = util.listify(self.allow_push())
        if remove_auth:
            allow_push.remove(remove_auth)
        else:
            for username in util.listify(usernames):
                if username not in allow_push:
                    allow_push.append(username)
        allow_push = f"{','.join(allow_push)}\n"
        # Why doesn't the following work?
        # repo.ui.setconfig('web', 'allow_push', allow_push)
        repo_dir = self.repo_path()
        hgrc_file = hg_util.get_hgrc_path(repo_dir)
        with open(hgrc_file) as fh:
            lines = fh.readlines()
        with open(hgrc_file, "w") as fh:
            for line in lines:
                if line.startswith("allow_push"):
                    fh.write(f"allow_push = {allow_push}")
                else:
                    fh.write(line)

    def tip(self):
        repo = self.hg_repo
        return str(repo[repo.changelog.tip()])

    def to_dict(self, view="collection", value_mapper=None):
        rval = super().to_dict(view=view, value_mapper=value_mapper)
        if "user_id" in rval:
            rval["owner"] = self.user.username
        return rval


class RepositoryReview(Base, Dictifiable, _HasTable):
    __tablename__ = "repository_review"

    id = Column(Integer, primary_key=True)
    create_time = Column(DateTime, default=now)
    update_time = Column(DateTime, default=now, onupdate=now)
    repository_id = Column(ForeignKey("repository.id"), index=True)
    changeset_revision = Column(TrimmedString(255), index=True)
    user_id = Column(ForeignKey("galaxy_user.id"), index=True, nullable=False)
    approved = Column(TrimmedString(255))
    rating = Column(Integer, index=True)
    deleted = Column(Boolean, index=True, default=False)
    repository = relationship("Repository", back_populates="reviews")
    # Take care when using the mapper below!  It should be used only when a new review is being created for a repository change set revision.
    # Keep in mind that repository_metadata records can be removed from the database for certain change set revisions when metadata is being
    # reset on a repository!
    repository_metadata = relationship(
        "RepositoryMetadata",
        viewonly=True,
        foreign_keys=lambda: [RepositoryReview.repository_id, RepositoryReview.changeset_revision],
        primaryjoin=lambda: (
            (RepositoryReview.repository_id == RepositoryMetadata.repository_id)  # type: ignore[has-type]
            & (RepositoryReview.changeset_revision == RepositoryMetadata.changeset_revision)  # type: ignore[has-type]
        ),
        back_populates="reviews",
    )
    user = relationship("User", back_populates="repository_reviews")

    component_reviews = relationship(
        "ComponentReview",
        viewonly=True,
        primaryjoin=lambda: (
            (RepositoryReview.id == ComponentReview.repository_review_id)  # type: ignore[has-type]
            & (ComponentReview.deleted == false())  # type: ignore[has-type]
        ),
        back_populates="repository_review",
    )

    private_component_reviews = relationship(
        "ComponentReview",
        viewonly=True,
        primaryjoin=lambda: (
            (RepositoryReview.id == ComponentReview.repository_review_id)  # type: ignore[has-type]
            & (ComponentReview.deleted == false())  # type: ignore[has-type]
            & (ComponentReview.private == true())  # type: ignore[has-type]
        ),
    )

    dict_collection_visible_keys = ["id", "repository_id", "changeset_revision", "user_id", "rating", "deleted"]
    dict_element_visible_keys = ["id", "repository_id", "changeset_revision", "user_id", "rating", "deleted"]
    approved_states = Bunch(NO="no", YES="yes")

    def __init__(self, deleted=False, **kwd):
        super().__init__(**kwd)
        self.deleted = deleted


class ComponentReview(Base, Dictifiable, _HasTable):
    __tablename__ = "component_review"

    id = Column(Integer, primary_key=True)
    create_time = Column(DateTime, default=now)
    update_time = Column(DateTime, default=now, onupdate=now)
    repository_review_id = Column(ForeignKey("repository_review.id"), index=True)
    component_id = Column(ForeignKey("component.id"), index=True)
    comment = Column(TEXT)
    private = Column(Boolean, default=False)
    approved = Column(TrimmedString(255))
    rating = Column(Integer)
    deleted = Column(Boolean, index=True, default=False)
    repository_review = relationship("RepositoryReview", back_populates="component_reviews")
    component = relationship("Component")

    dict_collection_visible_keys = [
        "id",
        "repository_review_id",
        "component_id",
        "private",
        "approved",
        "rating",
        "deleted",
    ]
    dict_element_visible_keys = [
        "id",
        "repository_review_id",
        "component_id",
        "private",
        "approved",
        "rating",
        "deleted",
    ]
    approved_states = Bunch(NO="no", YES="yes", NA="not_applicable")

    def __init__(self, private=False, approved=False, deleted=False, **kwd):
        super().__init__(**kwd)
        self.private = private
        self.approved = approved
        self.deleted = deleted


class Component(Base, _HasTable):
    __tablename__ = "component"

    id = Column(Integer, primary_key=True)
    name = Column(TrimmedString(255))
    description = Column(TEXT)


class ItemRatingAssociation(_HasTable):
    def __init__(self, id=None, user=None, item=None, rating=0, comment=""):
        self.id = id
        self.user = user
        self.item = item
        self.rating = rating
        self.comment = comment

    def set_item(self, item):
        """Set association's item."""


class RepositoryRatingAssociation(Base, ItemRatingAssociation, _HasTable):
    __tablename__ = "repository_rating_association"

    id = Column(Integer, primary_key=True)
    create_time = Column(DateTime, default=now)
    update_time = Column(DateTime, default=now, onupdate=now)
    repository_id = Column(ForeignKey("repository.id"), index=True)
    user_id = Column(ForeignKey("galaxy_user.id"), index=True)
    rating = Column(Integer, index=True)
    comment = Column(TEXT)
    repository = relationship("Repository", back_populates="ratings")
    user = relationship("User")

    def set_item(self, repository):
        self.repository = repository


class Category(Base, Dictifiable, _HasTable):
    __tablename__ = "category"

    id = Column(Integer, primary_key=True)
    create_time = Column(DateTime, default=now)
    update_time = Column(DateTime, default=now, onupdate=now)
    name = Column(TrimmedString(255), index=True, unique=True)
    description = Column(TEXT)
    deleted = Column(Boolean, index=True, default=False)
    repositories = relationship("RepositoryCategoryAssociation", back_populates="category")

    dict_collection_visible_keys = ["id", "name", "description", "deleted"]
    dict_element_visible_keys = ["id", "name", "description", "deleted"]

    def __init__(self, deleted=False, **kwd):
        super().__init__(**kwd)
        self.deleted = deleted


class RepositoryCategoryAssociation(Base, _HasTable):
    __tablename__ = "repository_category_association"

    id = Column(Integer, primary_key=True)
    repository_id = Column(ForeignKey("repository.id"), index=True)
    category_id = Column(ForeignKey("category.id"), index=True)
    category = relationship("Category", back_populates="repositories")
    repository = relationship("Repository", back_populates="categories")

    def __init__(self, repository=None, category=None):
        self.repository = repository
        self.category = category


class Tag(Base, _HasTable):
    __tablename__ = "tag"
    __table_args__ = (UniqueConstraint("name"),)

    id = Column(Integer, primary_key=True)
    type = Column(Integer)
    parent_id = Column(ForeignKey("tag.id"))
    name = Column(TrimmedString(255))
    children = relationship("Tag", back_populates="parent")
    parent = relationship("Tag", back_populates="children", remote_side=[id])

    def __str__(self):
        return "Tag(id=%s, type=%i, parent_id=%s, name=%s)" % (self.id, self.type, self.parent_id, self.name)


# The RepositoryMetadata model is mapped imperatively (for details see discussion in PR #12064).
# TLDR: a declaratively-mapped class cannot have a .metadata attribute (it is used by SQLAlchemy's DeclarativeBase).


class RepositoryMetadata(Dictifiable, _HasTable):
    # Once the class has been mapped, all Column items in this table will be available
    # as instrumented class attributes on RepositoryMetadata.
    table = Table(
        "repository_metadata",
        mapper_registry.metadata,
        Column("id", Integer, primary_key=True),
        Column("create_time", DateTime, default=now),
        Column("update_time", DateTime, default=now, onupdate=now),
        Column("repository_id", ForeignKey("repository.id"), index=True),
        Column("changeset_revision", TrimmedString(255), index=True),
        Column("numeric_revision", Integer, index=True),
        Column("metadata", MutableJSONType, nullable=True),
        Column("tool_versions", MutableJSONType, nullable=True),
        Column("malicious", Boolean, default=False),
        Column("downloadable", Boolean, default=True),
        Column("missing_test_components", Boolean, default=False, index=True),
        Column("has_repository_dependencies", Boolean, default=False, index=True),
        Column("includes_datatypes", Boolean, default=False, index=True),
        Column("includes_tools", Boolean, default=False, index=True),
        Column("includes_tool_dependencies", Boolean, default=False, index=True),
        Column("includes_workflows", Boolean, default=False, index=True),
    )

    dict_collection_visible_keys = [
        "id",
        "repository_id",
        "numeric_revision",
        "changeset_revision",
        "malicious",
        "downloadable",
        "missing_test_components",
        "has_repository_dependencies",
        "includes_datatypes",
        "includes_tools",
        "includes_tool_dependencies",
        "includes_tools_for_display_in_tool_panel",
        "includes_workflows",
    ]
    dict_element_visible_keys = [
        "id",
        "repository_id",
        "numeric_revision",
        "changeset_revision",
        "malicious",
        "downloadable",
        "missing_test_components",
        "has_repository_dependencies",
        "includes_datatypes",
        "includes_tools",
        "includes_tool_dependencies",
        "includes_tools_for_display_in_tool_panel",
        "includes_workflows",
        "repository_dependencies",
    ]

    def __init__(
        self,
        id=None,
        repository_id=None,
        numeric_revision=None,
        changeset_revision=None,
        metadata=None,
        tool_versions=None,
        malicious=False,
        downloadable=False,
        missing_test_components=None,
        tools_functionally_correct=False,
        test_install_error=False,
        has_repository_dependencies=False,
        includes_datatypes=False,
        includes_tools=False,
        includes_tool_dependencies=False,
        includes_workflows=False,
    ):
        self.id = id
        self.repository_id = repository_id
        self.numeric_revision = numeric_revision
        self.changeset_revision = changeset_revision
        self.metadata = metadata
        self.tool_versions = tool_versions
        self.malicious = malicious
        self.downloadable = downloadable
        self.missing_test_components = missing_test_components
        self.has_repository_dependencies = has_repository_dependencies
        # We don't consider the special case has_repository_dependencies_only_if_compiling_contained_td here.
        self.includes_datatypes = includes_datatypes
        self.includes_tools = includes_tools
        self.includes_tool_dependencies = includes_tool_dependencies
        self.includes_workflows = includes_workflows

    @property
    def includes_tools_for_display_in_tool_panel(self):
        if self.metadata:
            tool_dicts = self.metadata.get("tools", [])
            for tool_dict in tool_dicts:
                if tool_dict.get("add_to_tool_panel", True):
                    return True
        return False

    @property
    def repository_dependencies(self):
        if self.has_repository_dependencies:
            return [
                repository_dependency
                for repository_dependency in self.metadata["repository_dependencies"]["repository_dependencies"]
            ]
        return []


# After the map_imperatively statement has been executed, the members of the
# properties dictionary (repository, reviews) will be available as instrumented
# class attributes on RepositoryMetadata.
mapper_registry.map_imperatively(
    RepositoryMetadata,
    RepositoryMetadata.table,
    properties=dict(
        repository=relationship(Repository, back_populates="metadata_revisions"),
        reviews=relationship(
            RepositoryReview,
            viewonly=True,
            foreign_keys=lambda: [RepositoryReview.repository_id, RepositoryReview.changeset_revision],
            primaryjoin=lambda: (
                (RepositoryReview.repository_id == RepositoryMetadata.repository_id)
                & (RepositoryReview.changeset_revision == RepositoryMetadata.changeset_revision)
            ),
            back_populates="repository_metadata",
        ),
    ),
)


# Utility methods
def sort_by_attr(seq, attr):
    """
    Sort the sequence of objects by object's attribute
    Arguments:
    seq  - the list or any sequence (including immutable one) of objects to sort.
    attr - the name of attribute to sort by
    """
    # Use the "Schwartzian transform"
    # Create the auxiliary list of tuples where every i-th tuple has form
    # (seq[i].attr, i, seq[i]) and sort it. The second item of tuple is needed not
    # only to provide stable sorting, but mainly to eliminate comparison of objects
    # (which can be expensive or prohibited) in case of equal attribute values.
    intermed = [(getattr(v, attr), i, v) for i, v in enumerate(seq)]
    intermed.sort()
    return [_[-1] for _ in intermed]
