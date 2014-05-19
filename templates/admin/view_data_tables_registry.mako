<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if message:
    ${render_msg( message, status )}
%endif

<%
    ctr = 0
    sorted_data_tables = sorted( trans.app.tool_data_tables.get_tables().items() )
%>

<div class="toolForm">
    <div class="toolFormTitle">Current data table registry contains ${len( sorted_data_tables )} data tables</div>
    <div class="toolFormBody">
        <table class="manage-table colored" border="0" cellspacing="0" cellpadding="0" width="100%">
            <tr>
                <th bgcolor="#D8D8D8">Name</th>
                <th bgcolor="#D8D8D8">Filename</th>
                <th bgcolor="#D8D8D8">Tool data path</th>
                <th bgcolor="#D8D8D8">Errors</th>
            </tr>
            %for data_table_elem_name, data_table in sorted_data_tables:
                %if ctr % 2 == 1:
                    <tr class="odd_row">
                %else:
                    <tr class="tr">
                %endif
                    <td><a href="${ h.url_for( controller="data_manager", action="manage_data_table", table_name=data_table.name ) }">${data_table.name}</a></td>
                    %for i, ( filename, file_dict ) in enumerate( data_table.filenames.iteritems() ):
                        %if i > 0:
                            <tr><td></td>
                        %endif
                        <td>${ filename | h }</td>
                        <td>${ file_dict.get( 'tool_data_path' ) | h }</td>
                        <td>
                            %if not file_dict.get( 'found' ):
                                file missing
                            %endif
                            %for error in file_dict.get( 'errors', [] ):
                                ${ error | h } <br/>
                            %endfor
                        </td>
                        </tr>
                    %endfor
                <% ctr += 1 %>
            %endfor
        </table>
    </div>
</div>
