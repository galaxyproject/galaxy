<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<%def name="title()">Tool Data Table: ${ data_table.name | h }</%def>

%if message:
    ${render_msg( message, status )}
%endif

%if view_only:
    <p>Not implemented</p>
%else:
    <p>
        <% column_name_list = data_table.get_column_name_list() %>
        <table class="tabletip">
            <thead>
                <tr><th colspan="${len (column_name_list) }" style="font-size: 120%;">
                    Data Manager: ${ data_table.name | h }
                    <a class="icon-btn" href="${ h.url_for( controller="data_manager", action="reload_tool_data_tables", table_name=data_table.name ) }" title="Reload ${data_table.name} tool data table" data-placement="bottom">
                        <span class="fa fa-refresh"></span>
                    </a>
                </th></tr>
                <tr>

                %for name in column_name_list:
                    <th>${name | h}</th>
                %endfor
                </tr>
            </thead>
            <tbody>
                %for table_row in data_table.data:
                <tr>
                %for field in table_row:
                    <td>${field | h}</td>
                %endfor
                </tr>
                %endfor
            </tbody>
        </table>
    </p>
    %if not data_table.data:
        ${render_msg( "There are currently no entries in this Tool Data Table.", "warning" ) }
    %endif

%endif
