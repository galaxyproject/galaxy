<%def name="render_sample_state( sample )">
    <a href="${h.url_for( controller='requests_admin', action='show_events', sample_id=sample.id)}">${sample.current_state().name}</a>
</%def>

${render_sample_state( sample )}
