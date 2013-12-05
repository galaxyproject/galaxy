import logging
import galaxy.model as model
import galaxy.model.tool_shed_install as install_model
from galaxy.model.orm import and_
from functional.database_contexts import galaxy_context as sa_session

log = logging.getLogger(__name__)

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

def get_repository( repository_id ):
    return sa_session.query( install_model.ToolShedRepository ) \
                     .filter( install_model.ToolShedRepository.table.c.id == repository_id ) \
                     .first()

def get_installed_repository_by_name_owner_changeset_revision( name, owner, changeset_revision ):
    return sa_session.query( install_model.ToolShedRepository ) \
                     .filter( and_( install_model.ToolShedRepository.table.c.name == name,
                                    install_model.ToolShedRepository.table.c.owner == owner,
                                    install_model.ToolShedRepository.table.c.installed_changeset_revision == changeset_revision ) ) \
                     .one()


def get_private_role( user ):
    for role in user.all_roles():
        if role.name == user.email and role.description == 'Private Role for %s' % user.email:
            return role
    raise AssertionError( "Private role not found for user '%s'" % user.email )

def get_tool_dependencies_for_installed_repository( repository_id, status=None, exclude_status=None ):
    if status is not None:
        return sa_session.query( install_model.ToolDependency ) \
                         .filter( and_( install_model.ToolDependency.table.c.tool_shed_repository_id == repository_id,
                                        install_model.ToolDependency.table.c.status == status ) ) \
                         .all()
    elif exclude_status is not None:
        return sa_session.query( install_model.ToolDependency ) \
                         .filter( and_( install_model.ToolDependency.table.c.tool_shed_repository_id == repository_id,
                                        install_model.ToolDependency.table.c.status != exclude_status ) ) \
                         .all()
    else:
        return sa_session.query( install_model.ToolDependency ) \
                         .filter( install_model.ToolDependency.table.c.tool_shed_repository_id == repository_id ) \
                         .all()

def mark_obj_deleted( obj ):
    obj.deleted = True
    sa_session.add( obj )
    sa_session.flush()

def refresh( obj ):
    sa_session.refresh( obj )

def get_private_role( user ):
    for role in user.all_roles():
        if role.name == user.email and role.description == 'Private Role for %s' % user.email:
            return role
    raise AssertionError( "Private role not found for user '%s'" % user.email )

def get_user( email ):
    return sa_session.query( model.User ) \
                     .filter( model.User.table.c.email==email ) \
                     .first()
