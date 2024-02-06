"""
Manager and Serializers for Visualizations.

Visualizations are saved configurations/variables used to
reproduce a specific view in a Galaxy visualization.
"""

import logging
from typing import (
    Dict,
    List,
    Tuple,
)

from sqlalchemy import (
    false,
    func,
    or_,
    select,
    true,
)
from sqlalchemy.orm import aliased

from galaxy import (
    exceptions,
    model,
)
from galaxy.managers import (
    base,
    sharable,
)
from galaxy.managers.context import ProvidesUserContext
from galaxy.model.index_filter_util import (
    append_user_filter,
    raw_text_column_filter,
    tag_filter,
    text_column_filter,
)
from galaxy.schema.visualization import VisualizationIndexQueryPayload
from galaxy.structured_app import MinimalManagerApp
from galaxy.util.search import (
    FilteredTerm,
    parse_filters_structured,
    RawTextTerm,
)

log = logging.getLogger(__name__)


INDEX_SEARCH_FILTERS = {
    "title": "title",
    "slug": "slug",
    "tag": "tag",
    "user": "user",
    "u": "user",
    "s": "slug",
    "t": "tag",
    "is": "is",
}


class VisualizationManager(sharable.SharableModelManager):
    """
    Handle operations outside and between visualizations and other models.
    """

    # TODO: copy, revisions

    model_class = model.Visualization
    foreign_key_name = "visualization"
    user_share_model = model.VisualizationUserShareAssociation

    tag_assoc = model.VisualizationTagAssociation
    annotation_assoc = model.VisualizationAnnotationAssociation
    rating_assoc = model.VisualizationRatingAssociation

    def index_query(
        self, trans: ProvidesUserContext, payload: VisualizationIndexQueryPayload, include_total_count: bool = False
    ) -> Tuple[List[model.Visualization], int]:
        show_deleted = payload.deleted
        show_own = payload.show_own
        show_published = payload.show_published
        show_shared = payload.show_shared
        is_admin = trans.user_is_admin
        user = trans.user

        if not user and not show_published:
            message = "Requires user to log in."
            raise exceptions.RequestParameterInvalidException(message)

        stmt = select(self.model_class)

        filters = []
        if show_own or (not show_published and not show_shared and not is_admin):
            filters = [self.model_class.user == user]
        if show_published:
            filters.append(self.model_class.published == true())
        if user and show_shared:
            filters.append(self.user_share_model.user == user)
            stmt = stmt.outerjoin(self.model_class.users_shared_with)
        stmt = stmt.where(or_(*filters))

        if payload.user_id:
            stmt = stmt.where(self.model_class.user_id == payload.user_id)

        if payload.search:
            search_query = payload.search
            parsed_search = parse_filters_structured(search_query, INDEX_SEARCH_FILTERS)

            def p_tag_filter(term_text: str, quoted: bool):
                nonlocal stmt
                alias = aliased(model.VisualizationTagAssociation)
                stmt = stmt.outerjoin(self.model_class.tags.of_type(alias))
                return tag_filter(alias, term_text, quoted)

            for term in parsed_search.terms:
                if isinstance(term, FilteredTerm):
                    key = term.filter
                    q = term.text
                    if key == "tag":
                        pg = p_tag_filter(term.text, term.quoted)
                        stmt = stmt.where(pg)
                    elif key == "title":
                        stmt = stmt.where(text_column_filter(self.model_class.title, term))
                    elif key == "slug":
                        stmt = stmt.where(text_column_filter(self.model_class.slug, term))
                    elif key == "user":
                        stmt = append_user_filter(stmt, self.model_class, term)
                    elif key == "is":
                        if q == "deleted":
                            show_deleted = True
                        if q == "published":
                            stmt = stmt.where(self.model_class.published == true())
                        if q == "importable":
                            stmt = stmt.where(self.model_class.importable == true())
                        elif q == "shared_with_me":
                            if not show_shared:
                                message = "Can only use tag is:shared_with_me if show_shared parameter also true."
                                raise exceptions.RequestParameterInvalidException(message)
                            stmt = stmt.where(self.user_share_model.user == user)
                elif isinstance(term, RawTextTerm):
                    tf = p_tag_filter(term.text, False)
                    alias = aliased(model.User)
                    stmt = stmt.outerjoin(self.model_class.user.of_type(alias))
                    stmt = stmt.where(
                        raw_text_column_filter(
                            [
                                self.model_class.title,
                                self.model_class.slug,
                                tf,
                                alias.username,
                            ],
                            term,
                        )
                    )

        if (show_published or show_shared) and not is_admin:
            show_deleted = False

        stmt = stmt.where(self.model_class.deleted == (true() if show_deleted else false())).distinct()

        if include_total_count:
            total_matches = get_count(trans.sa_session, stmt)
        else:
            total_matches = None
        sort_column = getattr(model.Visualization, payload.sort_by)
        if payload.sort_desc:
            sort_column = sort_column.desc()
        stmt = stmt.order_by(sort_column)
        if payload.limit is not None:
            stmt = stmt.limit(payload.limit)
        if payload.offset is not None:
            stmt = stmt.offset(payload.offset)
        return trans.sa_session.scalars(stmt), total_matches  # type:ignore[return-value]


class VisualizationSerializer(sharable.SharableModelSerializer):
    """
    Interface/service object for serializing visualizations into dictionaries.
    """

    model_manager_class = VisualizationManager
    SINGLE_CHAR_ABBR = "v"

    def __init__(self, app: MinimalManagerApp):
        super().__init__(app)
        self.visualization_manager = self.manager

        self.default_view = "summary"
        self.add_view("summary", [])
        self.add_view("detailed", [])

    def add_serializers(self):
        super().add_serializers()
        serializers: Dict[str, base.Serializer] = {}
        self.serializers.update(serializers)


class VisualizationDeserializer(sharable.SharableModelDeserializer):
    """
    Interface/service object for validating and deserializing
    dictionaries into visualizations.
    """

    model_manager_class = VisualizationManager

    def __init__(self, app):
        super().__init__(app)
        self.visualization_manager = self.manager

    def add_deserializers(self):
        super().add_deserializers()
        self.deserializers.update({})
        self.deserializable_keyset.update(self.deserializers.keys())


def get_count(session, statement):
    stmt = select(func.count()).select_from(statement)
    return session.scalar(stmt)
