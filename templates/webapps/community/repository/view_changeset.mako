<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/webapps/community/common/common.mako" import="*" />
<%namespace file="/webapps/community/repository/common.mako" import="render_clone_str" />

<%
    from galaxy.web.framework.helpers import time_ago
    is_new = repository.is_new
    can_browse_contents = not is_new
    can_rate = repository.user != trans.user
    can_manage = trans.user == repository.user
    can_push = trans.app.security_agent.can_push( trans.user, repository )
    can_view_change_log = not is_new
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
        %if can_view_change_log:
            <a class="action-button" href="${h.url_for( controller='repository', action='view_changelog', id=trans.app.security.encode_id( repository.id ) )}">View change log</a>
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
    <div class="toolFormTitle">Changeset ${ctx}</div>
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
                    # Read the first line of diff
                    line = diff.split( '\n' )[0]
                    diff = diff.replace( '\n', '<br/>' )
                    anchor_str = ''
                    for anchor in anchors:
                        if line.find( anchor ) >= 0:
                            anchor_str = '<a name="%s">%s</a>' % ( anchor, anchor )
                            break
                %>
                <tr><td bgcolor="#E0E0E0">${anchor_str}</td></tr>
                <tr><td>${diff}</td></tr>
            %endfor
        </table>
    </div>
</div>
