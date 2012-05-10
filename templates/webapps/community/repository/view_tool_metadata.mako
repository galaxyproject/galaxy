<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/webapps/community/common/common.mako" import="*" />
<%namespace file="/webapps/community/repository/common.mako" import="*" />

<%
    from galaxy.web.framework.helpers import time_ago
    from urllib import quote_plus
    is_admin = trans.user_is_admin()
    is_new = repository.is_new
    can_contact_owner = trans.user and trans.user != repository.user
    can_push = trans.app.security_agent.can_push( trans.user, repository )
    can_upload = can_push
    can_download = not is_new and ( not is_malicious or can_push )
    can_browse_contents = webapp == 'community' and not is_new
    can_rate = repository.user != trans.user
    can_manage = is_admin or repository.user == trans.user
    can_view_change_log = webapp == 'community' and not is_new
    if can_push:
        browse_label = 'Browse or delete repository tip files'
    else:
        browse_label = 'Browse repository tip files'
%>

<%!
   def inherit(context):
       if context.get('use_panels'):
           return '/webapps/community/base_panels.mako'
       else:
           return '/base.mako'
%>
<%inherit file="${inherit(context)}"/>

<br/><br/>
<ul class="manage-table-actions">
    %if webapp == 'galaxy':
        <li><a class="action-button" id="repository-${repository.id}-popup" class="menubutton">Repository Actions</a></li>
        <div popupmenu="repository-${repository.id}-popup">
            <li><a class="action-button" href="${h.url_for( controller='repository', action='install_repository_revision', repository_id=trans.security.encode_id( repository.id ), webapp=webapp, changeset_revision=changeset_revision )}">Install to local Galaxy</a></li>
            <li><a class="action-button" href="${h.url_for( controller='repository', action='preview_tools_in_changeset', repository_id=trans.security.encode_id( repository.id ), webapp=webapp, changeset_revision=changeset_revision )}">Browse repository</a></li>
        </div>
        <li><a class="action-button" id="tool_shed-${repository.id}-popup" class="menubutton">Tool Shed Actions</a></li>
        <div popupmenu="tool_shed-${repository.id}-popup">
            <a class="action-button" href="${h.url_for( controller='repository', action='browse_valid_repositories', webapp=webapp )}">Browse valid repositories</a>
            <a class="action-button" href="${h.url_for( controller='repository', action='find_tools', webapp=webapp )}">Search for valid tools</a>
            <a class="action-button" href="${h.url_for( controller='repository', action='find_workflows', webapp=webapp )}">Search for workflows</a>
        </div>
    %else:
        %if is_new:
            <a class="action-button" href="${h.url_for( controller='upload', action='upload', repository_id=trans.security.encode_id( repository.id ), webapp=webapp )}">Upload files to repository</a>
        %else:
            <li><a class="action-button" id="repository-${repository.id}-popup" class="menubutton">Repository Actions</a></li>
            <div popupmenu="repository-${repository.id}-popup">
                %if can_manage:
                    <a class="action-button" href="${h.url_for( controller='repository', action='manage_repository', id=trans.app.security.encode_id( repository.id ), changeset_revision=changeset_revision )}">Manage repository</a>
                %else:
                    <a class="action-button" href="${h.url_for( controller='repository', action='view_repository', id=trans.app.security.encode_id( repository.id ), changeset_revision=changeset_revision, webapp=webapp )}">View repository</a>
                %endif
                %if can_upload:
                    <a class="action-button" href="${h.url_for( controller='upload', action='upload', repository_id=trans.security.encode_id( repository.id ), webapp=webapp )}">Upload files to repository</a>
                %endif
                %if can_view_change_log:
                    <a class="action-button" href="${h.url_for( controller='repository', action='view_changelog', id=trans.app.security.encode_id( repository.id ), webapp=webapp )}">View change log</a>
                %endif
                %if can_browse_contents:
                    <a class="action-button" href="${h.url_for( controller='repository', action='browse_repository', id=trans.app.security.encode_id( repository.id ), webapp=webapp )}">${browse_label}</a>
                %endif
                %if can_contact_owner:
                    <a class="action-button" href="${h.url_for( controller='repository', action='contact_owner', id=trans.security.encode_id( repository.id ), webapp=webapp )}">Contact repository owner</a>
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
        %if len( changeset_revision_select_field.options ) > 1:
            <form name="change_revision" id="change_revision" action="${h.url_for( controller='repository', action='view_tool_metadata', repository_id=trans.security.encode_id( repository.id ), tool_id=metadata[ 'id' ], webapp=webapp )}" method="post" >
                <div class="form-row">
                    <%
                        if changeset_revision == repository.tip:
                            tip_str = 'repository tip'
                        else:
                            tip_str = ''
                    %>
                    ${changeset_revision_select_field.get_html()} <i>${tip_str}</i>
                    <div class="toolParamHelp" style="clear: both;">
                        Select a revision to inspect and download versions of tools from this repository.
                    </div>
                </div>
            </form>
        %else:
            <div class="form-row">
                <label>Revision:</label>
                %if can_view_change_log:
                    <a href="${h.url_for( controller='repository', action='view_changelog', id=trans.app.security.encode_id( repository.id ) )}">${revision_label}</a>
                %else:
                    ${revision_label}
                %endif
            </div>
        %endif
    </div>
</div>
<p/>
%if can_download:
    <div class="toolForm">
        <div class="toolFormTitle">${repository.name}</div>
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
%if metadata:
    <p/>
    <div class="toolForm">
        <div class="toolFormTitle">${metadata[ 'name' ]} tool metadata</div>
        <div class="toolFormBody">
            <div class="form-row">
                <label>Name:</label>
                <a href="${h.url_for( controller='repository', action='display_tool', repository_id=trans.security.encode_id( repository.id ), tool_config=metadata[ 'tool_config' ], changeset_revision=changeset_revision, webapp=webapp )}">${metadata[ 'name' ]}</a>
                <div style="clear: both"></div>
            </div>
            %if 'description' in metadata:
                <div class="form-row">
                    <label>Description:</label>
                    ${metadata[ 'description' ]}
                    <div style="clear: both"></div>
                </div>
            %endif
            %if 'id' in metadata:
                <div class="form-row">
                    <label>Id:</label>
                    ${metadata[ 'id' ]}
                    <div style="clear: both"></div>
                </div>
            %endif
            %if 'guid' in metadata:
                <div class="form-row">
                    <label>Guid:</label>
                    ${metadata[ 'guid' ]}
                    <div style="clear: both"></div>
                </div>
            %endif
            %if 'version' in metadata:
                <div class="form-row">
                    <label>Version:</label>
                    ${metadata[ 'version' ]}
                    <div style="clear: both"></div>
                </div>
            %endif
            %if 'version_string_cmd' in metadata:
                <div class="form-row">
                    <label>Version command string:</label>
                    ${metadata[ 'version_string_cmd' ]}
                    <div style="clear: both"></div>
                </div>
            %endif
            %if tool:
                <div class="form-row">
                    <label>Command:</label>
                    <pre>${tool.command}</pre>
                    <div style="clear: both"></div>
                </div>
                <div class="form-row">
                    <label>Interpreter:</label>
                    ${tool.interpreter}
                    <div style="clear: both"></div>
                </div>
                <div class="form-row">
                    <label>Is multi-byte:</label>
                    ${tool.is_multi_byte}
                    <div style="clear: both"></div>
                </div>
                <div class="form-row">
                    <label>Forces a history refresh:</label>
                    ${tool.force_history_refresh}
                    <div style="clear: both"></div>
                </div>
                <div class="form-row">
                    <label>Parallelism:</label>
                    ${tool.parallelism}
                    <div style="clear: both"></div>
                </div>
            %endif
            <%
                if 'requirements' in metadata:
                    requirements = metadata[ 'requirements' ]
                else:
                    requirements = None
            %>
            %if requirements:
                <%
                    requirements_str = ''
                    for requirement_dict in metadata[ 'requirements' ]:
                        requirements_str += '%s (%s), ' % ( requirement_dict[ 'name' ], requirement_dict[ 'type' ] )
                    requirements_str = requirements_str.rstrip( ', ' )
                %>
                <div class="form-row">
                    <label>Requirements:</label>
                    ${requirements_str}
                    <div style="clear: both"></div>
                </div>
            %endif
            <%
                if 'tests' in metadata:
                    tests = metadata[ 'tests' ]
                else:
                    tests = None
            %>
            %if tests:
                <div class="form-row">
                    <label>Functional tests:</label></td>
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
                                        <b>${input[0]}:</b> ${input[1]}<br/>
                                    %endfor
                                </td>
                                <td>
                                    %for output in outputs:
                                        <b>${output[0]}:</b> ${output[1]}<br/>
                                    %endfor
                                </td>
                                <td>
                                    %for required_file in required_files:
                                        ${required_file}<br/>
                                    %endfor
                                </td>
                            </tr>
                        %endfor
                    </table>
                </div>
            %endif
        </div>
    </div>
%endif
