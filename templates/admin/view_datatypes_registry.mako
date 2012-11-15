<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if message:
    ${render_msg( message, status )}
%endif

<%
    import galaxy.util
    from galaxy.web.base.controller import sort_by_attr, Datatype
    ctr = 0
    datatypes = []
    for elem in trans.app.datatypes_registry.datatype_elems:
        # Build a list of objects that can be sorted.
        extension = elem.get( 'extension', None )
        dtype = elem.get( 'type', None )
        type_extension = elem.get( 'type_extension', None )
        mimetype = elem.get( 'mimetype', None )
        display_in_upload = galaxy.util.string_as_bool( elem.get( 'display_in_upload', False ) )
        datatypes.append( Datatype( extension, dtype, type_extension, mimetype, display_in_upload ) )
    sorted_datatypes = sort_by_attr( datatypes, 'extension' )
%>

<div class="toolForm">
    <div class="toolFormTitle">Current data types registry contains ${len( sorted_datatypes )} data types</div>
    <div class="toolFormBody">
        <table class="manage-table colored" border="0" cellspacing="0" cellpadding="0" width="100%">
            <tr>
                <th bgcolor="#D8D8D8">Extension</th>
                <th bgcolor="#D8D8D8">Type</th>
                <th bgcolor="#D8D8D8">Mimetype</th>
                <th bgcolor="#D8D8D8">Display in upload</th>
            </tr>
            %for datatype in sorted_datatypes:
                %if ctr % 2 == 1:
                    <tr class="odd_row">
                %else:
                    <tr class="tr">
                %endif
                    <td>${datatype.extension}</td>
                    <td>${datatype.dtype}</td>
                    <td>
                        %if datatype.mimetype:
                            ${datatype.mimetype}
                        %endif
                    </td>
                    <td>
                        %if datatype.display_in_upload:
                            ${datatype.display_in_upload}
                        %endif
                    </td>
                </tr>
                <% ctr += 1 %>
            %endfor
        </table>
    </div>
</div>
