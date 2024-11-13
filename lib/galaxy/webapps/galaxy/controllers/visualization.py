import logging
from json import loads

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
from galaxy.model.base import transaction
from galaxy.model.item_attrs import (
    UsesAnnotations,
    UsesItemRatings,
)
from galaxy.structured_app import StructuredApp
from galaxy.util.sanitize_html import sanitize_html
from galaxy.visualization.genomes import GenomeRegion
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
        with transaction(session):
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
            with transaction(session):
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

    @web.json
    def save(self, trans, vis_json=None, type=None, id=None, title=None, dbkey=None, annotation=None, **kwargs):
        """
        Save a visualization; if visualization does not have an ID, a new
        visualization is created. Returns JSON of visualization.
        """
        # Get visualization attributes from kwargs or from config.
        vis_config = loads(vis_json)
        vis_type = type or vis_config["type"]
        vis_id = id or vis_config.get("id", None)
        vis_title = title or vis_config.get("title", None)
        vis_dbkey = dbkey or vis_config.get("dbkey", None)
        vis_annotation = annotation or vis_config.get("annotation", None)
        return self.save_visualization(trans, vis_config, vis_type, vis_id, vis_title, vis_dbkey, vis_annotation)

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
                with transaction(trans.sa_session):
                    trans.sa_session.commit()
            return {"message": f"Attributes of '{v.title}' successfully saved.", "status": "success"}

    # ------------------------- registry.
    @web.expose
    @web.require_login("use Galaxy visualizations", use_panels=True)
    def render(self, trans, visualization_name, embedded=None, **kwargs):
        """
        Render the appropriate visualization template, parsing the `kwargs`
        into appropriate variables and resources (such as ORM models)
        based on this visualizations `param` data in visualizations_conf.xml.

        URL: /visualization/show/{visualization_name}
        """
        plugin = self._get_plugin_from_registry(trans, visualization_name)
        try:
            return plugin.render(trans=trans, embedded=embedded, **kwargs)
        except Exception as exception:
            return self._handle_plugin_error(trans, visualization_name, exception)

    def _get_plugin_from_registry(self, trans, visualization_name):
        """
        Get the named plugin from the registry.
        :raises HTTPNotFound: if registry has been turned off in config.
        :raises HTTPNotFound: if visualization_name isn't a registered plugin.
        """
        if not trans.app.visualizations_registry:
            raise HTTPNotFound("No visualization registry (possibly disabled in galaxy.ini)")
        return trans.app.visualizations_registry.get_plugin(visualization_name)

    def _handle_plugin_error(self, trans, visualization_name, exception):
        """
        Log, raise if debugging; log and show html message if not.
        """
        if isinstance(exception, MessageException):
            log.debug("error rendering visualization (%s): %s", visualization_name, exception)
        else:
            log.exception("error rendering visualization (%s)", visualization_name)
        if trans.debug:
            raise exception
        return trans.show_error_message(
            "There was an error rendering the visualization. "
            "Contact your Galaxy administrator if the problem persists."
            f"<br/>Details: {exception}",
            use_panels=False,
        )

    @web.expose
    @web.require_login("use Galaxy visualizations", use_panels=True)
    def saved(self, trans, id=None, revision=None, type=None, config=None, title=None, **kwargs):
        """
        Save (on POST) or load (on GET) a visualization then render.
        """
        # TODO: consider merging saved and render at this point (could break saved URLs, tho)
        if trans.request.method == "POST":
            self._POST_to_saved(trans, id=id, revision=revision, type=type, config=config, title=title, **kwargs)

        # check the id and load the saved visualization
        if id is None:
            return HTTPBadRequest("A valid visualization id is required to load a visualization")
        visualization = self.get_visualization(trans, id, check_ownership=False, check_accessible=True)

        # re-add title to kwargs for passing to render
        if title:
            kwargs["title"] = title
        plugin = self._get_plugin_from_registry(trans, visualization.type)
        try:
            return plugin.render_saved(visualization, trans=trans, **kwargs)
        except Exception as exception:
            self._handle_plugin_error(trans, visualization.type, exception)

    def _POST_to_saved(self, trans, id=None, revision=None, type=None, config=None, title=None, **kwargs):
        """
        Save the visualiztion info (revision, type, config, title, etc.) to
        the Visualization at `id` or to a new Visualization if `id` is None.

        Uses POST/redirect/GET after a successful save, redirecting to GET.
        """
        DEFAULT_VISUALIZATION_NAME = "Unnamed Visualization"

        # post to saved in order to save a visualization
        if type is None or config is None:
            return HTTPBadRequest("A visualization type and config are required to save a visualization")
        if isinstance(config, str):
            config = loads(config)
        title = title or DEFAULT_VISUALIZATION_NAME

        # TODO: allow saving to (updating) a specific revision - should be part of UsesVisualization
        # TODO: would be easier if this returned the visualization directly
        # check security if posting to existing visualization
        if id is not None:
            self.get_visualization(trans, id, check_ownership=True, check_accessible=False)
            # ??: on not owner: error raised, but not returned (status = 200)
        # TODO: there's no security check in save visualization (if passed an id)
        returned = self.save_visualization(trans, config, type, id, title)

        # redirect to GET to prevent annoying 'Do you want to post again?' dialog on page reload
        render_url = web.url_for(controller="visualization", action="saved", id=returned.get("vis_id"))
        return trans.response.send_redirect(render_url)

    #
    # Visualizations.
    #
    @web.expose
    @web.require_login()
    def trackster(self, trans, **kwargs):
        """
        Display browser for the visualization denoted by id and add the datasets listed in `dataset_ids`.
        """

        # define app configuration
        app = {"jscript": "trackster"}

        # get dataset to add
        id = kwargs.get("id", None)

        # get dataset to add
        new_dataset_id = kwargs.get("dataset_id", None)

        # set up new browser if no id provided
        if not id:
            # use dbkey from dataset to be added or from incoming parameter
            dbkey = None
            if new_dataset_id:
                decoded_id = self.decode_id(new_dataset_id)
                hda = self.hda_manager.get_owned(decoded_id, trans.user, current_history=trans.user)
                dbkey = hda.dbkey
                if dbkey == "?":
                    dbkey = kwargs.get("dbkey", None)

            # save database key
            app["default_dbkey"] = dbkey
        else:
            # load saved visualization
            vis = self.get_visualization(trans, id, check_ownership=False, check_accessible=True)
            app["viz_config"] = self.get_visualization_config(trans, vis)

        # backup id
        app["id"] = id

        # add dataset id
        app["add_dataset"] = new_dataset_id

        # check for gene region
        gene_region = GenomeRegion.from_str(kwargs.get("gene_region", ""))

        # update gene region of saved visualization if user parses a new gene region in the url
        if gene_region.chrom is not None:
            app["gene_region"] = {"chrom": gene_region.chrom, "start": gene_region.start, "end": gene_region.end}

        # fill template
        return trans.fill_template("visualization/trackster.mako", config={"app": app, "bundle": "extended"})
