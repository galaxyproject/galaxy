<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/dataset/security_common.mako" import="render_permission_form" />

<%
    from galaxy import util

    roles = trans.sa_session.query( trans.app.model.Role ) \
                            .filter( trans.app.model.Role.table.c.deleted==False ) \
                            .order_by( trans.app.model.Role.table.c.name )
    if len( lddas ) > 1:
        name_str = '%d selected datasets' % len( lddas )
    else:
        ldda = lddas[0]
        name_str = ldda.name
%>

<br/><br/>
<ul class="manage-table-actions">
    <li>
        <a class="action-button" href="${h.url_for( controller='library_common', action='browse_library', cntrller=cntrller, id=library_id )}"><span>Browse this data library</span></a>
    </li>
</ul>

%if msg:
    ${render_msg( msg, messagetype )}
%endif

%if len( lddas ) > 1:
    <div class="toolFormTitle">Manage the following selected datasets</div>
    <p/>
    <table cellspacing="0" cellpadding="5" border="0" width="100%" class="libraryTitle">
        %for ldd_assoc in lddas:
            <tr>
                <td>
                    <div class="rowTitle">
                        <span class="historyItemTitle"><b>${ldd_assoc.name}</b></span>
                        <a id="ldda-${ldd_assoc.id}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
                    </div>
                    <div popupmenu="ldd_assoc-${ldd_assoc.id}-popup">
                        <a class="action-button" href="${h.url_for( controller='library_common', action='library_dataset_info', id=trans.security.encode_id( ldd_assoc.library_dataset_id ), library_id=library_id )}">Manage this dataset's versions</a>
                    </div>
                </td>
                <td>
                    %if ldd_assoc == ldd_assoc.library_dataset.library_dataset_dataset_association:
                        <i>This is the latest version of this library dataset</i>
                    %else:
                        <font color="red"><i>This is an expired version of this library dataset</i></font>
                    %endif
                </td>
            </tr>
        %endfor
    </table>
    <p/>
%else:
    %if ldda == ldda.library_dataset.library_dataset_dataset_association:
        <b><i>This is the latest version of this library dataset</i></b>
    %else:
        <font color="red"><b><i>This is an expired version of this library dataset</i></b></font>
    %endif
    <p/>
%endif

<% ldda_ids = ",".join( [ trans.security.encode_id( d.id ) for d in lddas ] ) %>
${render_permission_form( lddas[0], name_str, h.url_for( controller='library_common', action='ldda_permissions', cntrller=cntrller, library_id=library_id, folder_id=trans.security.encode_id( lddas[0].library_dataset.folder.id ), id=ldda_ids ), roles )}
