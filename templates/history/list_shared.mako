<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if msg:
    ${render_msg( msg, messagetype )}
%endif

%if shared_by_others:
    <table class="colored" border="0" cellspacing="0" cellpadding="0" width="100%">
        <tr class="header">
            <th>Name</th>
            <th>Owner</th>
        </tr>
        %for i, association in enumerate( shared_by_others ):
            <% history = association.history %>
            <tr>
                <td>
                    ${history.name}
                    <a id="shared-${i}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
                    <div popupmenu="shared-${i}-popup">
                        <a class="action-button" href="${h.url_for( controller='history', action='clone', id=trans.security.encode_id( history.id ) )}">Clone</a>
                    </div>
                </td>
                <td>${history.user.email}</td>
            </tr>    
        %endfor
    </table>
%else:
    No histories have been shared with you.
%endif
