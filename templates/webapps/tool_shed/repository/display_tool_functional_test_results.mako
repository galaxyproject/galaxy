<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/webapps/tool_shed/common/common.mako" import="*" />
<%namespace file="/webapps/tool_shed/repository/common.mako" import="*" />

<%
    from galaxy.web.framework.helpers import time_ago
    from tool_shed.util.shed_util_common import to_safe_string

    changeset_revision = repository_metadata.changeset_revision
    has_metadata = repository.metadata_revisions
    has_readme = metadata and 'readme' in metadata
    is_admin = trans.user_is_admin()
    is_new = repository.is_new( trans.app )
    is_deprecated = repository.deprecated

    can_browse_contents = trans.webapp.name == 'tool_shed' and not is_new
    can_contact_owner = trans.user and trans.user != repository.user
    can_download = not is_new and ( not is_malicious or can_push )
    can_manage = is_admin or repository.user == trans.user
    can_push = trans.app.security_agent.can_push( trans.app, trans.user, repository )
    can_rate = repository.user != trans.user
    can_review_repository = has_metadata and not is_deprecated and trans.app.security_agent.user_can_review_repositories( trans.user )
    can_upload = can_push
    can_view_change_log = trans.webapp.name == 'tool_shed' and not is_new
    if repository_metadata.tool_test_errors:
        # The tool_test_errors is mis-named (it should have been named tool_test_results) it will contain a dictionary that includes information
        # about the test environment even if all tests passed and the repository_metadata.tools_functionally_correct column is set to True.
        tool_test_errors = repository_metadata.tool_test_errors
        test_environment_dict = tool_test_errors.get( 'test_environment', None )
        invalid_tests = tool_test_errors.get( 'invalid_tests', [] )
        test_errors = tool_test_errors.get( 'test_errors', [] )
        tests_passed = tool_test_errors.get( 'tests_passed', [] )
    else:
        tool_test_errors = None
        test_environment_dict = {}
        invalid_tests = []
        test_errors = []
        tests_passed = []

    if can_push:
        browse_label = 'Browse or delete repository tip files'
    else:
        browse_label = 'Browse repository tip files'
%>

<%!
   def inherit(context):
       if context.get('use_panels'):
           return '/webapps/tool_shed/base_panels.mako'
       else:
           return '/base.mako'
%>
<%inherit file="${inherit(context)}"/>

<br/><br/>
<ul class="manage-table-actions">
    %if is_new:
        <a class="action-button" href="${h.url_for( controller='upload', action='upload', repository_id=trans.security.encode_id( repository.id ) )}">Upload files to repository</a>
    %else:
        <li><a class="action-button" id="repository-${repository.id}-popup" class="menubutton">Repository Actions</a></li>
        <div popupmenu="repository-${repository.id}-popup">
            %if can_review_repository:
                %if reviewed_by_user:
                    <a class="action-button" href="${h.url_for( controller='repository_review', action='edit_review', id=review_id )}">Manage my review of this revision</a>
                %else:
                    <a class="action-button" href="${h.url_for( controller='repository_review', action='create_review', id=trans.app.security.encode_id( repository.id ), changeset_revision=changeset_revision )}">Add a review to this revision</a>
                %endif
            %endif
            %if can_manage:
                <a class="action-button" href="${h.url_for( controller='repository', action='manage_repository', id=trans.app.security.encode_id( repository.id ), changeset_revision=changeset_revision )}">Manage repository</a>
            %else:
                <a class="action-button" href="${h.url_for( controller='repository', action='view_repository', id=trans.app.security.encode_id( repository.id ), changeset_revision=changeset_revision )}">View repository</a>
            %endif
            %if can_upload:
                <a class="action-button" href="${h.url_for( controller='upload', action='upload', repository_id=trans.security.encode_id( repository.id ) )}">Upload files to repository</a>
            %endif
            %if can_view_change_log:
                <a class="action-button" href="${h.url_for( controller='repository', action='view_changelog', id=trans.app.security.encode_id( repository.id ) )}">View change log</a>
            %endif
            %if can_browse_contents:
                <a class="action-button" href="${h.url_for( controller='repository', action='browse_repository', id=trans.app.security.encode_id( repository.id ) )}">${browse_label}</a>
            %endif
            %if can_contact_owner:
                <a class="action-button" href="${h.url_for( controller='repository', action='contact_owner', id=trans.security.encode_id( repository.id ) )}">Contact repository owner</a>
            %endif
            %if can_download:
                <a class="action-button" href="${h.url_for( controller='repository', action='download', repository_id=trans.app.security.encode_id( repository.id ), changeset_revision=changeset_revision, file_type='gz' )}">Download as a .tar.gz file</a>
                <a class="action-button" href="${h.url_for( controller='repository', action='download', repository_id=trans.app.security.encode_id( repository.id ), changeset_revision=changeset_revision, file_type='bz2' )}">Download as a .tar.bz2 file</a>
                <a class="action-button" href="${h.url_for( controller='repository', action='download', repository_id=trans.app.security.encode_id( repository.id ), changeset_revision=changeset_revision, file_type='zip' )}">Download as a zip file</a>
            %endif
        </div>
    %endif
</ul>

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Repository revision</div>
    <div class="toolFormBody">
        <div class="form-row">
            <label>Revision:</label>
            %if can_view_change_log:
                <a href="${h.url_for( controller='repository', action='view_changelog', id=trans.app.security.encode_id( repository.id ) )}">${revision_label}</a>
            %else:
                ${revision_label}
            %endif
        </div>
    </div>
</div>
<p/>
%if can_download:
    <div class="toolForm">
        <div class="toolFormTitle">Repository '${repository.name}'</div>
        <div class="toolFormBody">
            <div class="form-row">
                <label>Clone this repository:</label>
                ${render_clone_str( repository )}
            </div>
        </div>
    </div>
%else:
    <b>Repository name:</b><br/>
    ${repository.name}
%endif
%if invalid_tests or tool_test_errors or tests_passed:
    <p/>
    <div class="toolForm">
        <div class="toolFormTitle">Tool functional test results</div>
        <div class="toolFormBody">
            <div class="form-row">
                <label>Time tested:</label>
                ${time_ago( repository_metadata.time_last_tested ) | h}
            </div>
            <div class="form-row">
                <table width="100%">
                    <tr bgcolor="#D8D8D8" width="100%"><td><b>Test environment</td></tr>
                </table>
            </div>
            <div class="form-row">
                <label>Architecture:</label>
                ${test_environment_dict.get( 'architecture', 'unknown' ) | h}
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Python version:</label>
                ${test_environment_dict.get( 'python_version', 'unknown' ) | h}
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Operating system:</label>
                ${test_environment_dict.get( 'system', 'unknown' ) | h}
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Galaxy version:</label>
                ${test_environment_dict.get( 'galaxy_revision', 'unknown' ) | h}
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Galaxy database version:</label>
                ${test_environment_dict.get( 'galaxy_database_version', 'unknown' ) | h}
                <div style="clear: both"></div>
            </div>
            %if test_errors:
                <div class="form-row">
                    <table width="100%">
                        <tr bgcolor="#D8D8D8" width="100%"><td><b>Tests that failed</td></tr>
                    </table>
                </div>
                <div class="form-row">
                    <table class="grid">
                        %for test_results_dict in test_errors:
                            <%
                                test_id = test_results_dict.get( 'test_id', 'unknown' )
                                tool_id = test_results_dict.get( 'tool_id', 'unknown' )
                                tool_version = test_results_dict.get( 'tool_version', 'unknown' )
                                test_status = '<font color="red">Test failed</font>'
    
                                stderr = test_results_dict.get( 'stderr', '' )
                                if stderr:
                                    stderr = to_safe_string( stderr, to_html=True )
                                traceback = test_results_dict.get( 'traceback', '' )
                                if traceback:
                                    traceback = to_safe_string( traceback, to_html=True )
                            %>
                            <tr>
                                <td colspan="2" bgcolor="#FFFFCC">Tool id: <b>${tool_id}</b> version: <b>${tool_version}</b></td>
                            </tr>
                            <tr>
                                <td><b>Test id</b></td>
                                <td>${test_id}</td>
                            </tr>
                            <tr>
                                <td><b>Status</b></td>
                                <td>${test_status}</td>
                            </tr>
                            <tr>
                                <td><b>Stderr</b></td>
                                <td>${stderr}</td>
                            </tr>
                            <tr>
                                <td><b>Traceback</b></td>
                                <td>${traceback}</td>
                            </tr>
                        %endfor
                    </table>
                    <div style="clear: both"></div>
                </div>
            %endif
            %if tests_passed:
                <div class="form-row">
                    <table width="100%">
                        <tr bgcolor="#D8D8D8" width="100%"><td><b>Tests that passed successfully</td></tr>
                    </table>
                </div>
                <div class="form-row">
                    <table class="grid">
                        %for test_results_dict in tests_passed:
                            <%
                                test_id = test_results_dict.get( 'test_id', 'unknown' )
                                tool_id = test_results_dict.get( 'tool_id', 'unknown' )
                                tool_version = test_results_dict.get( 'tool_version', 'unknown' )
                                test_status = '<font color="green">Test passed</font>'
                            %>
                            <tr>
                                <td colspan="2" bgcolor="#FFFFCC">Tool id: <b>${tool_id}</b> version: <b>${tool_version}</b></td>
                            </tr>
                            <tr>
                                <td><b>Test id</b></td>
                                <td>${test_id}</td>
                            </tr>
                            <tr>
                                <td><b>Status</b></td>
                                <td>${test_status}</td>
                            </tr>
                        %endfor
                    </table>
                </div>
            %endif
            %if invalid_tests:
                <div class="form-row">
                    <table width="100%">
                        <tr bgcolor="#D8D8D8" width="100%"><td><b>Invalid tests</td></tr>
                    </table>
                </div>
                <div class="form-row">
                    <table class="grid">
                        %for test_results_dict in invalid_tests:
                            <%
                                guid = test_results_dict.get( 'tool_guid', None )
                                tool_id = test_results_dict.get( 'tool_id', None )
                                tool_version = test_results_dict.get( 'tool_version', None )
                                reason_test_is_invalid = test_results_dict.get( 'reason_test_is_invalid', None )
                                if reason_test_is_invalid:
                                    reason_test_is_invalid = to_safe_string( reason_test_is_invalid, to_html=True )
                            %>
                            %if tool_id or tool_version:
                                <tr>
                                    <td colspan="2" bgcolor="#FFFFCC">Tool id: <b>${tool_id}</b> version: <b>${tool_version}</b></td>
                                </tr>
                            %endif
                            %if reason_test_is_invalid:
                                <tr>
                                    <td><b>Reason test is invalid</b></td>
                                    <td>${reason_test_is_invalid}</td>
                                </tr>
                            %endif
                        %endfor
                    </table>
                </div>
            %endif
        </div>
    </div>
%endif
