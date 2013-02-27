<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/webapps/tool_shed/common/common.mako" import="*" />
<%namespace file="/webapps/tool_shed/repository/common.mako" import="*" />

<%
    from galaxy.web.framework.helpers import time_ago
    from urllib import quote_plus

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
    %if trans.webapp.name == 'galaxy':
        <li><a class="action-button" id="repository-${repository.id}-popup" class="menubutton">Repository Actions</a></li>
        <div popupmenu="repository-${repository.id}-popup">
            <li><a class="action-button" href="${h.url_for( controller='repository', action='install_repositories_by_revision', repository_ids=trans.security.encode_id( repository.id ), changeset_revisions=changeset_revision )}">Install to Galaxy</a></li>
            <li><a class="action-button" href="${h.url_for( controller='repository', action='preview_tools_in_changeset', repository_id=trans.security.encode_id( repository.id ), changeset_revision=changeset_revision )}">Browse repository</a></li>
        </div>
        <li><a class="action-button" id="tool_shed-${repository.id}-popup" class="menubutton">Tool Shed Actions</a></li>
        <div popupmenu="tool_shed-${repository.id}-popup">
            <a class="action-button" href="${h.url_for( controller='repository', action='browse_valid_categories' )}">Browse valid repositories</a>
            <a class="action-button" href="${h.url_for( controller='repository', action='find_tools' )}">Search for valid tools</a>
            <a class="action-button" href="${h.url_for( controller='repository', action='find_workflows' )}">Search for workflows</a>
        </div>
    %else:
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
%if tool_metadata_dict:
    <p/>
    <div class="toolForm">
        <div class="toolFormTitle">${tool_metadata_dict[ 'name' ]} tool metadata</div>
        <div class="toolFormBody">
            <div class="form-row">
                <table width="100%">
                    <tr bgcolor="#D8D8D8" width="100%"><td><b>Miscellaneous</td></tr>
                </table>
            </div>
            <div class="form-row">
                <label>Name:</label>
                <a href="${h.url_for( controller='repository', action='display_tool', repository_id=trans.security.encode_id( repository.id ), tool_config=tool_metadata_dict[ 'tool_config' ], changeset_revision=changeset_revision )}">${tool_metadata_dict[ 'name' ]}</a>
                <div style="clear: both"></div>
            </div>
            %if 'description' in tool_metadata_dict:
                <div class="form-row">
                    <label>Description:</label>
                    ${tool_metadata_dict[ 'description' ] | h}
                    <div style="clear: both"></div>
                </div>
            %endif
            %if 'id' in tool_metadata_dict:
                <div class="form-row">
                    <label>Id:</label>
                    ${tool_metadata_dict[ 'id' ] | h}
                    <div style="clear: both"></div>
                </div>
            %endif
            %if 'guid' in tool_metadata_dict:
                <div class="form-row">
                    <label>Guid:</label>
                    ${tool_metadata_dict[ 'guid' ] | h}
                    <div style="clear: both"></div>
                </div>
            %endif
            %if 'version' in tool_metadata_dict:
                <div class="form-row">
                    <label>Version:</label>
                    ${tool_metadata_dict[ 'version' ] | h}
                    <div style="clear: both"></div>
                </div>
            %endif
            %if 'version_string_cmd' in tool_metadata_dict:
                <div class="form-row">
                    <label>Version command string:</label>
                    ${tool_metadata_dict[ 'version_string_cmd' ] | h}
                    <div style="clear: both"></div>
                </div>
            %endif
            <div class="form-row">
                <table width="100%">
                    <tr bgcolor="#D8D8D8" width="100%"><td><b>Version lineage of this tool (guids ordered most recent to oldest)</td></tr>
                </table>
            </div>
            <div class="form-row">
                %if tool_lineage:
                    <table class="grid">
                        %for guid in tool_lineage:
                            <tr>
                                <td>
                                    %if guid == tool_metadata_dict[ 'guid' ]:
                                        ${guid | h} <b>(this tool)</b>
                                    %else:
                                        ${guid | h}
                                    %endif
                                </td>
                            </tr>
                        %endfor
                    </table>
                %else:
                    No tool versions are defined for this tool so it is critical that you <b>Reset all repository metadata</b> from the
                    <b>Manage repository</b> page.
                %endif
            </div>
            <div class="form-row">
                <table width="100%">
                    <tr bgcolor="#D8D8D8" width="100%"><td><b>Requirements (dependencies defined in the &lt;requirements&gt; tag set)</td></tr>
                </table>
            </div>
            <%
                if 'requirements' in tool_metadata_dict:
                    requirements = tool_metadata_dict[ 'requirements' ]
                else:
                    requirements = None
            %>
            %if requirements:
                <div class="form-row">
                    <label>Requirements:</label>
                    <table class="grid">
                        <tr>
                            <td><b>name</b></td>
                            <td><b>version</b></td>
                            <td><b>type</b></td>
                        </tr>
                        %for requirement_dict in requirements:
                            <%
                                requirement_name = requirement_dict[ 'name' ] or 'not provided'
                                requirement_version = requirement_dict[ 'version' ] or 'not provided'
                                requirement_type = requirement_dict[ 'type' ] or 'not provided'
                            %>
                            <tr>
                                <td>${requirement_name | h}</td>
                                <td>${requirement_version | h}</td>
                                <td>${requirement_type | h}</td>
                            </tr>
                        %endfor
                    </table>
                    <div style="clear: both"></div>
                </div>
            %else:
                <div class="form-row">
                    No requirements defined
                </div>
            %endif
            %if tool:
                <div class="form-row">
                    <table width="100%">
                        <tr bgcolor="#D8D8D8" width="100%"><td><b>Additional information about this tool</td></tr>
                    </table>
                </div>
                <div class="form-row">
                    <label>Command:</label>
                    <pre>${tool.command | h}</pre>
                    <div style="clear: both"></div>
                </div>
                <div class="form-row">
                    <label>Interpreter:</label>
                    ${tool.interpreter | h}
                    <div style="clear: both"></div>
                </div>
                <div class="form-row">
                    <label>Is multi-byte:</label>
                    ${tool.is_multi_byte | h}
                    <div style="clear: both"></div>
                </div>
                <div class="form-row">
                    <label>Forces a history refresh:</label>
                    ${tool.force_history_refresh | h}
                    <div style="clear: both"></div>
                </div>
                <div class="form-row">
                    <label>Parallelism:</label>
                    ${tool.parallelism | h}
                    <div style="clear: both"></div>
                </div>
            %endif
            <div class="form-row">
                <table width="100%">
                    <tr bgcolor="#D8D8D8" width="100%"><td><b>Functional tests</td></tr>
                </table>
            </div>
            <%
                if 'tests' in tool_metadata_dict:
                    tests = tool_metadata_dict[ 'tests' ]
                else:
                    tests = None
            %>
            %if tests:
                <div class="form-row">
                    <table class="grid">
                        <tr>
                            <td><b>name</b></td>
                            <td><b>inputs</b></td>
                            <td><b>outputs</b></td>
                            <td><b>required files</b></td>
                        </tr>
                        %for test_dict in tests:
                            <%
                                inputs = test_dict[ 'inputs' ]
                                outputs = test_dict[ 'outputs' ]
                                required_files = test_dict[ 'required_files' ]
                            %>
                            <tr>
                                <td>${test_dict[ 'name' ]}</td>
                                <td>
                                    %for input in inputs:
                                        <b>${input[0]}:</b> ${input[1] | h}<br/>
                                    %endfor
                                </td>
                                <td>
                                    %for output in outputs:
                                        <b>${output[0]}:</b> ${output[1] | h}<br/>
                                    %endfor
                                </td>
                                <td>
                                    %for required_file in required_files:
                                        ${required_file | h}<br/>
                                    %endfor
                                </td>
                            </tr>
                        %endfor
                    </table>
                </div>
            %else:
                <div class="form-row">
                    No functional tests defined
                </div>
            %endif
        </div>
    </div>
%endif
