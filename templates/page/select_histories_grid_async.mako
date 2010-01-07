<%namespace file="../grid_base.mako" import="*" />

## Always show item checkboxes so that users can select histories.
${render_grid_table_body_contents(show_item_checkboxes=True)}
*****
${num_pages}
*****
${render_grid_message()}