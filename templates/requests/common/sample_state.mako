<%def name="render_sample_state( cntrller, sample )">
    <a href="${h.url_for( controller='requests_common', action='sample_events', cntrller=cntrller, sample_id=trans.security.encode_id( sample.id ) )}">${sample.state.name}</a>
</%def>

${render_sample_state( cntrller, sample )}
