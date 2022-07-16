"""
Manager and Serializer for Datasets.
"""
import glob
import logging
import os
from typing import (
    Dict,
    List,
    Optional,
    Type,
    TypeVar,
)

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
from galaxy.structured_app import MinimalManagerApp

log = logging.getLogger(__name__)

T = TypeVar("T")


class DatasetManager(base.ModelManager, secured.AccessibleManagerMixin, deletable.PurgableManagerMixin):
    """
    Manipulate datasets: the components contained in DatasetAssociations/DatasetInstances/HDAs/LDDAs
    """

    model_class = model.Dataset
    foreign_key_name = "dataset"
    app: MinimalManagerApp

    # TODO:?? get + error_if_uploading is common pattern, should upload check be worked into access/owed?

    def __init__(self, app: MinimalManagerApp):
        super().__init__(app)
        self.permissions = DatasetRBACPermissions(app)
        # needed for admin test
        self.user_manager = users.UserManager(app)

    def create(self, manage_roles=None, access_roles=None, flush=True, **kwargs):
        """
        Create and return a new Dataset object.
        """
        # default to NEW state on new datasets
        kwargs.update(dict(state=(kwargs.get("state", model.Dataset.states.NEW))))
        dataset = model.Dataset(**kwargs)
        self.session().add(dataset)

        self.permissions.set(dataset, manage_roles, access_roles, flush=False)

        if flush:
            self.session().flush()
        return dataset

    def copy(self, dataset, **kwargs):
        raise exceptions.NotImplemented("Datasets cannot be copied")

    def purge(self, dataset, flush=True):
        """
        Remove the object_store/file for this dataset from storage and mark
        as purged.

        :raises exceptions.ConfigDoesNotAllowException: if the instance doesn't allow
        """
        self.error_unless_dataset_purge_allowed(dataset)

        # the following also marks dataset as purged and deleted
        dataset.full_delete()
        self.session().add(dataset)
        if flush:
            self.session().flush()
        return dataset

    # TODO: this may be more conv. somewhere else
    # TODO: how to allow admin bypass?
    def error_unless_dataset_purge_allowed(self, msg=None):
        if not self.app.config.allow_user_dataset_purge:
            msg = msg or "This instance does not allow user dataset purging"
            raise exceptions.ConfigDoesNotAllowException(msg)

    # .... accessibility
    # datasets can implement the accessible interface, but accessibility is checked in an entirely different way
    #   than those resources that have a user attribute (histories, pages, etc.)
    def is_accessible(self, dataset, user, **kwargs):
        """
        Is this dataset readable/viewable to user?
        """
        if self.user_manager.is_admin(user, trans=kwargs.get("trans")):
            return True
        if self.has_access_permission(dataset, user):
            return True
        return False

    def has_access_permission(self, dataset, user):
        """
        Return T/F if the user has role-based access to the dataset.
        """
        roles = user.all_roles_exploiting_cache() if user else []
        return self.app.security_agent.can_access_dataset(roles, dataset)

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
                return dataset.file_name
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


# ============================================================================= AKA DatasetInstanceManager
class DatasetAssociationManager(
    base.ModelManager, secured.AccessibleManagerMixin, secured.OwnableManagerMixin, deletable.PurgableManagerMixin
):
    """
    DatasetAssociation/DatasetInstances are intended to be working
    proxies to a Dataset, associated with either a library or a
    user/history (HistoryDatasetAssociation).
    """

    # DA's were meant to be proxies - but were never fully implemented as them
    # Instead, a dataset association HAS a dataset but contains metadata specific to a library (lda) or user (hda)
    model_class: Type[model.DatasetInstance]
    app: MinimalManagerApp

    # NOTE: model_manager_class should be set in HDA/LDA subclasses

    def __init__(self, app):
        super().__init__(app)
        self.dataset_manager = DatasetManager(app)

    def is_accessible(self, dataset_assoc, user, **kwargs):
        """
        Is this DA accessible to `user`?
        """
        # defer to the dataset
        return self.dataset_manager.is_accessible(dataset_assoc.dataset, user, **kwargs)

    def delete(self, item, flush: bool = True, stop_job: bool = False, **kwargs):
        """
        Marks this dataset association as deleted.
        If `stop_job` is True, will stop the creating job if all other outputs are deleted.
        """
        super().delete(item, flush=flush)
        if stop_job:
            self.stop_creating_job(item, flush=flush)
        return item

    def purge(self, dataset_assoc, flush=True):
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
        super().purge(dataset_assoc, flush=flush or flush_required)

        # stop any jobs outputing the dataset_assoc
        self.stop_creating_job(dataset_assoc, flush=True)

        # more importantly, purge underlying dataset as well
        if dataset_assoc.dataset.user_can_purge:
            self.dataset_manager.purge(dataset_assoc.dataset)
        return dataset_assoc

    def by_user(self, user):
        raise exceptions.NotImplemented("Abstract Method")

    # .... associated job
    def creating_job(self, dataset_assoc):
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

    def stop_creating_job(self, dataset_assoc, flush=False):
        """
        Stops an dataset_assoc's creating job if all the job's other outputs are deleted.
        """

        # Optimize this to skip other checks if this dataset is terminal - we can infer the
        # job is already complete.
        if dataset_assoc.state in model.Dataset.terminal_states:
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
                        self.session().flush()
                    return True
        return False

    def is_composite(self, dataset_assoc):
        """
        Return True if this hda/ldda is a composite type dataset.

        .. note:: see also (whereever we keep information on composite datatypes?)
        """
        return dataset_assoc.extension in self.app.datatypes_registry.get_composite_extensions()

    def extra_files(self, dataset_assoc):
        """Return a list of file paths for composite files, an empty list otherwise."""
        if not self.is_composite(dataset_assoc):
            return []
        return glob.glob(os.path.join(dataset_assoc.dataset.extra_files_path, "*"))

    def serialize_dataset_association_roles(self, trans, dataset_assoc):
        if hasattr(dataset_assoc, "library_dataset_dataset_association"):
            library_dataset = dataset_assoc
            dataset = library_dataset.library_dataset_dataset_association.dataset
        else:
            library_dataset = None
            dataset = dataset_assoc.dataset

        # Omit duplicated roles by converting to set
        security_agent = trans.app.security_agent
        access_roles = set(dataset.get_access_roles(security_agent))
        manage_roles = set(dataset.get_manage_permissions_roles(security_agent))

        access_dataset_role_list = [
            (access_role.name, trans.security.encode_id(access_role.id)) for access_role in access_roles
        ]
        manage_dataset_role_list = [
            (manage_role.name, trans.security.encode_id(manage_role.id)) for manage_role in manage_roles
        ]
        rval = dict(access_dataset_roles=access_dataset_role_list, manage_dataset_roles=manage_dataset_role_list)
        if library_dataset is not None:
            modify_roles = set(
                security_agent.get_roles_for_action(
                    library_dataset, trans.app.security_agent.permitted_actions.LIBRARY_MODIFY
                )
            )
            modify_item_role_list = [
                (modify_role.name, trans.security.encode_id(modify_role.id)) for modify_role in modify_roles
            ]
            rval["modify_item_roles"] = modify_item_role_list
        return rval

    def ensure_can_change_datatype(self, dataset: model.DatasetInstance, raiseException: bool = True) -> bool:
        if not dataset.datatype.is_datatype_change_allowed():
            if not raiseException:
                return False
            raise exceptions.InsufficientPermissionsException(
                f'Changing datatype "{dataset.extension}" is not allowed.'
            )
        return True

    def ensure_can_set_metadata(self, dataset: model.DatasetInstance, raiseException: bool = True) -> bool:
        if not dataset.ok_to_edit_metadata():
            if not raiseException:
                return False
            raise exceptions.ItemAccessibilityException(
                "This dataset is currently being used as input or output. You cannot change datatype until the jobs have completed or you have canceled them."
            )
        return True

    def detect_datatype(self, trans, dataset_assoc):
        """Sniff and assign the datatype to a given dataset association (ldda or hda)"""
        data = trans.sa_session.query(self.model_class).get(dataset_assoc.id)
        self.ensure_can_change_datatype(data)
        self.ensure_can_set_metadata(data)
        path = data.dataset.file_name
        datatype = sniff.guess_ext(path, trans.app.datatypes_registry.sniff_order)
        trans.app.datatypes_registry.change_datatype(data, datatype)
        trans.sa_session.flush()
        self.set_metadata(trans, dataset_assoc)

    def set_metadata(self, trans, dataset_assoc, overwrite=False, validate=True):
        """Trigger a job that detects and sets metadata on a given dataset association (ldda or hda)"""
        data = trans.sa_session.query(self.model_class).get(dataset_assoc.id)
        self.ensure_can_set_metadata(data)
        if overwrite:
            self.overwrite_metadata(data)

        job, *_ = self.app.datatypes_registry.set_external_metadata_tool.tool_action.execute(
            self.app.datatypes_registry.set_external_metadata_tool,
            trans,
            incoming={"input1": data, "validate": validate},
            overwrite=overwrite,
        )
        self.app.job_manager.enqueue(job, tool=self.app.datatypes_registry.set_external_metadata_tool)

    def overwrite_metadata(self, data):
        for name, spec in data.metadata.spec.items():
            # We need to be careful about the attributes we are resetting
            if name not in ["name", "info", "dbkey", "base_name"]:
                if spec.get("default"):
                    setattr(data.metadata, name, spec.unwrap(spec.get("default")))

    def update_permissions(self, trans, dataset_assoc, **kwd):
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
        can_manage = trans.app.security_agent.can_manage_dataset(current_user_roles, dataset) or trans.user_is_admin
        if not can_manage:
            raise exceptions.InsufficientPermissionsException(
                "You do not have proper permissions to manage permissions on this dataset."
            )

        if action == "remove_restrictions":
            trans.app.security_agent.make_dataset_public(dataset)
            if not trans.app.security_agent.dataset_is_public(dataset):
                raise exceptions.InternalServerError("An error occurred while making dataset public.")
        elif action == "make_private":
            if not trans.app.security_agent.dataset_is_private_to_user(trans, dataset):
                private_role = trans.app.security_agent.get_private_user_role(trans.user)
                dp = trans.app.model.DatasetPermissions(
                    trans.app.security_agent.permitted_actions.DATASET_ACCESS.action, dataset, private_role
                )
                trans.sa_session.add(dp)
                trans.sa_session.flush()
            if not trans.app.security_agent.dataset_is_private_to_user(trans, dataset):
                # Check again and inform the user if dataset is not private.
                raise exceptions.InternalServerError("An error occurred and the dataset is NOT private.")
        elif action == "set_permissions":

            def to_role_id(encoded_role_id):
                role_id = base.decode_id(self.app, encoded_role_id)
                return role_id

            def parameters_roles_or_none(role_type):
                encoded_role_ids = kwd.get(role_type, kwd.get(f"{role_type}_ids[]", None))
                if encoded_role_ids is not None:
                    return list(map(to_role_id, encoded_role_ids))
                else:
                    return None

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

    def _set_permissions(self, trans, dataset_assoc, roles_dict):
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
            "copied_from_history_dataset_association_id": self.serialize_id,
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
            "genome_build": lambda item, key, **context: item.dbkey,
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
                val = val.file_name
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

    def serialize(self, dataset_assoc, keys, **context):
        """
        Override to add metadata as flattened keys on the serialized DatasetInstance.
        """
        # if 'metadata' isn't removed from keys here serialize will retrieve the un-serializable MetadataCollection
        # TODO: remove these when metadata is sub-object
        KEYS_HANDLED_SEPARATELY = ("metadata",)
        left_to_handle = self._pluck_from_list(keys, KEYS_HANDLED_SEPARATELY)
        serialized = super().serialize(dataset_assoc, keys, **context)

        # add metadata directly to the dict instead of as a sub-object
        if "metadata" in left_to_handle:
            metadata = self._prefixed_metadata(dataset_assoc)
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
        sa_session.flush()
        trans = context.get("trans")
        assert (
            trans
        ), "Logic error in Galaxy, deserialize_datatype not send a transation object"  # TODO: restructure this for stronger typing
        job, *_ = self.app.datatypes_registry.set_external_metadata_tool.tool_action.execute(
            self.app.datatypes_registry.set_external_metadata_tool, trans, incoming={"input1": item}, overwrite=False
        )  # overwrite is False as per existing behavior
        trans.app.job_manager.enqueue(job, tool=trans.app.datatypes_registry.set_external_metadata_tool)
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
