<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/webapps/tool_shed/common/common.mako" import="*" />
<%namespace file="/webapps/tool_shed/repository/common.mako" import="render_clone_str" />
<%namespace file="/webapps/tool_shed/common/repository_actions_menu.mako" import="render_tool_shed_repository_actions" />

<%
    is_new = repository.is_new( trans.app )
    can_push = trans.app.security_agent.can_push( trans.app, trans.user, repository )
    can_download = not is_new and ( not is_malicious or can_push )
%>

<%!
   def inherit(context):
       if context.get('use_panels'):
           return '/webapps/tool_shed/base_panels.mako'
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
</%def>

${render_tool_shed_repository_actions( repository=repository, metadata=metadata )}

%if message:
    ${render_msg( message, status )}
%endif

%if can_download:
    <div class="toolForm">
        <div class="toolFormTitle">Repository '${repository.name | h}'</div>
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
        from tool_shed.util.hg_util import get_readable_ctx_date
        changeset_revision_date = get_readable_ctx_date( ctx )
        if can_download:
            title_str = 'Changeset <b>%s:%s</b> <i>(%s)</i>' % ( ctx.rev(), ctx, changeset_revision_date )
        else:
            title_str = '%s changeset <b>%s:%s</b> <i>(%s)</i>' % ( repository.name, ctx.rev(), ctx, changeset_revision_date )
    %>
    <div class="toolFormTitle">
        ${title_str}
    </div>
    <div class="toolFormBody">
        <table class="grid">
            %if prev or next:
                <tr>
                    <td>
                        %if prev:
                            <a class="action-button" href="${h.url_for( controller='repository', action='view_changeset', id=trans.security.encode_id( repository.id ), ctx_str=ctx_parent )}">Previous changeset ${prev}</a>
                        %endif
                        %if next:
                            <a class="action-button" href="${h.url_for( controller='repository', action='view_changeset', id=trans.security.encode_id( repository.id ), ctx_str=ctx_child )}">Next changeset ${next}</a>
                        %endif
                    </td>
                </tr>
            %endif
            <tr>
                <td class="preserve-text-breaks">
                    <b>Commit message:</b>
                    <br/>${ util.unicodify( ctx.description() ) | h}<br/>
                </td>
            </tr>
            %if modified:
                <tr>
                    <td>
                        <b>modified:</b>
                        %for item in modified:
                            <br/><a href="#${ util.unicodify( item ) }">${ util.unicodify( item ) | h}</a>
                        %endfor
                    </td>
                </tr>
            %endif
            %if added:
                <tr>
                    <td>
                        <b>added:</b>
                        %for item in added:
                            <br/><a href="#${ util.unicodify( item ) }">${ util.unicodify( item ) | h}</a>
                        %endfor
                    </td>
                </tr>
            %endif
            %if removed:
                <tr>
                    <td>
                        <b>removed:</b>
                        %for item in removed:
                            <br/><a href="#${ util.unicodify( item ) }">${ util.unicodify( item ) | h}</a>
                        %endfor
                    </td>
                </tr>
            %endif
            %if deleted:
                <tr>
                    <td>
                        <b>deleted:</b>
                        %for item in deleted:
                            <br/><a href="#${ util.unicodify( item ) }">${ util.unicodify( item ) | h}</a>
                        %endfor
                    </td>
                </tr>
            %endif
            %if unknown:
                <tr>
                    <td>
                        <b>unknown:</b>
                        %for item in unknown:
                            <br/><a href="#${ util.unicodify( item ) }">${ util.unicodify( item ) | h}</a>
                        %endfor
                    }</td>
                </tr>
            %endif
            %if ignored:
                <tr>
                    <td>
                        <b>ignored:</b>
                        %for item in ignored:
                            <br/><a href="#${ util.unicodify( item ) }">${ util.unicodify( item ) | h}</a>
                        %endfor
                    </td>
                </tr>
            %endif
            %if clean:
                <tr>
                    <td>
                        clean:
                        %for item in clean:
                            <br/><a href="#${ util.unicodify( item ) }">${ util.unicodify( item ) | h}</a>
                        %endfor
                    </td>
                </tr>
            %endif
            %for diff in diffs:
                <%
                    # Read at most the first 10 lines of diff to determine the anchor
                    ctr = 0
                    lines = diff.split( '\n' )
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
                <tr><td bgcolor="#E0E0E0">${ util.unicodify( anchor_str ) }</td></tr>
                <tr><td>${ util.unicodify( diff ) }</td></tr>
            %endfor
        </table>
    </div>
</div>
