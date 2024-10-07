"""
Visualizations resource control over the API.

NOTE!: this is a work in progress and functionality and data structures
may change often.
"""

import json
import logging
from typing import Optional

from fastapi import (
    Body,
    Path,
    Query,
    Response,
    status,
)
from typing_extensions import Annotated

from galaxy import (
    exceptions,
    util,
    web,
)
from galaxy.managers.context import ProvidesUserContext
from galaxy.model.base import transaction
from galaxy.model.item_attrs import UsesAnnotations
from galaxy.schema.fields import DecodedDatabaseIdField
from galaxy.schema.schema import (
    SetSlugPayload,
    ShareWithPayload,
    ShareWithStatus,
    SharingStatus,
)
from galaxy.schema.visualization import (
    VisualizationIndexQueryPayload,
    VisualizationSortByEnum,
    VisualizationSummaryList,
)
from galaxy.util.hash_util import md5_hash_str
from galaxy.web import expose_api
from galaxy.webapps.base.controller import UsesVisualizationMixin
from galaxy.webapps.base.webapp import GalaxyWebTransaction
from galaxy.webapps.galaxy.api import (
    BaseGalaxyAPIController,
    depends,
    DependsOnTrans,
    IndexQueryTag,
    Router,
    search_query_param,
)
from galaxy.webapps.galaxy.api.common import (
    LimitQueryParam,
    OffsetQueryParam,
)
from galaxy.webapps.galaxy.services.visualizations import VisualizationsService

log = logging.getLogger(__name__)

router = Router(tags=["visualizations"])

DeletedQueryParam: bool = Query(
    default=False, title="Display deleted", description="Whether to include deleted visualizations in the result."
)

UserIdQueryParam: Optional[DecodedDatabaseIdField] = Query(
    default=None,
    title="Encoded user ID to restrict query to, must be own id if not an admin user",
)

query_tags = [
    IndexQueryTag("title", "The visualization's title."),
    IndexQueryTag("slug", "The visualization's slug.", "s"),
    IndexQueryTag("tag", "The visualization's tags.", "t"),
    IndexQueryTag("user", "The visualization's owner's username.", "u"),
]

SearchQueryParam: Optional[str] = search_query_param(
    model_name="Visualization",
    tags=query_tags,
    free_text_fields=["title", "slug", "tag", "type"],
)

SharingQueryParam: bool = Query(
    default=False, title="Provide sharing status", description="Whether to provide sharing details in the result."
)

ShowOwnQueryParam: bool = Query(default=True, title="Show visualizations owned by user.", description="")

ShowPublishedQueryParam: bool = Query(default=True, title="Include published visualizations.", description="")

ShowSharedQueryParam: bool = Query(
    default=False, title="Include visualizations shared with authenticated user.", description=""
)

SortByQueryParam: VisualizationSortByEnum = Query(
    default="update_time",
    title="Sort attribute",
    description="Sort visualization index by this specified attribute on the visualization model",
)

SortDescQueryParam: bool = Query(
    default=True,
    title="Sort Descending",
    description="Sort in descending order?",
)

VisualizationIdPathParam = Annotated[
    DecodedDatabaseIdField,
    Path(..., title="Visualization ID", description="The encoded database identifier of the Visualization."),
]


@router.cbv
class FastAPIVisualizations:
    service: VisualizationsService = depends(VisualizationsService)

    @router.get(
        "/api/visualizations",
        summary="Returns visualizations for the current user.",
    )
    def index(
        self,
        response: Response,
        trans: ProvidesUserContext = DependsOnTrans,
        deleted: bool = DeletedQueryParam,
        limit: Optional[int] = LimitQueryParam,
        offset: Optional[int] = OffsetQueryParam,
        user_id: Optional[DecodedDatabaseIdField] = UserIdQueryParam,
        show_own: bool = ShowOwnQueryParam,
        show_published: bool = ShowPublishedQueryParam,
        show_shared: bool = ShowSharedQueryParam,
        sort_by: VisualizationSortByEnum = SortByQueryParam,
        sort_desc: bool = SortDescQueryParam,
        search: Optional[str] = SearchQueryParam,
    ) -> VisualizationSummaryList:
        payload = VisualizationIndexQueryPayload.model_construct(
            deleted=deleted,
            user_id=user_id,
            show_published=show_published,
            show_own=show_own,
            show_shared=show_shared,
            sort_by=sort_by,
            sort_desc=sort_desc,
            limit=limit,
            offset=offset,
            search=search,
        )
        entries, total_matches = self.service.index(trans, payload, include_total_count=True)
        response.headers["total_matches"] = str(total_matches)
        return entries

    @router.get(
        "/api/visualizations/{id}/sharing",
        summary="Get the current sharing status of the given Visualization.",
    )
    def sharing(
        self,
        id: VisualizationIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> SharingStatus:
        """Return the sharing status of the item."""
        return self.service.shareable_service.sharing(trans, id)

    @router.put(
        "/api/visualizations/{id}/enable_link_access",
        summary="Makes this item accessible by a URL link.",
    )
    def enable_link_access(
        self,
        id: VisualizationIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> SharingStatus:
        """Makes this item accessible by a URL link and return the current sharing status."""
        return self.service.shareable_service.enable_link_access(trans, id)

    @router.put(
        "/api/visualizations/{id}/disable_link_access",
        summary="Makes this item inaccessible by a URL link.",
    )
    def disable_link_access(
        self,
        id: VisualizationIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> SharingStatus:
        """Makes this item inaccessible by a URL link and return the current sharing status."""
        return self.service.shareable_service.disable_link_access(trans, id)

    @router.put(
        "/api/visualizations/{id}/publish",
        summary="Makes this item public and accessible by a URL link.",
    )
    def publish(
        self,
        id: VisualizationIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> SharingStatus:
        """Makes this item publicly available by a URL link and return the current sharing status."""
        return self.service.shareable_service.publish(trans, id)

    @router.put(
        "/api/visualizations/{id}/unpublish",
        summary="Removes this item from the published list.",
    )
    def unpublish(
        self,
        id: VisualizationIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> SharingStatus:
        """Removes this item from the published list and return the current sharing status."""
        return self.service.shareable_service.unpublish(trans, id)

    @router.put(
        "/api/visualizations/{id}/share_with_users",
        summary="Share this item with specific users.",
    )
    def share_with_users(
        self,
        id: VisualizationIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
        payload: ShareWithPayload = Body(...),
    ) -> ShareWithStatus:
        """Shares this item with specific users and return the current sharing status."""
        return self.service.shareable_service.share_with_users(trans, id, payload)

    @router.put(
        "/api/visualizations/{id}/slug",
        summary="Set a new slug for this shared item.",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def set_slug(
        self,
        id: VisualizationIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
        payload: SetSlugPayload = Body(...),
    ):
        """Sets a new slug to access this item by URL. The new slug must be unique."""
        self.service.shareable_service.set_slug(trans, id, payload)
        return Response(status_code=status.HTTP_204_NO_CONTENT)


class VisualizationsController(BaseGalaxyAPIController, UsesVisualizationMixin, UsesAnnotations):
    """
    RESTful controller for interactions with visualizations.
    """

    service: VisualizationsService = depends(VisualizationsService)

    @expose_api
    def show(self, trans: GalaxyWebTransaction, id: str, **kwargs):
        """
        GET /api/visualizations/{viz_id}
        """
        # TODO: revisions should be a contents/nested controller like viz/xxx/r/xxx)?
        # the important thing is the config
        # TODO:?? /api/visualizations/registry -> json of registry.listings?
        visualization = self.get_visualization(trans, id, check_ownership=False, check_accessible=True)
        dictionary = trans.security.encode_dict_ids(self.get_visualization_dict(visualization))
        dictionary["url"] = web.url_for(
            controller="visualization",
            action="display_by_username_and_slug",
            username=visualization.user.username,
            slug=visualization.slug,
        )
        dictionary["username"] = visualization.user.username
        dictionary["email_hash"] = md5_hash_str(visualization.user.email)
        dictionary["tags"] = visualization.make_tag_string_list()
        dictionary["annotation"] = self.get_item_annotation_str(trans.sa_session, trans.user, visualization)
        # need to encode ids in revisions as well
        encoded_revisions = []
        for revision in dictionary["revisions"]:
            # NOTE: does not encode ids inside the configs
            encoded_revisions.append(trans.security.encode_id(revision))
        dictionary["revisions"] = encoded_revisions
        dictionary["latest_revision"] = trans.security.encode_dict_ids(dictionary["latest_revision"])
        if trans.app.visualizations_registry:
            visualization = trans.app.visualizations_registry.get_plugin(dictionary["type"])
            dictionary["plugin"] = visualization.to_dict()
        return dictionary

    @expose_api
    def create(self, trans: GalaxyWebTransaction, payload: dict, **kwargs):
        """
        POST /api/visualizations
        creates a new visualization using the given payload

        POST /api/visualizations?import_id={encoded_visualization_id}
        imports a copy of an existing visualization into the user's workspace
        """
        rval = None

        if "import_id" in payload:
            import_id = payload["import_id"]
            visualization = self.import_visualization(trans, import_id, user=trans.user)

        else:
            payload = self._validate_and_parse_payload(payload)
            # must have a type (I've taken this to be the visualization name)
            if "type" not in payload:
                raise exceptions.RequestParameterMissingException("key/value 'type' is required")
            vis_type = payload.pop("type", False)

            payload["save"] = True
            try:
                # generate defaults - this will err if given a weird key?
                visualization = self.create_visualization(trans, vis_type, **payload)
            except ValueError as val_err:
                raise exceptions.RequestParameterMissingException(str(val_err))

        rval = {"id": trans.security.encode_id(visualization.id)}

        return rval

    @expose_api
    def update(self, trans: GalaxyWebTransaction, id: str, payload: dict, **kwargs):
        """
        PUT /api/visualizations/{encoded_visualization_id}
        """
        rval = None
        payload = self._validate_and_parse_payload(payload)

        # there's a differentiation here between updating the visualization and creating a new revision
        # that needs to be handled clearly here or alternately, using a different controller
        # like e.g. PUT /api/visualizations/{id}/r/{id}

        # TODO: consider allowing direct alteration of revisions title (without a new revision)
        #   only create a new revsion on a different config

        # only update owned visualizations
        visualization = self.get_visualization(trans, id, check_ownership=True)
        title = payload.get("title", visualization.latest_revision.title)
        dbkey = payload.get("dbkey", visualization.latest_revision.dbkey)
        deleted = payload.get("deleted", visualization.deleted)
        config = payload.get("config", visualization.latest_revision.config)

        latest_config = visualization.latest_revision.config
        if (
            (title != visualization.latest_revision.title)
            or (dbkey != visualization.latest_revision.dbkey)
            or (json.dumps(config) != json.dumps(latest_config))
        ):
            revision = self.add_visualization_revision(trans, visualization, config, title, dbkey)
            rval = {"id": id, "revision": revision.id}

        # allow updating vis title
        visualization.title = title
        visualization.deleted = deleted
        with transaction(trans.sa_session):
            trans.sa_session.commit()

        return rval

    def _validate_and_parse_payload(self, payload):
        """
        Validate and parse incomming data payload for a visualization.
        """
        # This layer handles (most of the stricter idiot proofing):
        #   - unknown/unallowed keys
        #   - changing data keys from api key to attribute name
        #   - protection against bad data form/type
        #   - protection against malicious data content
        # all other conversions and processing (such as permissions, etc.) should happen down the line

        # keys listed here don't error when attempting to set, but fail silently
        #   this allows PUT'ing an entire model back to the server without attribute errors on uneditable attrs
        valid_but_uneditable_keys = (
            "id",
            "model_class",
            # TODO: fill out when we create to_dict, get_dict, whatevs
        )
        # TODO: importable
        ValidationError = exceptions.RequestParameterInvalidException

        validated_payload = {}
        for key, val in payload.items():
            # TODO: validate types in VALID_TYPES/registry names at the mixin/model level?
            if key == "type":
                if not isinstance(val, str):
                    raise ValidationError(f"{key} must be a string or unicode: {str(type(val))}")
                val = util.sanitize_html.sanitize_html(val)
            elif key == "config":
                if not isinstance(val, dict):
                    raise ValidationError(f"{key} must be a dictionary: {str(type(val))}")
            elif key == "annotation":
                if not isinstance(val, str):
                    raise ValidationError(f"{key} must be a string or unicode: {str(type(val))}")
                val = util.sanitize_html.sanitize_html(val)
            elif key == "deleted":
                if not isinstance(val, bool):
                    raise ValidationError(f"{key} must be a bool: {str(type(val))}")

            # these are keys that actually only be *updated* at the revision level and not here
            #   (they are still valid for create, tho)
            elif key == "title":
                if not isinstance(val, str):
                    raise ValidationError(f"{key} must be a string or unicode: {str(type(val))}")
                val = util.sanitize_html.sanitize_html(val)
            elif key == "slug":
                if not isinstance(val, str):
                    raise ValidationError(f"{key} must be a string: {str(type(val))}")
                val = util.sanitize_html.sanitize_html(val)
            elif key == "dbkey":
                if not isinstance(val, str):
                    raise ValidationError(f"{key} must be a string or unicode: {str(type(val))}")
                val = util.sanitize_html.sanitize_html(val)

            elif key not in valid_but_uneditable_keys:
                continue
                # raise AttributeError( 'unknown key: %s' %( str( key ) ) )

            validated_payload[key] = val
        return validated_payload
