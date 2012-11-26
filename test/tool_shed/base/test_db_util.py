import galaxy.webapps.community.model as model
from galaxy.model.orm import *
from galaxy.webapps.community.model.mapping import context as sa_session

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
def get_default_user_permissions_by_role( role ):
    return sa_session.query( model.DefaultUserPermissions ) \
                     .filter( model.DefaultUserPermissions.table.c.role_id == role.id ) \
                     .all()
def get_default_user_permissions_by_user( user ):
    return sa_session.query( model.DefaultUserPermissions ) \
                     .filter( model.DefaultUserPermissions.table.c.user_id==user.id ) \
                     .all()
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
def get_repository_by_name( name, owner_username ):
    owner = get_user_by_name( owner_username )
    repository = sa_session.query( model.Repository ) \
                           .filter( model.Repository.table.c.name==name ) \
                           .filter( model.Repository.table.c.user_id==owner.id ) \
                           .first()
    return repository
