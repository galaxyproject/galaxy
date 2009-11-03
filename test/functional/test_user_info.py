import galaxy.model
from galaxy.model.orm import *
from galaxy.model.mapping import context as sa_session
from base.twilltestcase import *

not_logged_in_as_admin_security_msg = 'You must be logged in as an administrator to access this feature.'
logged_in_as_admin_security_msg = 'You must be an administrator to access this feature.'
not_logged_in_security_msg = 'You must be logged in to create/submit sequencing requests'
form_one_name = "Student"
form_two_name = "Researcher"

def get_latest_form(form_name):
    fdc_list = sa_session.query( galaxy.model.FormDefinitionCurrent ) \
                         .filter( galaxy.model.FormDefinitionCurrent.table.c.deleted==False ) \
                         .order_by( galaxy.model.FormDefinitionCurrent.table.c.create_time.desc() )
    for fdc in fdc_list:
        if form_name == fdc.latest_form.name:
            return fdc.latest_form
    return None


class TestUserInfo( TwillTestCase ):
    def test_000_create_user_info_forms( self ):
        """Testing creating a new user info form and editing it"""
        self.logout()
        self.login( email='test@bx.psu.edu' )
        # create a the first form
        global form_one_name
        name = form_one_name
        desc = "This is Student user info form's description"
        formtype = galaxy.model.FormDefinition.types.USER_INFO
        self.create_form( name=name, desc=desc, formtype=formtype, num_fields=0 )
        # Get the form_definition object for later tests
        form_one = get_latest_form(form_one_name)
        assert form_one is not None, 'Problem retrieving form named "%s" from the database' % name
        # edit form & add few more fields
        fields = [dict(name='Affiliation',
                       desc='The type of  organization you are affiliated with',
                       type='SelectField',
                       required='optional',
                       selectlist=['Educational', 'Research', 'Commercial']),
                  dict(name='Name of Organization',
                       desc='',
                       type='TextField',
                       required='optional')]
        form_one = get_latest_form(form_one_name)
        self.form_add_field(form_one.id, form_one.name, form_one.desc, form_one.type, field_index=len(form_one.fields), fields=fields)
        form_one_latest = get_latest_form(form_one_name)        
        assert len(form_one_latest.fields) == len(form_one.fields)+len(fields)
        # create the second form
        global form_two_name
        name = form_two_name
        desc = "This is Researcher user info form's description"
        self.create_form( name=name, desc=desc, formtype=formtype, num_fields=0 )
        # Get the form_definition object for later tests
        form_two = get_latest_form(form_two_name)
        assert form_two is not None, 'Problem retrieving form named "%s" from the database' % name
        # edit form & add few more fields
        fields = [dict(name='Affiliation',
                       desc='The type of  organization you are affiliated with',
                       type='SelectField',
                       required='optional',
                       selectlist=['Educational', 'Research', 'Commercial']),
                  dict(name='Name of Organization',
                       desc='',
                       type='TextField',
                       required='optional')]
        form_two = get_latest_form(form_two_name)
        self.form_add_field(form_two.id, form_two.name, form_two.desc, form_two.type, field_index=len(form_one.fields), fields=fields)
        form_two_latest = get_latest_form(form_two_name)        
        assert len(form_two_latest.fields) == len(form_two.fields)+len(fields)
    def test_005_user_reqistration_multiple_user_info_forms( self ):
        ''' Testing user registration with multiple user info forms '''
        self.logout()
        # user a new user with 'Student' user info form
        form_one = get_latest_form(form_one_name)
        user_info_values=['Educational', 'Penn State']
        self.create_user_with_info( 'test11@bx.psu.edu', 'testuser', 'test11', 
                                    user_info_forms='multiple',
                                    user_info_form_id=form_one.id, 
                                    user_info_values=user_info_values )
        self.home()
        self.visit_page( "user/show_info" )
        self.check_page_for_string( "Manage User Information" )
        for value in user_info_values:
            self.check_page_for_string( value )
    def test_010_user_reqistration_single_user_info_forms( self ):
        ''' Testing user registration with a single user info form '''
        # lets delete the 'Researcher' user info form
        self.login( 'test@bx.psu.edu' )
        form_two_latest = get_latest_form(form_two_name)
        form_two_latest.current.deleted = True
        form_two_latest.current.flush()
        self.home()
        self.visit_page('forms/manage?show_filter=Deleted')
        self.check_page_for_string(form_two_latest.name)
        self.logout()
        # user a new user with 'Student' user info form
        form_one = get_latest_form(form_one_name)
        user_info_values=['Educational', 'Penn State']
        self.create_user_with_info( 'test12@bx.psu.edu', 'testuser', 'test12', 
                                    user_info_forms='single',
                                    user_info_form_id=form_one.id, 
                                    user_info_values=user_info_values )
        self.home()
        self.visit_page( "user/show_info" )
        self.check_page_for_string( "Manage User Information" )
        for value in user_info_values:
            self.check_page_for_string( value )
    def test_015_edit_user_info( self ):
        """Testing editing user info as a regular user"""
        self.logout()
        self.login( 'test11@bx.psu.edu' )
        user = sa_session.query( galaxy.model.User ) \
                         .filter( and_( galaxy.model.User.table.c.email=='test11@bx.psu.edu' ) ).first()
        self.edit_login_info( new_email='test11_new@bx.psu.edu', new_username='test11_new' )
        self.change_password('testuser', 'new_testuser')
        self.edit_user_info( ['Research', 'PSU'] )
    def test_020_create_user_as_admin( self ):
        ''' Testing creating users as an admin '''
        self.logout()
        self.login( 'test@bx.psu.edu' )
        form_one = get_latest_form(form_one_name)
        user_info_values=['Educational', 'Penn State']
        self.create_user_with_info( 'test13@bx.psu.edu', 'testuser', 'test13', 
                                    user_info_forms='single',
                                    user_info_form_id=form_one.id, 
                                    user_info_values=user_info_values )
        self.logout()
        self.login( 'test@bx.psu.edu' )
        user = sa_session.query( galaxy.model.User ) \
                         .filter( and_( galaxy.model.User.table.c.email=='test13@bx.psu.edu' ) ).first()
        self.home()
        page = "admin/users?id=%s&operation=information&f-deleted=False" % self.security.encode_id( user.id )
        self.visit_page( page )
        self.check_page_for_string( 'Manage User Information' )
        self.check_page_for_string( 'test13@bx.psu.edu' )
        for value in user_info_values:
            self.check_page_for_string( value )        
        # lets delete the 'Student' user info form
        self.login( 'test@bx.psu.edu' )
        form_one_latest = get_latest_form(form_one_name)
        form_one_latest.current.deleted = True
        form_one_latest.current.flush()
        self.home()
        self.visit_page('forms/manage?show_filter=Deleted')
        self.check_page_for_string(form_one_latest.name)
        self.logout()
        