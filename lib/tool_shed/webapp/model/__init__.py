import logging
import os
import random
import string
import weakref
from datetime import (
    datetime,
    timedelta,
)
from typing import (
    Any,
    Mapping,
    Optional,
    TYPE_CHECKING,
)

from mercurial import (
    hg,
    ui,
)
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    desc,
    ForeignKey,
    Integer,
    not_,
    String,
    Table,
    text,
    TEXT,
    true,
    UniqueConstraint,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    object_session,
    registry,
    relationship,
)

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
from galaxy.util.hash_util import new_insecure_hash
from tool_shed.dependencies.repository import relation_builder
from tool_shed.util import (
    hg_util,
    metadata_util,
)
from tool_shed.util.hgweb_config import hgweb_config_manager

log = logging.getLogger(__name__)

WEAK_HG_REPO_CACHE: Mapping["Repository", Any] = weakref.WeakKeyDictionary()

if TYPE_CHECKING:
    # Workaround for https://github.com/python/mypy/issues/14182
    from sqlalchemy.orm import DeclarativeMeta as _DeclarativeMeta

    class DeclarativeMeta(_DeclarativeMeta, type):
        pass

else:
    from sqlalchemy.orm import DeclarativeMeta

mapper_registry = registry()


class Base(metaclass=DeclarativeMeta):
    __abstract__ = True
    registry = mapper_registry
    metadata = mapper_registry.metadata
    __init__ = mapper_registry.constructor
    table: Table
    __table__: Table

    @classmethod
    def __declare_last__(cls):
        cls.table = cls.__table__


class APIKeys(Base):
    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    create_time: Mapped[Optional[datetime]] = mapped_column(DateTime, default=now)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("galaxy_user.id"), index=True)
    key: Mapped[Optional[str]] = mapped_column(TrimmedString(32), index=True, unique=True)
    user = relationship("User", back_populates="api_keys")
    deleted: Mapped[Optional[bool]] = mapped_column(index=True, default=False, nullable=False)


class User(Base, Dictifiable):
    __tablename__ = "galaxy_user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    create_time: Mapped[Optional[datetime]] = mapped_column(DateTime, default=now)
    update_time: Mapped[Optional[datetime]] = mapped_column(DateTime, default=now, onupdate=now)
    email: Mapped[str] = mapped_column(TrimmedString(255), nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    password: Mapped[str] = mapped_column(TrimmedString(40), nullable=False)
    external: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    new_repo_alert: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    deleted: Mapped[Optional[bool]] = mapped_column(Boolean, index=True, default=False)
    purged: Mapped[Optional[bool]] = mapped_column(Boolean, index=True, default=False)
    active_repositories = relationship(
        "Repository",
        primaryjoin=(lambda: (Repository.user_id == User.id) & (not_(Repository.deleted))),
        back_populates="user",
        order_by=lambda: desc(Repository.name),
    )
    galaxy_sessions = relationship(
        "GalaxySession", back_populates="user", order_by=lambda: desc(GalaxySession.update_time)
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
            lambda: (User.id == UserRoleAssociation.user_id)
            & (UserRoleAssociation.role_id == Role.id)
            & not_(Role.name == User.email)
        ),
    )

    def __init__(self, email=None, password=None):
        self.email = email
        self.password = password
        self.external = False
        self.deleted = False
        self.purged = False
        self.new_repo_alert = False

    @property
    def current_galaxy_session(self):
        if self.galaxy_sessions:
            return self.galaxy_sessions[0]

    def all_roles(self):
        roles = [ura.role for ura in self.roles]
        for group in [uga.group for uga in self.groups]:
            for role in [gra.role for gra in group.roles]:
                if role not in roles:
                    roles.append(role)
        return roles

    def check_password(self, cleartext):
        """Check if 'cleartext' matches 'self.password' when hashed."""
        return self.password == new_insecure_hash(text_type=cleartext)

    def get_disk_usage(self, nice_size=False):
        return 0

    @property
    def nice_total_disk_usage(self):
        return 0

    def set_disk_usage(self, bytes):
        pass

    total_disk_usage = property(get_disk_usage, set_disk_usage)

    def set_password_cleartext(self, cleartext):
        if message := validate_password_str(cleartext):
            raise Exception(f"Invalid password: {message}")
        # Set 'self.password' to the digest of 'cleartext'.
        self.password = new_insecure_hash(text_type=cleartext)

    def set_random_password(self, length=16):
        """
        Sets user password to a random string of the given length.
        :return: void
        """
        self.set_password_cleartext(
            "".join(random.SystemRandom().choice(string.ascii_letters + string.digits) for _ in range(length))
        )


class PasswordResetToken(Base):
    __tablename__ = "password_reset_token"

    token: Mapped[str] = mapped_column(String(32), primary_key=True, unique=True, index=True)
    expiration_time: Mapped[Optional[datetime]] = mapped_column(DateTime)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("galaxy_user.id"), index=True)
    user = relationship("User", back_populates="reset_tokens")

    def __init__(self, user, token=None):
        if token:
            self.token = token
        else:
            self.token = unique_id()
        add_object_to_object_session(self, user)
        self.user = user
        self.expiration_time = now() + timedelta(hours=24)


class Group(Base, Dictifiable):
    __tablename__ = "galaxy_group"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    create_time: Mapped[Optional[datetime]] = mapped_column(DateTime, default=now)
    update_time: Mapped[Optional[datetime]] = mapped_column(DateTime, default=now, onupdate=now)
    name: Mapped[Optional[str]] = mapped_column(String(255), index=True, unique=True)
    deleted: Mapped[Optional[bool]] = mapped_column(Boolean, index=True, default=False)
    roles = relationship("GroupRoleAssociation", back_populates="group")
    users = relationship("UserGroupAssociation", back_populates="group")

    dict_collection_visible_keys = ["id", "name"]
    dict_element_visible_keys = ["id", "name"]

    def __init__(self, name=None):
        self.name = name
        self.deleted = False


class Role(Base, Dictifiable):
    __tablename__ = "role"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    create_time: Mapped[Optional[datetime]] = mapped_column(DateTime, default=now)
    update_time: Mapped[Optional[datetime]] = mapped_column(DateTime, default=now, onupdate=now)
    name: Mapped[Optional[str]] = mapped_column(String(255), index=True, unique=True)
    description: Mapped[Optional[str]] = mapped_column(TEXT)
    type: Mapped[Optional[str]] = mapped_column(String(40), index=True)
    deleted: Mapped[Optional[bool]] = mapped_column(Boolean, index=True, default=False)
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


class UserGroupAssociation(Base):
    __tablename__ = "user_group_association"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("galaxy_user.id"), index=True)
    group_id: Mapped[Optional[int]] = mapped_column(ForeignKey("galaxy_group.id"), index=True)
    create_time: Mapped[Optional[datetime]] = mapped_column(DateTime, default=now)
    update_time: Mapped[Optional[datetime]] = mapped_column(DateTime, default=now, onupdate=now)
    user = relationship("User", back_populates="groups")
    group = relationship("Group", back_populates="users")

    def __init__(self, user, group):
        add_object_to_object_session(self, user)
        self.user = user
        self.group = group


class UserRoleAssociation(Base):
    __tablename__ = "user_role_association"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("galaxy_user.id"), index=True)
    role_id: Mapped[Optional[int]] = mapped_column(ForeignKey("role.id"), index=True)
    create_time: Mapped[Optional[datetime]] = mapped_column(DateTime, default=now)
    update_time: Mapped[Optional[datetime]] = mapped_column(DateTime, default=now, onupdate=now)
    user = relationship("User", back_populates="roles")
    role = relationship("Role", back_populates="users")

    def __init__(self, user, role):
        add_object_to_object_session(self, user)
        self.user = user
        add_object_to_object_session(self, role)
        self.role = role


class GroupRoleAssociation(Base):
    __tablename__ = "group_role_association"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    group_id: Mapped[Optional[int]] = mapped_column(ForeignKey("galaxy_group.id"), index=True)
    role_id: Mapped[Optional[int]] = mapped_column(ForeignKey("role.id"), index=True)
    create_time: Mapped[Optional[datetime]] = mapped_column(DateTime, default=now)
    update_time: Mapped[Optional[datetime]] = mapped_column(DateTime, default=now, onupdate=now)
    group = relationship("Group", back_populates="roles")
    role = relationship("Role", back_populates="groups")

    def __init__(self, group, role):
        self.group = group
        self.role = role


class RepositoryRoleAssociation(Base):
    __tablename__ = "repository_role_association"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    repository_id: Mapped[Optional[int]] = mapped_column(ForeignKey("repository.id"), index=True)
    role_id: Mapped[Optional[int]] = mapped_column(ForeignKey("role.id"), index=True)
    create_time: Mapped[Optional[datetime]] = mapped_column(DateTime, default=now)
    update_time: Mapped[Optional[datetime]] = mapped_column(DateTime, default=now, onupdate=now)
    repository = relationship("Repository", back_populates="roles")
    role = relationship("Role", back_populates="repositories")

    def __init__(self, repository, role):
        add_object_to_object_session(self, repository)
        self.repository = repository
        self.role = role


class GalaxySession(Base):
    __tablename__ = "galaxy_session"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    create_time: Mapped[Optional[datetime]] = mapped_column(DateTime, default=now)
    update_time: Mapped[Optional[datetime]] = mapped_column(DateTime, default=now, onupdate=now)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("galaxy_user.id"), index=True, nullable=True)
    remote_host: Mapped[Optional[str]] = mapped_column(String(255))
    remote_addr: Mapped[Optional[str]] = mapped_column(String(255))
    referer: Mapped[Optional[str]] = mapped_column(TEXT)
    # unique 128 bit random number coerced to a string
    session_key: Mapped[Optional[str]] = mapped_column(TrimmedString(255), index=True, unique=True)
    is_valid: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    # saves a reference to the previous session so we have a way to chain them together
    prev_session_id: Mapped[Optional[int]] = mapped_column(Integer)
    last_action: Mapped[Optional[datetime]] = mapped_column(DateTime)
    user = relationship("User", back_populates="galaxy_sessions")

    def __init__(self, is_valid=False, **kwd):
        super().__init__(**kwd)
        self.is_valid = is_valid
        self.last_action = self.last_action or datetime.now()


class Repository(Base, Dictifiable):
    __tablename__ = "repository"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    create_time: Mapped[Optional[datetime]] = mapped_column(DateTime, default=now)
    update_time: Mapped[Optional[datetime]] = mapped_column(DateTime, default=now, onupdate=now)
    name: Mapped[Optional[str]] = mapped_column(TrimmedString(255), index=True)
    type: Mapped[Optional[str]] = mapped_column(TrimmedString(255), index=True)
    remote_repository_url: Mapped[Optional[str]] = mapped_column(TrimmedString(255))
    homepage_url: Mapped[Optional[str]] = mapped_column(TrimmedString(255))
    description: Mapped[Optional[str]] = mapped_column(TEXT)
    long_description: Mapped[Optional[str]] = mapped_column(TEXT)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("galaxy_user.id"), index=True)
    private: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    deleted: Mapped[Optional[bool]] = mapped_column(Boolean, index=True, default=False)
    email_alerts: Mapped[Optional[bytes]] = mapped_column(MutableJSONType, nullable=True)
    times_downloaded: Mapped[Optional[int]] = mapped_column(Integer)
    deprecated: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    categories = relationship("RepositoryCategoryAssociation", back_populates="repository")
    ratings = relationship(
        "RepositoryRatingAssociation",
        order_by=lambda: desc(RepositoryRatingAssociation.update_time),
        back_populates="repository",
    )
    user = relationship("User", back_populates="active_repositories")
    downloadable_revisions = relationship(
        "RepositoryMetadata",
        primaryjoin=lambda: (Repository.id == RepositoryMetadata.repository_id) & (RepositoryMetadata.downloadable == true()),  # type: ignore[has-type]
        viewonly=True,
        order_by=lambda: desc(RepositoryMetadata.update_time),  # type: ignore[attr-defined]
    )
    metadata_revisions = relationship(
        "RepositoryMetadata",
        order_by=lambda: desc(RepositoryMetadata.update_time),  # type: ignore[attr-defined]
        back_populates="repository",
    )
    roles = relationship("RepositoryRoleAssociation", back_populates="repository")

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
        "update_time",
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
        "update_time",
    ]
    file_states = Bunch(NORMAL="n", NEEDS_MERGING="m", MARKED_FOR_REMOVAL="r", MARKED_FOR_ADDITION="a", NOT_TRACKED="?")

    def __init__(self, private=False, times_downloaded=0, deprecated=False, user=None, **kwd):
        super().__init__(**kwd)
        self.private = private
        self.times_downloaded = times_downloaded
        self.deprecated = deprecated
        self.name = self.name or "Unnamed repository"
        self.user = user

    @property
    def hg_repo(self):
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
            f"Repository {self.name} owned by {self.user.username} is not associated with a required administrative role."
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
        return hgweb_config_manager.get_entry(
            os.path.join(hgweb_config_manager.hgweb_repo_prefix, self.user.username, self.name)
        )

    def hg_repository_path(self, repositories_directory: str) -> str:
        if self.id is None:
            raise Exception("Attempting to call hg_repository_path before id has been set on repository object")
        dir = os.path.join(repositories_directory, *util.directory_hash_id(self.id))
        final_repository_path = os.path.join(dir, "repo_%d" % self.id)
        return final_repository_path

    def ensure_hg_repository_path(self, repositories_directory: str) -> str:
        final_repository_path = self.hg_repository_path(repositories_directory)
        if not os.path.exists(final_repository_path):
            os.makedirs(final_repository_path)
        return final_repository_path

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


class ItemRatingAssociation:
    def __init__(self, id=None, user=None, item=None, rating=0, comment=""):
        self.id = id
        self.user = user
        self.item = item
        self.rating = rating
        self.comment = comment

    def set_item(self, item):
        """Set association's item."""


class RepositoryRatingAssociation(Base, ItemRatingAssociation):
    __tablename__ = "repository_rating_association"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    create_time: Mapped[Optional[datetime]] = mapped_column(DateTime, default=now)
    update_time: Mapped[Optional[datetime]] = mapped_column(DateTime, default=now, onupdate=now)
    repository_id: Mapped[Optional[int]] = mapped_column(ForeignKey("repository.id"), index=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("galaxy_user.id"), index=True)
    rating: Mapped[Optional[int]] = mapped_column(Integer, index=True)
    comment: Mapped[Optional[str]] = mapped_column(TEXT)
    repository = relationship("Repository", back_populates="ratings")
    user = relationship("User")

    def set_item(self, repository):
        self.repository = repository


class Category(Base, Dictifiable):
    __tablename__ = "category"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    create_time: Mapped[Optional[datetime]] = mapped_column(DateTime, default=now)
    update_time: Mapped[Optional[datetime]] = mapped_column(DateTime, default=now, onupdate=now)
    name: Mapped[Optional[str]] = mapped_column(TrimmedString(255), index=True, unique=True)
    description: Mapped[Optional[str]] = mapped_column(TEXT)
    deleted: Mapped[Optional[bool]] = mapped_column(Boolean, index=True, default=False)
    repositories = relationship("RepositoryCategoryAssociation", back_populates="category")

    dict_collection_visible_keys = ["id", "name", "description", "deleted"]
    dict_element_visible_keys = ["id", "name", "description", "deleted"]

    def active_repository_count(self, session=None) -> int:
        statement = """
SELECT count(*) as count
FROM repository r
INNER JOIN repository_category_association rca on rca.repository_id = r.id
WHERE
    rca.category_id = :category_id
    AND r.private = false
    AND r.deleted = false
    and r.deprecated = false
"""
        if session is None:
            session = object_session(self)
        params = {"category_id": self.id}
        return session.execute(text(statement), params).scalar()

    def __init__(self, deleted=False, **kwd):
        super().__init__(**kwd)
        self.deleted = deleted


class RepositoryCategoryAssociation(Base):
    __tablename__ = "repository_category_association"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    repository_id: Mapped[Optional[int]] = mapped_column(ForeignKey("repository.id"), index=True)
    category_id: Mapped[Optional[int]] = mapped_column(ForeignKey("category.id"), index=True)
    category = relationship("Category", back_populates="repositories")
    repository = relationship("Repository", back_populates="categories")

    def __init__(self, repository=None, category=None):
        self.repository = repository
        self.category = category


class Tag(Base):
    __tablename__ = "tag"
    __table_args__ = (UniqueConstraint("name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type: Mapped[Optional[int]] = mapped_column(Integer)
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("tag.id"))
    name: Mapped[Optional[str]] = mapped_column(TrimmedString(255))
    children = relationship("Tag", back_populates="parent")
    parent = relationship("Tag", back_populates="children", remote_side=[id])

    def __str__(self):
        return "Tag(id=%s, type=%i, parent_id=%s, name=%s)" % (self.id, self.type, self.parent_id, self.name)


# The RepositoryMetadata model is mapped imperatively (for details see discussion in PR #12064).
# TLDR: a declaratively-mapped class cannot have a .metadata attribute (it is used by SQLAlchemy's DeclarativeBase).


class RepositoryMetadata(Dictifiable):
    repository: "Repository"

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
            return list(self.metadata["repository_dependencies"]["repository_dependencies"])
        return []


# After the map_imperatively statement has been executed, the members of the
# properties dictionary (repository) will be available as instrumented
# class attributes on RepositoryMetadata.
mapper_registry.map_imperatively(
    RepositoryMetadata,
    RepositoryMetadata.table,
    properties=dict(
        repository=relationship(Repository, back_populates="metadata_revisions"),
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
