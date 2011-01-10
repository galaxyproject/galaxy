<%namespace file="./grid_base.mako" import="*" />
<%namespace file="/display_common.mako" import="render_message" />

<%
    # Set flag to indicate whether grid has operations that operate on multiple items.
    multiple_item_ops_exist = False
    for operation in grid.operations:
        if operation.allow_multiple:
            multiple_item_ops_exist = True
%>

${render_grid_table_body_contents( grid, show_item_checkboxes=( show_item_checkboxes or multiple_item_ops_exist ) )}
*****
${render_grid_table_footer_contents( grid, show_item_checkboxes=( show_item_checkboxes or multiple_item_ops_exist ) )}
*****
${render_message( message, status )}