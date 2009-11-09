<%!
    from galaxy.model import History, HistoryDatasetAssociation
    def inherit(context):
        if context.get('use_panels'):
            return '/base_panels.mako'
        else:
            return '/base.mako'
%>
<%inherit file="${inherit(context)}"/>

## Render the grid's basic elements. Each of these elements can be subclassed.
%if message:
    <p>
        <div class="${message_type}message transient-message">${message}</div>
        <div style="clear: both"></div>
    </p>
%endif

${self.grid_header()}
${self.grid_table()}

## Function definitions.

<%def name="title()">${grid.title}</%def>

<%def name="javascripts()">
    ${parent.javascripts()}
    ${h.js("jquery.autocomplete", "autocomplete_tagging" )}
    <script type="text/javascript">        
        ## TODO: generalize and move into galaxy.base.js
        $(document).ready(function() {
            // Initialize grid elements.
            $(".grid").each( function() {
                var grid = this;
                var checkboxes = $(this).find("input.grid-row-select-checkbox");
                var update = $(this).find( "span.grid-selected-count" );
                $(checkboxes).each( function() {
                    $(this).change( function() {
                        var n = $(checkboxes).filter("[checked]").size();
                        update.text( n );
                    });
                })
            });
            
            // Initialize autocomplete for text inputs in search UI.
            var t = $("#input-tags-filter");
            if (t.length)
            {
                        
                var autocomplete_options = 
                    { selectFirst: false, autoFill: false, highlight: false, mustMatch: false };

                t.autocomplete("${h.url_for( controller='tag', action='tag_autocomplete_data', item_class='History' )}", autocomplete_options);
            }      
            
            var t2 = $("#input-name-filter");
            if (t2.length)
            {
                var autocomplete_options = 
                    { selectFirst: false, autoFill: false, highlight: false, mustMatch: false };

                t2.autocomplete("${h.url_for( controller='history', action='name_autocomplete_data' )}", autocomplete_options);
            }
        });
        ## Can this be moved into base.mako?
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
        
        // Filter and sort args for grid.
        var filter_args = ${h.to_json_string(cur_filter_dict)};
        var sort_key = "${sort_key}";
        
        //
        // Add tag to grid filter.
        //
        function add_tag_to_grid_filter(tag_name, tag_value)
        {
            // Put tag name and value together.
            var tag = tag_name + (tag_value != null && tag_value != "" ? ":" + tag_value : "");
            add_condition_to_grid_filter("tags", tag, true);         
        }
        
        //
        // Add a filter to the current grid filter; this adds the filter and then issues a request to refresh the grid.
        //
        function add_condition_to_grid_filter(name, value, append)
        {
            // Update filter arg with new condition.            
            if (append)
            {
                // Append value.
                var cur_val = filter_args[name];
                if (cur_val != "All")
                    cur_val = cur_val + ", " + value;
                else
                    cur_val = value;
                filter_args[name] = cur_val;
            }
            else
            {
                // Replace value.
                filter_args[name] = value;
            }
            
            // Build URL with filter args, sort key.
            var filter_arg_value_strs = new Array();
            var i = 0;
            for (arg in filter_args)
            {
                filter_arg_value_strs[i++] = "f-" + arg + "=" + filter_args[arg];
            }
            var filter_str = filter_arg_value_strs.join("&");
            var url_base = "${h.url_for( action='list')}";
            var url = url_base + "?" + filter_str + "&sort=" + sort_key;
            self.location = url;
        }
        
        //
        // Initiate navigation when user selects a page to view.
        //
        function navigate_to_page(page_select)
        {
            page_num = $(page_select).val();
            <% url_args = {"page" : "PAGE"} %>
            var url_base = "${url( url_args )}";
            var url = url_base.replace("PAGE", page_num);
            self.location = url;
        }
    </script>
</%def>

<%def name="stylesheets()">
    ${h.css( "base", "autocomplete_tagging" )}
    <style>
        ## Not generic to all grids -- move to base?
        .count-box {
            min-width: 1.1em;
            padding: 5px;
            border-width: 1px;
            border-style: solid;
            text-align: center;
            display: inline-block;
        }
    </style>
</%def>

<%namespace file="./grid_common.mako" import="*" />

## Print grid header.
<%def name="grid_header()">
    <div class="grid-header">
        <h2>${grid.title}</h2>
    
        %if grid.global_actions:
            <ul class="manage-table-actions">
            %for action in grid.global_actions:
                <li>
                    <a class="action-button" href="${h.url_for( **action.url_args )}">${action.label}</a>
                </li>
            %endfor
            </ul>
        %endif
    
        ${render_grid_filters()}
    </div>
</%def>

## Print grid.
<%def name="grid_table()">
    <form action="${url()}" method="post" >
        <table class="grid">
            <thead>
                <tr>
                    <th></th>
                    %for column in grid.columns:
                        %if column.visible:
                            <%
                                href = ""
                                extra = ""
                                if column.sortable:
                                    if sort_key == column.key:
                                        if sort_order == "asc":
                                            href = url( sort=( "-" + column.key ) )
                                            extra = "&darr;"
                                        else:
                                            href = url( sort=( column.key ) )
                                            extra = "&uarr;"
                                    else:
                                        href = url( sort=column.key )
                            %>
                            <th\
                            %if column.ncells > 1:
                                colspan="${column.ncells}"
                            %endif
                            >
                                %if href:
                                    <a href="${href}">${column.label}</a>
                                %else:
                                    ${column.label}
                                %endif
                                <span>${extra}</span>
                            </th>
                        %endif
                    %endfor
                    <th></th>
                </tr>
            </thead>
            <tbody>
                %for i, item in enumerate( query ):
                    <tr \
                    %if current_item == item:
                        class="current" \
                    %endif
                    > 
                        ## Item selection column
                        <td style="width: 1.5em;">
                            <input type="checkbox" name="id" value=${trans.security.encode_id( item.id )} class="grid-row-select-checkbox" />
                        </td>
                        ## Data columns
                        %for column in grid.columns:
                            %if column.visible:
                                <%
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
                                        # Handle non-ascii chars.
                                        if isinstance(v, str):
                                            v = unicode(v, 'utf-8')
                                        # Attach popup menu?
                                        if column.attach_popup and cellnum == 0:
                                            extra = '<a id="grid-%d-popup" class="arrow" style="display: none;"><span>&#9660;</span></a>' % i
                                        else:
                                            extra = ""
                                    %>
                                    %if href:                    
                                        <td><div class="menubutton split" style="float: left;"><a class="label" href="${href}">${v}</a>${extra}</td>
                                    %else:
                                        <td >${v}${extra}</td>
                                    %endif
                                %endfor
                            %endif
                        %endfor
                        ## Actions column
                        <td>
                            <div popupmenu="grid-${i}-popup">
                                %for operation in grid.operations:
                                    %if operation.allowed( item ):
                                        <%
                                        target = ""
                                        if operation.target:
                                            target = "target='" + operation.target + "'"
                                        %>
                                        <a class="action-button" ${target} href="${url( operation=operation.label, id=item.id )}">${operation.label}</a>  
                                    %endif
                                %endfor
                            </div>
                        </td>
                    </tr>
                %endfor
            </tbody>
            <tfoot>
            ## Row for navigating among pages.
            %if num_pages > 1:
                <tr>
                    <td></td>
                    <td colspan="100">
                        Page ${cur_page_num} of ${num_pages} 
                        &nbsp;&nbsp;&nbsp;&nbsp;Go to: 
                        ## Next page link.
                        %if cur_page_num != num_pages:
                            <% args = { "page" : cur_page_num+1 } %>
                            <span><a href="${url( args )}">Next</a></span>
                        %endif
                        ## Previous page link.
                        %if cur_page_num != 1:
                            <span>|</span>
                            <% args = { "page" : cur_page_num-1 } %>
                            <span><a href="${url( args )}">Previous</a></span>
                        %endif
                        ## Go to page select box.
                        <span>| Select:</span>
                        <select id="page-select" onchange="navigate_to_page(this)">
                            <option value=""></option>
                            %for page_index in range(1, num_pages + 1):
                                %if page_index == cur_page_num:
                                    continue
                                %else:
                                    <% args = { "page" : page_index } %>
                                    <option value='${page_index}'>Page ${page_index}</option>
                                %endif
                            %endfor
                        </select>
                        ## Show all link.
                        <% args = { "page" : "all" } %>
                        <span>| <a href="${url( args )}">Show all histories on one page</a></span>
                    </td>
                </tr>    
            %endif
                <tr>
                    ## Grid operations.
                    <td></td>
                    <td colspan="100">
                        <%
                            # Mapping between item class and plural term for item.
                            plural = "items"
                            if grid.model_class == History:
                                plural = "histories"
                            elif grid.model_class == HistoryDatasetAssociation:
                                 plural = "datasets"
                        %>
                        For <span class="grid-selected-count"></span> selected ${plural}:
                        %for operation in grid.operations:
                            %if operation.allow_multiple:
                                <input type="submit" name="operation" value="${operation.label}" class="action-button">
                            %endif
                        %endfor
                    </td>
                </tr>
            </tfoot>
        </table>
    </form>
</%def>