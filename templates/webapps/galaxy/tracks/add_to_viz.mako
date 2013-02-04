## Template generates a grid that enables user to add tracks
<%namespace file="../grid_base.mako" import="*" />

${stylesheets()}
${grid_javascripts()}
${render_grid_header( grid, False )}
${render_grid_table( grid, show_item_checkboxes=True )}

