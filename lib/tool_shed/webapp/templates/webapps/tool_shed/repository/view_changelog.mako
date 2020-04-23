<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/webapps/tool_shed/common/common.mako" import="*" />
<%namespace file="/webapps/tool_shed/repository/common.mako" import="render_clone_str" />
<%namespace file="/webapps/tool_shed/common/repository_actions_menu.mako" import="render_tool_shed_repository_actions" />

<%
    is_new = repository.is_new()
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
        if can_download:
            title_str = 'Changesets'
        else:
            title_str = '%s changesets' % repository.name
    %>
    <div class="toolFormTitle">${title_str | h}</div>
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
                    if changeset[ 'has_metadata' ]:
                        has_metadata_str = '<table border="0"><tr><td  bgcolor="#D8D8D8">Repository metadata is associated with this change set.</td></tr></table>'
                    else:
                        has_metadata_str = ''
                    display_date = changeset[ 'display_date' ]
                %>
                %if test_date != display_date:
                    <tr colspan="2"><td bgcolor="#D8D8D8">${display_date}</td></tr>
                %endif
                <tr>
                    <td>
                        %if has_metadata_str:
                            <div class="form-row">
                                ${has_metadata_str}
                            </div>
                        %endif
                        <div class="form-row">
                            <label>Description:</label>
                            <a href="${h.url_for( controller='repository', action='view_changeset', id=trans.security.encode_id( repository.id ), ctx_str=ctx_str )}">${ util.unicodify( changeset[ 'description' ] ) | h}</a>
                        </div>
                        <div class="form-row">
                            <label>Commit:</label>
                            <a href="${h.url_for( controller='repository', action='view_changeset', id=trans.security.encode_id( repository.id ), ctx_str=ctx_str )}">${changeset_str | h}</a>
                        </div>
                        <div class="form-row">
                            <label>Parent:</label>
                            %if ctx_parent_str == 'None':
                                ${ctx_parent_str}
                            %else:
                                <a href="${h.url_for( controller='repository', action='view_changeset', id=trans.security.encode_id( repository.id ), ctx_str=ctx_parent )}">${ctx_parent_str | h}</a>
                            %endif
                        </div>
                        <div class="form-row">
                            <label>Commited by:</label>
                            ${changeset[ 'user' ].split()[0] | h}
                        </div>
                        <div class="form-row">
                            <label>Pushed:</label>
                            ${changeset[ 'display_date' ]}
                        </div>
                    </td>
                </tr>
            %endfor
        </table>
    </div>
</div>
