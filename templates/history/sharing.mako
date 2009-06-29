<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<h2>Public access via link</h2>

%if msg:
    ${render_msg( msg, messagetype )}
%endif

%for history in histories:
    <p>
        %if history.importable:
            Send the following URL to users as an easy way for them to import the history, making a copy of their own:
            <% url = h.url_for( controller='history', action='imp', id=trans.security.encode_id(history.id), qualified=True ) %>
            <blockquote>
                <a href="${url}">${url}</a>
            </blockquote>
            <br/>
            <form action="${h.url_for( controller='history', action='sharing', id=trans.security.encode_id( history.id ) )}" method="POST">
                <input class="action-button" type="submit" name="disable_import_via_link" value="Disable import via link">
            </form>
        %else:
            This history is currently restricted (only you and the users listed below
            can access it). Enabling the following option will generate a URL that you
            can give to a user to allow them to import this history.
            <br/>
            <form action="${h.url_for( action='sharing', id=trans.security.encode_id(history.id) )}" method="POST">
                <input class="action-button" type="submit" name="enable_import_via_link" value="Enable import via link">
            </form>
        %endif
    </p>
    <h2>Sharing with specific users</h2>
    %if history.users_shared_with:
        <ul class="manage-table-actions">
            <li>
                <a class="action-button" href="${h.url_for( controller='history', action='share', id=trans.security.encode_id( history.id ) )}">
                    <span>Share with another user</span>
                </a>
            </li>
        </ul>
        <p>
            The following users will see this history in their list of histories 
            shared with them by others, and they will be able to create their own copy of it:
        </p>
        <table class="colored" border="0" cellspacing="0" cellpadding="0" width="100%">
            <tr class="header">
                <th>History '${history.name}' currently shared with</th>
                <th></th>
            </tr>
            %for i, association in enumerate( history.users_shared_with ):
                <% user = association.user %>
                <tr>
                    <td>
                        ${user.email}
                        <a id="user-${i}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
                    </td>
                    <td>
                        %if len( histories ) == 1:
                            ## Only allow unsharing if we're dealing with 1 history, otherwise
                            ## page refreshes screw things up
                            <div popupmenu="user-${i}-popup">
                                <a class="action-button" href="${h.url_for( controller='history', action='sharing', id=trans.security.encode_id( history.id ), unshare_user=trans.security.encode_id( user.id ) )}">Unshare</a>
                            </div>
                        %endif
                    </td>
                </tr>    
            %endfor
        </table>
    %else:
        <p>You have not shared this history with any users.</p>
        <a class="action-button" href="${h.url_for( controller='history', action='share', id=trans.security.encode_id(history.id) )}">
            <span>Share with another user</span>
        </a>
    %endif
%endfor
