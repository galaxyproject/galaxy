<%
    ## TEMPORARY: create tool dictionary in mako while both tool forms are in use.
    ## This avoids making two separate requests since the classic form requires the mako anyway.
    from galaxy.tools.parameters import params_to_incoming
    incoming = {}
    params_to_incoming( incoming, tool.inputs, module.state.inputs, trans.app )
    self.form_config = tool.to_json(trans, incoming, workflow_building_mode=True)
    self.form_config.update({
        'id'                : tool.id,
        'job_id'            : trans.security.encode_id( job.id ) if job else None,
        'history_id'        : trans.security.encode_id( trans.history.id ),
        'container'         : '#right-content'
    })
%>
${ h.dumps(self.form_config) }