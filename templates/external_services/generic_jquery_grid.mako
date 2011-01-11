<%inherit file="/base.mako"/>
<%namespace file="json_common.mako" import="display_item" />

<%def name="display_json_grid_result( headers, rows )">
    <div class="form-row">
        <table class="grid">
            <thead>
                <tr>
                    %for name in headers:
                        <th>${name}</th>
                    %endfor
                    </tr>
                </thead>
                %for row in rows:
                    <tr>
                        %for name in headers:
                            <td>${display_item( row.get( name ) )}</td>
                        %endfor
                    </tr>
                %endfor
        </table>
    </div>
</%def>

<%def name="title()">${param_dict['service_instance'].name}: ${action.label}</%def>
<%
#print result
#HACK!!!! need to use better method of displaying jqGrid here, needs to allow paging as optionally available.
if 'Rows' in result: #paged
    records = result['Records']
    total = result['Total']
    rows = result['Rows']
    page = result['Page']
else:
    rows = result
    records = None
    total = None
    page = None
headers = rows[0].keys()
%>
%if records:
    <p>records: ${records}</p>
%endif
%if total:
    <p>total: ${total}</p>
%endif
%if page:
    <p>page: ${page}</p>
%endif

${display_json_grid_result( headers, rows )}
