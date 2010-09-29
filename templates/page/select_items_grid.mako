## Template generates a grid that enables user to select items.
<%namespace file="../grid_base.mako" import="*" />

${javascripts()}
${stylesheets()}
${render_grid_header( grid, False )}
${render_grid_table( grid, show_item_checkboxes=True )}
