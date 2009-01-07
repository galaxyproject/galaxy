<%inherit file="/base.mako"/>
<%def name="title()">Your saved histories</%def>
    
<h1>History Options</h1>

%if not user:
<div class="infomessage">
    <div>You must be <a target="galaxy_main" href="${h.url_for( controller='user', action='login' )}">logged in</a> to store or switch histories.</div>
</div>
%endif

<ul>
%if user:
    <li><a href="${h.url_for( controller='root', action='history_rename', id=history.id )}" target="galaxy_main">Rename</a> current history (stored as "${history.name}")</li>
    <li><a href="${h.url_for( controller='root', action='history_available')}" target="galaxy_main">List</a> previously stored histories</li>
    %if len( history.active_datasets ) > 0:
        <li><a href="${h.url_for( controller='root', action='history_new' )}">Create</a> a new empty history</li>
    %endif
    <li><a href="${h.url_for( controller='workflow', action='build_from_current_history' )}">Construct workflow</a> from the current history</li>
    <li><a href="${h.url_for( controller='root', action='history_share' )}" target="galaxy_main">Share</a> current history</div>
    <li><a href="${h.url_for( action='history_set_default_permissions' )}">Change default permissions</a> for the current history</li>
%endif
    <li><a href="${h.url_for( controller='root', action='history', show_deleted=True)}" target="galaxy_history">Show deleted</a> datasets in history</li>
    <li><a href="${h.url_for( controller='root', action='history_delete', id=history.id )}" confirm="Are you sure you want to delete the current history?">Delete</a> current history</div>
</ul>

