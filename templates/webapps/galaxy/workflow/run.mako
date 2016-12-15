<%inherit file="/base.mako"/>
${h.js("libs/bibtex", "libs/jquery/jquery-ui")}
${h.css('jquery-ui/smoothness/jquery-ui')}
<script>
    require(['mvc/tool/tool-form-composite'], function( ToolForm ) {
        $(function() {
            var form = new ToolForm.View(${ h.dumps( workflow_dict ) });
        });
    });
</script>