<%inherit file="/base.mako"/>

${h.js("libs/bibtex", "libs/jquery/jquery-ui")}
${h.css('base', 'jquery-ui/smoothness/jquery-ui')}

<%
    ## TEMPORARY: create tool dictionary in mako while both tool forms are in use.
    ## This avoids making two separate requests since the classic form requires the mako anyway.
    params = dict(trans.request.params)
    params['__dataset_id__'] = params.get('id', None)
    params['__job_id__'] = params.get('job_id', None)
    self.form_config = tool.to_json(trans, params)
    self.form_config.update({
        'id'                : tool.id,
        'job_id'            : trans.security.encode_id( job.id ) if job else None,
        'history_id'        : trans.security.encode_id( trans.history.id )
    })
%>
<script>
    require(['mvc/tools/tools-form'], function(ToolsForm){
        $(function(){
            var form = new ToolsForm.View(${ h.dumps(self.form_config) });
            $('body').append(form.$el);
        });
    });
</script>