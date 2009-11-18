<%!
    from galaxy.web.framework.helpers.grids import TextColumn
    from galaxy.model import History, HistoryDatasetAssociation, User, Role, Group
    import galaxy.util
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
        <div class="${message_type}message transient-message">${util.restore_text( message )}</div>
        <div style="clear: both"></div>
    </p>
%endif

${self.render_grid_header()}
${self.render_grid_table()}

## Function definitions.

<%def name="title()">${grid.title}</%def>

<%def name="javascripts()">
    ${parent.javascripts()}
    ${h.js("jquery.autocomplete", "autocomplete_tagging" )}
    <script type="text/javascript">        
        ## TODO: generalize and move into galaxy.base.js
        $(document).ready(function() {
            // Initialize grid elements.
            init_grid_elements();
            
            // Operations that are not async (AJAX) compatible.
            var no_async_ops = new Object();
            %for operation in grid.operations:
                %if not operation.async_compatible:
                    no_async_ops['${operation.label}'] = "True";
                %endif
            %endfor
            
            // Initialize each operation button to do operation when clicked.
            $('input[name=operation]:submit').each(function() {
                $(this).click( function() {
                   var this_value = $(this).attr("value");
                   var no_async = ( no_async_ops[this_value] != undefined && no_async_ops[this_value] != null);
                   do_operation(this_value, no_async); 
                });
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
        
        //
        // Code to handle grid operations: filtering, sorting, paging, and operations.
        //
        
        // Initialize grid elements.
        function init_grid_elements() 
        {
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
        }
        
        // Filter values for categorical filters.
        var categorical_filters = new Object();
        %for column in grid.columns:
            %if column.filterable is not None and not isinstance( column, TextColumn ):
                var ${column.key}_filters =
                {
                %for i, filter in enumerate( column.get_accepted_filters() ):
                    %if i > 0:
                        ,
                    %endif
                    ${filter.label} : ${h.to_json_string( filter.args )}
                %endfor
                };
                categorical_filters['${column.key}'] = ${column.key}_filters;
            %endif
        %endfor
            
        // Initialize URL args with filter arguments.
        var url_args = ${h.to_json_string( cur_filter_dict )};
        
        // Place "f-" in front of all filter arguments.
        var arg;
        for (arg in url_args)
        {
            value = url_args[arg];
            delete url_args[arg];
            url_args["f-" + arg] = value;
        }
        
        // Add sort argument to URL args.
        url_args['sort'] = "${encoded_sort_key}";
        
        // Add async keyword to URL args.
        url_args['async'] = true;
        
        // Add tag to grid filter.
        function add_tag_to_grid_filter(tag_name, tag_value)
        {
            // Put tag name and value together.
            var tag = tag_name + (tag_value != null && tag_value != "" ? ":" + tag_value : "");
            add_filter_condition("tags", tag, true);         
        }
        
        // Add a condition to the grid filter; this adds the condition and refreshes the grid.
        function add_filter_condition(name, value, append)
        {
            // Update URL arg with new condition.            
            if (append)
            {
                // Update or append value.
                var cur_val = url_args["f-" + name];
                var new_val;
                if (cur_val == null || cur_val == undefined)
                {
                    new_val = value;
                }
                else if (typeof(cur_val) == "string")
                {
                    if (cur_val == "All")
                        new_val = value;
                    else
                    {
                        // Replace string with array.
                        var values = new Array();
                        values[0] = cur_val;
                        values[1] = value;
                        new_val = values;   
                    }
                }
                else {
                    // Current value is an array.
                    new_val = cur_val;
                    new_val[new_val.length] = value;
                }
                url_args["f-" + name] = new_val;
            }
            else
            {
                // Replace value.
                url_args["f-" + name] = value;
            }
            
            // Add button that displays filter and provides a button to delete it.
            var t = $("<span>" + value +
                      "&nbsp;<a href='#'><img src='${h.url_for('/static/images/delete_tag_icon_gray.png')}'/></a></span>");
            t.addClass('text-filter-val');
            t.click(function() {
                //
                // Remove filter condition.
                //
                
                // TODO: remove element.
                //var tag_button = $(this).parent();
                $(this).remove();
                
                // Remove condition from URL args.
                var cur_val = url_args["f-" + name];
                if (cur_val == null || cur_val == undefined)
                {
                    // Unexpected. Throw error?
                }
                else if (typeof(cur_val) == "string")
                {
                    if (cur_val == "All") 
                    {
                        // Unexpected. Throw error?
                    }        
                    else
                        // Remove condition.
                        delete url_args["f-" + name];
                }
                else {
                    // Current value is an array.
                    var conditions = cur_val;
                    var index;
                    for (index = 0; index < conditions.length; index++)
                        if (conditions[index] == value)
                        {
                            conditions.splice(index, 1);
                            break;
                        }   
                }

                update_grid();
            });
            
            var container = $('#' + name + "-filtering-criteria");
            container.append(t);
            
            update_grid();
        }
        
        // Set sort condition for grid.
        function set_sort_condition(col_key)
        {
            // Set new sort condition. New sort is col_key if sorting new column; if reversing sort on
            // currently sorted column, sort is reversed.
            var cur_sort = url_args['sort'];
            var new_sort = col_key;
            if ( cur_sort.indexOf( col_key ) != -1)
            {                
                // Reverse sort.
                if ( cur_sort.substring(0,1) != '-' )
                    new_sort = '-' + col_key;
                else
                { 
                    // Sort reversed by using just col_key.
                }
            }
            
            // Remove sort arrows elements.
            $('.sort-arrow').remove()
            
            // Add sort arrow element to new sort column.
            var sort_arrow = "&uarr;";
            if (new_sort.substring(0,1) != '-')
                sort_arrow = "&darr;";
            var t = $("<span>" + sort_arrow + "</span>").addClass('sort-arrow');
            var th = $("#" + col_key + '-header');
            th.append(t);
            
            // Update grid.
            url_args['sort'] = new_sort;
            update_grid();
        }
        
        // Set new value for categorical filter.
        function set_categorical_filter(this_obj, name, new_value)
        {
            // Update filter hyperlinks to reflect new filter value.
            var category_filter = categorical_filters[name];
            var cur_value = url_args["f-" + name];
            $("." + name + "-filter").each( function() {
                var text = $(this).text().trim();
                var filter = category_filter[text];
                var filter_value = filter[name];
                if (filter_value == new_value)
                {
                    // Remove filter link since grid will be using this filter. It is assumed that
                    // this element has a single child, a hyperlink/anchor with text.
                    $(this).empty();
                    $(this).append("<span style='font-style: italic'>" + text + "</span>");
                }
                else if (filter_value == cur_value)
                {
                    // Add hyperlink for this filter since grid will no longer be using this filter. It is assumed that
                    // this element has a single child, a hyperlink/anchor.
                    $(this).empty();
                    var t = $("<a href='#'>" + text + "</a>");
                    t.click(function() {
                        set_categorical_filter( $(this), name, filter_value ); 
                    });
                    $(this).append(t);
                }
            });
            
            // Need to go back to page 1 if not showing all.
            var cur_page = url_args['page'];
            if (cur_page != null && cur_page != undefined && cur_page != 'all')
                url_args['page'] = 1;
                        
            // Update grid.
            url_args["f-" + name] = new_value;
            update_grid();
        }
        
        var num_pages = ${num_pages};
        url_args['page'] = 1;
        // Set page to view.
        function set_page(new_page)
        {
            // Update page hyperlink to reflect new page.
            $(".page-link").each( function() {
               var id = $(this).attr('id');
               var page_num = parseInt( id.split("-")[2] ); // Id has form 'page-link-<page_num>
               var cur_page = url_args['page'];
               if (page_num == new_page)
               {
                   // Remove link to page since grid will be on this page. It is assumed that
                   // this element has a single child, a hyperlink/anchor with text.
                   var text = $(this).children().text();
                   $(this).empty();
                   $(this).addClass("inactive-link");
                   $(this).text(text);
               }
               else if (page_num == cur_page)
               {
                   // Add hyperlink to this page since grid will no longer be on this page. It is assumed that
                   // this element has a single child, a hyperlink/anchor.
                   var text = $(this).text();
                   $(this).empty();
                   $(this).removeClass("inactive-link");
                   var t = $("<a href='#'>" + text + "</a>");
                   t.click(function() {
                      set_page(page_num); 
                   });
                   $(this).append(t);
               }
            });

            
            if (new_page == "all")
            {
                url_args['page'] = new_page;
                $('#page-links-row').hide('slow');
            }
            else
            {
                url_args['page'] = parseInt(new_page);
            }
            update_grid(true);
        }
        
        // Perform a grid operation. TODO: this is not complete.
        function do_operation(operation, no_async)
        {
            // For some reason, $('input[name=id]:checked').val() does not return all ids for checked boxes.
            // The code below performs this function.
            var item_ids = new Array()
            $('input[name=id]:checked').each(function() {
                item_ids[item_ids.length] = $(this).val();
            });

            // Update URL args.
            url_args['operation'] = operation;
            url_args['id'] = item_ids;
            
            // If operation cannot be performed asynchronously, redirect to location. Otherwise do operation.
            if (no_async)
            {
                var arg_str = "";
                var arg;
                
                for (arg in url_args)
                    arg_str = arg_str + arg + "=" + url_args[arg] + "&";
                
                self.location = encodeURI( "${h.url_for()}?" + arg_str );
            }
            else
                update_grid();
            
        }
        
        // Update grid.
        function update_grid(maintain_page_links)
        {
            // If there's an operation in the args, do POST; otherwise, do GET.
            var operation = url_args['operation'];
            var method = (operation != null && operation != undefined ? "POST" : "GET" );
            $.ajax({
                type: method,
                url: "${h.url_for()}",
                data: url_args,
                error: function() { alert( "Grid refresh failed" ) },
                success: function(response_text) {
                    // HACK: use a simple string to separate the two elements in the
                    // response: (1) table body and (2) number of pages in table.
                    var parsed_response_text = response_text.split("*****");
                    
                    // Update grid body.
                    var table_body = parsed_response_text[0];
                    $('#grid-table-body').html(table_body);
                    
                    // Process grid body.
                    init_grid_elements();
                    make_popup_menus();
                    
                    // Update pages.
                    var num_pages = parseInt( parsed_response_text[1] );
                    
                    // Rebuild page links.
                    if (!maintain_page_links)
                    {
                        var page_link_container = $('#page-link-container');
                        page_link_container.children().remove();
                        if (num_pages > 1)
                        {
                            // Show page link row.
                            $('#page-links-row').show();
                        
                            // First page is the current page.
                            var t = $("<span>1</span>");
                            t.addClass('page-link');
                            t.addClass('inactive-link');
                            t.attr('id', 'page-link-1');
                            page_link_container.append(t);
                
                            // Subsequent pages are navigable.
                            for (var i = 2; i <= num_pages; i++)
                            {
                                var span = $("<span></span>");
                                span.addClass('page-link');
                                span.attr('id', 'page-link-' + i);
                                var t = $("<a href='#'>" + i + "</a>");
                                var page_num = i
                                t.click(function() {
                                    set_page(page_num);
                                });
                                span.append(t)
                                page_link_container.append(span);
                            }
                        }
                        else 
                        {
                            // Hide page link row.
                            $('#page-links-row').hide('slow');
                        }
                    }        
                }
            });    
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
        .text-filter-val {
            border: solid 1px #AAAAAA;
            padding: 1px 3px 1px 3px;
            margin-right: 5px;
            -moz-border-radius: .5em;
            -webkit-border-radius: .5em;
            font-style: italic;
        }
        .page-link a, .inactive-link {
            padding: 0px 7px 0px 7px;
        }
        .inactive-link {
            font-style: italic;
        }
    </style>
</%def>

<%namespace file="./grid_common_async.mako" import="*" />

## Print grid header.
<%def name="render_grid_header(include_title)">
    <div class="grid-header">
        %if include_title:
            <h2>${grid.title}</h2>
        %endif
    
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
<%def name="render_grid_table()">
    <form action="${url()}" method="post" onsubmit="return false;">
        <table class="grid">
            <thead id="grid-table-header">
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
                            id="${column.key}-header"
                            %if column.ncells > 1:
                                colspan="${column.ncells}"
                            %endif
                            >
                                %if href:
                                    <a href="${href}" onclick="set_sort_condition('${column.key}');return false;">${column.label}</a>
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
                ${render_grid_table_body_contents()}
            </tbody>
            <tfoot id="grid-table-footer">
                ${render_grid_table_footer_contents()}
            </tfoot>
        </table>
    </form>        
</%def>

<%def name="render_grid_table_body_contents()">
        %if query.count() == 0:
            ## No results.
            <tr><td></td><td><em>No Items</em></td></tr>
        %endif
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
                                <a class="action-button" ${target} href="${ url( **operation.get_url_args( item ) ) }">${operation.label}</a>  
                            %endif
                        %endfor
                    </div>
                </td>
            </tr>
        %endfor
</%def>

<%def name="render_grid_table_footer_contents()">
    ## Row for navigating among pages.
    <%
        # Mapping between item class and plural term for item.
        items_plural = "items"
        if grid.model_class == History:
            items_plural = "histories"
        elif grid.model_class == HistoryDatasetAssociation:
             items_plural = "datasets"
        elif grid.model_class == User:
            items_plural = "users"
        elif grid.model_class == Role:
            items_plural = "roles"
        elif grid.model_class == Group:
            items_plural = "groups"
    %>
    %if num_pages > 1:
        <tr id="page-links-row">
            <td></td>
            <td colspan="100">
                <span id='page-link-container'>
                    ## Page links.
                    Page:
                    %for page_index in range(1, num_pages + 1):
                        %if page_index == cur_page_num:
                            <span class='page-link inactive-link' id="page-link-${page_index}">${page_index}</span>
                        %else:
                            <% args = { 'page' : page_index } %>
                            <span class='page-link' id="page-link-${page_index}"><a href="${url( args )}" onclick="set_page('${page_index}'); return false;">${page_index}</a></span>
                        %endif
                    %endfor
                </span>
                
                ## Show all link.
                <% args = { "page" : "all" } %>
                <span id='show-all-link'>| <a href="${url( args )}" onclick="set_page('all');return false;">Show all ${items_plural} on one page</a></span>
            </td>
        </tr>    
    %endif
    ## Grid operations.
    %if grid.operations:
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
</%def>

