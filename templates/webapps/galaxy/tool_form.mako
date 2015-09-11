<%inherit file="/base.mako"/>

${h.js("libs/bibtex", "libs/jquery/jquery-ui")}
${h.css('base', 'jquery-ui/smoothness/jquery-ui')}

<%
    ## TEMPORARY: create tool dictionary in mako while both tool forms are in use.
    ## This avoids making two separate requests since the classic form requires the mako anyway.
    self.form_config = tool.to_json(trans, dict(trans.request.params))
%>
<script>
    require(['mvc/tools/tools-form'], function(ToolsForm){
        $(function(){
            var form = new ToolsForm.View(${ h.dumps(self.form_config) });
            $('body').append(form.$el);
        });
    });
</script>