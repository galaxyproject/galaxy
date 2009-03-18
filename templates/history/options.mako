<% _=n_ %>
<%inherit file="/base.mako"/>
<%def name="title()">Your saved histories</%def>
    
<h1>${_('History Options')}</h1>

%if not user:
<div class="infomessage">
    <div>${_('You must be ')}<a target="galaxy_main" href="${h.url_for( controller='user', action='login' )}">${_('logged in')}</a>${_(' to store or switch histories.')}</div>
</div>
%endif

<ul>
%if user:
    <li><a href="${h.url_for( controller='root', action='history_rename', id=history.id )}" target="galaxy_main">${_('Rename')}</a>${_(' current history (stored as "%s")') % history.name}</li>
    <li><a href="${h.url_for( controller='root', action='history_available')}" target="galaxy_main">${_('List')}</a>${_(' previously stored histories')}</li>
    %if len( history.active_datasets ) > 0:
        <li><a href="${h.url_for( controller='root', action='history_new' )}">${_('Create')}</a>${_(' a new empty history')}</li>
    %endif
    <li><a href="${h.url_for( controller='workflow', action='build_from_current_history' )}">${_('Construct workflow')}</a>${_(' from the current history')}</li>
    <li><a href="${h.url_for( controller='root', action='history_share' )}" target="galaxy_main">${_('Share')}</a>${_(' current history')}</div>
%endif
    <li><a href="${h.url_for( controller='root', action='history', show_deleted=True)}" target="galaxy_history">${_('Show deleted')}</a>${_(' datasets in history')}</li>
    <li><a href="${h.url_for( controller='root', action='history_delete', id=history.id )}" confirm="${_('Are you sure you want to delete the current history?')}">${_('Delete')}</a>${_(' current history')}</div>
</ul>

