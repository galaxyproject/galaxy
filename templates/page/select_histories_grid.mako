## Template generates a grid that enables user to select histories.
<%namespace file="../grid_base.mako" import="*" />

${javascripts()}
${stylesheets()}
${render_grid_header(False)}
${render_grid_table(show_item_checkboxes=True)}

## Initialize the grid.
<script type="text/javascript">
    init_grid_elements();
    init_grid_controls();
</script>
