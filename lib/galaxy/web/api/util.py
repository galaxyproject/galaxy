"""
Utility methods for API controllers
"""

class BadRequestException( Exception ):
    pass

def get_history_for_access( trans, history_id ):
    try:
        decoded_history_id = trans.security.decode_id( history_id )
    except TypeError:
        trans.response.status = 400
        raise BadRequestException( "Malformed history id ( %s ) specified, unable to decode." % str( history_id ) )
    try:
        history = trans.sa_session.query( trans.app.model.History ).get( decoded_history_id )
        assert history
        if history.user != trans.user and not trans.user_is_admin():
            assert trans.sa_session.query( trans.app.model.HistoryUserShareAssociation ).filter_by( user=trans.user, history=history ).count() != 0
    except:
        trans.response.status = 400
        raise BadRequestException( "Invalid history id ( %s ) specified." % str( history_id ) )
    return history

def get_history_for_modification( trans, history_id ):
    history = get_history_for_access( trans, history_id )
    try:
        assert trans.user_is_admin() or history.user == trans.user
    except:
        trans.response.status = 400
        raise BadRequestException( "Invalid history id ( %s ) specified." % str( history_id ) )
    return history

def get_history_content_for_access( trans, content_id ):
    # Note that we could check the history provided in the URL heirarchy here,
    # but it's irrelevant, we care about the history associated with the hda.
    try:
        content_type, decoded_content_id = trans.security.decode_string_id( content_id ).split( '.' )
        decoded_content_id = int( decoded_content_id )
    except:
        trans.response.status = 400
        raise BadRequestException( "Malformed history content id ( %s ) specified, unable to decode." % str( content_id ) )
    try:
        assert content_type == 'file'
        model_class = trans.app.model.HistoryDatasetAssociation
    except:
        trans.response.status = 400
        raise BadRequestException( "Invalid type ( %s ) specified." % str( content_type ) )
    try:
        content = trans.sa_session.query( model_class ).get( decoded_content_id )
        assert content
        if content.history.user != trans.user and not trans.user_is_admin():
            assert trans.sa_session.query(trans.app.model.HistoryUserShareAssociation).filter_by(user=trans.user, history=content.history).count() != 0
    except:
        trans.response.status = 400
        raise BadRequestException( "Invalid %s id ( %s ) specified." % ( content_type, str( content_id ) ) )
    return content

def get_library_content_for_access( trans, content_id ):
    try:
        content_type, decoded_content_id = trans.security.decode_string_id( content_id ).split( '.' )
        decoded_content_id = int( decoded_content_id )
    except:
        trans.response.status = 400
        raise BadRequestException( "Malformed library %s id ( %s ) specified, unable to decode." % ( content_type, str( content_id ) ) )
    if content_type == 'file':
        model_class = trans.app.model.LibraryDataset
    elif content_type == 'folder':
        model_class = trans.app.model.LibraryFolder
    else:
        trans.response.status = 400
        raise BadRequestException( "Invalid type ( %s ) specified." % str( content_type ) )
    try:
        content = trans.sa_session.query( model_class ).get( decoded_content_id )
        assert content
        assert trans.user_is_admin() or trans.app.security_agent.can_access_library_item( trans.get_current_user_roles(), content, trans.user )
    except:
        trans.response.status = 400
        raise BadRequestException( "Invalid %s id ( %s ) specified." % ( content_type, str( content_id ) ) )
    return content
