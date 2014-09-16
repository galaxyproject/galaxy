<%def name="add_config_defaults( defaults )">
## overwrite default_config_dict with config (if any) then assign to config
<%
    for key, default in defaults.items():
        if key not in config or config[ key ] is None:
            config[ key ] = default
%>
</%def>

<%def name="config_form( config_dict )">
## render form for everything in possible config
</%def>

<%def name="link_to_change_config( link_contents, new_settings, target='' )">
<%
    # assumes there's a config var
    url_for_args = {
        'controller'            : 'visualization',
        'action'                : 'render',
        'visualization_name'    : visualization_name,
        'title'                 : title
    }
    url_for_args.update( config )
    url_for_args.update( new_settings )
    if visualization_id:
        url_for_args[ 'id' ] = visualization_id
%>
    <a href="${h.url_for( **url_for_args )}" target="${target}">${link_contents}</a>
</%def>

<%def name="save_button( text='Save' )">
<%
    # still a GET
    url_for_args = {
        'controller'    : 'visualization',
        'action'        : 'saved',
        'type'          : visualization_name,
        'title'         : title,
        'config'        : h.dumps( config )
    }
    # save to existing visualization
    if visualization_id:
        url_for_args[ 'id' ] = visualization_id
%>
    <form action="${h.url_for( **url_for_args )}" method="post"><input type="submit" value="${text}" /></form>
</%def>
