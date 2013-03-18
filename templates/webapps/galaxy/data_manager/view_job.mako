<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<% from galaxy.util import nice_size %>

<%def name="title()">Data Manager: ${ data_manager.name | h } - ${ data_manager.description | h }</%def>

%if message:
    ${render_msg( message, status )}
%endif

%if view_only:
    <p>Not implemented</p>
%else:
%for i, hda in enumerate( hdas ):
<table class="tabletip">
    <thead>
        <tr><th colspan="2" style="font-size: 120%;">
            Data Manager: ${ data_manager.name | h } - ${ data_manager.description | h }
        </th></tr>
    </thead>
    <tbody>
        <tr><td>Name:</td><td>${hda.name | h}</td></tr>
        <tr><td>Created:</td><td>${hda.create_time.strftime("%b %d, %Y")}</td></tr>
        <tr><td>Filesize:</td><td>${nice_size(hda.dataset.file_size)}</td></tr>
        <tr><td>Tool Exit Code:</td><td>${job.exit_code | h}</td></tr>
        <tr><td>Full Path:</td><td>${hda.file_name | h}</td></tr>
        <tr><td>View complete info:</td><td><a href="${h.url_for( controller='dataset', action='show_params', dataset_id=trans.security.encode_id( hda.id ))}">${ hda.id | h }</a></td></tr>
        
</table>
<br />

<% json_tables = data_manager_output[i]%>
%for table_name, json_table in json_tables: 
<table class="tabletip">
    <thead>
        <tr><th colspan="2" style="font-size: 120%;">
            Data Table: ${ table_name | h }
        </th></tr>
    </thead>
    <% len_json_table = len( json_table ) %>
        %for j, table_row in enumerate( json_table ):
        <tbody>
        %if len_json_table > 1:
        <tr><td><strong>Entry &#35;${j}</strong></td><td> </td></tr>
        %endif
        %for name, value in table_row.iteritems():
        <tr><td>${name | h}:</td><td>${value | h}</td></tr>
        %endfor
        %endfor
        </tbody>
</table>
<br />
%endfor

%endfor

%endif
