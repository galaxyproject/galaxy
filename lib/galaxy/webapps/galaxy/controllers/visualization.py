import logging

from markupsafe import escape
from paste.httpexceptions import (
    HTTPBadRequest,
    HTTPNotFound,
)

from galaxy import (
    model,
    web,
)
from galaxy.exceptions import MessageException
from galaxy.managers.hdas import HDAManager
from galaxy.managers.sharable import SlugBuilder
from galaxy.model.item_attrs import (
    UsesAnnotations,
    UsesItemRatings,
)
from galaxy.structured_app import StructuredApp
from galaxy.util.sanitize_html import sanitize_html
from galaxy.webapps.base.controller import (
    BaseUIController,
    SharableMixin,
    UsesVisualizationMixin,
)
from ..api import depends

log = logging.getLogger(__name__)


class VisualizationController(
    BaseUIController, SharableMixin, UsesVisualizationMixin, UsesAnnotations, UsesItemRatings
):
    hda_manager: HDAManager = depends(HDAManager)
    slug_builder: SlugBuilder = depends(SlugBuilder)

    def __init__(self, app: StructuredApp):
        super().__init__(app)

    def get_visualization(self, trans, visualization_id, check_ownership=True, check_accessible=False):
        """
        Get a Visualization from the database by id, verifying ownership.
        """
        visualization = trans.sa_session.get(model.Visualization, trans.security.decode_id(visualization_id))
        if not visualization:
            raise MessageException("Visualization not found")
        else:
            return self.security_check(trans, visualization, check_ownership, check_accessible)

    #
    # -- Functions for operating on visualizations. --
    #

    @web.expose
    @web.require_login()
    def copy(self, trans, id, **kwargs):
        visualization = self.get_visualization(trans, id, check_ownership=False, check_accessible=True)
        user = trans.get_user()
        owner = visualization.user == user
        new_title = f"Copy of '{visualization.title}'"
        if not owner:
            new_title += f" shared by {visualization.user.email}"

        copied_viz = visualization.copy(user=trans.user, title=new_title)

        # Persist
        session = trans.sa_session
        session.add(copied_viz)
        session.commit()

        # Display the management page
        trans.set_message(f'Created new visualization with name "{copied_viz.title}"')
        return

    @web.expose
    @web.require_login("share Galaxy visualizations")
    def imp(self, trans, id, **kwargs):
        """Import a visualization into user's workspace."""
        # Set referer message.
        referer = trans.request.referer
        if referer and not referer.startswith(f"{trans.request.application_url}{web.url_for('/login')}"):
            referer_message = f"<a href='{escape(referer)}'>return to the previous page</a>"
        else:
            referer_message = f"<a href='{web.url_for('/')}'>go to Galaxy's start page</a>"

        # Do import.
        session = trans.sa_session
        visualization = self.get_visualization(trans, id, check_ownership=False, check_accessible=True)
        if visualization.importable is False:
            return trans.show_error_message(
                f"The owner of this visualization has disabled imports via this link.<br>You can {referer_message}",
                use_panels=True,
            )
        elif visualization.deleted:
            return trans.show_error_message(
                f"You can't import this visualization because it has been deleted.<br>You can {referer_message}",
                use_panels=True,
            )
        else:
            # Create imported visualization via copy.
            #   TODO: need to handle custom db keys.

            imported_visualization = visualization.copy(user=trans.user, title=f"imported: {visualization.title}")

            # Persist
            session = trans.sa_session
            session.add(imported_visualization)
            session.commit()

            # Redirect to load galaxy frames.
            return trans.show_ok_message(
                message="""Visualization "{}" has been imported. <br>You can <a href="{}">start using this visualization</a> or {}.""".format(
                    visualization.title, web.url_for("/visualizations/list"), referer_message
                ),
                use_panels=True,
            )

    def _display_by_username_and_slug(self, trans, username, slug, **kwargs):
        """Display visualization based on a username and slug."""

        # Get visualization.
        session = trans.sa_session
        user = session.query(model.User).filter_by(username=username).first()
        visualization = (
            trans.sa_session.query(model.Visualization).filter_by(user=user, slug=slug, deleted=False).first()
        )
        if visualization is None:
            raise web.httpexceptions.HTTPNotFound()

        # Security check raises error if user cannot access visualization.
        self.security_check(trans, visualization, check_ownership=False, check_accessible=True)

        # Encode page identifier.
        visualization_id = trans.security.encode_id(visualization.id)

        # Redirect to client.
        return trans.response.send_redirect(
            web.url_for(
                controller="published",
                action="visualization",
                id=visualization_id,
            )
        )

    @web.legacy_expose_api
    @web.require_login("edit visualizations")
    def edit(self, trans, payload=None, **kwd):
        """
        Edit a visualization's attributes.
        """
        id = kwd.get("id")
        if not id:
            return self.message_exception(trans, "No visualization id received for editing.")
        trans_user = trans.get_user()
        v = self.get_visualization(trans, id, check_ownership=True)
        if trans.request.method == "GET":
            if v.slug is None:
                self.slug_builder.create_item_slug(trans.sa_session, v)
            return {
                "title": "Edit visualization attributes",
                "inputs": [
                    {"name": "title", "label": "Name", "value": v.title},
                    {
                        "name": "slug",
                        "label": "Identifier",
                        "value": v.slug,
                        "help": "A unique identifier that will be used for public links to this visualization. This field can only contain lowercase letters, numbers, and dashes (-).",
                    },
                    {
                        "name": "dbkey",
                        "label": "Build",
                        "type": "select",
                        "optional": True,
                        "value": v.dbkey,
                        "options": trans.app.genomes.get_dbkeys(trans_user, chrom_info=True),
                        "help": "Parameter to associate your visualization with a database key.",
                    },
                    {
                        "name": "annotation",
                        "label": "Annotation",
                        "value": self.get_item_annotation_str(trans.sa_session, trans.user, v),
                        "help": "A description of the visualization. The annotation is shown alongside published visualizations.",
                    },
                ],
            }
        else:
            v_title = payload.get("title")
            v_slug = payload.get("slug")
            v_dbkey = payload.get("dbkey")
            v_annotation = payload.get("annotation")
            if not v_title:
                return self.message_exception(trans, "Please provide a visualization name is required.")
            elif not v_slug:
                return self.message_exception(trans, "Please provide a unique identifier.")
            elif not self._is_valid_slug(v_slug):
                return self.message_exception(
                    trans, "Visualization identifier can only contain lowercase letters, numbers, and dashes (-)."
                )
            elif (
                v_slug != v.slug
                and trans.sa_session.query(model.Visualization)
                .filter_by(user=v.user, slug=v_slug, deleted=False)
                .first()
            ):
                return self.message_exception(trans, "Visualization id must be unique.")
            else:
                v.title = v_title
                v.slug = v_slug
                v.dbkey = v_dbkey
                if v_annotation:
                    v_annotation = sanitize_html(v_annotation)
                    self.add_item_annotation(trans.sa_session, trans_user, v, v_annotation)
                trans.sa_session.add(v)
                trans.sa_session.commit()
            return {"message": f"Attributes of '{v.title}' successfully saved.", "status": "success"}
