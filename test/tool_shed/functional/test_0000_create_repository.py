import tempfile, time, re, tempfile, os, shutil
import galaxy.webapps.community.model
from galaxy.util import parse_xml, string_as_bool
from galaxy.util.shed_util import clean_tool_shed_url
from galaxy.model.orm import *
from tool_shed.base.twilltestcase import *
from tool_shed.base.test_db_util import *

admin_user = None
admin_user_private_role = None
admin_email = 'test@bx.psu.edu'
admin_username = 'admin-user'

class TestCreateRepository( ShedTwillTestCase ):
 
    def test_0000_initiate_users( self ):
        """Create necessary users and login as an admin user."""
        self.logout()
        self.login( email=admin_email, username=admin_username )
        admin_user = get_user( admin_email )
        assert admin_user is not None, 'Problem retrieving user with email %s from the database' % admin_email
        admin_user_private_role = get_private_role( admin_user )
    def test_0005_create_category( self ):
        """Create a category"""
        self.visit_url( '/admin/manage_categories?operation=create' )
        try: 
            tc.fv( "1", "name", "Text Manipulation" )
            tc.fv( "1", "description", "Tools for manipulating text" )
            tc.submit( "create_category_button" )
        except Exception, e:
            errmsg = "Problem creating a category: %s" % str( e )
            raise AssertionError( e )
    def test_0010_create_filter_repository( self ):
        """Create a repository"""
        self.visit_url( '/repository/create_repository' )
        try: 
            tc.fv( "1", "name", "filter" )
            tc.fv( "1", "description", "Galaxy's filter tool" )
            tc.fv( "1", "long_description", "Long description of Galaxy's filter tool" )
            tc.fv( "1", "category_id", "Text Manipulation" )
            tc.submit( "create_repository_button" )
        except Exception, e:
            errmsg = "Problem creating a repository: %s" % str( e )
            raise AssertionError( e )
