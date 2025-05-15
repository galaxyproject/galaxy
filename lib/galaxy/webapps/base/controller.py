"""
Contains functionality needed in every web interface
"""

import logging
from typing import (
    Any,
    Callable,
    Optional,
)

from webob.exc import (
    HTTPBadRequest,
    HTTPInternalServerError,
    HTTPNotImplemented,
)

from galaxy import (
    exceptions,
    security,
    util,
    web,
)
from galaxy.datatypes.interval import ChromatinInteractions
from galaxy.managers import (
    base as managers_base,
    configuration,
    users,
    workflows,
)
from galaxy.managers.forms import (
    get_filtered_form_definitions_current,
    get_form_definitions,
    get_form_definitions_current,
)
from galaxy.managers.sharable import (
    slug_exists,
    SlugBuilder,
)
from galaxy.model import (
    Dataset,
    ExtendedMetadata,
    ExtendedMetadataIndex,
    HistoryDatasetAssociation,
    HistoryDatasetCollectionAssociation,
    LibraryDatasetDatasetAssociation,
    LibraryDatasetPermissions,
    StoredWorkflow,
)
from galaxy.model.item_attrs import UsesAnnotations
from galaxy.structured_app import BasicSharedApp
from galaxy.util.dictifiable import Dictifiable
from galaxy.util.sanitize_html import sanitize_html
from galaxy.web import (
    error,
    url_for,
)
from galaxy.web.form_builder import (
    AddressField,
    CheckboxField,
    PasswordField,
)
from galaxy.workflow.modules import WorkflowModuleInjector

log = logging.getLogger(__name__)

# States for passing messages
SUCCESS, INFO, WARNING, ERROR = "done", "info", "warning", "error"


class BaseController:
    """
    Base class for Galaxy web application controllers.
    """

    def __init__(self, app: BasicSharedApp):
        """Initialize an interface for application 'app'"""
        self.app = app
        self.sa_session = app.model.context
        self.user_manager = users.UserManager(app)

    def get_toolbox(self):
        """Returns the application toolbox"""
        return self.app.toolbox

    def get_class(self, class_name):
        """Returns the class object that a string denotes. Without this method, we'd have to do eval(<class_name>)."""
        return managers_base.get_class(class_name)

    def get_object(self, trans, id, class_name, check_ownership=False, check_accessible=False, deleted=None):
        """
        Convenience method to get a model object with the specified checks.
        """
        return managers_base.get_object(
            trans, id, class_name, check_ownership=check_ownership, check_accessible=check_accessible, deleted=deleted
        )

    # this should be here - but catching errors from sharable item controllers that *should* have SharableItemMixin
    #   but *don't* then becomes difficult
    # def security_check( self, trans, item, check_ownership=False, check_accessible=False ):
    #    log.warning( 'BaseController.security_check: %s, %b, %b', str( item ), check_ownership, check_accessible )
    #    # meant to be overridden in SharableSecurityMixin
    #    return item

    def get_user(self, trans, id, check_ownership=False, check_accessible=False, deleted=None):
        return self.get_object(trans, id, "User", check_ownership=False, check_accessible=False, deleted=deleted)

    def get_group(self, trans, id, check_ownership=False, check_accessible=False, deleted=None):
        return self.get_object(trans, id, "Group", check_ownership=False, check_accessible=False, deleted=deleted)

    def get_role(self, trans, id, check_ownership=False, check_accessible=False, deleted=None):
        return self.get_object(trans, id, "Role", check_ownership=False, check_accessible=False, deleted=deleted)

    # ---- parsing query params
    def decode_id(self, id):
        return managers_base.decode_id(self.app, id)

    def encode_all_ids(self, trans, rval, recursive=False):
        """
        Encodes all integer values in the dict rval whose keys are 'id' or end with '_id'

        It might be useful to turn this in to a decorator
        """
        return trans.security.encode_all_ids(rval, recursive=recursive)

    # TODO this will be replaced by lib.galaxy.managers.base.ModelFilterParser.build_filter_params
    def parse_filter_params(self, qdict, filter_attr_key="q", filter_value_key="qv", attr_op_split_char="-"):
        """ """
        # TODO: import DEFAULT_OP from FilterParser
        DEFAULT_OP = "eq"
        if filter_attr_key not in qdict:
            return []
        # precondition: attrs/value pairs are in-order in the qstring
        attrs = qdict.get(filter_attr_key)
        if not isinstance(attrs, list):
            attrs = [attrs]
        # ops are strings placed after the attr strings and separated by a split char (e.g. 'create_time-lt')
        # ops are optional and default to 'eq'
        reparsed_attrs = []
        ops = []
        for attr in attrs:
            op = DEFAULT_OP
            if attr_op_split_char in attr:
                # note: only split the last (e.g. q=community-tags-in&qv=rna yields ( 'community-tags', 'in', 'rna' )
                attr, op = attr.rsplit(attr_op_split_char, 1)
            ops.append(op)
            reparsed_attrs.append(attr)
        attrs = reparsed_attrs

        values = qdict.get(filter_value_key, [])
        if not isinstance(values, list):
            values = [values]
        # TODO: it may be more helpful to the consumer if we error on incomplete 3-tuples
        #   (instead of relying on zip to shorten)
        return list(zip(attrs, ops, values))

    def parse_limit_offset(self, qdict):
        """ """

        def _parse_pos_int(i):
            try:
                new_val = int(i)
                if new_val >= 0:
                    return new_val
            except (TypeError, ValueError):
                pass
            return None

        limit = _parse_pos_int(qdict.get("limit", None))
        offset = _parse_pos_int(qdict.get("offset", None))
        return (limit, offset)


Root = BaseController


class BaseUIController(BaseController):
    def get_object(self, trans, id, class_name, check_ownership=False, check_accessible=False, deleted=None):
        try:
            return BaseController.get_object(
                self,
                trans,
                id,
                class_name,
                check_ownership=check_ownership,
                check_accessible=check_accessible,
                deleted=deleted,
            )
        except exceptions.MessageException:
            raise  # handled in the caller
        except Exception:
            log.exception("Exception in get_object check for %s %s:", class_name, str(id))
            raise Exception(f"Server error retrieving {class_name} id ( {str(id)} ).")

    def message_exception(self, trans, message, sanitize=True):
        trans.response.status = 400
        return {"err_msg": util.sanitize_text(message) if sanitize else message}


class BaseAPIController(BaseController):
    def get_object(self, trans, id, class_name, check_ownership=False, check_accessible=False, deleted=None):
        try:
            return BaseController.get_object(
                self,
                trans,
                id,
                class_name,
                check_ownership=check_ownership,
                check_accessible=check_accessible,
                deleted=deleted,
            )

        except exceptions.MessageException:
            raise
        except Exception as e:
            log.exception("Exception in get_object check for %s %s.", class_name, str(id))
            raise HTTPInternalServerError(comment=util.unicodify(e))

    def not_implemented(self, trans, **kwd):
        raise HTTPNotImplemented()

    def _parse_serialization_params(self, kwd, default_view):
        view = kwd.get("view", None)
        keys = kwd.get("keys")
        if isinstance(keys, str):
            keys = keys.split(",")
        return dict(view=view, keys=keys, default_view=default_view)

    # TODO: this will be replaced by lib.galaxy.schema.FilterQueryParams.build_order_by
    def _parse_order_by(self, manager, order_by_string):
        if (ORDER_BY_SEP_CHAR := ",") in order_by_string:
            return [manager.parse_order_by(o) for o in order_by_string.split(ORDER_BY_SEP_CHAR)]
        return manager.parse_order_by(order_by_string)


class JSAppLauncher(BaseUIController):
    """
    A controller that launches JavaScript web applications.
    """

    #: path to js app template
    JS_APP_MAKO_FILEPATH = "/js-app.mako"
    #: window-scoped js function to call to start the app (will be passed options, bootstrapped)
    DEFAULT_ENTRY_FN = "app"
    #: keys used when serializing current user for bootstrapped data
    USER_BOOTSTRAP_KEYS = (
        "id",
        "email",
        "username",
        "is_admin",
        "total_disk_usage",
        "nice_total_disk_usage",
        "quota_percent",
        "preferences",
    )

    def __init__(self, app):
        super().__init__(app)
        self.user_manager = users.UserManager(app)
        self.user_serializer = users.CurrentUserSerializer(app)
        self.config_serializer = configuration.ConfigSerializer(app)
        self.admin_config_serializer = configuration.AdminConfigSerializer(app)

    def _check_require_login(self, trans):
        if self.app.config.require_login and self.user_manager.is_anonymous(trans.user):
            # TODO: this doesn't properly redirect when login is done
            # (see webapp __ensure_logged_in_user for the initial redirect - not sure why it doesn't redirect to login?)
            login_url = web.url_for(controller="root", action="login")
            trans.response.send_redirect(login_url)

    @web.expose
    def client(self, trans, **kwd):
        """
        Endpoint for clientside routes.  This ships the primary SPA client.

        Should not be used with url_for -- see
        (https://github.com/galaxyproject/galaxy/issues/1878) for why.
        """
        return self._bootstrapped_client(trans, **kwd)

    # This includes contextualized user options in the bootstrapped data; we
    # don't want to cache it.
    @web.do_not_cache
    def _bootstrapped_client(self, trans, app_name="analysis", **kwd):
        js_options = self._get_js_options(trans)
        js_options["config"].update(self._get_extended_config(trans))
        return self.template(trans, app_name, options=js_options, **kwd)

    def _get_js_options(self, trans, root=None):
        """
        Return a dictionary of session/site configuration/options to jsonify
        and pass onto the js app.

        Defaults to `config`, `user`, and the root url. Pass kwargs to update further.
        """
        root = root or web.url_for("/")
        js_options = {
            "root": root,
            "user": self.user_serializer.serialize(trans.user, self.USER_BOOTSTRAP_KEYS, trans=trans),
            "config": self._get_site_configuration(trans),
            "params": dict(trans.request.params),
            "session_csrf_token": trans.session_csrf_token,
        }
        return js_options

    def _get_extended_config(self, trans):
        config = {
            "active_view": "analysis",
            "enable_webhooks": True if trans.app.webhooks_registry.webhooks else False,
            "message_box_visible": trans.app.config.message_box_visible,
            "show_inactivity_warning": trans.app.config.user_activation_on and trans.user and not trans.user.active,
            "tool_dynamic_configs": list(trans.app.toolbox.dynamic_conf_filenames()),
        }

        # TODO: move to user
        stored_workflow_menu_index = {}
        stored_workflow_menu_entries = []
        for menu_item in getattr(trans.user, "stored_workflow_menu_entries", []):
            encoded_stored_workflow_id = trans.security.encode_id(menu_item.stored_workflow_id)
            if encoded_stored_workflow_id not in stored_workflow_menu_index:
                stored_workflow_menu_index[encoded_stored_workflow_id] = True
                stored_workflow_menu_entries.append(
                    {"id": encoded_stored_workflow_id, "name": util.unicodify(menu_item.stored_workflow.name)}
                )
        config["stored_workflow_menu_entries"] = stored_workflow_menu_entries
        return config

    def _get_site_configuration(self, trans):
        """
        Return a dictionary representing Galaxy's current configuration.
        """
        try:
            serializer = self.config_serializer
            if self.user_manager.is_admin(trans.user, trans=trans):
                serializer = self.admin_config_serializer
            return serializer.serialize_to_view(self.app.config, view="all", host=trans.host)
        except Exception as exc:
            log.exception(exc)
            return {}

    def template(
        self,
        trans,
        app_name: str,
        entry_fn: str = "app",
        options=None,
        bootstrapped_data: Optional[dict] = None,
        masthead: Optional[bool] = True,
        **additional_options,
    ):
        """
        Render and return the single page mako template that starts the app.

        :param app_name: the first portion of the webpack bundle to as the app.
        :param entry_fn: the name of the window-scope function that starts the
                         app. Defaults to 'app'.
        :param bootstrapped_data: update containing any more data
                                  the app may need.
        :param masthead: include masthead elements in the initial page dom.
        :param additional_options: update to the options sent to the app.
        """
        options = options or self._get_js_options(trans)
        options.update(additional_options)
        return trans.fill_template(
            self.JS_APP_MAKO_FILEPATH,
            js_app_name=app_name,
            js_app_entry_fn=(entry_fn or self.DEFAULT_ENTRY_FN),
            options=options,
            bootstrapped=(bootstrapped_data or {}),
            masthead=masthead,
        )


class Datatype:
    """Used for storing in-memory list of datatypes currently in the datatypes registry."""

    def __init__(self, extension, dtype, type_extension, mimetype, display_in_upload):
        self.extension = extension
        self.dtype = dtype
        self.type_extension = type_extension
        self.mimetype = mimetype
        self.display_in_upload = display_in_upload


#
# -- Mixins for working with Galaxy objects. --
#


class SharableItemSecurityMixin:
    """Mixin for handling security for sharable items."""

    def security_check(self, trans, item, check_ownership=False, check_accessible=False):
        """Security checks for an item: checks if (a) user owns item or (b) item is accessible to user."""
        return managers_base.security_check(
            trans, item, check_ownership=check_ownership, check_accessible=check_accessible
        )


class UsesLibraryMixinItems(SharableItemSecurityMixin):
    get_object: Callable

    def get_library_folder(self, trans, id: int, check_ownership=False, check_accessible=True):
        return self.get_object(trans, id, "LibraryFolder", check_ownership=False, check_accessible=check_accessible)

    def get_library_dataset_dataset_association(self, trans, id, check_ownership=False, check_accessible=True):
        # Deprecated in lieu to galaxy.managers.lddas.LDDAManager.get() but not
        # reusing that exactly because of subtle differences in exception handling
        # logic (API controller override get_object to be slightly different).
        return self.get_object(
            trans, id, "LibraryDatasetDatasetAssociation", check_ownership=False, check_accessible=check_accessible
        )

    def get_library_dataset(self, trans, id, check_ownership=False, check_accessible=True):
        return self.get_object(trans, id, "LibraryDataset", check_ownership=False, check_accessible=check_accessible)

    # TODO: it makes no sense that I can get roles from a user but not user.is_admin()
    # def can_user_add_to_library_item( self, trans, user, item ):
    #    if not user: return False
    #    return (  ( user.is_admin() )
    #           or ( trans.app.security_agent.can_add_library_item( user.all_roles(), item ) ) )

    def can_current_user_add_to_library_item(self, trans, item):
        if not trans.user:
            return False
        return trans.user_is_admin or trans.app.security_agent.can_add_library_item(
            trans.get_current_user_roles(), item
        )

    def check_user_can_add_to_library_item(self, trans, item, check_accessible=True):
        """
        Raise exception if user cannot add to the specified library item (i.e.
        Folder). Can set check_accessible to False if folder was loaded with
        this check.
        """
        if not trans.user:
            raise exceptions.ItemAccessibilityException("Anonymous users cannot add to library items")

        current_user_roles = trans.get_current_user_roles()
        if trans.user_is_admin:
            return True

        if check_accessible:
            if not trans.app.security_agent.can_access_library_item(current_user_roles, item, trans.user):
                raise exceptions.ItemAccessibilityException("You do not have access to the requested item")

        if not trans.app.security_agent.can_add_library_item(trans.get_current_user_roles(), item):
            # Slight misuse of ItemOwnershipException?
            raise exceptions.ItemOwnershipException("User cannot add to library item.")

    def _copy_hdca_to_library_folder(self, trans, hda_manager, from_hdca_id: int, folder_id: int, ldda_message=""):
        """
        Fetches the collection identified by `from_hcda_id` and dispatches individual collection elements to
        _copy_hda_to_library_folder
        """
        hdca = trans.sa_session.get(HistoryDatasetCollectionAssociation, from_hdca_id)
        if hdca.collection.collection_type != "list":
            raise exceptions.NotImplemented(
                "Cannot add nested collections to library. Please flatten your collection first."
            )
        hdas = []
        for element in hdca.collection.elements:
            hdas.append((element.element_identifier, element.dataset_instance.id))
        return [
            self._copy_hda_to_library_folder(
                trans,
                hda_manager=hda_manager,
                from_hda_id=hda_id,
                folder_id=folder_id,
                ldda_message=ldda_message,
                element_identifier=element_identifier,
            )
            for (element_identifier, hda_id) in hdas
        ]

    def _copy_hda_to_library_folder(
        self, trans, hda_manager, from_hda_id: int, folder_id: int, ldda_message="", element_identifier=None
    ):
        """
        Copies hda ``from_hda_id`` to library folder ``folder_id``, optionally
        adding ``ldda_message`` to the new ldda's ``message``.

        ``library_contents.create`` will branch to this if called with 'from_hda_id'
        in its payload.
        """
        log.debug(f"_copy_hda_to_library_folder: {str((from_hda_id, folder_id, ldda_message))}")
        # TODO: allow name and other, editable ldda attrs?
        if ldda_message:
            ldda_message = sanitize_html(ldda_message)

        # check permissions on (all three?) resources: hda, library, folder
        # TODO: do we really need the library??
        hda = hda_manager.get_owned(from_hda_id, trans.user, current_history=trans.history)
        hda = hda_manager.error_if_uploading(hda)
        folder = self.get_library_folder(trans, folder_id, check_accessible=True)

        # TOOD: refactor to use check_user_can_add_to_library_item, eliminate boolean
        # can_current_user_add_to_library_item.
        if folder.parent_library.deleted:
            raise exceptions.ObjectAttributeInvalidException(
                "You cannot add datasets into deleted library. Undelete it first."
            )
        if not self.can_current_user_add_to_library_item(trans, folder):
            raise exceptions.InsufficientPermissionsException(
                "You do not have proper permissions to add a dataset to this folder,"
            )

        ldda = self.copy_hda_to_library_folder(
            trans, hda, folder, ldda_message=ldda_message, element_identifier=element_identifier
        )
        # I don't see a reason why hdas copied into libraries should not be visible.
        # If there is, refactor `ldda.visible = True` to do this only when adding HDCAs.
        ldda.visible = True
        ldda.update_parent_folder_update_times()
        trans.sa_session.commit()
        ldda_dict = ldda.to_dict()
        rval = trans.security.encode_dict_ids(ldda_dict)
        update_time = ldda.update_time.isoformat()
        rval["update_time"] = update_time
        return rval

    def copy_hda_to_library_folder(
        self, trans, hda, library_folder, roles=None, ldda_message="", element_identifier=None
    ):
        # PRECONDITION: permissions for this action on hda and library_folder have been checked
        roles = roles or []

        # this code was extracted from library_common.add_history_datasets_to_library
        # TODO: refactor library_common.add_history_datasets_to_library to use this for each hda to copy

        # create the new ldda and apply the folder perms to it
        ldda = hda.to_library_dataset_dataset_association(
            trans,
            target_folder=library_folder,
            roles=roles,
            ldda_message=ldda_message,
            element_identifier=element_identifier,
        )
        self._apply_library_folder_permissions_to_ldda(trans, library_folder, ldda)
        self._apply_hda_permissions_to_ldda(trans, hda, ldda)
        # TODO:?? not really clear on how permissions are being traded here
        #   seems like hda -> ldda permissions should be set in to_library_dataset_dataset_association
        #   then they get reset in _apply_library_folder_permissions_to_ldda
        #   then finally, re-applies hda -> ldda for missing actions in _apply_hda_permissions_to_ldda??
        return ldda

    def _apply_library_folder_permissions_to_ldda(self, trans, library_folder, ldda):
        """
        Copy actions/roles from library folder to an ldda (and its library_dataset).
        """
        # PRECONDITION: permissions for this action on library_folder and ldda have been checked
        security_agent = trans.app.security_agent
        security_agent.copy_library_permissions(trans, library_folder, ldda)
        security_agent.copy_library_permissions(trans, library_folder, ldda.library_dataset)
        return security_agent.get_permissions(ldda)

    def _apply_hda_permissions_to_ldda(self, trans, hda, ldda):
        """
        Copy actions/roles from hda to ldda.library_dataset (and then ldda) if ldda
        doesn't already have roles for the given action.
        """
        # PRECONDITION: permissions for this action on hda and ldda have been checked
        # Make sure to apply any defined dataset permissions, allowing the permissions inherited from the
        #   library_dataset to over-ride the same permissions on the dataset, if they exist.
        security_agent = trans.app.security_agent
        dataset_permissions_dict = security_agent.get_permissions(hda.dataset)
        library_dataset = ldda.library_dataset
        library_dataset_actions = [permission.action for permission in library_dataset.actions]

        # except that: if DATASET_MANAGE_PERMISSIONS exists in the hda.dataset permissions,
        #   we need to instead apply those roles to the LIBRARY_MANAGE permission to the library dataset
        dataset_manage_permissions_action = security_agent.get_action("DATASET_MANAGE_PERMISSIONS").action
        library_manage_permissions_action = security_agent.get_action("LIBRARY_MANAGE").action
        # TODO: test this and remove if in loop below
        # TODO: doesn't handle action.action
        # if dataset_manage_permissions_action in dataset_permissions_dict:
        #    managing_roles = dataset_permissions_dict.pop( dataset_manage_permissions_action )
        #    dataset_permissions_dict[ library_manage_permissions_action ] = managing_roles

        flush_needed = False
        for action, dataset_permissions_roles in dataset_permissions_dict.items():
            if isinstance(action, security.Action):
                action = action.action

            # alter : DATASET_MANAGE_PERMISSIONS -> LIBRARY_MANAGE (see above)
            if action == dataset_manage_permissions_action:
                action = library_manage_permissions_action

            # TODO: generalize to util.update_dict_without_overwrite
            # add the hda actions & roles to the library_dataset
            # NOTE: only apply an hda perm if it's NOT set in the library_dataset perms (don't overwrite)
            if action not in library_dataset_actions:
                for role in dataset_permissions_roles:
                    ldps = LibraryDatasetPermissions(action, library_dataset, role)
                    ldps = [ldps] if not isinstance(ldps, list) else ldps
                    for ldp in ldps:
                        trans.sa_session.add(ldp)
                        flush_needed = True

        if flush_needed:
            trans.sa_session.commit()

        # finally, apply the new library_dataset to its associated ldda (must be the same)
        security_agent.copy_library_permissions(trans, library_dataset, ldda)
        return security_agent.get_permissions(ldda)


class UsesVisualizationMixin(UsesLibraryMixinItems):
    """
    Mixin for controllers that use Visualization objects.
    """

    slug_builder = SlugBuilder()

    def get_tool_def(self, trans, hda):
        """Returns definition of an interactive tool for an HDA."""

        # Get dataset's job.
        job = None
        for job_output_assoc in hda.creating_job_associations:
            job = job_output_assoc.job
            break
        if not job:
            return None

        tool = trans.app.toolbox.get_tool(job.tool_id, tool_version=job.tool_version)
        if not tool:
            return None

        # Tool must have a Trackster configuration.
        if not tool.trackster_conf:
            return None

        # -- Get tool definition and add input values from job. --
        tool_dict = tool.to_dict(trans, io_details=True)
        tool_param_values = {p.name: p.value for p in job.parameters}
        tool_param_values = tool.params_from_strings(tool_param_values, trans.app, ignore_errors=True)

        # Only get values for simple inputs for now.
        inputs_dict = [i for i in tool_dict["inputs"] if i["type"] not in ["data", "hidden_data", "conditional"]]
        for t_input in inputs_dict:
            # Add value to tool.
            if "name" in t_input:
                name = t_input["name"]
                if name in tool_param_values:
                    value = tool_param_values[name]
                    if isinstance(value, Dictifiable):
                        value = value.to_dict()
                    t_input["value"] = value

        return tool_dict

    def get_visualization_config(self, trans, visualization):
        """Returns a visualization's configuration. Only works for trackster visualizations right now."""
        config = None
        if visualization.type in ["trackster", "genome"]:
            # Unpack Trackster config.
            latest_revision = visualization.latest_revision
            bookmarks = latest_revision.config.get("bookmarks", [])

            def pack_track(track_dict):
                unencoded_id = track_dict.get("dataset_id")
                if unencoded_id:
                    encoded_id = trans.security.encode_id(unencoded_id)
                else:
                    encoded_id = track_dict["dataset"]["id"]
                hda_ldda = track_dict.get("hda_ldda", "hda")

                dataset = self.get_hda_or_ldda(trans, hda_ldda, encoded_id)
                try:
                    prefs = track_dict["prefs"]
                except KeyError:
                    prefs = {}
                track_data_provider = trans.app.data_provider_registry.get_data_provider(
                    trans, original_dataset=dataset, source="data"
                )
                return {
                    "track_type": dataset.datatype.track_type,
                    "dataset": trans.security.encode_dict_ids(dataset.to_dict()),
                    "prefs": prefs,
                    "mode": track_dict.get("mode", "Auto"),
                    "filters": track_dict.get("filters", {"filters": track_data_provider.get_filters()}),
                    "tool": self.get_tool_def(trans, dataset),
                    "tool_state": track_dict.get("tool_state", {}),
                }

            def pack_collection(collection_dict):
                drawables = []
                for drawable_dict in collection_dict["drawables"]:
                    if "track_type" in drawable_dict:
                        drawables.append(pack_track(drawable_dict))
                    else:
                        drawables.append(pack_collection(drawable_dict))
                return {
                    "obj_type": collection_dict["obj_type"],
                    "drawables": drawables,
                    "prefs": collection_dict.get("prefs", []),
                    "filters": collection_dict.get("filters", {}),
                }

            def encode_dbkey(dbkey):
                """
                Encodes dbkey as needed. For now, prepends user's public name
                to custom dbkey keys.
                """
                encoded_dbkey = dbkey
                user = visualization.user
                if "dbkeys" in user.preferences and str(dbkey) in user.preferences["dbkeys"]:
                    encoded_dbkey = f"{user.username}:{dbkey}"
                return encoded_dbkey

            # Set tracks.
            tracks = []
            if "tracks" in latest_revision.config:
                # Legacy code.
                for track_dict in visualization.latest_revision.config["tracks"]:
                    tracks.append(pack_track(track_dict))
            elif "view" in latest_revision.config:
                for drawable_dict in visualization.latest_revision.config["view"]["drawables"]:
                    if "track_type" in drawable_dict:
                        tracks.append(pack_track(drawable_dict))
                    else:
                        tracks.append(pack_collection(drawable_dict))

            config = {
                "title": visualization.title,
                "vis_id": trans.security.encode_id(visualization.id) if visualization.id is not None else None,
                "tracks": tracks,
                "bookmarks": bookmarks,
                "chrom": "",
                "dbkey": encode_dbkey(visualization.dbkey),
            }

            if "viewport" in latest_revision.config:
                config["viewport"] = latest_revision.config["viewport"]
        else:
            # Default action is to return config unaltered.
            latest_revision = visualization.latest_revision
            config = latest_revision.config

        return config

    def get_new_track_config(self, trans, dataset):
        """
        Returns track configuration dict for a dataset.
        """
        # Get data provider.
        track_data_provider = trans.app.data_provider_registry.get_data_provider(trans, original_dataset=dataset)

        # Get track definition.
        return {
            "track_type": dataset.datatype.track_type,
            "name": dataset.name,
            "dataset": trans.security.encode_dict_ids(dataset.to_dict()),
            "prefs": {},
            "filters": {"filters": track_data_provider.get_filters()},
            "tool": self.get_tool_def(trans, dataset),
            "tool_state": {},
        }

    def get_hda_or_ldda(self, trans, hda_ldda, dataset_id):
        """Returns either HDA or LDDA for hda/ldda and id combination."""
        if hda_ldda == "hda":
            return self.get_hda(trans, dataset_id, check_ownership=False, check_accessible=True)
        else:
            return self.get_library_dataset_dataset_association(trans, dataset_id)

    def get_hda(self, trans, dataset_id, check_ownership=True, check_accessible=False, check_state=True):
        """
        Get an HDA object by id performing security checks using
        the current transaction.

        Deprecated in lieu to galaxy.managers.hdas.HDAManager.get_accessible(decoded_id, user)
        """
        try:
            dataset_id = trans.security.decode_id(dataset_id)
        except (AttributeError, TypeError):
            raise HTTPBadRequest(f"Invalid dataset id: {str(dataset_id)}.")

        try:
            data = trans.sa_session.get(HistoryDatasetAssociation, int(dataset_id))
        except Exception:
            raise HTTPBadRequest(f"Invalid dataset id: {str(dataset_id)}.")

        if not data:
            raise HTTPBadRequest(f"Invalid dataset id: {str(dataset_id)}.")

        if check_ownership:
            # Verify ownership.
            user = trans.get_user()
            if not user:
                error("Must be logged in to manage Galaxy items")
            if data.user != user:
                error(f"{data.__class__.__name__} is not owned by current user")

        if check_accessible:
            current_user_roles = trans.get_current_user_roles()

            if not trans.app.security_agent.can_access_dataset(current_user_roles, data.dataset):
                error("You are not allowed to access this dataset")

            if check_state and data.state == Dataset.states.UPLOAD:
                return trans.show_error_message(
                    "Please wait until this dataset finishes uploading " + "before attempting to view it."
                )
        return data

    def _get_genome_data(self, trans, dataset, dbkey=None):
        """
        Returns genome-wide data for dataset if available; if not, message is returned.
        """
        rval = None

        # Get data sources.
        data_sources = dataset.get_datasources(trans)
        query_dbkey = dataset.dbkey
        if query_dbkey == "?":
            query_dbkey = dbkey
        chroms_info = self.app.genomes.chroms(trans, dbkey=query_dbkey)

        # If there are no messages (messages indicate data is not ready/available), get data.
        messages_list = [data_source_dict["message"] for data_source_dict in data_sources.values()]
        if message := self._get_highest_priority_msg(messages_list):
            rval = message
        else:
            # HACK: chromatin interactions tracks use data as source.
            source = "index"
            if isinstance(dataset.datatype, ChromatinInteractions):
                source = "data"

            data_provider = trans.app.data_provider_registry.get_data_provider(
                trans, original_dataset=dataset, source=source
            )
            # HACK: pass in additional params which are used for only some
            # types of data providers; level, cutoffs used for summary tree,
            # num_samples for BBI, and interchromosomal used for chromatin interactions.
            rval = data_provider.get_genome_data(
                chroms_info, level=4, detail_cutoff=0, draw_cutoff=0, num_samples=150, interchromosomal=True
            )

        return rval

    # FIXME: this method probably belongs down in the model.Dataset class.
    def _get_highest_priority_msg(self, message_list):
        """
        Returns highest priority message from a list of messages.
        """
        return_message = None

        # For now, priority is: job error (dict), no converter, pending.
        for message in message_list:
            if message is not None:
                if isinstance(message, dict):
                    return_message = message
                    break
                elif message == "no converter":
                    return_message = message
                elif return_message is None and message == "pending":
                    return_message = message
        return return_message


class UsesStoredWorkflowMixin(SharableItemSecurityMixin, UsesAnnotations):
    """Mixin for controllers that use StoredWorkflow objects."""

    slug_builder = SlugBuilder()

    def get_stored_workflow(self, trans, id, check_ownership=True, check_accessible=False):
        """Get a StoredWorkflow from the database by id, verifying ownership."""
        # Load workflow from database
        workflow_contents_manager = workflows.WorkflowsManager(self.app)
        workflow = workflow_contents_manager.get_stored_workflow(trans=trans, workflow_id=id)

        if not workflow:
            error("Workflow not found")
        else:
            self.security_check(trans, workflow, check_ownership, check_accessible)

            # Older workflows may be missing slugs, so set them here.
            if not workflow.slug:
                self.slug_builder.create_item_slug(trans.sa_session, workflow)
                trans.sa_session.commit()

        return workflow

    def get_stored_workflow_steps(self, trans, stored_workflow: StoredWorkflow):
        """Restores states for a stored workflow's steps."""
        module_injector = WorkflowModuleInjector(trans)
        workflow = stored_workflow.latest_workflow
        module_injector.inject_all(workflow, exact_tools=False, ignore_tool_missing_exception=True)
        for step in workflow.steps:
            try:
                module_injector.compute_runtime_state(step)
            except exceptions.ToolMissingException:
                pass

    def _import_shared_workflow(self, trans, stored: StoredWorkflow):
        """Imports a shared workflow"""
        # Copy workflow.
        imported_stored = StoredWorkflow()
        imported_stored.name = f"imported: {stored.name}"
        workflow = stored.latest_workflow.copy(user=trans.user)
        workflow.stored_workflow = imported_stored
        imported_stored.latest_workflow = workflow
        imported_stored.user = trans.user
        imported_stored.copy_tags_from(stored.user, stored)
        # Save new workflow.
        session = trans.sa_session
        session.add(imported_stored)
        session.commit()

        # Copy annotations.
        self.copy_item_annotation(session, stored.user, stored, imported_stored.user, imported_stored)
        for order_index, step in enumerate(stored.latest_workflow.steps):
            self.copy_item_annotation(
                session, stored.user, step, imported_stored.user, imported_stored.latest_workflow.steps[order_index]
            )
        session.commit()
        return imported_stored

    def _workflow_to_dict(self, trans, stored):
        """
        Converts a workflow to a dict of attributes suitable for exporting.
        """
        workflow_contents_manager = workflows.WorkflowContentsManager(self.app, self.app.trs_proxy)
        return workflow_contents_manager.workflow_to_dict(
            trans,
            stored,
        )


class UsesFormDefinitionsMixin:
    """Mixin for controllers that use Galaxy form objects."""

    def get_all_forms(self, trans, all_versions=False, filter=None, form_type="All"):
        """
        Return all the latest forms from the form_definition_current table
        if all_versions is set to True. Otherwise return all the versions
        of all the forms from the form_definition table.
        """
        if all_versions:
            return get_form_definitions(trans.sa_session)
        if filter:
            fdc_list = get_filtered_form_definitions_current(trans.sa_session, filter)
        else:
            fdc_list = get_form_definitions_current(trans.sa_session)
        if form_type == "All":
            return [fdc.latest_form for fdc in fdc_list]
        else:
            return [fdc.latest_form for fdc in fdc_list if fdc.latest_form.type == form_type]

    def save_widget_field(self, trans, field_obj, widget_name, **kwd):
        # Save a form_builder field object
        params = util.Params(kwd)
        if isinstance(field_obj, trans.model.UserAddress):
            field_obj.desc = util.restore_text(params.get(f"{widget_name}_short_desc", ""))
            field_obj.name = util.restore_text(params.get(f"{widget_name}_name", ""))
            field_obj.institution = util.restore_text(params.get(f"{widget_name}_institution", ""))
            field_obj.address = util.restore_text(params.get(f"{widget_name}_address", ""))
            field_obj.city = util.restore_text(params.get(f"{widget_name}_city", ""))
            field_obj.state = util.restore_text(params.get(f"{widget_name}_state", ""))
            field_obj.postal_code = util.restore_text(params.get(f"{widget_name}_postal_code", ""))
            field_obj.country = util.restore_text(params.get(f"{widget_name}_country", ""))
            field_obj.phone = util.restore_text(params.get(f"{widget_name}_phone", ""))
            trans.sa_session.add(field_obj)
            trans.sa_session.commit()

    def get_form_values(self, trans, user, form_definition, **kwd):
        """
        Returns the name:value dictionary containing all the form values
        """
        params = util.Params(kwd)
        values = {}
        for field in form_definition.fields:
            field_type = field["type"]
            field_name = field["name"]
            input_value = params.get(field_name, "")
            if field_type == AddressField.__name__:
                input_text_value = util.restore_text(input_value)
                if input_text_value == "new":
                    # Save this new address in the list of this user's addresses
                    user_address = trans.model.UserAddress(user=user)
                    self.save_widget_field(trans, user_address, field_name, **kwd)
                    trans.sa_session.refresh(user)
                    field_value = int(user_address.id)
                elif input_text_value in ["", "none", "None", None]:
                    field_value = ""
                else:
                    field_value = int(input_text_value)
            elif field_type == CheckboxField.__name__:
                field_value = CheckboxField.is_checked(input_value)
            elif field_type == PasswordField.__name__:
                field_value = kwd.get(field_name, "")
            else:
                field_value = util.restore_text(input_value)
            values[field_name] = field_value
        return values


class SharableMixin:
    """Mixin for a controller that manages an item that can be shared."""

    manager: Any = None
    serializer: Any = None
    slug_builder = SlugBuilder()

    # -- Implemented methods. --

    def _is_valid_slug(self, slug):
        """Returns true if slug is valid."""
        return SlugBuilder.is_valid_slug(slug)

    @web.expose
    @web.require_login("modify Galaxy items")
    def set_slug_async(self, trans, id, new_slug):
        item = self.get_item(trans, id)
        if item:
            # Only update slug if slug is not already in use.
            if not slug_exists(trans.sa_session, item.__class__, item.user, new_slug):
                item.slug = new_slug
                trans.sa_session.commit()

        return item.slug

    def _make_item_accessible(self, sa_session, item):
        """Makes item accessible--viewable and importable--and sets item's slug.
        Does not flush/commit changes, however. Item must have name, user,
        importable, and slug attributes."""
        item.importable = True
        self.slug_builder.create_item_slug(sa_session, item)

    # -- Abstract methods. --

    @web.expose
    @web.require_login("share Galaxy items")
    def share(self, trans, id=None, email="", **kwd):
        """Handle sharing an item with a particular user."""
        raise NotImplementedError()

    @web.expose
    def display_by_username_and_slug(self, trans, username, slug, **kwargs):
        """Display item by username and slug."""
        # Ensure slug is in the correct format.
        slug = slug.encode("latin1").decode("utf-8")
        self._display_by_username_and_slug(trans, username, slug, **kwargs)

    def _display_by_username_and_slug(self, trans, username, slug, **kwargs):
        raise NotImplementedError()

    def get_item(self, trans, id):
        """Return item based on id."""
        raise NotImplementedError()


class UsesTagsMixin(SharableItemSecurityMixin):
    def _get_user_tags(self, trans, item_class_name, id):
        user = trans.user
        tagged_item = self._get_tagged_item(trans, item_class_name, id)
        return [tag for tag in tagged_item.tags if tag.user == user]

    def _get_tagged_item(self, trans, item_class_name, id, check_ownership=True):
        tagged_item = self.get_object(
            trans, id, item_class_name, check_ownership=check_ownership, check_accessible=True
        )
        return tagged_item

    def _remove_items_tag(self, trans, item_class_name, id, tag_name):
        """Remove a tag from an item."""
        user = trans.user
        tagged_item = self._get_tagged_item(trans, item_class_name, id)
        deleted = tagged_item and trans.tag_handler.remove_item_tag(user, tagged_item, tag_name)
        trans.sa_session.commit()
        return deleted

    def _apply_item_tag(self, trans, item_class_name, id, tag_name, tag_value=None):
        user = trans.user
        tagged_item = self._get_tagged_item(trans, item_class_name, id)
        tag_assoc = trans.tag_handler.apply_item_tag(user, tagged_item, tag_name, tag_value)
        trans.sa_session.commit()
        return tag_assoc

    def _get_item_tag_assoc(self, trans, item_class_name, id, tag_name):
        user = trans.user
        tagged_item = self._get_tagged_item(trans, item_class_name, id)
        log.debug(f"In get_item_tag_assoc with tagged_item {tagged_item}")
        return trans.tag_handler._get_item_tag_assoc(user, tagged_item, tag_name)

    def set_tags_from_list(self, trans, item, new_tags_list, user=None):
        return trans.tag_handler.set_tags_from_list(user, item, new_tags_list)


class UsesExtendedMetadataMixin(SharableItemSecurityMixin):
    """Mixin for getting and setting item extended metadata."""

    def get_item_extended_metadata_obj(self, trans, item):
        """
        Given an item object (such as a LibraryDatasetDatasetAssociation), find the object
        of the associated extended metadata
        """
        if item.extended_metadata:
            return item.extended_metadata
        return None

    def set_item_extended_metadata_obj(self, trans, item, extmeta_obj, check_writable=False):
        if item.__class__ == LibraryDatasetDatasetAssociation:
            if not check_writable or trans.app.security_agent.can_modify_library_item(
                trans.get_current_user_roles(), item, trans.user
            ):
                item.extended_metadata = extmeta_obj
                trans.sa_session.commit()
        if item.__class__ == HistoryDatasetAssociation:
            history = None
            if check_writable:
                history = self.security_check(trans, item, check_ownership=True, check_accessible=True)
            else:
                history = self.security_check(trans, item, check_ownership=False, check_accessible=True)
            if history:
                item.extended_metadata = extmeta_obj
                trans.sa_session.commit()

    def unset_item_extended_metadata_obj(self, trans, item, check_writable=False):
        if item.__class__ == LibraryDatasetDatasetAssociation:
            if not check_writable or trans.app.security_agent.can_modify_library_item(
                trans.get_current_user_roles(), item, trans.user
            ):
                item.extended_metadata = None
                trans.sa_session.commit()
        if item.__class__ == HistoryDatasetAssociation:
            history = None
            if check_writable:
                history = self.security_check(trans, item, check_ownership=True, check_accessible=True)
            else:
                history = self.security_check(trans, item, check_ownership=False, check_accessible=True)
            if history:
                item.extended_metadata = None
                trans.sa_session.commit()

    def create_extended_metadata(self, trans, extmeta):
        """
        Create/index an extended metadata object. The returned object is
        not associated with any items
        """
        ex_meta = ExtendedMetadata(extmeta)
        trans.sa_session.add(ex_meta)
        trans.sa_session.commit()
        for path, value in self._scan_json_block(extmeta):
            meta_i = ExtendedMetadataIndex(ex_meta, path, value)
            trans.sa_session.add(meta_i)
        trans.sa_session.commit()
        return ex_meta

    def delete_extended_metadata(self, trans, item):
        if item.__class__ == ExtendedMetadata:
            trans.sa_session.delete(item)
            trans.sa_session.commit()

    def _scan_json_block(self, meta, prefix=""):
        """
        Scan a json style data structure, and emit all fields and their values.
        Example paths

        Data
        { "data" : [ 1, 2, 3 ] }

        Path:
        /data == [1,2,3]

        /data/[0] == 1

        """
        if isinstance(meta, dict):
            for a in meta:
                yield from self._scan_json_block(meta[a], f"{prefix}/{a}")
        elif isinstance(meta, list):
            for i, a in enumerate(meta):
                yield from self._scan_json_block(a, prefix + f"[{i}]")
        else:
            # BUG: Everything is cast to string, which can lead to false positives
            # for cross type comparisions, ie "True" == True
            yield prefix, (f"{meta}").encode()


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


__all__ = (
    "HTTPBadRequest",
    "SharableMixin",
    "sort_by_attr",
    "url_for",
    "UsesExtendedMetadataMixin",
    "UsesFormDefinitionsMixin",
    "UsesTagsMixin",
    "web",
)
