"""
Galaxy Security

"""

from typing import (
    List,
    Optional,
)

from typing_extensions import Literal

from galaxy.util.bunch import Bunch

ActionModel = Literal["grant", "restrict"]


class Action:
    action: str
    description: str
    model: ActionModel

    def __init__(self, action: str, description: str, model: ActionModel):
        self.action = action
        self.description = description
        self.model = model


class RBACAgent:
    """Class that handles galaxy security"""

    permitted_actions = Bunch(
        DATASET_MANAGE_PERMISSIONS=Action(
            "manage permissions",
            "Users having associated role can manage the roles associated with permissions on this dataset.",
            "grant",
        ),
        DATASET_ACCESS=Action(
            "access",
            "Users having all associated roles can import this dataset into their history for analysis.",
            "restrict",
        ),
        LIBRARY_ACCESS=Action(
            "access library", "Restrict access to this library to only users having associated role", "restrict"
        ),
        LIBRARY_ADD=Action(
            "add library item", "Users having associated role can add library items to this library item", "grant"
        ),
        LIBRARY_MODIFY=Action(
            "modify library item", "Users having associated role can modify this library item", "grant"
        ),
        LIBRARY_MANAGE=Action(
            "manage library permissions",
            "Users having associated role can manage roles associated with permissions on this library item",
            "grant",
        ),
    )

    def get_action(self, name: str, default: Optional[Action] = None) -> Optional[Action]:
        """Get a permitted action by its dict key or action name"""
        for k, v in self.permitted_actions.items():
            if k == name or v.action == name:
                return v
        return default

    def get_actions(self) -> List[Action]:
        """Get all permitted actions as a list of Action objects"""
        return list(self.permitted_actions.__dict__.values())

    def get_item_actions(self, action, item):
        raise Exception(f"No valid method of retrieving action ({action}) for item {item}.")

    def guess_derived_permissions_for_datasets(self, datasets=None):
        datasets = datasets or []
        raise Exception("Unimplemented Method")

    def can_access_dataset(self, roles, dataset):
        raise Exception("Unimplemented Method")

    def can_manage_dataset(self, roles, dataset):
        raise Exception("Unimplemented Method")

    def can_access_library(self, roles, library):
        raise Exception("Unimplemented Method")

    def can_add_library_item(self, roles, item):
        raise Exception("Unimplemented Method")

    def can_modify_library_item(self, roles, item):
        raise Exception("Unimplemented Method")

    def can_change_object_store_id(self, user, dataset):
        raise Exception("Unimplemented Method")

    def can_manage_library_item(self, roles, item):
        raise Exception("Unimplemented Method")

    def create_private_user_role(self, user):
        raise Exception("Unimplemented Method")

    def get_private_user_role(self, user):
        raise Exception("Unimplemented Method")

    def user_set_default_permissions(self, user, permissions=None, history=False, dataset=False):
        permissions = permissions or {}
        raise Exception("Unimplemented Method")

    def history_set_default_permissions(self, history, permissions=None, dataset=False, bypass_manage_permission=False):
        raise Exception("Unimplemented Method")

    def set_all_dataset_permissions(self, dataset, permissions, new=False):
        raise Exception("Unimplemented Method")

    def set_dataset_permission(self, dataset, permission):
        raise Exception("Unimplemented Method")

    def set_all_library_permissions(self, trans, dataset, permissions):
        raise Exception("Unimplemented Method")

    def set_library_item_permission(self, library_item, permission):
        raise Exception("Unimplemented Method")

    def library_is_public(self, library):
        raise Exception("Unimplemented Method")

    def make_library_public(self, library):
        raise Exception("Unimplemented Method")

    def get_accessible_libraries(self, trans, user):
        raise Exception("Unimplemented Method")

    def get_permitted_libraries(self, trans, user, actions):
        raise Exception("Unimplemented Method")

    def folder_is_public(self, library):
        raise Exception("Unimplemented Method")

    def make_folder_public(self, folder, count=0):
        raise Exception("Unimplemented Method")

    def dataset_is_public(self, dataset):
        raise Exception("Unimplemented Method")

    def make_dataset_public(self, dataset):
        raise Exception("Unimplemented Method")

    def get_permissions(self, library_dataset):
        raise Exception("Unimplemented Method")

    def get_all_roles(self, trans, cntrller):
        raise Exception("Unimplemented Method")

    def get_legitimate_roles(self, trans, item, cntrller):
        raise Exception("Unimplemented Method")

    def derive_roles_from_access(self, trans, item_id, cntrller, library=False, **kwd):
        raise Exception("Unimplemented Method")

    def get_component_associations(self, **kwd):
        raise Exception("Unimplemented Method")

    def components_are_associated(self, **kwd):
        return bool(self.get_component_associations(**kwd))

    def convert_permitted_action_strings(self, permitted_action_strings):
        """
        When getting permitted actions from an untrusted source like a
        form, ensure that they match our actual permitted actions.
        """
        return [
            _
            for _ in [self.permitted_actions.get(action_string) for action_string in permitted_action_strings]
            if _ is not None
        ]


def get_permitted_actions(filter=None):
    """Utility method to return a subset of RBACAgent's permitted actions"""
    if filter is None:
        return RBACAgent.permitted_actions
    tmp_bunch = Bunch()
    [tmp_bunch.dict().__setitem__(k, v) for k, v in RBACAgent.permitted_actions.items() if k.startswith(filter)]
    return tmp_bunch
