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
        decoded_content_id = trans.security.decode_id( content_id )
        model_class = trans.app.model.HistoryDatasetAssociation
    except:
        trans.response.status = 400
        raise BadRequestException( "Malformed history content id ( %s ) specified, unable to decode." % str( content_id ) )
    try:
        content = trans.sa_session.query( model_class ).get( decoded_content_id )
        assert content
        if content.history.user != trans.user and not trans.user_is_admin():
            assert trans.sa_session.query(trans.app.model.HistoryUserShareAssociation).filter_by(user=trans.user, history=content.history).count() != 0
    except:
        trans.response.status = 400
        raise BadRequestException( "Invalid history content id ( %s ) specified." % ( str( content_id ) ) )
    return content

def get_library_folder_for_access( trans, library_id, folder_id ):
    """
    When we know we're looking for a folder, take either the 'F' + encoded_id or bare encoded_id.
    """
    if ( len( folder_id ) % 16 == 0 ):
        folder_id = 'F' + folder_id
    return get_library_content_for_access( trans, folder_id )

def get_library_content_for_access( trans, content_id ):
    try:
        if ( len( content_id ) % 16 == 0 ):
            model_class = trans.app.model.LibraryDataset
            decoded_content_id = trans.security.decode_id( content_id )
        elif ( content_id.startswith( 'F' ) ):
            model_class = trans.app.model.LibraryFolder
            decoded_content_id = trans.security.decode_id( content_id[1:] )
        else:
            raise Exception( 'Bad id' )
    except:
        trans.response.status = 400
        raise BadRequestException( "Malformed library content id ( %s ) specified, unable to decode." % str( content_id ) )
    try:
        content = trans.sa_session.query( model_class ).get( decoded_content_id )
        assert content
        assert trans.user_is_admin() or trans.app.security_agent.can_access_library_item( trans.get_current_user_roles(), content, trans.user )
    except:
        trans.response.status = 400
        raise BadRequestException( "Invalid library content id ( %s ) specified." % str( content_id ) )
    return content

def encode_all_ids( trans, rval ):
    """
    encodes all integer values in the dict rval whose keys are 'id' or end with '_id'
    """
    if type( rval ) != dict:
        return rval
    for k, v in rval.items():
        if k == 'id' or k.endswith( '_id' ):
            try:
                rval[k] = trans.security.encode_id( v )
            except:
                pass # probably already encoded
    return rval
