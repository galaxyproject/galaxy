<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<%
    is_admin = trans.user_is_admin()
    is_new = repository.is_new
    can_contact_owner = trans.user and trans.user != repository.user
    can_push = trans.app.security_agent.can_push( trans.user, repository )
    can_upload = can_push
    can_download = not is_new and ( not is_malicious or can_push )
    can_browse_contents = not is_new
    can_rate = repository.user != trans.user
    can_manage = is_admin or repository.user == trans.user
    can_view_change_log = not is_new
    if can_push:
        browse_label = 'Browse or delete repository tip files'
    else:
        browse_label = 'Browse repository tip files'
%>

<%!
   def inherit(context):
       if context.get('use_panels'):
           return '/webapps/community/base_panels.mako'
       else:
           return '/base.mako'
%>
<%inherit file="${inherit(context)}"/>

<br/><br/>
<ul class="manage-table-actions">
    %if is_new and can_upload:
        <a class="action-button" href="${h.url_for( controller='upload', action='upload', repository_id=trans.security.encode_id( repository.id ), webapp='community' )}">Upload files to repository</a>
    %else:
        <li><a class="action-button" id="repository-${repository.id}-popup" class="menubutton">Repository Actions</a></li>
        <div popupmenu="repository-${repository.id}-popup">
            %if can_manage:
                <a class="action-button" href="${h.url_for( controller='repository', action='manage_repository', id=trans.app.security.encode_id( repository.id ) )}">Manage repository</a>
            %else:
                <a class="action-button" href="${h.url_for( controller='repository', action='view_repository', id=trans.app.security.encode_id( repository.id ), webapp='community' )}">View repository</a>
            %endif
            %if can_upload:
                <a class="action-button" href="${h.url_for( controller='upload', action='upload', repository_id=trans.security.encode_id( repository.id ), webapp='community' )}">Upload files to repository</a>
            %endif
            %if can_view_change_log:
                <a class="action-button" href="${h.url_for( controller='repository', action='view_changelog', id=trans.app.security.encode_id( repository.id ), webapp='community' )}">View change log</a>
            %endif
            %if can_browse_contents:
                <a class="action-button" href="${h.url_for( controller='repository', action='browse_repository', id=trans.app.security.encode_id( repository.id ), webapp='community' )}">${browse_label}</a>
            %endif
            %if can_download:
                <a class="action-button" href="${h.url_for( controller='repository', action='download', repository_id=trans.app.security.encode_id( repository.id ), changeset_revision=repository.tip, file_type='gz' )}">Download as a .tar.gz file</a>
                <a class="action-button" href="${h.url_for( controller='repository', action='download', repository_id=trans.app.security.encode_id( repository.id ), changeset_revision=repository.tip, file_type='bz2' )}">Download as a .tar.bz2 file</a>
                <a class="action-button" href="${h.url_for( controller='repository', action='download', repository_id=trans.app.security.encode_id( repository.id ), changeset_revision=repository.tip, file_type='zip' )}">Download as a zip file</a>
            %endif
        </div>
    %endif
</ul>

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Contact the owner of the repository named '${repository.name}'</div>
    <div class="toolFormBody">
        <div class="form-row">
            This feature is intended to streamline appropriate communication between
            Galaxy tool developers and those in the Galaxy community that use them.
            Please don't send messages unnecessarily.
        </div>
        <form name="send_to_owner" id="send_to_owner" action="${h.url_for( controller='repository', action='send_to_owner', id=trans.security.encode_id( repository.id ) )}" method="post" >
            <div class="form-row">
                <label>Message:</label>
                <textarea name="message" rows="10" cols="40"></textarea>
            </div>
            <div class="form-row">
                <input type="submit" value="Send to owner"/>
            </div>
        </form>
    </div>
</div>
