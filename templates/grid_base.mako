<%!
    from galaxy.web.framework.helpers.grids import TextColumn
    import galaxy.util
    def inherit(context):
        if context.get('use_panels'):
            if context.get('webapp'):
                webapp = context.get('webapp')
            else:
                webapp = 'galaxy'
            return '/webapps/%s/base_panels.mako' % webapp
        else:
            return '/base.mako'
%>
<%inherit file="${inherit(context)}"/>
<%namespace file="/display_common.mako" import="render_message" />

<%def name="init()">
<%
    self.has_left_panel=False
    self.has_right_panel=False
    self.message_box_visible=False
    self.active_view="user"
    self.overlay_visible=False
%>
</%def>

##
## Override methods from base.mako and base_panels.mako
##

<%def name="center_panel()">
    ${self.grid_body( grid )}
</%def>

## Render the grid's basic elements. Each of these elements can be subclassed.
<%def name="body()">
    ${self.grid_body( grid )}
</%def>

## Because body() is special and always exists even if not explicitly defined,
## it's not possible to override body() in the topmost template in the chain.
## Because of this, override grid_body() instead.
<%def name="grid_body( grid )">
    ${self.make_grid( grid )}
</%def>

<%def name="title()">${grid.title}</%def>

<%def name="javascripts()">
   ${parent.javascripts()}
   ${self.grid_javascripts()}
</%def>

<%def name="grid_javascripts()">
    ${h.js("libs/jquery/jquery.autocomplete", "galaxy.autocom_tagging", "libs/jquery/jquery.rating", "galaxy.grids" )}
    <script type="text/javascript">
        ## TODO: Can this be moved into base.mako? Also, this is history-specific grid code.
        %if refresh_frames:
            %if 'masthead' in refresh_frames:            
                ## Refresh masthead == user changes (backward compatibility)
                if ( parent.user_changed ) {
                    %if trans.user:
                        parent.user_changed( "${trans.user.email}", ${int( app.config.is_admin_user( trans.user ) )} );
                    %else:
                        parent.user_changed( null, false );
                    %endif
                }
            %endif
            %if 'history' in refresh_frames:
                if ( parent.frames && parent.frames.galaxy_history ) {
                    parent.frames.galaxy_history.location.href="${h.url_for( controller='root', action='history')}";
                    if ( parent.force_right_panel ) {
                        parent.force_right_panel( 'show' );
                    }
                }
                else {
                    // TODO: redirecting to root should be done on the server side so that page
                    // does not have to load.
                     
                    // No history frame, so refresh to root to see history.
                    window.top.location.href = "${h.url_for( controller='root' )}";
                }
            %endif
            %if 'tools' in refresh_frames:
                if ( parent.frames && parent.frames.galaxy_tools ) {
                    parent.frames.galaxy_tools.location.href="${h.url_for( controller='root', action='tool_menu')}";
                    if ( parent.force_left_panel ) {
                        parent.force_left_panel( 'show' );
                    }
                }
            %endif
        %endif

        // Needed URLs for grid history searching.
        var history_tag_autocomplete_url = "${h.url_for( controller='tag', action='tag_autocomplete_data', item_class='History' )}",
            history_name_autocomplete_url = "${h.url_for( controller='history', action='name_autocomplete_data' )}";

        //
        // Create grid object.
        //

        // Operations that are async (AJAX) compatible.
        var async_ops = [];
        %for operation in [op for op in grid.operations if op.async_compatible]:
            async_ops.push('${operation.label.lower()}');
        %endfor

        // Filter values for categorical filters.
        var categorical_filters = {};
        %for column in grid.columns:
            %if column.filterable is not None and not isinstance( column, TextColumn ):
                var ${column.key}_filters = ${ h.to_json_string( dict([ (filter.label, filter.args) for filter in column.get_accepted_filters() ]) ) };
                categorical_filters['${column.key}'] = ${column.key}_filters;
            %endif
        %endfor

        /** Returns true if string denotes true. */
        var is_true = function(s) { return _.indexOf(['True', 'true', 't'], s) !== -1; };

        // Create grid.
        var grid = new Grid({
            url_base: '${h.url_for()}',
            async: is_true('${grid.use_async}'),
            async_ops: async_ops,
            categorical_filters: categorical_filters,
            filters: ${h.to_json_string( cur_filter_dict )},
            sort_key: '${sort_key}',
            show_item_checkboxes: is_true('${context.get('show_item_checkboxes', False)}'),
            cur_page: ${cur_page_num},
            num_pages: ${num_pages}
        });

        // Initialize grid objects on load.
        // FIXME: use a grid view object eventually.
        $(document).ready(function() {
            init_grid_elements();
            init_grid_controls();
            
            // Initialize text filters to select text on click and use normal font when user is typing.
            $('input[type=text]').each(function() {
                $(this).click(function() { $(this).select(); } )
                       .keyup(function () { $(this).css("font-style", "normal"); });
            });
        });
    </script>
</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    ${h.css( "autocomplete_tagging", "jquery.rating" )}
    <style>
        ## If page is displayed in panels, pad from edges for readability.
        %if context.get('use_panels'):
        div#center {
            padding: 10px;
        }
        %endif
    </style>
</%def>

##
## Custom grid methods.
##

<%namespace file="./grid_common.mako" import="*" />

<%def name="make_grid( grid )">
    <div class="loading-elt-overlay"></div>
    <table>
        <tr>
            <td width="75%">${self.render_grid_header( grid )}</td>
            <td></td>
            <td></td>
        </tr>
        <tr>
            <td width="100%" id="grid-message" valign="top">${render_message( message, status )}</td>
            <td></td>
            <td></td>
        </tr>
    </table>

    ${self.render_grid_table( grid, show_item_checkboxes )}
</%def>

<%def name="grid_title()">
    <h2>${grid.title}</h2>
</%def>

## Render grid header.
<%def name="render_grid_header( grid, render_title=True)">
    <div class="grid-header">
        %if render_title:
            ${self.grid_title()}
        %endif
    
        %if grid.global_actions:
            <ul class="manage-table-actions">
                %if len( grid.global_actions ) < 3:
                    %for action in grid.global_actions:
                        <li><a class="action-button" href="${h.url_for( **action.url_args )}">${action.label}</a></li>
                    %endfor
                %else:
                    <li><a class="action-button" id="action-8675309-popup" class="menubutton">Actions</a></li>
                    <div popupmenu="action-8675309-popup">
                        %for action in grid.global_actions:
                            <a class="action-button" href="${h.url_for( **action.url_args )}">${action.label}</a>
                        %endfor
                    </div>
                %endif
            </ul>
        %endif
    
        ${render_grid_filters( grid )}
    </div>
</%def>

## Render grid.
<%def name="render_grid_table( grid, show_item_checkboxes=False)">
    <%
        # Set flag to indicate whether grid has operations that operate on multiple items.
        multiple_item_ops_exist = False
        for operation in grid.operations:
            if operation.allow_multiple:
                multiple_item_ops_exist = True
                
        # Show checkboxes if flag is set or if multiple item ops exist.
        if show_item_checkboxes or multiple_item_ops_exist:
            show_item_checkboxes = True
    %>
    <form action="${url()}" method="post" onsubmit="return false;">
        <table id="grid-table" class="grid">
            <thead id="grid-table-header">
                <tr>
                    %if show_item_checkboxes:
                        <th>
                            %if query.count() > 0:
                                <input type="checkbox" id="check_all" name=select_all_checkbox value="true" onclick='check_all_items(1);'><input type="hidden" name=select_all_checkbox value="true">
                            %endif
                        </th>
                    %endif
                    %for column in grid.columns:
                        %if column.visible:
                            <%
                                href = ""
                                extra = ""
                                if column.sortable:
                                    if sort_key.endswith(column.key):
                                        if not sort_key.startswith("-"):
                                            href = url( sort=( "-" + column.key ) )
                                            extra = "&darr;"
                                        else:
                                            href = url( sort=( column.key ) )
                                            extra = "&uarr;"
                                    else:
                                        href = url( sort=column.key )
                            %>
                            <th\
                            id="${column.key}-header"
                            %if column.ncells > 1:
                                colspan="${column.ncells}"
                            %endif
                            >
                                %if href:
                                    <a href="${href}" class="sort-link" sort_key="${column.key}">${column.label}</a>
                                %else:
                                    ${column.label}
                                %endif
                                <span class="sort-arrow">${extra}</span>
                            </th>
                        %endif
                    %endfor
                    <th></th>
                </tr>
            </thead>
            <tbody id="grid-table-body">
                ${render_grid_table_body_contents( grid, show_item_checkboxes )}
            </tbody>
            <tfoot id="grid-table-footer">
                ${render_grid_table_footer_contents( grid, show_item_checkboxes )}
            </tfoot>
        </table>
    </form>
</%def>

## Render grid table body contents.
<%def name="render_grid_table_body_contents(grid, show_item_checkboxes=False)">
        <% num_rows_rendered = 0 %>
        %if query.count() == 0:
            ## No results.
            <tr><td colspan="100"><em>No Items</em></td></tr>
            <% num_rows_rendered = 1 %>
        %endif
        %for i, item in enumerate( query ):
            <% encoded_id = trans.security.encode_id( item.id ) %>
            <tr \
            %if current_item == item:
                class="current" \
            %endif
            > 
                ## Item selection column
                %if show_item_checkboxes:
                    <td style="width: 1.5em;">
                        <input type="checkbox" name="id" value="${encoded_id}" id="${encoded_id}" class="grid-row-select-checkbox" />
                    </td>
                %endif
                ## Data columns
                %for column in grid.columns:
                    %if column.visible:
                        <%
                            # Nowrap
                            nowrap = ""
                            if column.nowrap:
                              nowrap = 'style="white-space:nowrap;"'
                            # Link
                            link = column.get_link( trans, grid, item )
                            if link:
                                href = url( **link )
                            else:
                                href = None
                            # Value (coerced to list so we can loop)
                            value = column.get_value( trans, grid, item )
                            if column.ncells == 1:
                                value = [ value ]
                        %>
                        %for cellnum, v in enumerate( value ):
                            <%
                                id = ""
                                # Handle non-ascii chars.
                                if isinstance(v, str):
                                    v = unicode(v, 'utf-8')
                                # Attach popup menu?
                                if column.attach_popup and cellnum == 0:
                                    id = 'grid-%d-popup' % i
                                # Determine appropriate class
                                cls = ""
                                if column.attach_popup:
                                    cls = "menubutton"
                                    if href:
                                        cls += " split"

                            %>
                            <td ${nowrap}>
                            %if href:
                                %if len(grid.operations) != 0:
                                <div id="${id}" class="${cls}" style="float: left;">
                                %endif
                                    <a class="label" href="${href}">${v}</a>
                                %if len(grid.operations) != 0:
                                </div>
                                %endif
                            %else:
                                <div id="${id}" class="${cls}"><label id="${column.label_id_prefix}${encoded_id}" for="${encoded_id}">${v}</label></div>
                            %endif
                            </td>
                        %endfor
                    %endif
                %endfor
                ## Actions column
                <td>
                    <div popupmenu="grid-${i}-popup">
                        %for operation in grid.operations:
                            %if operation.allowed( item ) and operation.allow_popup:
                                <%
                                target = ""
                                if operation.target:
                                    target = "target='" + operation.target + "'"
                                %>
                                %if operation.confirm:
                                    <a class="action-button" ${target} confirm="${operation.confirm}" href="${ url( **operation.get_url_args( item ) ) }">${operation.label}</a>
                                %else:
                                    <a class="action-button" ${target} href="${ url( **operation.get_url_args( item ) ) }">${operation.label}</a>
                                %endif  
                            %endif
                        %endfor
                    </div>
                </td>
            </tr>
            <% num_rows_rendered += 1 %>
        %endfor
        ## Dummy rows to prevent table for moving too much.
        ##%if grid.use_paging:
        ##    %for i in range( num_rows_rendered , grid.num_rows_per_page ):
        ##        <tr><td colspan="1000">  </td></tr>
        ##    %endfor
        ##%endif
</%def>

## Render grid table footer contents.
<%def name="render_grid_table_footer_contents(grid, show_item_checkboxes=False)">
    ## Row for navigating among pages.
    <%namespace file="/display_common.mako" import="get_class_plural" />
    <% items_plural = get_class_plural( grid.model_class ).lower() %>
    %if grid.use_paging and num_pages > 1:
        <tr id="page-links-row">
            %if show_item_checkboxes:
                <td></td>
            %endif
            <td colspan="100">
                <span id='page-link-container'>
                    ## Page links. Show 10 pages around current page.
                    <%
                        #
                        # Set minimum & maximum page.
                        # 
                        page_link_range = num_page_links/2
                        
                        # First pass on min page.
                        min_page = cur_page_num - page_link_range
                        if min_page >= 1:
                            # Min page is fine.
                            min_offset = 0
                        else:
                            # Min page is too low.
                            min_page = 1
                            min_offset = page_link_range - ( cur_page_num - min_page )
                        
                        # Set max page.
                        max_range = page_link_range + min_offset
                        max_page = cur_page_num + max_range
                        if max_page <= num_pages:
                            # Max page is fine.
                            max_offset = 0
                        else:
                            # Max page is too high.
                            max_page = num_pages
                            # +1 to account for the +1 in the loop below.
                            max_offset = max_range - ( max_page + 1 - cur_page_num )
                        
                        # Second and final pass on min page to add any unused 
                        # offset from max to min.
                        if max_offset != 0:
                            min_page -= max_offset
                            if min_page < 1:
                                min_page = 1
                    %>
                    Page:
                    % if min_page > 1:
                        <span class='page-link' id="page-link-1"><a href="${url( page=1 )}" page_num="1">1</a></span> ...
                    % endif
                    %for page_index in range(min_page, max_page + 1):
                        %if page_index == cur_page_num:
                            <span class='page-link inactive-link' id="page-link-${page_index}">${page_index}</span>
                        %else:
                            <% args = { 'page' : page_index } %>
                            <span class='page-link' id="page-link-${page_index}"><a href="${url( args )}" page_num='${page_index}'>${page_index}</a></span>
                        %endif
                    %endfor
                    %if max_page < num_pages:
                        ...
                        <span class='page-link' id="page-link-${num_pages}"><a href="${url( page=num_pages )}" page_num="${num_pages}">${num_pages}</a></span>
                    %endif
                </span>
                
                ## Show all link
                <span class='page-link' id='show-all-link-span'> | <a href="${url( page='all' )}" page_num="all">Show All</a></span>
            </td>
        </tr>    
    %endif
    ## Grid operations for multiple items.
    %if show_item_checkboxes:
        <tr>
            <td></td>
            <td colspan="100">
                For <span class="grid-selected-count"></span> selected ${items_plural}:
                %for operation in grid.operations:
                    %if operation.allow_multiple:
                        <input type="submit" name="operation" value="${operation.label}" class="action-button">
                    %endif
                %endfor
            </td>
        </tr>
    %endif
    %if len([o for o in grid.operations if o.global_operation]) > 0:
    <tr>
        <td colspan="100">
            %for operation in grid.operations:
            %if operation.global_operation:
                <%
                    link = operation.global_operation()
                    href = url( **link )
                %>
                <a class="action-button" href="${href}">${operation.label}</a>
            %endif
            %endfor
        </td>
    </tr>
    %endif
</%def>

