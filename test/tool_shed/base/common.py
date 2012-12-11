admin_user = None
admin_user_private_role = None
admin_email = 'test@bx.psu.edu'
admin_username = 'admin-user'

test_user_1 = None
test_user_1_private_role = None
test_user_1_email = 'test-1@bx.psu.edu'
test_user_1_name = 'user1'

new_repository_dependencies_xml = '''<?xml version="1.0"?>
<repositories${description}>
${dependency_lines}
</repositories>
'''

new_repository_dependencies_line = '''    <repository toolshed="${toolshed_url}" name="${repository_name}" owner="${owner}" changeset_revision="${changeset_revision}" />'''