<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/webapps/community/common/common.mako" import="*" />
<%namespace file="/webapps/community/repository/common.mako" import="render_clone_str" />

<%
    from galaxy.web.framework.helpers import time_ago
    is_admin = trans.user_is_admin()
    is_new = repository.is_new
    can_contact_owner = trans.user and trans.user != repository.user
    can_browse_contents = not is_new
    can_rate = trans.user and repository.user != trans.user
    can_manage = is_admin or trans.user == repository.user
    can_push = trans.app.security_agent.can_push( trans.user, repository )
    can_view_change_log = not is_new
    can_upload = can_push
    can_download = not is_new and ( not is_malicious or can_push )
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
            <a class="action-button" href="${h.url_for( controller='repository', action='manage_repository', id=trans.app.security.encode_id( repository.id ), changeset_revision=repository.tip )}">Manage repository</a>
        %else:
            <a class="action-button" href="${h.url_for( controller='repository', action='view_repository', id=trans.app.security.encode_id( repository.id ), changeset_revision=repository.tip, webapp='community' )}">View repository</a>
        %endif
        %if can_view_change_log:
            <a class="action-button" href="${h.url_for( controller='repository', action='view_changelog', id=trans.app.security.encode_id( repository.id ), webapp='community' )}">View change log</a>
        %endif
        %if can_rate:
            <a class="action-button" href="${h.url_for( controller='repository', action='rate_repository', id=trans.app.security.encode_id( repository.id ) )}">Rate repository</a>
        %endif
        %if can_browse_contents:
            <a class="action-button" href="${h.url_for( controller='repository', action='browse_repository', id=trans.app.security.encode_id( repository.id ), webapp='community' )}">${browse_label}</a>
        %endif
        %if can_contact_owner:
            <a class="action-button" href="${h.url_for( controller='repository', action='contact_owner', id=trans.security.encode_id( repository.id ), webapp='community' )}">Contact repository owner</a>
        %endif
        %if can_download:
            <a class="action-button" href="${h.url_for( controller='repository', action='download', repository_id=trans.app.security.encode_id( repository.id ), changeset_revision=repository.tip, file_type='gz' )}">Download as a .tar.gz file</a>
            <a class="action-button" href="${h.url_for( controller='repository', action='download', repository_id=trans.app.security.encode_id( repository.id ), changeset_revision=repository.tip, file_type='bz2' )}">Download as a .tar.bz2 file</a>
            <a class="action-button" href="${h.url_for( controller='repository', action='download', repository_id=trans.app.security.encode_id( repository.id ), changeset_revision=repository.tip, file_type='zip' )}">Download as a zip file</a>
        %endif
    </div>
</ul>

%if message:
    ${render_msg( message, status )}
%endif

%if can_download:
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
%endif
<div class="toolForm">
    <%
        if can_download:
            title_str = 'Changeset %s' % ctx
        else:
            title_str = '%s changeset %s' % ( repository.name, ctx )
    %>
    <div class="toolFormTitle">${title_str}</div>
    <div class="toolFormBody">
        <table class="grid">
            %if modified:
                <tr>
                    <td>
                        <b>modified:</b>
                        %for item in modified:
                            <br/><a href="#${item}">${item}</a>
                        %endfor
                    </td>
                </tr>
            %endif
            %if added:
                <tr>
                    <td>
                        <b>added:</b>
                        %for item in added:
                            <br/><a href="#${item}">${item}</a>
                        %endfor
                    </td>
                </tr>
            %endif
            %if removed:
                <tr>
                    <td>
                        <b>removed:</b>
                        %for item in removed:
                            <br/><a href="#${item}">${item}</a>
                        %endfor
                    </td>
                </tr>
            %endif
            %if deleted:
                <tr>
                    <td>
                        <b>deleted:</b>
                        %for item in deleted:
                            <br/><a href="#${item}">${item}</a>
                        %endfor
                    </td>
                </tr>
            %endif
            %if unknown:
                <tr>
                    <td>
                        <b>unknown:</b>
                        %for item in unknown:
                            <br/><a href="#${item}">${item}</a>
                        %endfor
                    }</td>
                </tr>
            %endif
            %if ignored:
                <tr>
                    <td>
                        <b>ignored:</b>
                        %for item in ignored:
                            <br/><a href="#${item}">${item}</a>
                        %endfor
                    </td>
                </tr>
            %endif
            %if clean:
                <tr>
                    <td>
                        clean:
                        %for item in clean:
                            <br/><a href="#${item}">${item}</a>
                        %endfor
                    </td>
                </tr>
            %endif
            %for diff in diffs:
                <%
                    # Read at most the first 10 lines of diff to determine the anchor
                    ctr = 0
                    lines = diff.split( '\n' )
                    diff = diff.replace( '\n', '<br/>' )
                    anchor_str = ''
                    for line in lines:
                        if ctr > 9:
                            break
                        for anchor in anchors:
                            if line.find( anchor ) >= 0:
                                anchor_str = '<a name="%s">%s</a>' % ( anchor, anchor )
                                break
                        ctr += 1
                %>
                <tr><td bgcolor="#E0E0E0">${anchor_str}</td></tr>
                <tr><td>${diff}</td></tr>
            %endfor
        </table>
    </div>
</div>
