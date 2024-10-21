import logging
import os
from urllib.parse import (
    quote_plus,
    unquote_plus,
)

import paste.httpexceptions
from markupsafe import escape

from galaxy import (
    datatypes,
    util,
    web,
)
from galaxy.datatypes.data import DatatypeConverterNotFoundException
from galaxy.datatypes.display_applications.util import (
    decode_dataset_user,
    encode_dataset_user,
)
from galaxy.datatypes.sniff import guess_ext
from galaxy.exceptions import (
    InsufficientPermissionsException,
    MessageException,
    RequestParameterInvalidException,
)
from galaxy.managers.hdas import (
    HDADeserializer,
    HDAManager,
)
from galaxy.managers.histories import HistoryManager
from galaxy.model.base import transaction
from galaxy.model.item_attrs import (
    UsesAnnotations,
    UsesItemRatings,
)
from galaxy.structured_app import StructuredApp
from galaxy.util import (
    inflector,
    sanitize_text,
)
from galaxy.util.sanitize_html import sanitize_html
from galaxy.util.zipstream import ZipstreamWrapper
from galaxy.web import form_builder
from galaxy.webapps.base.controller import (
    BaseUIController,
    url_for,
    UsesExtendedMetadataMixin,
)
from galaxy.webapps.galaxy.services.datasets import DatasetsService
from ..api import depends

log = logging.getLogger(__name__)

comptypes = []

try:
    import zlib  # noqa: F401

    comptypes.append("zip")
except ImportError:
    pass


class DatasetInterface(BaseUIController, UsesAnnotations, UsesItemRatings, UsesExtendedMetadataMixin):
    history_manager: HistoryManager = depends(HistoryManager)
    hda_manager: HDAManager = depends(HDAManager)
    hda_deserializer: HDADeserializer = depends(HDADeserializer)
    service: DatasetsService = depends(DatasetsService)

    def __init__(self, app: StructuredApp):
        super().__init__(app)

    def _can_access_dataset(self, trans, dataset_association, allow_admin=True, additional_roles=None):
        roles = trans.get_current_user_roles()
        if additional_roles:
            roles = roles + additional_roles
        return (allow_admin and trans.user_is_admin) or trans.app.security_agent.can_access_dataset(
            roles, dataset_association.dataset
        )

    @web.expose
    def default(self, trans, dataset_id=None, **kwd):
        return "This link may not be followed from within Galaxy."

    @web.expose_api_raw_anonymous_and_sessionless
    def get_metadata_file(self, trans, hda_id, metadata_name, **kwd):
        """Allows the downloading of metadata files associated with datasets (eg. bai index for bam files)"""
        # Backward compatibility with legacy links, should use `/api/datasets/{hda_id}/get_metadata_file` instead
        fh, headers = self.service.get_metadata_file(
            trans, history_content_id=hda_id, metadata_file=metadata_name, open_file=True
        )
        trans.response.headers.update(headers)
        return fh

    def _check_dataset(self, trans, hda_id):
        # DEPRECATION: We still support unencoded ids for backward compatibility
        try:
            data = trans.sa_session.query(trans.app.model.HistoryDatasetAssociation).get(self.decode_id(hda_id))
            if data is None:
                raise ValueError(f"Invalid reference dataset id: {hda_id}.")
        except Exception:
            try:
                data = trans.sa_session.query(trans.app.model.HistoryDatasetAssociation).get(int(hda_id))
            except Exception:
                data = None
        if not data:
            raise web.httpexceptions.HTTPNotFound(f"Invalid reference dataset id: {str(hda_id)}.")
        if not self._can_access_dataset(trans, data):
            raise InsufficientPermissionsException("You are not allowed to access this dataset")
        self.app.hda_manager.ensure_dataset_on_disk(trans, data)
        return data

    @web.expose
    def display(
        self, trans, dataset_id=None, preview=False, filename=None, to_ext=None, offset=None, ck_size=None, **kwd
    ):
        data = self._check_dataset(trans, dataset_id)
        if "hdca" in kwd:
            raise RequestParameterInvalidException("Invalid request parameter 'hdca' encountered.")
        if hdca_id := kwd.get("hdca_id", None):
            hdca = self.app.dataset_collection_manager.get_dataset_collection_instance(trans, "history", hdca_id)
            del kwd["hdca_id"]
            kwd["hdca"] = hdca
        # Ensure offset is an integer before passing through to datatypes.
        if offset:
            offset = int(offset)
        # Ensure ck_size is an integer before passing through to datatypes.
        if ck_size:
            ck_size = int(ck_size)
        kwd.pop("dataset", None)
        # `dataset` in kwd would interfere with positional dataset argument of `display_data` method.
        display_data, headers = data.datatype.display_data(
            trans, data, preview, filename, to_ext, offset=offset, ck_size=ck_size, **kwd
        )
        if isinstance(display_data, ZipstreamWrapper):
            trans.response.headers.update(headers)
            return display_data.response()
        trans.response.headers.update(headers)
        return display_data

    @web.expose_api_anonymous
    def get_edit(self, trans, dataset_id=None, **kwd):
        """Produces the input definitions available to modify dataset attributes"""
        status = None
        data, message = self._get_dataset_for_edit(trans, dataset_id)
        if message:
            return message

        if self._can_access_dataset(trans, data):
            if data.state == trans.model.Dataset.states.UPLOAD:
                raise MessageException(
                    "Please wait until this dataset finishes uploading before attempting to edit its metadata."
                )
            # let's not overwrite the imported datatypes module with the variable datatypes?
            # the built-in 'id' is overwritten in lots of places as well
            ldatatypes = [
                (dtype_name, dtype_name)
                for dtype_name, dtype_value in trans.app.datatypes_registry.datatypes_by_extension.items()
                if dtype_value.is_datatype_change_allowed()
            ]
            ldatatypes.sort()
            all_roles = [
                (r.name, trans.security.encode_id(r.id))
                for r in trans.app.security_agent.get_legitimate_roles(trans, data.dataset, "root")
            ]
            data_metadata = list(data.metadata.spec.items())
            converters_collection = [(key, value.name) for key, value in data.get_converter_types().items()]
            can_manage_dataset = trans.app.security_agent.can_manage_dataset(
                trans.get_current_user_roles(), data.dataset
            )
            # attribute editing
            attribute_inputs = [
                {"name": "name", "type": "text", "label": "Name", "value": data.get_display_name()},
                {"name": "info", "type": "text", "area": True, "label": "Info", "value": data.info},
                {
                    "name": "annotation",
                    "type": "text",
                    "area": True,
                    "label": "Annotation",
                    "optional": True,
                    "value": self.get_item_annotation_str(trans.sa_session, trans.user, data),
                    "help": "Add an annotation or notes to a dataset; annotations are available when a history is viewed.",
                },
            ]
            for name, spec in data_metadata:
                if spec.visible:
                    attributes = data.metadata.get_metadata_parameter(name, trans=trans)
                    if type(attributes) is form_builder.SelectField:
                        attribute_inputs.append(
                            {
                                "type": "select",
                                "multiple": attributes.multiple,
                                "optional": spec.get("optional"),
                                "name": name,
                                "label": spec.desc,
                                "options": attributes.options,
                                "value": attributes.value,
                            }
                        )
                    elif type(attributes) is form_builder.TextField:
                        attribute_inputs.append(
                            {
                                "type": "text",
                                "name": name,
                                "label": spec.desc,
                                "value": attributes.value,
                                "readonly": spec.get("readonly"),
                            }
                        )
            if data.missing_meta():
                message = 'Required metadata values are missing. Some of these values may not be editable by the user. Selecting "Auto-detect" will attempt to fix these values.'
                status = "warning"
            metadata_disable = data.state not in [
                trans.model.Dataset.states.OK,
                trans.model.Dataset.states.FAILED_METADATA,
            ]
            # datatype conversion
            conversion_options = [
                (f"{convert_id} (using '{convert_name}')", convert_id)
                for convert_id, convert_name in converters_collection
            ]
            conversion_disable = len(conversion_options) == 0
            conversion_inputs = [
                {
                    "type": "select",
                    "name": "target_type",
                    "label": "Target datatype",
                    "help": "This will create a new dataset with the contents of this dataset converted to a new format.",
                    "options": conversion_options,
                }
            ]
            # datatype changing
            datatype_options = [(ext_name, ext_id) for ext_id, ext_name in ldatatypes]
            datatype_disable = len(datatype_options) == 0
            datatype_input_default_value = None
            current_datatype = trans.app.datatypes_registry.datatypes_by_extension.get(data.ext)
            if current_datatype and current_datatype.is_datatype_change_allowed():
                datatype_input_default_value = data.ext
            datatype_inputs = [
                {
                    "type": "select",
                    "name": "datatype",
                    "label": "New Type",
                    "options": datatype_options,
                    "value": datatype_input_default_value,
                    "help": "This will change the datatype of the existing dataset but not modify its contents. Use this if Galaxy has incorrectly guessed the type of your dataset.",
                }
            ]
            # permissions
            permission_disable = True
            permission_inputs = []
            if trans.user:
                if not data.dataset.shareable:
                    permission_message = "The dataset is stored on private storage to you and cannot be shared."
                    permission_inputs.append(
                        {"name": "not_shareable", "type": "hidden", "label": permission_message, "readonly": True}
                    )
                elif data.dataset.actions:
                    in_roles = {}
                    for action, roles in trans.app.security_agent.get_permissions(data.dataset).items():
                        in_roles[action.action] = [trans.security.encode_id(role.id) for role in roles]
                    for index, action in trans.app.model.Dataset.permitted_actions.items():
                        if action == trans.app.security_agent.permitted_actions.DATASET_ACCESS:
                            help_text = f"{action.description}<br/>NOTE: Users must have every role associated with this dataset in order to access it."
                        else:
                            help_text = action.description
                        permission_inputs.append(
                            {
                                "type": "select",
                                "multiple": True,
                                "optional": True,
                                "name": index,
                                "label": action.action,
                                "help": help_text,
                                "options": all_roles,
                                "value": in_roles.get(action.action),
                                "readonly": not can_manage_dataset,
                            }
                        )
                    permission_disable = not can_manage_dataset
                else:
                    permission_inputs.append(
                        {
                            "name": "access_public",
                            "type": "hidden",
                            "label": "This dataset is accessible by everyone (it is public).",
                            "readonly": True,
                        }
                    )
            else:
                permission_inputs.append(
                    {
                        "name": "no_access",
                        "type": "hidden",
                        "label": "Permissions not available (not logged in).",
                        "readonly": True,
                    }
                )
            return {
                "display_name": data.get_display_name(),
                "message": message,
                "status": status,
                "dataset_id": dataset_id,
                "metadata_disable": metadata_disable,
                "attribute_inputs": attribute_inputs,
                "conversion_inputs": conversion_inputs,
                "conversion_disable": conversion_disable,
                "datatype_inputs": datatype_inputs,
                "datatype_disable": datatype_disable,
                "permission_inputs": permission_inputs,
                "permission_disable": permission_disable,
            }
        else:
            raise MessageException(
                "You do not have permission to edit this dataset's ( id: {dataset_id} ) information."
            )

    @web.expose_api_anonymous
    def set_edit(self, trans, payload=None, **kwd):
        """Allows user to modify parameters of an HDA."""
        status = "success"
        operation = payload.get("operation")
        dataset_id = payload.get("dataset_id")
        data, message = self._get_dataset_for_edit(trans, dataset_id)
        if message:
            return message

        if operation == "attributes":
            # The user clicked the Save button on the 'Edit Attributes' form
            data.name = payload.get("name")
            data.info = payload.get("info")
            if data.ok_to_edit_metadata():
                # The following for loop will save all metadata_spec items
                for name, spec in data.datatype.metadata_spec.items():
                    if not spec.get("readonly"):
                        setattr(data.metadata, name, spec.unwrap(payload.get(name) or None))
                data.datatype.after_setting_metadata(data)
                # Sanitize annotation before adding it.
                if payload.get("annotation"):
                    annotation = sanitize_html(payload.get("annotation"))
                    self.add_item_annotation(trans.sa_session, trans.get_user(), data, annotation)
                # if setting metadata previously failed and all required elements have now been set, clear the failed state.
                if data.state == trans.model.Dataset.states.FAILED_METADATA and not data.missing_meta():
                    data.set_metadata_success_state()
                message = f"Attributes updated. {message}" if message else "Attributes updated."
            else:
                message = "Attributes updated, but metadata could not be changed because this dataset is currently being used as input or output. You must cancel or wait for these jobs to complete before changing metadata."
                status = "warning"
            with transaction(trans.sa_session):
                trans.sa_session.commit()
        elif operation == "datatype":
            # The user clicked the Save button on the 'Change data type' form
            datatype = payload.get("datatype")
            self.hda_deserializer.deserialize(data, {"datatype": datatype}, trans=trans)
            message = f"Changed the type to {datatype}."
        elif operation == "datatype_detect":
            # The user clicked the 'Detect datatype' button on the 'Change data type' form
            if data.datatype.is_datatype_change_allowed():
                # prevent modifying datatype when dataset is queued or running as input/output
                if not data.ok_to_edit_metadata():
                    raise MessageException(
                        "This dataset is currently being used as input or output.  You cannot change datatype until the jobs have completed or you have canceled them."
                    )
                else:
                    path = data.dataset.get_file_name()
                    datatype = guess_ext(path, trans.app.datatypes_registry.sniff_order)
                    trans.app.datatypes_registry.change_datatype(data, datatype)
                    with transaction(trans.sa_session):
                        trans.sa_session.commit()
                    job, *_ = trans.app.datatypes_registry.set_external_metadata_tool.tool_action.execute(
                        trans.app.datatypes_registry.set_external_metadata_tool,
                        trans,
                        incoming={"input1": data},
                        overwrite=False,
                    )  # overwrite is False as per existing behavior
                    trans.app.job_manager.enqueue(job, tool=trans.app.datatypes_registry.set_external_metadata_tool)
                    message = f"Detection was finished and changed the datatype to {datatype}."
            else:
                raise MessageException(f'Changing datatype "{data.extension}" is not allowed.')
        elif operation == "autodetect":
            # The user clicked the Auto-detect button on the 'Edit Attributes' form
            self.hda_manager.set_metadata(trans, data, overwrite=True)
            message = "Auto-detect operation successfully submitted."
        elif operation == "conversion":
            target_type = payload.get("target_type")
            if target_type:
                try:
                    message = data.datatype.convert_dataset(trans, data, target_type)
                except DatatypeConverterNotFoundException as e:
                    raise MessageException(str(e))
        elif operation == "permission":
            # Adapt form request to API - style.
            payload_permissions = {}
            for key, value in {"DATASET_MANAGE_PERMISSIONS": "manage_ids", "DATASET_ACCESS": "access_ids"}.items():
                role_ids = util.listify(payload.get(key))
                decoded_role_ids = list(map(self.decode_id, role_ids))
                payload_permissions[f"{value}[]"] = decoded_role_ids

            self.hda_manager.update_permissions(
                trans,
                data,
                action="set_permissions",
                **payload_permissions,
            )
            message = "Your changes completed successfully."
        else:
            raise MessageException(f"Invalid operation identifier ({operation}).")
        return {"status": status, "message": sanitize_text(message)}

    def _get_dataset_for_edit(self, trans, dataset_id):
        if dataset_id is not None:
            id = self.decode_id(dataset_id)
            data = trans.sa_session.query(self.app.model.HistoryDatasetAssociation).get(id)
        else:
            trans.log_event("dataset_id is None, cannot load a dataset to edit.")
            return None, self.message_exception(trans, "You must provide a dataset id to edit attributes.")
        if data is None:
            trans.log_event(f"Problem retrieving dataset id ({dataset_id}).")
            return None, self.message_exception(trans, "The dataset id is invalid.")
        if dataset_id is not None and data.user and data.user != trans.user:
            trans.log_event(f"User attempted to edit a dataset they do not own (encoded: {dataset_id}, decoded: {id}).")
            return None, self.message_exception(trans, "The dataset id is invalid.")
        if data.history.user and not data.dataset.has_manage_permissions_roles(trans.app.security_agent):
            # Permission setting related to DATASET_MANAGE_PERMISSIONS was broken for a period of time,
            # so it is possible that some Datasets have no roles associated with the DATASET_MANAGE_PERMISSIONS
            # permission.  In this case, we'll reset this permission to the hda user's private role.
            manage_permissions_action = trans.app.security_agent.get_action(
                trans.app.security_agent.permitted_actions.DATASET_MANAGE_PERMISSIONS.action
            )
            permissions = {manage_permissions_action: [trans.app.security_agent.get_private_user_role(data.user)]}
            trans.app.security_agent.set_dataset_permission(data.dataset, permissions)
        return data, None

    @web.expose
    def display_by_username_and_slug(self, trans, username, slug, filename=None, preview=True, **kwargs):
        """Display dataset by username and slug; because datasets do not yet have slugs, the slug is the dataset's id."""
        dataset = self._check_dataset(trans, slug)
        # Filename used for composite types.
        if filename:
            return self.display(trans, dataset_id=slug, filename=filename)

        truncated, dataset_data = self.hda_manager.text_data(dataset, preview)
        dataset.annotation = self.get_item_annotation_str(trans.sa_session, dataset.user, dataset)

        # If dataset is chunkable, get first chunk.
        first_chunk = None
        if dataset.datatype.CHUNKABLE:
            first_chunk = dataset.datatype.get_chunk(trans, dataset, 0)

        # If data is binary or an image, stream without template; otherwise, use display template.
        # TODO: figure out a way to display images in display template.
        if (
            isinstance(dataset.datatype, datatypes.binary.Binary)
            or isinstance(dataset.datatype, datatypes.images.Image)
            or isinstance(dataset.datatype, datatypes.text.Html)
        ):
            trans.response.set_content_type(dataset.get_mime())
            return open(dataset.get_file_name(), "rb")
        else:
            return trans.fill_template_mako(
                "/dataset/display.mako",
                item=dataset,
                item_data=dataset_data,
                truncated=truncated,
                first_chunk=first_chunk,
            )

    @web.expose
    def display_at(self, trans, dataset_id, filename=None, **kwd):
        """Sets up a dataset permissions so it is viewable at an external site"""
        if not trans.app.config.enable_old_display_applications:
            return trans.show_error_message(
                "This method of accessing external display applications has been disabled by a Galaxy administrator."
            )
        site = filename
        data = trans.sa_session.query(trans.app.model.HistoryDatasetAssociation).get(dataset_id)
        if not data:
            raise paste.httpexceptions.HTTPRequestRangeNotSatisfiable(
                f"Invalid reference dataset id: {str(dataset_id)}."
            )
        if "display_url" not in kwd or "redirect_url" not in kwd:
            return trans.show_error_message(
                'Invalid parameters specified for "display at" link, please contact a Galaxy administrator'
            )
        try:
            redirect_url = kwd["redirect_url"] % quote_plus(kwd["display_url"])
        except Exception:
            redirect_url = kwd["redirect_url"]  # not all will need custom text
        if trans.app.security_agent.dataset_is_public(data.dataset):
            return trans.response.send_redirect(redirect_url)  # anon access already permitted by rbac
        if self._can_access_dataset(trans, data):
            trans.app.host_security_agent.set_dataset_permissions(data, trans.user, site)
            return trans.response.send_redirect(redirect_url)
        else:
            return trans.show_error_message(
                "You are not allowed to view this dataset at external sites.  Please contact your Galaxy administrator to acquire management permissions for this dataset."
            )

    @web.expose
    @web.do_not_cache
    def display_application(
        self,
        trans,
        dataset_id=None,
        user_id=None,
        app_name=None,
        link_name=None,
        app_action=None,
        action_param=None,
        action_param_extra=None,
        **kwds,
    ):
        """Access to external display applications"""
        if None in [app_name, link_name]:
            return trans.show_error_message("A display application name and link name must be provided.")
        app_name = unquote_plus(app_name)
        link_name = unquote_plus(link_name)
        # Build list of parameters to pass in to display application logic (app_kwds)
        app_kwds = {}
        for name, value in dict(kwds).items():  # clone kwds because we remove stuff as we go.
            if name.startswith("app_"):
                app_kwds[name[len("app_") :]] = value
                del kwds[name]
        if kwds:
            log.debug(f"Unexpected Keywords passed to display_application: {kwds}")  # route memory?
        # decode ids
        data, user = decode_dataset_user(trans, dataset_id, user_id)
        if not data:
            raise paste.httpexceptions.HTTPRequestRangeNotSatisfiable(
                f"Invalid reference dataset id: {str(dataset_id)}."
            )
        if user is None:
            user = trans.user
        if user:
            user_roles = user.all_roles()
        else:
            user_roles = []
        # Decode application name and link name
        if self._can_access_dataset(trans, data, additional_roles=user_roles):
            msg = []
            preparable_steps = []
            refresh = False
            display_app = trans.app.datatypes_registry.display_applications.get(app_name)
            if not display_app:
                log.debug("Unknown display application has been requested: %s", app_name)
                return paste.httpexceptions.HTTPNotFound(
                    f"The requested display application ({app_name}) is not available."
                )
            dataset_hash, user_hash = encode_dataset_user(trans, data, user)
            try:
                display_link = display_app.get_link(link_name, data, dataset_hash, user_hash, trans, app_kwds)
            except Exception as e:
                log.debug("Error generating display_link: %s", e)
                # User can sometimes recover from, e.g. conversion errors by fixing input metadata, so use conflict
                return paste.httpexceptions.HTTPConflict(f"Error generating display_link: {e}")
            if not display_link:
                log.debug("Unknown display link has been requested: %s", link_name)
                return paste.httpexceptions.HTTPNotFound(f"Unknown display link has been requested: {link_name}")
            if data.state == data.states.ERROR:
                msg.append(
                    (
                        "This dataset is in an error state, you cannot view it at an external display application.",
                        "error",
                    )
                )
            elif data.deleted:
                msg.append(
                    ("This dataset has been deleted, you cannot view it at an external display application.", "error")
                )
            elif data.state != data.states.OK:
                msg.append(
                    (
                        "You must wait for this dataset to be created before you can view it at an external display application.",
                        "info",
                    )
                )
                refresh = True
            else:
                # We have permissions, dataset is not deleted and is in OK state, allow access
                if display_link.display_ready():
                    if app_action in ["data", "param"]:
                        assert action_param, "An action param must be provided for a data or param action"
                        # data is used for things with filenames that could be passed off to a proxy
                        # in case some display app wants all files to be in the same 'directory',
                        # data can be forced to param, but not the other way (no filename for other direction)
                        # get param name from url param name
                        try:
                            action_param = display_link.get_param_name_by_url(action_param)
                        except ValueError as e:
                            log.debug(e)
                            return paste.httpexceptions.HTTPNotFound(util.unicodify(e))
                        value = display_link.get_param_value(action_param)
                        assert value, f"An invalid parameter name was provided: {action_param}"
                        assert value.parameter.viewable, "This parameter is not viewable."
                        if value.parameter.type == "data":
                            try:
                                if action_param_extra:
                                    assert (
                                        value.parameter.allow_extra_files_access
                                    ), f"Extra file content requested ({action_param_extra}), but allow_extra_files_access is False."
                                    file_name = os.path.join(value.extra_files_path, action_param_extra)
                                else:
                                    file_name = value.get_file_name()
                                content_length = os.path.getsize(file_name)
                                rval = open(file_name, "rb")
                            except OSError as e:
                                log.debug("Unable to access requested file in display application: %s", e)
                                return paste.httpexceptions.HTTPNotFound("This file is no longer available.")
                        else:
                            rval = str(value)
                            content_length = len(rval)
                        # Set Access-Control-Allow-Origin as specified in GEDA
                        if value.parameter.allow_cors:
                            trans.set_cors_origin()
                            trans.set_cors_allow()
                        trans.response.set_content_type(value.mime_type(action_param_extra=action_param_extra))
                        trans.response.headers["Content-Length"] = str(content_length)
                        return rval
                    elif app_action is None:
                        # redirect user to url generated by display link
                        return trans.response.send_redirect(display_link.display_url())
                    else:
                        msg.append((f"Invalid action provided: {app_action}", "error"))
                else:
                    if app_action is None:
                        refresh = True
                        trans.response.status = 202
                        msg.append(
                            (
                                "Launching this display application requires additional datasets to be generated, you can view the status of these jobs below. ",
                                "info",
                            )
                        )
                        if not display_link.preparing_display():
                            display_link.prepare_display()
                        preparable_steps = display_link.get_prepare_steps()
                    else:
                        # Ideally we should respond with 202 in both cases.
                        # Since we don't exactly know if any consumer relies on this we'll just keep continuing to
                        # respond with a 500 status code.
                        trans.response.status = 500
                        return trans.show_error_message(
                            f"Attempted a view action ({app_action}) on a non-ready display application"
                        )
            return trans.fill_template_mako(
                "dataset/display_application/display.mako",
                msg=msg,
                display_app=display_app,
                display_link=display_link,
                refresh=refresh,
                preparable_steps=preparable_steps,
            )
        return trans.show_error_message(
            "You do not have permission to view this dataset at an external display application."
        )

    @web.expose
    def copy_datasets(
        self,
        trans,
        source_history=None,
        source_content_ids="",
        target_history_id=None,
        target_history_ids="",
        new_history_name="",
        do_copy=False,
        **kwd,
    ):
        user = trans.get_user()
        if source_history is not None:
            decoded_source_history_id = self.decode_id(source_history)
            history = self.history_manager.get_owned(
                decoded_source_history_id, trans.user, current_history=trans.history
            )
            current_history = trans.get_history()
        else:
            history = current_history = trans.get_history()
        refresh_frames = []
        if source_content_ids:
            if not isinstance(source_content_ids, list):
                source_content_ids = source_content_ids.split(",")
            encoded_dataset_collection_ids = [
                s[len("dataset_collection|") :] for s in source_content_ids if s.startswith("dataset_collection|")
            ]
            encoded_dataset_ids = [s[len("dataset|") :] for s in source_content_ids if s.startswith("dataset|")]
            decoded_dataset_collection_ids = set(map(self.decode_id, encoded_dataset_collection_ids))
            decoded_dataset_ids = set(map(self.decode_id, encoded_dataset_ids))
        else:
            decoded_dataset_collection_ids = []
            decoded_dataset_ids = []
        if new_history_name:
            target_history_ids = []
        else:
            if target_history_id:
                target_history_ids = [self.decode_id(target_history_id)]
            elif target_history_ids:
                if not isinstance(target_history_ids, list):
                    target_history_ids = target_history_ids.split(",")
                target_history_ids = list({self.decode_id(h) for h in target_history_ids if h})
            else:
                target_history_ids = []
        done_msg = error_msg = ""
        new_history = None
        if do_copy:
            invalid_contents = 0
            if not (decoded_dataset_ids or decoded_dataset_collection_ids) or not (
                target_history_ids or new_history_name
            ):
                error_msg = "You must provide both source datasets and target histories. "
            else:
                if new_history_name:
                    new_history = trans.app.model.History()
                    new_history.name = new_history_name
                    new_history.user = user
                    trans.sa_session.add(new_history)
                    with transaction(trans.sa_session):
                        trans.sa_session.commit()
                    target_history_ids.append(new_history.id)
                if user:
                    target_histories = [
                        hist
                        for hist in map(trans.sa_session.query(trans.app.model.History).get, target_history_ids)
                        if hist is not None and hist.user == user
                    ]
                else:
                    target_histories = [history]
                if len(target_histories) != len(target_history_ids):
                    error_msg = (
                        error_msg
                        + "You do not have permission to add datasets to %i requested histories.  "
                        % (len(target_history_ids) - len(target_histories))
                    )
                source_contents = list(
                    map(trans.sa_session.query(trans.app.model.HistoryDatasetAssociation).get, decoded_dataset_ids)
                )
                source_contents.extend(
                    map(
                        trans.sa_session.query(trans.app.model.HistoryDatasetCollectionAssociation).get,
                        decoded_dataset_collection_ids,
                    )
                )
                source_contents.sort(key=lambda content: content.hid)
                for content in source_contents:
                    if content is None:
                        error_msg = f"{error_msg}You tried to copy a dataset that does not exist. "
                        invalid_contents += 1
                    elif content.history != history:
                        error_msg = f"{error_msg}You tried to copy a dataset which is not in your current history. "
                        invalid_contents += 1
                    else:
                        for hist in target_histories:
                            if content.history_content_type == "dataset":
                                copy = content.copy(flush=False)
                                hist.stage_addition(copy)
                            else:
                                copy = content.copy(element_destination=hist)
                            if user:
                                copy.copy_tags_from(user, content)
                        for hist in target_histories:
                            hist.add_pending_items()
                with transaction(trans.sa_session):
                    trans.sa_session.commit()
                if current_history in target_histories:
                    refresh_frames = ["history"]
                hist_names_str = ", ".join(
                    '<a href="{}" target="_top">{}</a>'.format(
                        url_for(
                            controller="history", action="switch_to_history", hist_id=trans.security.encode_id(hist.id)
                        ),
                        escape(hist.name),
                    )
                    for hist in target_histories
                )
                num_source = len(source_content_ids) - invalid_contents
                num_target = len(target_histories)
                done_msg = "%i %s copied to %i %s: %s." % (
                    num_source,
                    inflector.cond_plural(num_source, "dataset"),
                    num_target,
                    inflector.cond_plural(num_target, "history"),
                    hist_names_str,
                )
                trans.sa_session.refresh(history)
        source_contents = history.active_contents
        target_histories = [history]
        if user:
            target_histories = user.active_histories
        return trans.fill_template(
            "/dataset/copy_view.mako",
            source_history=history,
            current_history=current_history,
            source_content_ids=source_content_ids,
            target_history_id=target_history_id,
            target_history_ids=target_history_ids,
            source_contents=source_contents,
            target_histories=target_histories,
            new_history_name=new_history_name,
            done_msg=done_msg,
            error_msg=error_msg,
            refresh_frames=refresh_frames,
        )
