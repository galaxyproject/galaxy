<%namespace file="/tracks/history_select_grid.mako" import="select_header" />
<%namespace file='/library/common/browse_library.mako' import="render_content, grid_javascripts" />

<%def name="title()">
    <h2>History '${grid.get_current_item( trans, **kwargs ).name}'</h2>
</%def>

${select_header()}
${grid_javascripts()}
${render_content(simple=True)}
<script type="text/javascript">
    make_popup_menus();
</script>