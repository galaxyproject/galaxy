<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/webapps/community/common/common.mako" import="*" />
<%namespace file="/webapps/community/repository/common.mako" import="render_clone_str" />

<%
    from galaxy.web.framework.helpers import time_ago
    is_admin = trans.user_is_admin()
    is_new = repository.is_new
    can_browse_contents = not is_new
    can_manage = is_admin or trans.user == repository.user
    can_push = trans.app.security_agent.can_push( trans.user, repository )
    can_rate = trans.user and repository.user != trans.user
    can_upload = can_push
    if can_push:
        browse_label = 'Browse or delete repository files'
    else:
        browse_label = 'Browse repository files'
%>

<%!
   def inherit(context):
       if context.get('use_panels'):
           return '/webapps/community/base_panels.mako'
       else:
           return '/base.mako'
%>
<%inherit file="${inherit(context)}"/>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    ${h.css( "library" )}
</%def>

<%def name="javascripts()">
    ${parent.javascripts()}
    ${h.js( "jquery.rating" )}
</%def>

<br/><br/>
<ul class="manage-table-actions">
    <li><a class="action-button" id="repository-${repository.id}-popup" class="menubutton">Repository Actions</a></li>
    <div popupmenu="repository-${repository.id}-popup">
        %if can_upload:
            <a class="action-button" href="${h.url_for( controller='upload', action='upload', repository_id=trans.security.encode_id( repository.id ), webapp='community' )}">Upload files to repository</a>
        %endif
        %if can_manage:
            <a class="action-button" href="${h.url_for( controller='repository', action='manage_repository', id=trans.app.security.encode_id( repository.id ) )}">Manage repository</a>
        %else:
            <a class="action-button" href="${h.url_for( controller='repository', action='view_repository', id=trans.app.security.encode_id( repository.id ) )}">View repository</a>
        %endif
        %if can_rate:
            <a class="action-button" href="${h.url_for( controller='repository', action='rate_repository', id=trans.app.security.encode_id( repository.id ) )}">Rate repository</a>
        %endif
        %if can_browse_contents:
            <a class="action-button" href="${h.url_for( controller='repository', action='browse_repository', id=trans.app.security.encode_id( repository.id ) )}">${browse_label}</a>
        %endif
        <a class="action-button" href="${h.url_for( controller='repository', action='download', repository_id=trans.app.security.encode_id( repository.id ), file_type='gz' )}">Download as a .tar.gz file</a>
        <a class="action-button" href="${h.url_for( controller='repository', action='download', repository_id=trans.app.security.encode_id( repository.id ), file_type='bz2' )}">Download as a .tar.bz2 file</a>
        <a class="action-button" href="${h.url_for( controller='repository', action='download', repository_id=trans.app.security.encode_id( repository.id ), file_type='zip' )}">Download as a zip file</a>
    </div>
</ul>

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">${repository.name}</div>
    <div class="toolFormBody">
        <div class="form-row">
            <label>Clone this repository:</label>
            ${render_clone_str( repository )}
        </div>
    </div>
</div>
<p/>
<div class="toolForm">
    <div class="toolFormTitle">Changesets</div>
    <% test_date = None %>
    <div class="toolFormBody">
        <table class="grid">
            %for changeset in changesets:
                <%
                    ctx_str = str( changeset[ 'ctx' ] )
                    ctx_parent = str( changeset[ 'parent' ] )
                    ctx_parent_rev = changeset[ 'parent' ].rev()
                    test_date = changeset[ 'display_date' ]
                    changeset_str = "%s:%s" % ( changeset[ 'rev' ], ctx_str )
                    if ctx_parent_rev < 0:
                        ctx_parent_str = 'None'
                    else:
                        ctx_parent_str = "%s:%s" % ( ctx_parent_rev, ctx_parent )
                %>
                <% display_date = changeset[ 'display_date' ] %>
                %if test_date != display_date:
                    <tr colspan="2"><td bgcolor="#D8D8D8 ">${display_date}</td></tr>
                %endif
                <tr>
                    <td>
                        <div class="form-row">
                            <label>Description:</label>
                            <a href="${h.url_for( controller='repository', action='view_changeset', id=trans.security.encode_id( repository.id ), ctx_str=ctx_str )}">${changeset[ 'description' ]}</a>
                        </div>
                        <div class="form-row">
                            <label>Commit:</label>
                            <a href="${h.url_for( controller='repository', action='view_changeset', id=trans.security.encode_id( repository.id ), ctx_str=ctx_str )}">${changeset_str}</a>
                        </div>
                        <div class="form-row">
                            <label>Parent:</label>
                            %if ctx_parent_str == 'None':
                                ${ctx_parent_str}
                            %else:
                                <a href="${h.url_for( controller='repository', action='view_changeset', id=trans.security.encode_id( repository.id ), ctx_str=ctx_parent )}">${ctx_parent_str}</a>
                            %endif
                        </div>
                        <div class="form-row">
                            <label>Commited by:</label>
                            ${changeset[ 'user' ].split()[0]}
                        </div>
                        <div class="form-row">
                            <label>Pushed:</label>
                            ${time_ago( changeset[ 'date' ] )}
                        </div>
                    </td>
                </tr>
            %endfor
        </table>
    </div>
</div>
