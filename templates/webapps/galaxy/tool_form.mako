<%inherit file="/base.mako"/>
${h.js("libs/bibtex", "libs/jquery/jquery-ui")}
${h.css('base', 'jquery-ui/smoothness/jquery-ui')}
<script>
    require(['mvc/tools/tools-form'], function(ToolsForm){
        $(function(){
            var form = new ToolsForm.View(${ h.dumps( tool.to_json( trans, dict( trans.request.params ) ) ) });
            $('body').append(form.$el);
        });
    });
</script>