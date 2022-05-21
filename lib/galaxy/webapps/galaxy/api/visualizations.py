"""
Visualizations resource control over the API.

NOTE!: this is a work in progress and functionality and data structures
may change often.
"""
import json
import logging

from fastapi import (
    Body,
    Path,
    Response,
    status,
)

from galaxy import (
    exceptions,
    util,
    web,
)
from galaxy.managers.context import ProvidesUserContext
from galaxy.model.item_attrs import UsesAnnotations
from galaxy.schema.fields import EncodedDatabaseIdField
from galaxy.schema.schema import (
    SetSlugPayload,
    ShareWithPayload,
    ShareWithStatus,
    SharingStatus,
)
from galaxy.web import expose_api
from galaxy.webapps.base.controller import UsesVisualizationMixin
from galaxy.webapps.base.webapp import GalaxyWebTransaction
from galaxy.webapps.galaxy.services.visualizations import VisualizationsService
from . import (
    BaseGalaxyAPIController,
    depends,
    DependsOnTrans,
    Router,
)

log = logging.getLogger(__name__)

router = Router(tags=["visualizations"])

VisualizationIdPathParam: EncodedDatabaseIdField = Path(
    ..., title="Visualization ID", description="The encoded database identifier of the Visualization."
)


@router.cbv
class FastAPIVisualizations:
    service: VisualizationsService = depends(VisualizationsService)

    @router.get(
        "/api/visualizations/{id}/sharing",
        summary="Get the current sharing status of the given Page.",
    )
    def sharing(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        id: EncodedDatabaseIdField = VisualizationIdPathParam,
    ) -> SharingStatus:
        """Return the sharing status of the item."""
        return self.service.shareable_service.sharing(trans, id)

    @router.put(
        "/api/visualizations/{id}/enable_link_access",
        summary="Makes this item accessible by a URL link.",
    )
    def enable_link_access(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        id: EncodedDatabaseIdField = VisualizationIdPathParam,
    ) -> SharingStatus:
        """Makes this item accessible by a URL link and return the current sharing status."""
        return self.service.shareable_service.enable_link_access(trans, id)

    @router.put(
        "/api/visualizations/{id}/disable_link_access",
        summary="Makes this item inaccessible by a URL link.",
    )
    def disable_link_access(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        id: EncodedDatabaseIdField = VisualizationIdPathParam,
    ) -> SharingStatus:
        """Makes this item inaccessible by a URL link and return the current sharing status."""
        return self.service.shareable_service.disable_link_access(trans, id)

    @router.put(
        "/api/visualizations/{id}/publish",
        summary="Makes this item public and accessible by a URL link.",
    )
    def publish(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        id: EncodedDatabaseIdField = VisualizationIdPathParam,
    ) -> SharingStatus:
        """Makes this item publicly available by a URL link and return the current sharing status."""
        return self.service.shareable_service.publish(trans, id)

    @router.put(
        "/api/visualizations/{id}/unpublish",
        summary="Removes this item from the published list.",
    )
    def unpublish(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        id: EncodedDatabaseIdField = VisualizationIdPathParam,
    ) -> SharingStatus:
        """Removes this item from the published list and return the current sharing status."""
        return self.service.shareable_service.unpublish(trans, id)

    @router.put(
        "/api/visualizations/{id}/share_with_users",
        summary="Share this item with specific users.",
    )
    def share_with_users(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        id: EncodedDatabaseIdField = VisualizationIdPathParam,
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
        trans: ProvidesUserContext = DependsOnTrans,
        id: EncodedDatabaseIdField = VisualizationIdPathParam,
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
    def index(self, trans: GalaxyWebTransaction, **kwargs):
        """
        GET /api/visualizations:
        """
        rval = []
        user = trans.user

        # TODO: search for: title, made by user, creation time range, type (vis name), dbkey, etc.
        # TODO: limit, offset, order_by
        # TODO: deleted

        # this is the default search - user's vis, vis shared with user, published vis
        visualizations = self.get_visualizations_by_user(trans, user)
        visualizations += self.get_visualizations_shared_with_user(trans, user)
        visualizations += self.get_published_visualizations(trans, exclude_user=user)
        # TODO: the admin case - everything

        for visualization in visualizations:
            item = self.get_visualization_summary_dict(visualization)
            item = trans.security.encode_dict_ids(item)
            item["url"] = web.url_for("visualization", id=item["id"])
            rval.append(item)

        return rval

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

        # there's a differentiation here between updating the visualiztion and creating a new revision
        #   that needs to be handled clearly here
        # or alternately, using a different controller like PUT /api/visualizations/{id}/r/{id}

        # TODO: consider allowing direct alteration of revisions title (without a new revision)
        #   only create a new revsion on a different config

        # only update owned visualizations
        visualization = self.get_visualization(trans, id, check_ownership=True)
        title = payload.get("title", visualization.latest_revision.title)
        dbkey = payload.get("dbkey", visualization.latest_revision.dbkey)
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
        trans.sa_session.flush()

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
            "model_class"
            # TODO: fill out when we create to_dict, get_dict, whatevs
        )
        # TODO: deleted
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
