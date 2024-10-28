"""
Manager and Serializer for Datasets.
"""

import glob
import logging
import os
from typing import (
    Any,
    Dict,
    Generic,
    List,
    Optional,
    Type,
    TypeVar,
)

from sqlalchemy import select

from galaxy import (
    exceptions,
    model,
)
from galaxy.datatypes import sniff
from galaxy.managers import (
    base,
    deletable,
    rbac_secured,
    secured,
    users,
)
from galaxy.model import (
    Dataset,
    DatasetHash,
    DatasetInstance,
    HistoryDatasetAssociation,
)
from galaxy.model.base import transaction
from galaxy.schema.tasks import (
    ComputeDatasetHashTaskRequest,
    PurgeDatasetsTaskRequest,
)
from galaxy.structured_app import MinimalManagerApp
from galaxy.util.hash_util import memory_bound_hexdigest

log = logging.getLogger(__name__)

T = TypeVar("T")


class DatasetManager(base.ModelManager[Dataset], secured.AccessibleManagerMixin, deletable.PurgableManagerMixin):
    """
    Manipulate datasets: the components contained in DatasetAssociations/DatasetInstances/HDAs/LDDAs
    """

    model_class = Dataset
    foreign_key_name = "dataset"
    app: MinimalManagerApp

    # TODO:?? get + error_if_uploading is common pattern, should upload check be worked into access/owed?

    def __init__(self, app: MinimalManagerApp):
        super().__init__(app)
        self.permissions = DatasetRBACPermissions(app)
        # needed for admin test
        self.user_manager = users.UserManager(app)
        self.quota_agent = app.quota_agent

    def copy(self, item, **kwargs):
        raise exceptions.NotImplemented("Datasets cannot be copied")

    def purge(self, item, flush=True, **kwargs):
        """
        Remove the object_store/file for this dataset from storage and mark
        as purged.

        :raises exceptions.ConfigDoesNotAllowException: if the instance doesn't allow
        """
        self.error_unless_dataset_purge_allowed(item)

        # the following also marks dataset as purged and deleted
        item.full_delete()
        self.session().add(item)
        if flush:
            session = self.session()
            with transaction(session):
                session.commit()
        return item

    def purge_datasets(self, request: PurgeDatasetsTaskRequest):
        """
        Caution: any additional security checks must be done before executing this action.

        Completely removes a set of object_store/files associated with the datasets from storage and marks them as purged.
        They might not be removed if there are still un-purged associations to the dataset.
        """
        self.error_unless_dataset_purge_allowed()
        with self.session().begin():
            for dataset_id in request.dataset_ids:
                dataset: Optional[Dataset] = self.session().get(Dataset, dataset_id)
                if dataset and dataset.user_can_purge:
                    try:
                        dataset.full_delete()
                    except Exception:
                        log.exception(f"Unable to purge dataset ({dataset.id})")

    # TODO: this may be more conv. somewhere else
    # TODO: how to allow admin bypass?
    def error_unless_dataset_purge_allowed(self, msg=None):
        if not self.app.config.allow_user_dataset_purge:
            msg = msg or "This instance does not allow user dataset purging"
            raise exceptions.ConfigDoesNotAllowException(msg)

    # .... accessibility
    # datasets can implement the accessible interface, but accessibility is checked in an entirely different way
    #   than those resources that have a user attribute (histories, pages, etc.)
    def is_accessible(self, item: Any, user: Optional[model.User], **kwargs) -> bool:
        """
        Is this dataset readable/viewable to user?
        """
        if self.user_manager.is_admin(user, trans=kwargs.get("trans")):
            return True
        if self.has_access_permission(item, user):
            return True
        return False

    def has_access_permission(self, dataset, user):
        """
        Whether the user has role-based access to the dataset.
        """
        roles = user.all_roles_exploiting_cache() if user else []
        return self.app.security_agent.can_access_dataset(roles, dataset)

    def update_object_store_id(self, trans, dataset, object_store_id: str):
        device_source_map = self.app.object_store.get_device_source_map()
        old_object_store_id = dataset.object_store_id
        new_object_store_id = object_store_id
        if old_object_store_id == new_object_store_id:
            return None
        old_device_id = device_source_map.get_device_id(old_object_store_id)
        new_device_id = device_source_map.get_device_id(new_object_store_id)
        if old_device_id != new_device_id:
            raise exceptions.RequestParameterInvalidException(
                "Cannot swap object store IDs for object stores that don't share a device ID."
            )

        if not self.app.security_agent.can_change_object_store_id(trans.user, dataset):
            # TODO: probably want separate exceptions for doesn't own the dataset and dataset
            # has been shared.
            raise exceptions.InsufficientPermissionsException("Cannot change dataset permissions...")

        if quota_source_map := self.app.object_store.get_quota_source_map():
            old_label = quota_source_map.get_quota_source_label(old_object_store_id)
            new_label = quota_source_map.get_quota_source_label(new_object_store_id)
            if old_label != new_label:
                self.quota_agent.relabel_quota_for_dataset(dataset, old_label, new_label)
        sa_session = self.session()
        with transaction(sa_session):
            dataset.object_store_id = new_object_store_id
            sa_session.add(dataset)
            sa_session.commit()

    def compute_hash(self, request: ComputeDatasetHashTaskRequest):
        # For files in extra_files_path
        dataset = self.by_id(request.dataset_id)
        extra_files_path = request.extra_files_path
        if extra_files_path:
            extra_dir = dataset.extra_files_path_name
            file_path = self.app.object_store.get_filename(dataset, extra_dir=extra_dir, alt_name=extra_files_path)
        else:
            file_path = dataset.get_file_name()
        hash_function = request.hash_function
        calculated_hash_value = memory_bound_hexdigest(hash_func_name=hash_function, path=file_path)
        extra_files_path = request.extra_files_path
        dataset_hash = model.DatasetHash(
            hash_function=hash_function,
            hash_value=calculated_hash_value,
            extra_files_path=extra_files_path,
        )
        dataset_hash.dataset = dataset
        # TODO: replace/update if the combination of dataset_id/hash_function has already
        # been stored.
        sa_session = self.session()
        hash = get_dataset_hash(sa_session, dataset.id, hash_function, extra_files_path)
        if hash is None:
            sa_session.add(dataset_hash)
            with transaction(sa_session):
                sa_session.commit()
        else:
            old_hash_value = hash.hash_value
            if old_hash_value != calculated_hash_value:
                log.warning(
                    f"Re-calculated dataset hash for dataset [{dataset.id}] and new hash value [{calculated_hash_value}] does not equal previous hash value [{old_hash_value}]."
                )
            else:
                log.debug("Duplicated dataset hash request, no update to the database.")

    # TODO: implement above for groups
    # TODO: datatypes?
    # .... data, object_store


# TODO: SecurityAgentDatasetRBACPermissions( object ):


class DatasetRBACPermissions:
    def __init__(self, app):
        self.app = app
        self.access = rbac_secured.AccessDatasetRBACPermission(app)
        self.manage = rbac_secured.ManageDatasetRBACPermission(app)

    # TODO: temporary facade over security_agent
    def available_roles(self, trans, dataset, controller="root"):
        return self.app.security_agent.get_legitimate_roles(trans, dataset, controller)

    def get(self, dataset, flush=True):
        manage = self.manage.by_dataset(dataset)
        access = self.access.by_dataset(dataset)
        return (manage, access)

    def set(self, dataset, manage_roles, access_roles, flush=True):
        manage = self.manage.set(dataset, manage_roles or [], flush=False)
        access = self.access.set(dataset, access_roles or [], flush=flush)
        return (manage, access)

    # ---- conv. settings
    def set_public_with_single_manager(self, dataset, user, flush=True):
        manage = self.manage.grant(dataset, user, flush=flush)
        self.access.clear(dataset, flush=False)
        return ([manage], [])

    def set_private_to_one_user(self, dataset, user, flush=True):
        manage = self.manage.grant(dataset, user, flush=False)
        access = self.access.set_private(dataset, user, flush=flush)
        return ([manage], access)


class DatasetSerializer(base.ModelSerializer[DatasetManager], deletable.PurgableSerializerMixin):
    model_manager_class = DatasetManager

    def __init__(self, app: MinimalManagerApp, user_manager: users.UserManager):
        super().__init__(app)
        self.dataset_manager = self.manager
        # needed for admin test
        self.user_manager = user_manager

        self.default_view = "summary"
        self.add_view(
            "summary",
            [
                "id",
                "create_time",
                "update_time",
                "state",
                "deleted",
                "purged",
                "purgable",
                # 'object_store_id',
                # 'external_filename',
                # 'extra_files_path',
                "file_size",
                "total_size",
                "uuid",
            ],
        )
        # could do visualizations and/or display_apps

    def add_serializers(self):
        super().add_serializers()
        deletable.PurgableSerializerMixin.add_serializers(self)
        serializers: Dict[str, base.Serializer] = {
            "create_time": self.serialize_date,
            "update_time": self.serialize_date,
            "uuid": lambda item, key, **context: str(item.uuid) if item.uuid else None,
            "file_name": self.serialize_file_name,
            "extra_files_path": self.serialize_extra_files_path,
            "permissions": self.serialize_permissions,
            "total_size": lambda item, key, **context: int(item.get_total_size()),
            "file_size": lambda item, key, **context: int(item.get_size(calculate_size=False)),
        }
        self.serializers.update(serializers)

    def serialize_file_name(self, item, key, user=None, **context):
        """
        If the config allows or the user is admin, return the file name
        of the file that contains this dataset's data.
        """
        dataset = item
        is_admin = self.user_manager.is_admin(user, trans=context.get("trans"))
        # expensive: allow config option due to cost of operation
        if is_admin or self.app.config.expose_dataset_path:
            if not dataset.purged:
                return dataset.get_file_name(sync_cache=False)
        self.skip()

    def serialize_extra_files_path(self, item, key, user=None, **context):
        """
        If the config allows or the user is admin, return the file path.
        """
        dataset = item
        is_admin = self.user_manager.is_admin(user, trans=context.get("trans"))
        # expensive: allow config option due to cost of operation
        if is_admin or self.app.config.expose_dataset_path:
            if not dataset.purged:
                return dataset.extra_files_path
        self.skip()

    def serialize_permissions(self, item, key, user=None, **context):
        """ """
        dataset = item
        trans = context.get("trans")
        if not self.dataset_manager.permissions.manage.is_permitted(dataset, user, trans=trans):
            self.skip()

        management_permissions = self.dataset_manager.permissions.manage.by_dataset(dataset)
        access_permissions = self.dataset_manager.permissions.access.by_dataset(dataset)
        permissions = {
            "manage": [self.app.security.encode_id(perm.role.id) for perm in management_permissions],
            "access": [self.app.security.encode_id(perm.role.id) for perm in access_permissions],
        }
        return permissions


U = TypeVar("U", bound=DatasetInstance)


class DatasetAssociationManager(
    base.ModelManager[DatasetInstance],
    secured.AccessibleManagerMixin,
    secured.OwnableManagerMixin,
    deletable.PurgableManagerMixin,
    Generic[U],
):
    """
    DatasetAssociation/DatasetInstances are intended to be working
    proxies to a Dataset, associated with either a library or a
    user/history (HistoryDatasetAssociation).
    """

    # DA's were meant to be proxies - but were never fully implemented as them
    # Instead, a dataset association HAS a dataset but contains metadata specific to a library (lda) or user (hda)
    app: MinimalManagerApp

    # NOTE: model_manager_class should be set in HDA/LDA subclasses

    def __init__(self, app: MinimalManagerApp):
        super().__init__(app)
        self.dataset_manager = DatasetManager(app)

    def is_accessible(self, item: U, user: Optional[model.User], **kwargs: Any) -> bool:
        """
        Is this DA accessible to `user`?
        """
        # defer to the dataset
        return self.dataset_manager.is_accessible(item.dataset, user, **kwargs)

    def delete(self, item: U, flush: bool = True, stop_job: bool = False, **kwargs):
        """
        Marks this dataset association as deleted.
        If `stop_job` is True, will stop the creating job if all other outputs are deleted.
        """
        super().delete(item, flush=flush)
        if stop_job:
            self.stop_creating_job(item, flush=flush)
        return item

    def purge(self, item: U, flush=True, **kwargs):
        """
        Purge this DatasetInstance and the dataset underlying it.
        """
        # error here if disallowed - before jobs are stopped
        # TODO: this check may belong in the controller
        self.dataset_manager.error_unless_dataset_purge_allowed()

        # We need to ignore a potential flush=False here if jobs are not tracked in the database,
        # so that job cleanup associated with stop_creating_job will see
        # the dataset as purged.
        flush_required = not self.app.config.track_jobs_in_database
        super().purge(item, flush=flush or flush_required, **kwargs)

        # stop any jobs outputing the dataset association
        self.stop_creating_job(item, flush=True)

        # more importantly, purge underlying dataset as well
        if item.dataset.user_can_purge:
            self.dataset_manager.purge(item.dataset, flush=flush, **kwargs)
        return item

    def by_user(self, user):
        raise exceptions.NotImplemented("Abstract Method")

    # .... associated job
    def creating_job(self, dataset_assoc: U):
        """
        Return the `Job` that created this dataset or None if not found.
        """
        # TODO: is this needed? Can't you use the dataset_assoc.creating_job attribute? When is this None?
        # TODO: this would be even better if outputs and inputs were the underlying datasets
        job = None
        for job_output_assoc in dataset_assoc.creating_job_associations:
            job = job_output_assoc.job
            break
        return job

    def stop_creating_job(self, dataset_assoc: U, flush=False):
        """
        Stops an dataset_assoc's creating job if all the job's other outputs are deleted.
        """

        # Optimize this to skip other checks if this dataset is terminal - we can infer the
        # job is already complete.
        if dataset_assoc.state in Dataset.terminal_states:
            return False

        if dataset_assoc.parent_id is None and len(dataset_assoc.creating_job_associations) > 0:
            # Mark associated job for deletion
            job = dataset_assoc.creating_job_associations[0].job
            if not job.finished:
                # Are *all* of the job's other output datasets deleted?
                if job.check_if_output_datasets_deleted():
                    track_jobs_in_database = self.app.config.track_jobs_in_database
                    job.mark_deleted(track_jobs_in_database)
                    if not track_jobs_in_database:
                        self.app.job_manager.stop(job)
                    if flush:
                        session = self.session()
                        with transaction(session):
                            session.commit()
                    return True
        return False

    def is_composite(self, dataset_assoc: U):
        """
        Return True if this hda/ldda is a composite type dataset.

        .. note:: see also (whereever we keep information on composite datatypes?)
        """
        return dataset_assoc.extension in self.app.datatypes_registry.get_composite_extensions()

    def extra_files(self, dataset_assoc: U):
        """Return a list of file paths for composite files, an empty list otherwise."""
        if not self.is_composite(dataset_assoc):
            return []
        return glob.glob(os.path.join(dataset_assoc.dataset.extra_files_path, "*"))

    def serialize_dataset_association_roles(self, dataset_assoc: U):
        if hasattr(dataset_assoc, "library_dataset_dataset_association"):
            library_dataset = dataset_assoc
            dataset = library_dataset.library_dataset_dataset_association.dataset
        else:
            library_dataset = None
            dataset = dataset_assoc.dataset

        # Omit duplicated roles by converting to set
        access_roles = set(dataset.get_access_roles(self.app.security_agent))
        manage_roles = set(dataset.get_manage_permissions_roles(self.app.security_agent))

        access_dataset_role_list = [
            (access_role.name, self.app.security.encode_id(access_role.id)) for access_role in access_roles
        ]
        manage_dataset_role_list = [
            (manage_role.name, self.app.security.encode_id(manage_role.id)) for manage_role in manage_roles
        ]
        rval = dict(access_dataset_roles=access_dataset_role_list, manage_dataset_roles=manage_dataset_role_list)
        if library_dataset is not None:
            modify_roles = set(
                self.app.security_agent.get_roles_for_action(
                    library_dataset, self.app.security_agent.permitted_actions.LIBRARY_MODIFY
                )
            )
            modify_item_role_list = [
                (modify_role.name, self.app.security.encode_id(modify_role.id)) for modify_role in modify_roles
            ]
            rval["modify_item_roles"] = modify_item_role_list
        return rval

    def ensure_dataset_on_disk(self, trans, dataset: U):
        # Not a guarantee data is really present, but excludes a lot of expected cases
        if not dataset.dataset:
            raise exceptions.InternalServerError("Item has no associated dataset.")
        if dataset.purged or dataset.dataset.purged:
            raise exceptions.ItemDeletionException("The dataset you are attempting to view has been purged.")
        elif dataset.deleted and not (
            trans.user_is_admin
            or (isinstance(dataset, HistoryDatasetAssociation) and self.is_owner(dataset, trans.get_user()))  # type: ignore[arg-type]
        ):
            raise exceptions.ItemDeletionException("The dataset you are attempting to view has been deleted.")
        elif dataset.state == Dataset.states.UPLOAD:
            raise exceptions.Conflict("Please wait until this dataset finishes uploading before attempting to view it.")
        elif dataset.state in (Dataset.states.NEW, Dataset.states.QUEUED):
            raise exceptions.Conflict(f"The dataset you are attempting to view is {dataset.state} and has no data.")
        elif dataset.state == Dataset.states.DISCARDED:
            raise exceptions.ItemDeletionException("The dataset you are attempting to view has been discarded.")
        elif dataset.state == Dataset.states.DEFERRED:
            raise exceptions.Conflict(
                "The dataset you are attempting to view has deferred data. You can only use this dataset as input for jobs."
            )
        elif dataset.state == Dataset.states.PAUSED:
            raise exceptions.Conflict(
                "The dataset you are attempting to view is in paused state. One of the inputs for the job that creates this dataset has failed."
            )
        elif dataset.state == Dataset.states.RUNNING:
            if not self.app.object_store.exists(dataset.dataset):
                raise exceptions.Conflict(
                    "The dataset you are attempting to view is still being created and has no data yet."
                )
        elif dataset.state == Dataset.states.ERROR:
            if not self.app.object_store.exists(dataset.dataset):
                raise exceptions.RequestParameterInvalidException("The dataset is in error and has no data.")

    def ensure_can_change_datatype(self, dataset: U, raiseException: bool = True) -> bool:
        if not dataset.datatype.is_datatype_change_allowed():
            if not raiseException:
                return False
            raise exceptions.InsufficientPermissionsException(
                f'Changing datatype "{dataset.extension}" is not allowed.'
            )
        return True

    def ensure_can_set_metadata(self, dataset: U, raiseException: bool = True) -> bool:
        if not dataset.ok_to_edit_metadata():
            if not raiseException:
                return False
            raise exceptions.ItemAccessibilityException(
                "This dataset is currently being used as input or output. You cannot change datatype until the jobs have completed or you have canceled them."
            )
        return True

    def detect_datatype(self, trans, dataset_assoc: U):
        """Sniff and assign the datatype to a given dataset association (ldda or hda)"""
        session = self.session()
        self.ensure_can_change_datatype(dataset_assoc)
        self.ensure_can_set_metadata(dataset_assoc)
        assert dataset_assoc.dataset
        path = dataset_assoc.dataset.get_file_name()
        datatype = sniff.guess_ext(path, self.app.datatypes_registry.sniff_order)
        self.app.datatypes_registry.change_datatype(dataset_assoc, datatype)
        with transaction(session):
            session.commit()
        self.set_metadata(trans, dataset_assoc)

    def set_metadata(self, trans, dataset_assoc: U, overwrite: bool = False, validate: bool = True) -> None:
        """Trigger a job that detects and sets metadata on a given dataset association (ldda or hda)"""
        self.ensure_can_set_metadata(dataset_assoc)
        if overwrite:
            self.overwrite_metadata(dataset_assoc)

        job, *_ = self.app.datatypes_registry.set_external_metadata_tool.tool_action.execute_via_trans(
            self.app.datatypes_registry.set_external_metadata_tool,
            trans,
            incoming={"input1": dataset_assoc, "validate": validate},
            overwrite=overwrite,
        )
        self.app.job_manager.enqueue(job, tool=self.app.datatypes_registry.set_external_metadata_tool)

    def overwrite_metadata(self, data):
        for name, spec in data.metadata.spec.items():
            # We need to be careful about the attributes we are resetting
            if name not in ["name", "info", "dbkey", "base_name"]:
                if spec.get("default"):
                    setattr(data.metadata, name, spec.unwrap(spec.get("default")))

    def update_permissions(self, trans, dataset_assoc: U, **kwd):
        action = kwd.get("action", "set_permissions")
        if action not in ["remove_restrictions", "make_private", "set_permissions"]:
            raise exceptions.RequestParameterInvalidException(
                'The mandatory parameter "action" has an invalid value. '
                'Allowed values are: "remove_restrictions", "make_private", "set_permissions"'
            )
        if hasattr(dataset_assoc, "library_dataset_dataset_association"):
            library_dataset = dataset_assoc
            dataset = library_dataset.library_dataset_dataset_association.dataset
        else:
            library_dataset = None
            dataset = dataset_assoc.dataset

        current_user_roles = trans.get_current_user_roles()
        can_manage = self.app.security_agent.can_manage_dataset(current_user_roles, dataset) or trans.user_is_admin
        if not can_manage:
            raise exceptions.InsufficientPermissionsException(
                "You do not have proper permissions to manage permissions on this dataset."
            )

        if action == "remove_restrictions":
            self.app.security_agent.make_dataset_public(dataset)
            if not self.app.security_agent.dataset_is_public(dataset):
                raise exceptions.InternalServerError("An error occurred while making dataset public.")
        elif action == "make_private":
            if not self.app.security_agent.dataset_is_private_to_user(trans, dataset):
                private_role = self.app.security_agent.get_private_user_role(trans.user)
                dp = self.app.model.DatasetPermissions(
                    self.app.security_agent.permitted_actions.DATASET_ACCESS.action, dataset, private_role
                )
                trans.sa_session.add(dp)
                with transaction(trans.sa_session):
                    trans.sa_session.commit()
            if not self.app.security_agent.dataset_is_private_to_user(trans, dataset):
                # Check again and inform the user if dataset is not private.
                raise exceptions.InternalServerError("An error occurred and the dataset is NOT private.")
        elif action == "set_permissions":

            def parameters_roles_or_none(role_type):
                return kwd.get(role_type, kwd.get(f"{role_type}_ids[]"))

            access_roles = parameters_roles_or_none("access")
            manage_roles = parameters_roles_or_none("manage")
            modify_roles = parameters_roles_or_none("modify")
            role_ids_dict = {
                "DATASET_MANAGE_PERMISSIONS": manage_roles,
                "DATASET_ACCESS": access_roles,
            }
            if library_dataset is not None:
                role_ids_dict["LIBRARY_MODIFY"] = modify_roles

            self._set_permissions(trans, dataset_assoc, role_ids_dict)

    def _set_permissions(self, trans, dataset_assoc: U, roles_dict):
        raise exceptions.NotImplemented()


class _UnflattenedMetadataDatasetAssociationSerializer(base.ModelSerializer[T], deletable.PurgableSerializerMixin):
    def __init__(self, app):
        self.dataset_serializer = app[DatasetSerializer]
        super().__init__(app)

    def add_serializers(self):
        super().add_serializers()
        deletable.PurgableSerializerMixin.add_serializers(self)

        serializers: Dict[str, base.Serializer] = {
            "create_time": self.serialize_date,
            "update_time": self.serialize_date,
            # underlying dataset
            "dataset": lambda item, key, **context: self.dataset_serializer.serialize_to_view(
                item.dataset, view="summary", **context
            ),
            "dataset_id": self._proxy_to_dataset(proxy_key="id"),
            # TODO: why is this named uuid!? The da doesn't have a uuid - it's the underlying dataset's uuid!
            "uuid": self._proxy_to_dataset(proxy_key="uuid"),
            # 'dataset_uuid': self._proxy_to_dataset( key='uuid' ),
            "file_name": self._proxy_to_dataset(serializer=self.dataset_serializer.serialize_file_name),
            "extra_files_path": self._proxy_to_dataset(serializer=self.dataset_serializer.serialize_extra_files_path),
            "permissions": self._proxy_to_dataset(serializer=self.dataset_serializer.serialize_permissions),
            # TODO: do the sizes proxy accurately/in the same way?
            "size": lambda item, key, **context: int(item.get_size(calculate_size=False)),
            "file_size": lambda item, key, **context: self.serializers["size"](item, key, **context),
            "nice_size": lambda item, key, **context: item.get_size(nice_size=True, calculate_size=False),
            # common to lddas and hdas - from mapping.py
            "copied_from_history_dataset_association_id": lambda item, key, **context: item.id,
            "copied_from_library_dataset_dataset_association_id": self.serialize_id,
            "info": lambda item, key, **context: item.info.strip() if isinstance(item.info, str) else item.info,
            "blurb": lambda item, key, **context: item.blurb,
            "peek": lambda item, key, **context: item.display_peek() if item.peek and item.peek != "no peek" else None,
            "meta_files": self.serialize_meta_files,
            "metadata": self.serialize_metadata,
            "creating_job": self.serialize_creating_job,
            "rerunnable": self.serialize_rerunnable,
            "parent_id": self.serialize_id,
            "designation": lambda item, key, **context: item.designation,
            # 'extended_metadata': self.serialize_extended_metadata,
            # 'extended_metadata_id': self.serialize_id,
            # remapped
            # TODO: Replace string cast with https://github.com/pydantic/pydantic/pull/9137 on 24.1
            "genome_build": lambda item, key, **context: str(item.dbkey) if item.dbkey is not None else None,
            # derived (not mapped) attributes
            "data_type": lambda item, key, **context: f"{item.datatype.__class__.__module__}.{item.datatype.__class__.__name__}",
            "converted": self.serialize_converted_datasets,
            # TODO: metadata/extra files
        }
        self.serializers.update(serializers)
        # this an abstract superclass, so no views created
        # because of that: we need to add a few keys that will use the default serializer
        self.serializable_keyset.update(["name", "state", "tool_version", "extension", "visible", "dbkey"])

    def _proxy_to_dataset(self, serializer: Optional[base.Serializer] = None, proxy_key: Optional[str] = None):
        # dataset associations are (rough) proxies to datasets - access their serializer using this remapping fn
        # remapping done by either kwarg key: IOW dataset attr key (e.g. uuid)
        # or by kwarg serializer: a function that's passed in (e.g. permissions)
        if proxy_key:
            serializer = self.dataset_serializer.serializers.get(proxy_key)
        if serializer:
            return lambda item, key, **context: serializer(item.dataset, proxy_key or key, **context)
        raise TypeError("kwarg serializer or key needed")

    def serialize_meta_files(self, item, key, **context):
        """
        Cycle through meta files and return them as a list of dictionaries.
        """
        dataset_assoc = item
        meta_files = []
        for meta_type in dataset_assoc.metadata_file_types:
            if getattr(dataset_assoc.metadata, meta_type, None):
                meta_files.append(
                    dict(
                        file_type=meta_type,
                        download_url=self.url_for(
                            "get_metadata_file",
                            history_id=self.app.security.encode_id(dataset_assoc.history_id),
                            history_content_id=self.app.security.encode_id(dataset_assoc.id),
                            query_params={"metadata_file": meta_type},
                            context=context,
                        ),
                    )
                )
        return meta_files

    def serialize_metadata(self, item, key, excluded=None, **context):
        """
        Cycle through metadata and return as dictionary.
        """
        dataset_assoc = item
        # dbkey is a repeat actually (metadata_dbkey == genome_build)
        # excluded = [ 'dbkey' ] if excluded is None else excluded
        excluded = [] if excluded is None else excluded

        metadata = {}
        for name, spec in dataset_assoc.metadata.spec.items():
            if name in excluded:
                continue
            val = dataset_assoc.metadata.get(name)
            # NOTE: no files
            if isinstance(val, model.MetadataFile):
                # only when explicitly set: fetching filepaths can be expensive
                if not self.app.config.expose_dataset_path:
                    continue
                val = val.get_file_name()
            # TODO:? possibly split this off?
            # If no value for metadata, look in datatype for metadata.
            elif val is None and hasattr(dataset_assoc.datatype, name):
                val = getattr(dataset_assoc.datatype, name)
            if val is None and spec.get("optional"):
                continue
            metadata[name] = val

        return metadata

    def serialize_creating_job(self, item, key, **context):
        """
        Return the id of the Job that created this dataset (or its original)
        or None if no `creating_job` is found.
        """
        dataset = item
        if dataset.creating_job:
            return self.serialize_id(dataset.creating_job, "id")
        else:
            return None

    def serialize_rerunnable(self, item, key, **context):
        """
        Return False if this tool that created this dataset can't be re-run
        (e.g. upload).
        """
        dataset = item
        if dataset.creating_job:
            tool = self.app.toolbox.get_tool(dataset.creating_job.tool_id, dataset.creating_job.tool_version)
            if tool and tool.is_workflow_compatible:
                return True
        return False

    def serialize_converted_datasets(self, item, key, **context):
        """
        Return a file extension -> converted dataset encoded id map with all
        the existing converted datasets associated with this instance.

        This filters out deleted associations.
        """
        dataset_assoc = item
        id_map = {}
        for converted in dataset_assoc.implicitly_converted_datasets:
            if not converted.deleted and converted.dataset:
                id_map[converted.type] = self.serialize_id(converted.dataset, "id")
        return id_map


class DatasetAssociationSerializer(_UnflattenedMetadataDatasetAssociationSerializer[T]):
    # TODO: remove this class - metadata should be a sub-object instead as in the superclass

    def add_serializers(self):
        super().add_serializers()
        # remove the single nesting key here
        del self.serializers["metadata"]

    def serialize(self, item, keys, **context):
        """
        Override to add metadata as flattened keys on the serialized DatasetInstance.
        """
        # if 'metadata' isn't removed from keys here serialize will retrieve the un-serializable MetadataCollection
        # TODO: remove these when metadata is sub-object
        KEYS_HANDLED_SEPARATELY = ("metadata",)
        left_to_handle = self._pluck_from_list(keys, KEYS_HANDLED_SEPARATELY)
        serialized = super().serialize(item, keys, **context)

        # add metadata directly to the dict instead of as a sub-object
        if "metadata" in left_to_handle:
            metadata = self._prefixed_metadata(item)
            serialized.update(metadata)
        return serialized

    # TODO: this is more util/gen. use
    def _pluck_from_list(self, list_, elems):
        """
        Removes found elems from list list_ and returns list of found elems if found.
        """
        found = []
        for elem in elems:
            try:
                index = list_.index(elem)
                found.append(list_.pop(index))
            except ValueError:
                pass
        return found

    def _prefixed_metadata(self, dataset_assoc):
        """
        Adds (a prefixed version of) the DatasetInstance metadata to the dict,
        prefixing each key with 'metadata_'.
        """
        # build the original, nested dictionary
        metadata = self.serialize_metadata(dataset_assoc, "metadata")

        # prefix each key within and return
        prefixed = {}
        for key, val in metadata.items():
            prefixed_key = f"metadata_{key}"
            prefixed[prefixed_key] = val
        return prefixed


class DatasetAssociationDeserializer(base.ModelDeserializer, deletable.PurgableDeserializerMixin):
    def add_deserializers(self):
        super().add_deserializers()
        deletable.PurgableDeserializerMixin.add_deserializers(self)

        self.deserializers.update(
            {
                "name": self.deserialize_basestring,
                "info": self.deserialize_basestring,
                "datatype": self.deserialize_datatype,
            }
        )
        self.deserializable_keyset.update(self.deserializers.keys())

    # TODO: untested
    def deserialize_metadata(self, dataset_assoc, metadata_key, metadata_dict, **context):
        """ """
        self.validate.matches_type(metadata_key, metadata_dict, dict)
        returned = {}
        for key, val in metadata_dict.items():
            returned[key] = self.deserialize_metadatum(dataset_assoc, key, val, **context)
        return returned

    def deserialize_metadatum(self, dataset_assoc, key, val, **context):
        """ """
        if key not in dataset_assoc.datatype.metadata_spec:
            return
        metadata_specification = dataset_assoc.datatype.metadata_spec[key]
        if metadata_specification.get("readonly"):
            return
        unwrapped_val = metadata_specification.unwrap(val)
        setattr(dataset_assoc.metadata, key, unwrapped_val)
        # ...?
        return unwrapped_val

    def deserialize_datatype(self, item, key, val, **context):
        if not item.datatype.is_datatype_change_allowed():
            raise exceptions.RequestParameterInvalidException("The current datatype does not allow datatype changes.")
        target_datatype = self.app.datatypes_registry.get_datatype_by_extension(val)
        if not target_datatype:
            raise exceptions.RequestParameterInvalidException("The target datatype does not exist.")
        if not target_datatype.is_datatype_change_allowed():
            raise exceptions.RequestParameterInvalidException("The target datatype does not allow datatype changes.")
        if not item.ok_to_edit_metadata():
            raise exceptions.RequestParameterInvalidException(
                "Dataset metadata could not be updated because it is used as input or output of a running job."
            )
        item.change_datatype(val)
        sa_session = self.app.model.context
        with transaction(sa_session):
            sa_session.commit()
        trans = context.get("trans")
        assert (
            trans
        ), "Logic error in Galaxy, deserialize_datatype not send a transation object"  # TODO: restructure this for stronger typing
        job, *_ = self.app.datatypes_registry.set_external_metadata_tool.tool_action.execute_via_trans(
            self.app.datatypes_registry.set_external_metadata_tool, trans, incoming={"input1": item}, overwrite=False
        )  # overwrite is False as per existing behavior
        self.app.job_manager.enqueue(job, tool=self.app.datatypes_registry.set_external_metadata_tool)
        return item.datatype


class DatasetAssociationFilterParser(base.ModelFilterParser, deletable.PurgableFiltersMixin):
    def _add_parsers(self):
        super()._add_parsers()
        deletable.PurgableFiltersMixin._add_parsers(self)

        self.orm_filter_parsers.update(
            {
                "name": {"op": ("eq", "contains", "like")},
                "state": {"column": "_state", "op": ("eq", "in")},
                "visible": {"op": ("eq"), "val": base.parse_bool},
            }
        )
        self.fn_filter_parsers.update(
            {
                "genome_build": self.string_standard_ops("dbkey"),
                "data_type": {"op": {"eq": self.eq_datatype, "isinstance": self.isinstance_datatype}},
            }
        )

    def eq_datatype(self, dataset_assoc, class_str):
        """
        Is the `dataset_assoc` datatype equal to the registered datatype `class_str`?
        """
        comparison_class = self.app.datatypes_registry.get_datatype_class_by_name(class_str)
        return comparison_class and dataset_assoc.datatype.__class__ == comparison_class

    def isinstance_datatype(self, dataset_assoc, class_strs):
        """
        Is the `dataset_assoc` datatype derived from any of the registered
        datatypes in the comma separated string `class_strs`?
        """
        parse_datatype_fn = self.app.datatypes_registry.get_datatype_class_by_name
        comparison_classes: List[Type] = []
        for class_str in class_strs.split(","):
            datatype_class = parse_datatype_fn(class_str)
            if datatype_class:
                comparison_classes.append(datatype_class)
        return comparison_classes and isinstance(dataset_assoc.datatype, tuple(comparison_classes))


def get_dataset_hash(session, dataset_id, hash_function, extra_files_path):
    stmt = (
        select(DatasetHash)
        .where(DatasetHash.dataset_id == dataset_id)
        .where(DatasetHash.hash_function == hash_function)
        .where(DatasetHash.extra_files_path == extra_files_path)
    )
    return session.scalars(stmt).one_or_none()
