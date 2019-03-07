<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/webapps/tool_shed/common/common.mako" import="*" />
<%namespace file="/webapps/tool_shed/repository/common.mako" import="*" />
<%namespace file="/webapps/tool_shed/common/repository_actions_menu.mako" import="render_galaxy_repository_actions" />

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
    ${container_javascripts()}
</%def>

${render_galaxy_repository_actions( repository=repository )}

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Repository '${repository.name | h}'</div>
    <div class="toolFormBody">
        %if len( changeset_revision_select_field.options ) > 1:
            <form name="change_revision" id="change_revision" action="${h.url_for( controller='repository', action='preview_tools_in_changeset', repository_id=trans.security.encode_id( repository.id ) )}" method="post" >
                <div class="form-row">
                    <%
                        if changeset_revision == repository.tip( trans.app ):
                            tip_str = 'repository tip'
                        else:
                            tip_str = ''
                    %>
                    ${render_select(changeset_revision_select_field)} <i>${tip_str | h}</i>
                    <div class="toolParamHelp" style="clear: both;">
                        Select a revision to inspect and download versions of Galaxy utilities from this repository.
                    </div>
                </div>
            </form>
        %else:
            <div class="form-row">
                <label>Revision:</label>
                ${revision_label}
            </div>
        %endif
    </div>
</div>
<p/>
${render_repository_items( metadata, containers_dict, can_set_metadata=False, render_repository_actions_for='galaxy' )}
