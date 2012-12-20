import galaxy.model
import galaxy.webapps.community.model as model
from galaxy.model.orm import *
from galaxy.webapps.community.model.mapping import context as sa_session
from galaxy.model.mapping import context as ga_session

def delete_obj( obj ):
    sa_session.delete( obj )
    sa_session.flush()
def delete_user_roles( user ):
    for ura in user.roles:
        sa_session.delete( ura )
    sa_session.flush()
def flush( obj ):
    sa_session.add( obj )
    sa_session.flush()
def get_all_repositories():
    return sa_session.query( model.Repository ).all()
def get_all_installed_repositories( actually_installed=False ):
    if actually_installed:
        return ga_session.query( galaxy.model.ToolShedRepository ) \
                         .filter( and_( galaxy.model.ToolShedRepository.table.c.deleted == False,
                                        galaxy.model.ToolShedRepository.table.c.uninstalled == False,
                                        galaxy.model.ToolShedRepository.table.c.status == galaxy.model.ToolShedRepository.installation_status.INSTALLED ) ) \
                         .all()
    else:
        return ga_session.query( galaxy.model.ToolShedRepository ).all()
def get_category_by_name( name ):
    return sa_session.query( model.Category ) \
                     .filter( model.Category.table.c.name == name ) \
                     .first()
def get_default_user_permissions_by_role( role ):
    return sa_session.query( model.DefaultUserPermissions ) \
                     .filter( model.DefaultUserPermissions.table.c.role_id == role.id ) \
                     .all()
def get_default_user_permissions_by_user( user ):
    return sa_session.query( model.DefaultUserPermissions ) \
                     .filter( model.DefaultUserPermissions.table.c.user_id==user.id ) \
                     .all()
def get_galaxy_repository_by_name_owner_changeset_revision( repository_name, owner, changeset_revision ):
    return ga_session.query( galaxy.model.ToolShedRepository ) \
                     .filter( and_( galaxy.model.ToolShedRepository.table.c.name == repository_name,
                                    galaxy.model.ToolShedRepository.table.c.owner == owner,
                                    galaxy.model.ToolShedRepository.table.c.changeset_revision == changeset_revision ) ) \
                     .first()
def get_installed_repository_by_name_owner( repository_name, owner ):
    return ga_session.query( galaxy.model.ToolShedRepository ) \
                     .filter( and_( galaxy.model.ToolShedRepository.table.c.name == repository_name,
                                    galaxy.model.ToolShedRepository.table.c.owner == owner ) ) \
                     .first()
def get_private_role( user ):
    for role in user.all_roles():
        if role.name == user.email and role.description == 'Private Role for %s' % user.email:
            return role
    raise AssertionError( "Private role not found for user '%s'" % user.email )
def get_user( email ):
    return sa_session.query( model.User ) \
                     .filter( model.User.table.c.email==email ) \
                     .first()
def get_user_by_name( username ):
    return sa_session.query( model.User ) \
                     .filter( model.User.table.c.username==username ) \
                     .first()
def mark_obj_deleted( obj ):
    obj.deleted = True
    sa_session.add( obj )
    sa_session.flush()
def refresh( obj ):
    sa_session.refresh( obj )
def ga_refresh( obj ):
    ga_session.refresh( obj )
def get_galaxy_private_role( user ):
    for role in user.all_roles():
        if role.name == user.email and role.description == 'Private Role for %s' % user.email:
            return role
    raise AssertionError( "Private role not found for user '%s'" % user.email )
def get_galaxy_user( email ):
    return ga_session.query( galaxy.model.User ) \
                     .filter( galaxy.model.User.table.c.email==email ) \
                     .first()
def get_repository_by_name_and_owner( name, owner_username ):
    owner = get_user_by_name( owner_username )
    repository = sa_session.query( model.Repository ) \
                           .filter( and_( model.Repository.table.c.name == name,
                                          model.Repository.table.c.user_id == owner.id ) ) \
                           .first()
    return repository
def get_repository_metadata_by_repository_id_changeset_revision( repository_id, changeset_revision ):
    repository_metadata = sa_session.query( model.RepositoryMetadata ) \
                                    .filter( and_( model.RepositoryMetadata.table.c.repository_id == repository_id,
                                                   model.RepositoryMetadata.table.c.changeset_revision == changeset_revision ) ) \
                                    .first()
    return repository_metadata
