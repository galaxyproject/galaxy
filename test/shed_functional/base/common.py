admin_user = None
admin_user_private_role = None
admin_email = 'test@bx.psu.edu'
admin_username = 'admin-user'

test_user_1 = None
test_user_1_private_role = None
test_user_1_email = 'test-1@bx.psu.edu'
test_user_1_name = 'user1'

test_user_2 = None
test_user_2_private_role = None
test_user_2_email = 'test-2@bx.psu.edu'
test_user_2_name = 'user2'

test_user_3 = None
test_user_3_private_role = None
test_user_3_email = 'test-3@bx.psu.edu'
test_user_3_name = 'user3'

complex_repository_dependency_template = '''<?xml version="1.0"?>
<tool_dependency>
    <package name="${package}" version="${version}">
${dependency_lines}
    </package>
</tool_dependency>
'''

new_repository_dependencies_xml = '''<?xml version="1.0"?>
<repositories${description}>
${dependency_lines}
</repositories>
'''

new_repository_dependencies_line = '''    <repository toolshed="${toolshed_url}" name="${repository_name}" owner="${owner}" changeset_revision="${changeset_revision}"${prior_installation_required} />'''
