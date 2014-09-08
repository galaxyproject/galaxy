<%inherit file="/base.mako"/>

<%
    # load tool help
    tool_help = ''
    if tool.help:
        if tool.has_multiple_pages:
            tool_help = tool.help_by_page[tool_state.page]
        else:
            tool_help = tool.help

        # Help is Mako template, so render using current static path.
        tool_help = tool_help.render( static_path=h.url_for( '/static' ), host_url=h.url_for('/', qualified=True) )

        # Convert to unicode to display non-ascii characters.
        if type( tool_help ) is not unicode:
            tool_help = unicode( tool_help, 'utf-8')
    endif

    # check if citations exist
    tool_citations = False
    if tool.citations:
        tool_citations = True

    # form configuration
    self.form_config = {
        'id'            : tool.id,
        'help'          : tool_help,
        'citations'     : tool_citations,
        'biostar_url'   : trans.app.config.biostar_url,
        'history_id'    : trans.security.encode_id( trans.history.id )
    }
%>
${h.js( "libs/bibtex", "libs/jquery/jquery-ui" )}
${h.css( 'base', 'jquery-ui/smoothness/jquery-ui')}
<script>
    require(['mvc/tools/tools-form'], function(ToolsForm){
        $(function(){
            var form = new ToolsForm.View(${ h.dumps(self.form_config) });
        });
    });
</script>

%if tool.tool_shed_repository:
    <% tool_url = tool.tool_shed_repository.get_sharable_url( tool.app ) %>
    %if tool_url:
        <br/>
        ${ render_msg( 'This tool was installed from a ToolShed, you may be able to find additional information by following this link: <a href="%s" target="_blank">%s</a>' % ( tool_url, tool_url ), 'info' ) }
    %endif
%endif
