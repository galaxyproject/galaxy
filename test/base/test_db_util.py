import galaxy.model
from galaxy.model.orm import *
from functional import database_contexts
# Deprecated - import database_contexts and use galaxy_context
sa_session = database_contexts.galaxy_context
from base.twilltestcase import *


def gx_context():
    return database_contexts.galaxy_context


def delete_obj( obj ):
    gx_context().delete( obj )
    gx_context().flush()


def delete_request_type_permissions( id ):
    rtps = gx_context().query( galaxy.model.RequestTypePermissions ) \
                     .filter( and_( galaxy.model.RequestTypePermissions.table.c.request_type_id == id ) ) \
                     .order_by( desc( galaxy.model.RequestTypePermissions.table.c.create_time ) )
    for rtp in rtps:
        gx_context().delete( rtp )
    gx_context().flush()


def delete_user_roles( user ):
    for ura in user.roles:
        gx_context().delete( ura )
    gx_context().flush()


def flush( obj ):
    gx_context().add( obj )
    gx_context().flush()


def get_all_histories_for_user( user ):
    return gx_context().query( galaxy.model.History ) \
                     .filter( and_( galaxy.model.History.table.c.user_id == user.id,
                                    galaxy.model.History.table.c.deleted == False ) ) \
                     .all()


def get_dataset_permissions_by_dataset( dataset ):
    return gx_context().query( galaxy.model.DatasetPermissions ) \
                     .filter( galaxy.model.DatasetPermissions.table.c.dataset_id == dataset.id ) \
                     .all()


def get_dataset_permissions_by_role( role ):
    return gx_context().query( galaxy.model.DatasetPermissions ) \
                     .filter( galaxy.model.DatasetPermissions.table.c.role_id == role.id ) \
                     .first()


def get_default_history_permissions_by_history( history ):
    return gx_context().query( galaxy.model.DefaultHistoryPermissions ) \
                     .filter( galaxy.model.DefaultHistoryPermissions.table.c.history_id == history.id ) \
                     .all()


def get_default_history_permissions_by_role( role ):
    return gx_context().query( galaxy.model.DefaultHistoryPermissions ) \
                     .filter( galaxy.model.DefaultHistoryPermissions.table.c.role_id == role.id ) \
                     .all()


def get_default_user_permissions_by_role( role ):
    return gx_context().query( galaxy.model.DefaultUserPermissions ) \
                     .filter( galaxy.model.DefaultUserPermissions.table.c.role_id == role.id ) \
                     .all()


def get_default_user_permissions_by_user( user ):
    return gx_context().query( galaxy.model.DefaultUserPermissions ) \
                     .filter( galaxy.model.DefaultUserPermissions.table.c.user_id == user.id ) \
                     .all()


def get_form( name ):
    fdc_list = gx_context().query( galaxy.model.FormDefinitionCurrent ) \
                         .filter( galaxy.model.FormDefinitionCurrent.table.c.deleted == False ) \
                         .order_by( galaxy.model.FormDefinitionCurrent.table.c.create_time.desc() )
    for fdc in fdc_list:
        gx_context().refresh( fdc )
        gx_context().refresh( fdc.latest_form )
        if fdc.latest_form.name == name:
            return fdc.latest_form
    return None


def get_folder( parent_id, name, description ):
    return gx_context().query( galaxy.model.LibraryFolder ) \
                     .filter( and_( galaxy.model.LibraryFolder.table.c.parent_id == parent_id,
                                    galaxy.model.LibraryFolder.table.c.name == name,
                                    galaxy.model.LibraryFolder.table.c.description == description ) ) \
                     .first()


def get_group_by_name( name ):
    return gx_context().query( galaxy.model.Group ).filter( galaxy.model.Group.table.c.name == name ).first()


def get_group_role_associations_by_group( group ):
    return gx_context().query( galaxy.model.GroupRoleAssociation ) \
                     .filter( galaxy.model.GroupRoleAssociation.table.c.group_id == group.id ) \
                     .all()


def get_group_role_associations_by_role( role ):
    return gx_context().query( galaxy.model.GroupRoleAssociation ) \
                     .filter( galaxy.model.GroupRoleAssociation.table.c.role_id == role.id ) \
                     .all()


def get_latest_dataset():
    return gx_context().query( galaxy.model.Dataset ) \
                     .order_by( desc( galaxy.model.Dataset.table.c.create_time ) ) \
                     .first()


def get_latest_hda():
    return gx_context().query( galaxy.model.HistoryDatasetAssociation ) \
                     .order_by( desc( galaxy.model.HistoryDatasetAssociation.table.c.create_time ) ) \
                     .first()


def get_latest_history_for_user( user ):
    return gx_context().query( galaxy.model.History ) \
                     .filter( and_( galaxy.model.History.table.c.deleted == False,
                                    galaxy.model.History.table.c.user_id == user.id ) ) \
                     .order_by( desc( galaxy.model.History.table.c.create_time ) ) \
                     .first()


def get_latest_ldda_by_name( name ):
    return gx_context().query( galaxy.model.LibraryDatasetDatasetAssociation ) \
                     .filter( and_( galaxy.model.LibraryDatasetDatasetAssociation.table.c.name == name,
                                    galaxy.model.LibraryDatasetDatasetAssociation.table.c.deleted == False ) ) \
                     .order_by( desc( galaxy.model.LibraryDatasetDatasetAssociation.table.c.create_time ) ) \
                     .first()


def get_latest_lddas( limit ):
    return gx_context().query( galaxy.model.LibraryDatasetDatasetAssociation ) \
                     .order_by( desc( galaxy.model.LibraryDatasetDatasetAssociation.table.c.update_time ) ) \
                     .limit( limit )


def get_library( name, description, synopsis ):
    return gx_context().query( galaxy.model.Library ) \
                     .filter( and_( galaxy.model.Library.table.c.name == name,
                                    galaxy.model.Library.table.c.description == description,
                                    galaxy.model.Library.table.c.synopsis == synopsis,
                                    galaxy.model.Library.table.c.deleted == False ) ) \
                     .first()


def get_private_role( user ):
    for role in user.all_roles():
        if role.name == user.email and role.description == 'Private Role for %s' % user.email:
            return role
    raise AssertionError( "Private role not found for user '%s'" % user.email )


def get_request_by_name( name ):
    return gx_context().query( galaxy.model.Request ) \
                     .filter( and_( galaxy.model.Request.table.c.name == name,
                                    galaxy.model.Request.table.c.deleted == False ) ) \
                     .first()


def get_request_type_by_name( name ):
    return gx_context().query( galaxy.model.RequestType ) \
                     .filter( and_( galaxy.model.RequestType.table.c.name == name ) ) \
                     .order_by( desc( galaxy.model.RequestType.table.c.create_time ) ) \
                     .first()


def get_role_by_name( name ):
    return gx_context().query( galaxy.model.Role ).filter( galaxy.model.Role.table.c.name == name ).first()


def get_user( email ):
    return gx_context().query( galaxy.model.User ) \
                     .filter( galaxy.model.User.table.c.email == email ) \
                     .first()


def get_user_address( user, short_desc ):
    return gx_context().query( galaxy.model.UserAddress ) \
                     .filter( and_( galaxy.model.UserAddress.table.c.user_id == user.id,
                                    galaxy.model.UserAddress.table.c.desc == short_desc,
                                    galaxy.model.UserAddress.table.c.deleted == False ) ) \
                     .order_by( desc( galaxy.model.UserAddress.table.c.create_time ) ) \
                     .first()


def get_user_group_associations_by_group( group ):
    return gx_context().query( galaxy.model.UserGroupAssociation ) \
                     .filter( galaxy.model.UserGroupAssociation.table.c.group_id == group.id ) \
                     .all()


def get_user_info_form_definition():
    return galaxy.model.FormDefinition.types.USER_INFO


def get_user_role_associations_by_role( role ):
    return gx_context().query( galaxy.model.UserRoleAssociation ) \
                     .filter( galaxy.model.UserRoleAssociation.table.c.role_id == role.id ) \
                     .all()


def mark_obj_deleted( obj ):
    obj.deleted = True
    gx_context().add( obj )
    gx_context().flush()


def refresh( obj ):
    gx_context().refresh( obj )
