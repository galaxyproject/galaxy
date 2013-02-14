<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<%def name="title()">Data Table Manager: ${ data_table.name | h }</%def>

%if message:
    ${render_msg( message, status )}
%endif

%if view_only:
    <p>Not implemented</p>
%else:
<% column_name_list = data_table.get_column_name_list() %>
<table class="tabletip">
    <thead>
        <tr><th colspan="${len (column_name_list) }" style="font-size: 120%;">
            Data Manager: ${ data_table.name | h }
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
</table>

%endif
