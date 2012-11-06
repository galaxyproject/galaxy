<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if message:
    ${render_msg( message, status )}
%endif

<%
    ctr = 0
    data_tables = trans.app.tool_data_tables
    sorted_data_table_elem_names = sorted( trans.app.tool_data_tables.data_table_elem_names )
%>

<div class="toolForm">
    <div class="toolFormTitle">Current data table registry contains ${len( sorted_data_table_elem_names )} data tables</div>
    <div class="toolFormBody">
        <table class="manage-table colored" border="0" cellspacing="0" cellpadding="0" width="100%">
            <tr>
                <th bgcolor="#D8D8D8">Name</th>
                <th bgcolor="#D8D8D8">Tool data path</th>
                <th bgcolor="#D8D8D8">Missing index file</th>
            </tr>
            %for data_table_elem_name in sorted_data_table_elem_names:
                <% data_table = data_tables[ data_table_elem_name ] %>
                %if ctr % 2 == 1:
                    <tr class="odd_row">
                %else:
                    <tr class="tr">
                %endif
                    <td>${data_table.name}</td>
                    <td>${data_table.tool_data_path}</td>
                    <td>
                        %if data_table.missing_index_file:
                            ${data_table.missing_index_file}
                        %endif
                    </td>
                </tr>
                <% ctr += 1 %>
            %endfor
        </table>
    </div>
</div>
