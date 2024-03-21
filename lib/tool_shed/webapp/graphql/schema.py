import graphene
from graphene import relay
from graphene_sqlalchemy import (
    SQLAlchemyConnectionField,
    SQLAlchemyObjectType,
)
from graphene_sqlalchemy.converter import convert_sqlalchemy_type
from graphene_sqlalchemy.utils import column_type_eq
from graphql import GraphQLResolveInfo
from sqlalchemy.orm import scoped_session
from typing_extensions import TypedDict

from galaxy.model.custom_types import TrimmedString
from galaxy.security.idencoding import IdEncodingHelper
from tool_shed.webapp.model import (
    Category as SaCategory,
    Repository as SaRepository,
    RepositoryCategoryAssociation,
    RepositoryMetadata as SaRepositoryMetadata,
    User as SaUser,
)

USER_FIELDS = (
    "id",
    "username",
)

CATEGORY_FIELDS = (
    "id",
    "create_time",
    "update_time",
    "name",
    "description",
    "deleted",
)

REPOSITORY_FIELDS = (
    "id",
    "create_time",
    "update_time",
    "name",
    "type",
    "remote_repository_url",
    "homepage_url",
    "description",
    "long_description",
)

REPOSITORY_METADATA_FIELDS = (
    "id",
    "create_time"
    "update_time"
    "changeset_revision"
    "numeric_revision"
    "metadata"
    "tool_versions"
    "malicious"
    "downloadable",
)


class InfoDict(TypedDict):
    session: scoped_session
    security: IdEncodingHelper


# Map these Galaxy-ism to Graphene for cleaner interfaces.
@convert_sqlalchemy_type.register(column_type_eq(TrimmedString))
def convert_sqlalchemy_type_trimmed_string(*args, **kwd):
    return graphene.String


@convert_sqlalchemy_type.register(column_type_eq(lambda t: t == TrimmedString))
def convert_sqlalchemy_hybrid_property_type_trimmed_string(arg):
    return graphene.String


class HasIdMixin:
    id = graphene.NonNull(graphene.ID)
    encoded_id = graphene.NonNull(graphene.String)

    def resolve_encoded_id(self: SQLAlchemyObjectType, info):
        return info.context["security"].encode_id(self.id)


class UserMixin(HasIdMixin):
    username = graphene.NonNull(graphene.String)


class RelayUser(SQLAlchemyObjectType, UserMixin):
    class Meta:
        model = SaUser
        only_fields = USER_FIELDS
        interfaces = (relay.Node,)


class SimpleUser(SQLAlchemyObjectType, UserMixin):
    class Meta:
        model = SaUser
        only_fields = USER_FIELDS


class CategoryQueryMixin(HasIdMixin):
    name = graphene.NonNull(graphene.String)
    repositories = graphene.List(lambda: SimpleRepository)

    def resolve_repositories(self, info: InfoDict):
        return [a.repository for a in self.repositories]


class SimpleCategory(SQLAlchemyObjectType, CategoryQueryMixin):
    class Meta:
        model = SaCategory
        only_fields = CATEGORY_FIELDS


class RelayCategory(SQLAlchemyObjectType, CategoryQueryMixin):
    class Meta:
        model = SaCategory
        only_fields = CATEGORY_FIELDS
        interfaces = (relay.Node,)


class RepositoryMixin(HasIdMixin):
    name = graphene.NonNull(graphene.String)


class RelayRepository(SQLAlchemyObjectType, RepositoryMixin):
    class Meta:
        model = SaRepository
        only_fields = REPOSITORY_FIELDS
        interfaces = (relay.Node,)

    categories = graphene.List(SimpleCategory)
    user = graphene.NonNull(SimpleUser)


class RevisionQueryMixin(HasIdMixin):
    # I think because it is imperatively mapped, but the fields are not
    # auto-populated for this and so we need to be a bit more explicit
    create_time = graphene.DateTime()
    update_time = graphene.DateTime()
    repository = graphene.NonNull(lambda: SimpleRepository)
    changeset_revision = graphene.NonNull(graphene.String)
    numeric_revision = graphene.Int()
    malicious = graphene.Boolean()
    downloadable = graphene.Boolean()


class SimpleRepositoryMetadata(SQLAlchemyObjectType, RevisionQueryMixin):
    class Meta:
        model = SaRepositoryMetadata
        only_fields = REPOSITORY_METADATA_FIELDS


class SimpleRepository(SQLAlchemyObjectType, RepositoryMixin):
    class Meta:
        model = SaRepository
        only_fields = REPOSITORY_FIELDS

    categories = graphene.List(SimpleCategory)
    user = graphene.NonNull(SimpleUser)
    metadata_revisions = graphene.List(lambda: SimpleRepositoryMetadata)
    downloadable_revisions = graphene.List(lambda: SimpleRepositoryMetadata)


class RelayRepositoryMetadata(SQLAlchemyObjectType, RevisionQueryMixin):
    class Meta:
        model = SaRepositoryMetadata
        only_fields = REPOSITORY_METADATA_FIELDS
        interfaces = (relay.Node,)


class RepositoriesForCategoryField(SQLAlchemyConnectionField):
    def __init__(self):
        super().__init__(RelayRepository.connection, id=graphene.Int(), encoded_id=graphene.String())

    @classmethod
    def get_query(cls, model, info: GraphQLResolveInfo, sort=None, **args):
        repository_query = super().get_query(model, info, sort=sort, **args)
        context: InfoDict = info.root_value
        query_id = args.get("id")
        if not query_id:
            encoded_id = args.get("encoded_id")
            assert encoded_id, f"Invalid encodedId found {encoded_id} in args {args}"
            query_id = context["security"].decode_id(encoded_id)
        if query_id:
            rval = repository_query.join(
                RepositoryCategoryAssociation,
                SaRepository.id == RepositoryCategoryAssociation.repository_id,
            ).filter(RepositoryCategoryAssociation.category_id == query_id)
            return rval
        else:
            return repository_query


class RepositoriesForOwnerField(SQLAlchemyConnectionField):
    def __init__(self):
        super().__init__(RelayRepository.connection, username=graphene.String())

    @classmethod
    def get_query(cls, model, info: GraphQLResolveInfo, sort=None, **args):
        repository_query = super().get_query(model, info, sort=sort, **args)
        username = args.get("username")
        rval = repository_query.join(
            SaUser,
        ).filter(SaUser.username == username)
        return rval


class Query(graphene.ObjectType):
    users = graphene.List(SimpleUser)
    repositories = graphene.List(SimpleRepository)
    categories = graphene.List(SimpleCategory)
    revisions = graphene.List(SimpleRepositoryMetadata)

    node = relay.Node.Field()
    relay_users = SQLAlchemyConnectionField(RelayUser.connection)
    relay_repositories_for_category = RepositoriesForCategoryField()
    relay_repositories_for_owner = RepositoriesForOwnerField()
    relay_repositories = SQLAlchemyConnectionField(RelayRepository.connection)
    relay_categories = SQLAlchemyConnectionField(RelayCategory.connection)
    relay_revisions = SQLAlchemyConnectionField(RelayRepositoryMetadata.connection)

    def resolve_users(self, info: InfoDict):
        query = SimpleUser.get_query(info)
        return query.all()

    def resolve_repositories(self, info: InfoDict):
        query = SimpleRepository.get_query(info)
        return query.all()

    def resolve_categories(self, info: InfoDict):
        query = SimpleCategory.get_query(info)
        return query.all()

    def resolve_revisions(self, info: InfoDict):
        query = SimpleRepositoryMetadata.get_query(info)
        return query.all()


schema = graphene.Schema(query=Query, types=[SimpleCategory])
