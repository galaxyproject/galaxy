<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Current datatypes registry contains ${len( trans.app.datatypes_registry.datatype_elems )} datatypes</div>
    <div class="toolFormBody">
        <table class="manage-table colored" border="0" cellspacing="0" cellpadding="0" width="100%">
            <tr>
                <th>Extension</th>
                <th>Type</th>
                <th>Mimetype</th>
                <th>Display in upload</th>
                <th>Datatype class</th>
            </tr>
            <% ctr = 0 %>
            %for elem in trans.app.datatypes_registry.datatype_elems:
                <%
                    import galaxy.util
                    extension = elem.get( 'extension', None )
                    dtype = elem.get( 'type', None )
                    type_extension = elem.get( 'type_extension', None )
                    mimetype = elem.get( 'mimetype', None )
                    display_in_upload = galaxy.util.string_as_bool( elem.get( 'display_in_upload', False ) )
                %>
                %if ctr % 2 == 1:
                    <tr class="odd_row">
                %else:
                    <tr class="tr">
                %endif
                    <td>${extension}</td>
                    <td>${dtype}</td>
                    <td>
                        %if mimetype:
                            ${mimetype}
                        %endif
                    </td>
                    <td>
                        %if display_in_upload:
                            ${display_in_upload}
                        %endif
                    </td>
                </tr>
                <% ctr += 1 %>
            %endfor
        </table>
    </div>
</div>
