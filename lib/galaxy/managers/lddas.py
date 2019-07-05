import logging

from galaxy import model, util
from galaxy.managers import base as manager_base
from galaxy.managers.datasets import DatasetAssociationManager

log = logging.getLogger(__name__)


class LDDAManager(DatasetAssociationManager):
    """
    A fairly sparse manager for LDDAs.
    """
    model_class = model.LibraryDatasetDatasetAssociation

    def __init__(self, app):
        """
        Set up and initialize other managers needed by lddas.
        """
        pass

    def get(self, trans, id, check_accessible=True):
        return manager_base.get_object(trans, id,
                                       'LibraryDatasetDatasetAssociation',
                                       check_ownership=False,
                                       check_accessible=check_accessible)

    def _set_permissions(self, trans, library_dataset, role_ids_dict):
        dataset = library_dataset.library_dataset_dataset_association.dataset
        new_access_roles_ids = role_ids_dict["DATASET_ACCESS"]
        new_manage_roles_ids = role_ids_dict["DATASET_MANAGE_PERMISSIONS"]
        new_modify_roles_ids = role_ids_dict["LIBRARY_MODIFY"]

        # ACCESS DATASET ROLES
        valid_access_roles = []
        invalid_access_roles_ids = []
        valid_roles_for_dataset, total_roles = trans.app.security_agent.get_valid_roles(trans, dataset)
        if new_access_roles_ids is None:
            trans.app.security_agent.make_dataset_public(dataset)
        else:
            for role_id in new_access_roles_ids:
                role = self.role_manager.get(trans, self.app, role_id)
                if role in valid_roles_for_dataset:
                    valid_access_roles.append(role)
                else:
                    invalid_access_roles_ids.append(role_id)
            if len(invalid_access_roles_ids) > 0:
                log.warning("The following roles could not be added to the dataset access permission: " + str(invalid_access_roles_ids))

            access_permission = dict(access=valid_access_roles)
            trans.app.security_agent.set_dataset_permission(dataset, access_permission)

        # MANAGE DATASET ROLES
        valid_manage_roles = []
        invalid_manage_roles_ids = []
        new_manage_roles_ids = util.listify(new_manage_roles_ids)
        for role_id in new_manage_roles_ids:
            role = self.role_manager.get(trans, self.app, role_id)
            if role in valid_roles_for_dataset:
                valid_manage_roles.append(role)
            else:
                invalid_manage_roles_ids.append(role_id)
        if len(invalid_manage_roles_ids) > 0:
            log.warning("The following roles could not be added to the dataset manage permission: " + str(invalid_manage_roles_ids))
        manage_permission = {trans.app.security_agent.permitted_actions.DATASET_MANAGE_PERMISSIONS: valid_manage_roles}
        trans.app.security_agent.set_dataset_permission(dataset, manage_permission)

        # MODIFY LIBRARY ITEM ROLES
        valid_modify_roles = []
        invalid_modify_roles_ids = []
        new_modify_roles_ids = util.listify(new_modify_roles_ids)
        for role_id in new_modify_roles_ids:
            role = self.role_manager.get(trans, self.app, role_id)
            if role in valid_roles_for_dataset:
                valid_modify_roles.append(role)
            else:
                invalid_modify_roles_ids.append(role_id)
        if len(invalid_modify_roles_ids) > 0:
            log.warning("The following roles could not be added to the dataset modify permission: " + str(invalid_modify_roles_ids))
        modify_permission = {trans.app.security_agent.permitted_actions.LIBRARY_MODIFY: valid_modify_roles}
        trans.app.security_agent.set_library_item_permission(library_dataset, modify_permission)
