## Template generates a grid that enables user to add tracks
<%namespace file="../grid_base.mako" import="*" />

${stylesheets()}
${grid_javascripts()}

${render_grid_table( grid, show_item_checkboxes=True )}

## Initialize the grid.
<script type="text/javascript">
    init_grid_elements();
    init_grid_controls();
</script>
