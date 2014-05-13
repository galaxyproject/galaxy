<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<%def name="title()">Data Manager</%def>

%if message:
    ${render_msg( message, status )}
%endif

<h2>Data Manager</h2>

%if view_only:
    <p>Not implemented</p>
%elif not data_managers.data_managers:
    ${ render_msg( 'You do not currently have any Data Managers installed. You can install some from a <a href="%s">ToolShed</a>.' % ( h.url_for( controller="admin_toolshed", action="browse_tool_sheds" ) ), "warning" ) }
%else:
    <p>Choose your data managing option from below. You may install additional Data Managers from a <a href="${ h.url_for( controller='admin_toolshed', action='browse_tool_sheds' ) }">ToolShed</a>.</p>
    <ul>
        <li><h3>Run Data Manager Tools</h3>
            <div style="margin-left:1em">
            <ul>
            %for data_manager_id, data_manager in sorted( data_managers.data_managers.iteritems(), key=lambda x:x[1].name ):
                <li>
                    <a href="${ h.url_for( controller='tool_runner', action='index', tool_id=data_manager.tool.id ) }"><strong>${ data_manager.name | h }</strong></a> - ${ data_manager.description | h }
                </li>
                <p/>
            %endfor
            </ul>
            </div>
        </li>
        <p/>
        <li><h3>View Data Manager Jobs</h3>
            <div style="margin-left:1em">
            <ul>
                %for data_manager_id, data_manager in sorted( data_managers.data_managers.iteritems(), key=lambda x:x[1].name ):
                    <li>
                        <a href="${ h.url_for( controller='data_manager', action='manage_data_manager', id=data_manager_id)}" target="galaxy_main"><strong>${ data_manager.name | h }</strong></a> - ${ data_manager.description | h }</a>
                    </li>
                    <p/>
                %endfor
            </ul>
            </div>
        </li>
        <p/>
        <p/>
        <li><h3>View Tool Data Table Entries</h3>
            <div style="margin-left:1em">
            <ul>
                <% managed_table_names = data_managers.managed_data_tables.keys() %>
                %for table_name in sorted( tool_data_tables.get_tables().keys() ):
                    <li>
                        <a href="${h.url_for( controller='data_manager', action='manage_data_table', table_name=table_name)}" target="galaxy_main">
                            %if table_name in managed_table_names:
                                </span><strong>${ table_name | h }</strong></a> <span class="fa fa-exchange">
                            %else:
                                ${ table_name | h }</a>
                            %endif
                    </li>
                    <p/>
                %endfor
            </ul>
            </div>
        </li>
        <p/>
    </ul>
    <p/>
    <br/>
%endif

${render_msg( 'To find out more information about Data Managers, please visit the <a href="https://wiki.galaxyproject.org/Admin/Tools/DataManagers" target="_blank">wiki.</a>', "info" ) }
