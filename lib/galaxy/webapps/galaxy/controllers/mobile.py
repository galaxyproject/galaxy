from galaxy.web.base.controller import *

class Mobile( BaseUIController ):
    @web.expose
    def index( self, trans, **kwargs ):
        return trans.fill_template( "mobile/index.mako" )
        
    @web.expose
    def history_list( self, trans ):
        return trans.fill_template( "mobile/history/list.mako" )
        
    @web.expose
    def history_detail( self, trans, id ):
        history = trans.sa_session.query( trans.app.model.History ).get( id )
        assert history.user == trans.user
        return trans.fill_template( "mobile/history/detail.mako", history=history )

    @web.expose
    def dataset_detail( self, trans, id ):
        dataset = trans.sa_session.query( trans.app.model.HistoryDatasetAssociation ).get( id )
        assert dataset.history.user == trans.user
        return trans.fill_template( "mobile/dataset/detail.mako", dataset=dataset )

    @web.expose
    def dataset_peek( self, trans, id ):
        dataset = trans.sa_session.query( trans.app.model.HistoryDatasetAssociation ).get( id )
        assert dataset.history.user == trans.user
        return trans.fill_template( "mobile/dataset/peek.mako", dataset=dataset )
        
    @web.expose
    def settings( self, trans, email=None, password=None ):
        message = None
        if email is not None and password is not None:
            if email == "":
                self.__logout( trans )
                message = "Logged out"
            else:
                error = self.__login( trans, email, password )
                message = error or "Login changed"
        return trans.fill_template( "mobile/settings.mako", message=message )
        
    def __logout( self, trans ):
        trans.log_event( "User logged out" )
        trans.handle_user_logout()

    def __login( self, trans, email="", password="" ):
        error = password_error = None
        user = trans.sa_session.query( model.User ).filter_by( email = email ).first()
        if not user:
            error = "No such user (please note that login is case sensitive)"
        elif user.deleted:
            error = "This account has been marked deleted, contact your Galaxy administrator to restore the account."
        elif user.external:
            error = "This account was created for use with an external authentication method, contact your local Galaxy administrator to activate it."
        elif not user.check_password( password ):
            error = "Invalid password"
        else:
            trans.handle_user_login( user, 'galaxy' )
            trans.log_event( "User logged in" )
        return error
