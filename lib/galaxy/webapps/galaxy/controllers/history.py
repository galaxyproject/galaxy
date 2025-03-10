import logging

from dateutil.parser import isoparse
from sqlalchemy import select

from galaxy import (
    exceptions,
    model,
    web,
)
from galaxy.managers import histories
from galaxy.managers.sharable import SlugBuilder
from galaxy.model import (
    Dataset,
    Role,
)
from galaxy.model.item_attrs import (
    UsesAnnotations,
    UsesItemRatings,
)
from galaxy.structured_app import StructuredApp
from galaxy.util import (
    listify,
    sanitize_text,
    string_as_bool,
)
from galaxy.web import (
    expose_api_anonymous,
    url_for,
)
from galaxy.webapps.base.controller import (
    BaseUIController,
    SharableMixin,
)
from ..api import depends

log = logging.getLogger(__name__)


class HistoryController(BaseUIController, SharableMixin, UsesAnnotations, UsesItemRatings):
    history_manager: histories.HistoryManager = depends(histories.HistoryManager)
    history_serializer: histories.HistorySerializer = depends(histories.HistorySerializer)
    slug_builder: SlugBuilder = depends(SlugBuilder)

    def __init__(self, app: StructuredApp):
        super().__init__(app)

    @web.expose
    def index(self, trans):
        return ""

    @expose_api_anonymous
    def view(self, trans, id=None, show_deleted=False, show_hidden=False, use_panels=True):
        """
        View a history. If a history is importable, then it is viewable by any user.
        """
        show_deleted = string_as_bool(show_deleted)
        show_hidden = string_as_bool(show_hidden)
        use_panels = string_as_bool(use_panels)

        history_dictionary = {}
        user_is_owner = False
        if id:
            history_to_view = self.history_manager.get_accessible(
                self.decode_id(id), trans.user, current_history=trans.history
            )
            user_is_owner = history_to_view.user == trans.user
            history_is_current = history_to_view == trans.history
        else:
            history_to_view = trans.history
            if not history_to_view:
                raise exceptions.RequestParameterMissingException(
                    "No 'id' parameter provided for history, and user does not have a current history."
                )
            user_is_owner = True
            history_is_current = True

        # include all datasets: hidden, deleted, and purged
        history_dictionary = self.history_serializer.serialize_to_view(
            history_to_view, view="dev-detailed", user=trans.user, trans=trans
        )

        return {
            "history": history_dictionary,
            "user_is_owner": user_is_owner,
            "history_is_current": history_is_current,
            "show_deleted": show_deleted,
            "show_hidden": show_hidden,
            "use_panels": use_panels,
            "allow_user_dataset_purge": trans.app.config.allow_user_dataset_purge,
        }

    def _display_by_username_and_slug(self, trans, username, slug, **kwargs):
        """
        Display history based on a username and slug.
        """
        # Get history.
        session = trans.sa_session

        user = session.scalars(select(model.User).filter_by(username=username).limit(1)).first()
        history = session.scalars(
            select(model.History)
            .filter_by(user=user, slug=slug, deleted=False)
            # return public histories first if slug is not unique
            .order_by(model.History.importable.desc())
            .limit(1)
        ).first()

        if history is None:
            raise web.httpexceptions.HTTPNotFound()

        # Security check raises error if user cannot access history.
        self.history_manager.error_unless_accessible(history, trans.user, current_history=trans.history)

        # Encode history id.
        history_id = trans.security.encode_id(history.id)

        # Redirect to client.
        return trans.response.send_redirect(
            web.url_for(
                controller="published",
                action="history",
                id=history_id,
            )
        )

    @web.expose_api
    @web.require_login("changing default permissions")
    def permissions(self, trans, payload=None, **kwd):
        """
        Sets the permissions on a history.
        """
        history_id = kwd.get("id")
        if not history_id:
            raise exceptions.RequestParameterMissingException("No history id received")
        history = self.history_manager.get_owned(self.decode_id(history_id), trans.user, current_history=trans.history)
        if trans.request.method == "GET":
            inputs = []
            all_roles = trans.user.all_roles()
            current_actions = history.default_permissions
            for action_key, action in Dataset.permitted_actions.items():
                in_roles = set()
                for a in current_actions:
                    if a.action == action.action:
                        in_roles.add(a.role)
                inputs.append(
                    {
                        "type": "select",
                        "multiple": True,
                        "optional": True,
                        "individual": True,
                        "name": action_key,
                        "label": action.action,
                        "help": action.description,
                        "options": [(role.name, trans.security.encode_id(role.id)) for role in set(all_roles)],
                        "value": [trans.security.encode_id(role.id) for role in in_roles],
                    }
                )
            return {"title": f"Change default dataset permissions for history '{history.name}'", "inputs": inputs}
        else:
            self.history_manager.error_unless_mutable(history)
            permissions = {}
            for action_key, action in Dataset.permitted_actions.items():
                in_roles = payload.get(action_key) or []
                in_roles = [trans.sa_session.get(Role, trans.security.decode_id(x)) for x in in_roles]
                permissions[trans.app.security_agent.get_action(action.action)] = in_roles
            trans.app.security_agent.history_set_default_permissions(history, permissions)
            return {"message": f"Default history '{history.name}' dataset permissions have been changed."}

    @web.expose_api
    @web.require_login("make datasets private")
    def make_private(self, trans, history_id=None, all_histories=False, **kwd):
        """
        Sets the datasets within a history to private.  Also sets the default
        permissions for the history to private, for future datasets.
        """
        histories = []
        all_histories = string_as_bool(all_histories)
        if all_histories:
            histories = trans.user.histories
        elif history_id:
            history = self.history_manager.get_owned(
                self.decode_id(history_id), trans.user, current_history=trans.history
            )
            if history:
                histories.append(history)
        if not histories:
            raise exceptions.RequestParameterMissingException("No history or histories specified.")
        private_role = trans.app.security_agent.get_private_user_role(trans.user)
        user_roles = trans.user.all_roles()
        private_permissions = {
            trans.app.security_agent.permitted_actions.DATASET_MANAGE_PERMISSIONS: [private_role],
            trans.app.security_agent.permitted_actions.DATASET_ACCESS: [private_role],
        }
        for history in histories:
            # Set default role for history to private
            trans.app.security_agent.history_set_default_permissions(history, private_permissions)
            # Set private role for all datasets
            for hda in history.datasets:
                if (
                    not hda.dataset.library_associations
                    and not trans.app.security_agent.dataset_is_private_to_user(trans, hda.dataset)
                    and trans.app.security_agent.can_manage_dataset(user_roles, hda.dataset)
                ):
                    # If it's not private to me, and I can manage it, set fixed private permissions.
                    trans.app.security_agent.set_all_dataset_permissions(hda.dataset, private_permissions)
        return {
            "message": f"Success, requested permissions have been changed in {'all histories' if all_histories else history.name}."
        }

    # ......................................................................... actions/orig. async

    @web.expose
    def purge_deleted_datasets(self, trans):
        count = 0
        if trans.app.config.allow_user_dataset_purge and trans.history:
            for hda in trans.history.datasets:
                if not hda.deleted or hda.purged:
                    continue
                hda.purge_usage_from_quota(trans.user, hda.dataset.quota_source_info)
                hda.purged = True
                trans.sa_session.add(hda)
                trans.log_event(f"HDA id {hda.id} has been purged")
                trans.sa_session.commit()
                if hda.dataset.user_can_purge:
                    try:
                        hda.dataset.full_delete()
                        trans.log_event(
                            f"Dataset id {hda.dataset.id} has been purged upon the purge of HDA id {hda.id}"
                        )
                        trans.sa_session.add(hda.dataset)
                    except Exception:
                        log.exception(f"Unable to purge dataset ({hda.dataset.id}) on purge of hda ({hda.id}):")
                count += 1
            return trans.show_ok_message(f"{count} datasets have been deleted permanently", refresh_frames=["history"])
        return trans.show_error_message("Cannot purge deleted datasets from this session.")

    @web.expose_api_anonymous
    def resume_paused_jobs(self, trans, current=False, ids=None, **kwargs):
        """Resume paused jobs for the active history -- this does not require a logged in user."""
        if not ids and string_as_bool(current):
            history = trans.get_history()
            if history:
                history.resume_paused_jobs()
                return {"message": "Your jobs have been resumed.", "status": "success"}
        raise exceptions.RequestParameterInvalidException(
            "You can currently only resume all the datasets of the current history."
        )

    @web.expose_api
    @web.require_login("rename histories")
    def rename(self, trans, payload=None, **kwd):
        id = kwd.get("id")
        if not id:
            raise exceptions.RequestParameterMissingException("No history id received for renaming.")
        user = trans.get_user()
        id = listify(id)
        histories = []
        for history_id in id:
            history = self.history_manager.get_mutable(
                self.decode_id(history_id), trans.user, current_history=trans.history
            )
            if history and history.user_id == user.id:
                histories.append(history)
        if trans.request.method == "GET":
            return {
                "title": "Change history name(s)",
                "inputs": [
                    {"name": f"name_{i}", "label": f"Current: {h.name}", "value": h.name}
                    for i, h in enumerate(histories)
                ],
            }
        else:
            messages = []
            for i, h in enumerate(histories):
                cur_name = h.get_display_name()
                new_name = payload.get(f"name_{i}")
                # validate name is empty
                if not isinstance(new_name, str) or not new_name.strip():
                    messages.append(f"You must specify a valid name for History '{cur_name}'.")
                # skip if not the owner
                elif h.user_id != user.id:
                    messages.append(f"History '{cur_name}' does not appear to belong to you.")
                # skip if it wouldn't be a change
                elif new_name != cur_name:
                    h.name = new_name
                    trans.sa_session.add(h)
                    trans.sa_session.commit()
                    trans.log_event(f"History renamed: id: {str(h.id)}, renamed to: {new_name}")
                    messages.append(f"History '{cur_name}' renamed to '{new_name}'.")
            message = sanitize_text(" ".join(messages)) if messages else "History names remain unchanged."
            return {"message": message, "status": "success"}

    # ------------------------------------------------------------------------- current history
    @web.expose
    @web.require_login("switch to a history")
    def switch_to_history(self, trans, hist_id=None, **kwargs):
        """Change the current user's current history to one with `hist_id`."""
        # remains for backwards compat
        self.set_as_current(trans, id=hist_id)
        return trans.response.send_redirect(url_for("/"))

    def get_item(self, trans, id):
        return self.history_manager.get_owned(self.decode_id(id), trans.user, current_history=trans.history)
        # TODO: override of base ui controller?

    def history_data(self, trans, history):
        """Return the given history in a serialized, dictionary form."""
        return self.history_serializer.serialize_to_view(history, view="dev-detailed", user=trans.user, trans=trans)

    # TODO: combine these next two - poss. with a redirect flag
    # @web.require_login( "switch to a history" )
    @web.json
    @web.do_not_cache
    def set_as_current(self, trans, id, **kwargs):
        """Change the current user's current history to one with `id`."""
        try:
            history = self.history_manager.get_owned(self.decode_id(id), trans.user, current_history=trans.history)
            trans.set_history(history)
            return self.history_data(trans, history)
        except exceptions.MessageException as msg_exc:
            trans.response.status = msg_exc.status_code
            return {"err_msg": msg_exc.err_msg, "err_code": msg_exc.err_code.code}

    @web.json
    @web.do_not_cache
    def current_history_json(self, trans, since=None, **kwargs):
        """Return the current user's current history in a serialized, dictionary form."""
        history = trans.get_history(most_recent=True, create=True)
        if since and history.update_time <= isoparse(since):
            # Should ideally be a 204 response, but would require changing web.json
            # This endpoint should either give way to a proper API or a SSE loop
            return
        return self.history_data(trans, history)

    @web.json
    def create_new_current(self, trans, name=None, **kwargs):
        """Create a new, current history for the current user"""
        new_history = trans.new_history(name)
        return self.history_data(trans, new_history)

    # TODO: /history/current to do all of the above: if ajax, return json; if post, read id and set to current
