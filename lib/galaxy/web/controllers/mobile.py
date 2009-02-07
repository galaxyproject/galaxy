from galaxy.web.base.controller import *

class Mobile( BaseController ):
    @web.expose
    def index( self, trans, **kwargs ):
        if trans.user is None:
            return self.__login( trans, **kwargs )
        else:
            return self.history_list( trans, **kwargs )
        
    @web.expose
    def history_list( self, trans ):
        if trans.user is None: trans.response.send_redirect( url_for( action='index' ) )
        return trans.fill_template( "mobile/history/list.mako" )
        
    @web.expose
    def history_detail( self, trans, id ):
        if trans.user is None: trans.response.send_redirect( url_for( action='index' ) )
        history = trans.app.model.History.get( id )
        assert history.user == trans.user
        return trans.fill_template( "mobile/history/detail.mako", history=history )

    @web.expose
    def dataset_detail( self, trans, id ):
        if trans.user is None: trans.response.send_redirect( url_for( action='index' ) )
        dataset = trans.app.model.HistoryDatasetAssociation.get( id )
        assert dataset.history.user == trans.user
        return trans.fill_template( "mobile/dataset/detail.mako", dataset=dataset )

    @web.expose
    def dataset_peek( self, trans, id ):
        if trans.user is None: trans.response.send_redirect( url_for( action='index' ) )
        dataset = trans.app.model.HistoryDatasetAssociation.get( id )
        assert dataset.history.user == trans.user
        yield "<html><body>"
        yield dataset.display_peek()
        yield "</body></html>"
        
    def __login( self, trans, email="", password="" ):
        email_error = password_error = None
        if email or password:
            user = model.User.filter( model.User.table.c.email==email ).first()
            if not user:
                email_error = "No such user"
            elif user.deleted:
                email_error = "This account has been marked deleted, contact your Galaxy administrator to restore the account."
            elif user.external:
                email_error = "This account was created for use with an external authentication method, contact your local Galaxy administrator to activate it."
            elif not user.check_password( password ):
                password_error = "Invalid password"
            else:
                trans.handle_user_login( user )
                trans.log_event( "User logged in" )
                trans.response.send_redirect( url_for( action='index' ) )
        form = web.FormBuilder( web.url_for(), "Login", submit_text="Login" ) \
                .add_text( "email", "Email", value=email, error=email_error ) \
                .add_password( "password", "Password", value='', error=password_error, 
                                help="<a href='%s'>Forgot password? Reset here</a>" % web.url_for( action='reset_password' ) )
        return trans.show_form( form, template="mobile/form.mako" )
        
