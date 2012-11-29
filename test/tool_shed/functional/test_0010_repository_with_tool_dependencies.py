from tool_shed.base.twilltestcase import *
from tool_shed.base.test_db_util import *

admin_user = None
admin_user_private_role = None
admin_email = 'test@bx.psu.edu'
admin_username = 'admin-user'

regular_user = None
regular_user_private_role = None
regular_email = 'test-1@bx.psu.edu'
regular_username = 'user1'

repository_name = 'freebayes'
repository_description = "Galaxy's freebayes tool"
repository_long_description = "Long description of Galaxy's freebayes tool"

class TestRepositoryWithToolDependencies( ShedTwillTestCase ):
    pass