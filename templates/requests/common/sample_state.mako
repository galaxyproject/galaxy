<%def name="render_sample_state( cntrller, sample )">
    <a href="${h.url_for( controller='requests_common', cntrller=cntrller, action='sample_events', sample_id=sample.id)}">${sample.current_state().name}</a>
</%def>

${render_sample_state( cntrller, sample )}
