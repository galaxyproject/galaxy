

class ApiKeyManager( object ):

    def __init__( self, app ):
        self.app = app

    def create_api_key( self, user ):
        guid = self.app.security.get_new_guid()
        new_key = self.app.model.APIKeys()
        new_key.user_id = user.id
        new_key.key = guid
        sa_session = self.app.model.context
        sa_session.add( new_key )
        sa_session.flush()
        return guid

    def get_or_create_api_key( self, user ):
        # Logic Galaxy has always used - but it would appear to have a race
        # condition. Worth fixing? Would kind of need a message queue to fix
        # in multiple process mode.
        if user.api_keys:
            key = user.api_keys[0].key
        else:
            key = self.create_api_key( user )
        return key
