<%inherit file="/base.mako"/>

<h2>Public access via link</h2>

<p>
    %if stored.importable:
    
        Anyone can import this workflow into their history via the following URL:
        <% url = h.url_for( action='imp', id=trans.security.encode_id(stored.id), qualified=True ) %>
        <blockquote>
            <a href="${url}">${url}</a>
        </blockquote>
        <br>
        
        <form action="${h.url_for( action='sharing', id=trans.security.encode_id(stored.id) )}" method="POST">
            <input class="action-button" type="submit" name="disable_import_via_link" value="Disable import via link">
        </form>
    
    %else:
    
        This workflow is currently restricted (only you and the users listed below
        can access it). Enabling the following option will generate a URL that you
        can give to anyone to allow them to import this workflow.
        
        <br>
        
        <form action="${h.url_for( action='sharing', id=trans.security.encode_id(stored.id) )}" method="POST">
            <input class="action-button" type="submit" name="enable_import_via_link" value="Enable import via link">
        </form>
        
    %endif
</p>

<h2>Sharing with specific users</h2>

%if stored.users_shared_with:

    <p>
        The following users will see this workflow in thier workflow list, and be
        able to run it or create their own copy of it:
    </p>
    
        <ul class="manage-table-actions">
        <li>
            <a class="action-button" href="${h.url_for( action='share', id=trans.security.encode_id(stored.id) )}">
                <span>Share with another user</span>
            </a>
        </li>
    </ul>
        
    <table class="colored" border="0" cellspacing="0" cellpadding="0" width="100%">
        <tr class="header">
            <th>Email</th>
            <th></th>
        </tr>
        %for i, association in enumerate( stored.users_shared_with ):
            <% user = association.user %>
            <tr>
                <td>
                    ${user.email}
                    <a id="user-${i}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
                </td>
                <td>
                    <div popupmenu="user-${i}-popup">
                    <a class="action-button" href="${h.url_for( id=trans.security.encode_id( stored.id ), unshare_user=trans.security.encode_id( user.id ) )}">Unshare</a>
                    </div>
                </td>
            </tr>    
        %endfor
    </table>

%else:

    <p>You have not shared this workflow with any users.</p>
    
    <a class="action-button" href="${h.url_for( action='share', id=trans.security.encode_id(stored.id) )}">
        <span>Share with another user</span>
    </a>
    
%endif