<%inherit file="/base.mako"/>
<script>
    require(['mvc/tools/tools-form'], function(ToolsForm){
        $(function(){
            var form = new ToolsForm.View({
                id : '${tool.id}'
            });
        });
    });
</script>
