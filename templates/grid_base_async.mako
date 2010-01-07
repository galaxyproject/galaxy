<%namespace file="./grid_base.mako" import="*" />

<%
    # Set flag to indicate whether grid has operations that operate on multiple items.
    multiple_item_ops_exist = False
    for operation in grid.operations:
        if operation.allow_multiple:
            multiple_item_ops_exist = True
%>

${render_grid_table_body_contents(multiple_item_ops_exist=multiple_item_ops_exist)}
*****
${num_pages}
*****
${render_grid_message()}