<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<%def name="title()">Data Manager</%def>

%if message:
    ${render_msg( message, status )}
%endif

<h2>Data Manager</h2>

%if view_only:
    <p>Not implemented</p>
%else:
    <p>Choose your data managing option from below.</p>
    <ul>
        <li><strong>Access data managers</strong> - get data, build indexes, etc
            <p/>
            <ul>
            %for data_manager_id, data_manager in data_managers.data_managers.iteritems():
                <li>
                    <a href="${ h.url_for( 'tool_runner?tool_id=%s' % ( data_manager.tool.id ) ) }"><strong>${ data_manager.name | h }</strong></a> - ${ data_manager.description | h }
                </li>
                <p/>
            %endfor
            </ul>
        </li>
        <p/>
        <li><strong>View managed data by manager</strong>
            <p/>
            <ul>
                %for data_manager_id, data_manager in data_managers.data_managers.iteritems():
                    <li>
                        <a href="${h.url_for( controller='data_manager', action='manage_data_manager', id=data_manager_id)}" target="galaxy_main"><strong>${ data_manager.name | h }</strong></a> - ${ data_manager.description | h }</a>
                    </li>
                    <p/>
                %endfor
            </ul>
        </li>
        <p/>
        <p/>
        <li><strong>View managed data by Tool Data Table</strong>
            <p/>
            <ul>
                %for table_name, managers in data_managers.managed_data_tables.iteritems():
                    <li>
                        <a href="${h.url_for( controller='data_manager', action='manage_data_table', table_name=table_name)}" target="galaxy_main"><strong>${ table_name | h }</strong></a>
                    </li>
                    <p/>
                %endfor
            </ul>
        </li>
        <p/>
    </ul>
    <p/>
    <br/>
%endif
