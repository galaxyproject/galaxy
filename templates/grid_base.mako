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
    ${h.js("jquery.autocomplete", "autocomplete_tagging", "jquery.rating" )}
    <script type="text/javascript">
        // This is necessary so that, when nested arrays are used in ajax/post/get methods, square brackets ('[]') are
        // not appended to the identifier of a nested array.
        jQuery.ajaxSettings.traditional = true;
        
        ## TODO: generalize and move into galaxy.base.js
        $(document).ready(function() {
            init_grid_elements();
            init_grid_controls();
            
            // Initialize text filters to select text on click and use normal font when user is typing.
            $('input[type=text]').each(function() {
                $(this).click(function() { $(this).select(); } )
                       .keyup(function () { $(this).css("font-style", "normal"); })
            });
        });
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
                    // doesn't have to load.
                     
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
        
        //
        // Code to handle grid operations: filtering, sorting, paging, and operations.
        //
        
        // Operations that are async (AJAX) compatible.
        var async_ops = {};
        %for operation in [op for op in grid.operations if op.async_compatible]:
            async_ops['${operation.label.lower()}'] = "True";
        %endfor
        
        // Init operation buttons.
        function init_operation_buttons() {
            // Initialize operation buttons.
            $('input[name=operation]:submit').each(function() {
                $(this).click( function() {
                   var webapp = $("input[name=webapp]").attr("value");
                   var operation_name = $(this).val();
                   // For some reason, $('input[name=id]:checked').val() does not return all ids for checked boxes.
                   // The code below performs this function.
                   var item_ids = [];
                   $('input[name=id]:checked').each(function() {
                       item_ids.push( $(this).val() );
                   });
                   do_operation(webapp, operation_name, item_ids); 
                });
            });
        };
        
        // Initialize grid controls
        function init_grid_controls() {
            init_operation_buttons();    
            
            // Initialize submit image elements.
            $('.submit-image').each( function() {
                // On mousedown, add class to simulate click.
                $(this).mousedown( function() {
                   $(this).addClass('gray-background'); 
                });
                
                // On mouseup, add class to simulate click.
                $(this).mouseup( function() {
                   $(this).removeClass('gray-background'); 
                });
            });
            
            // Initialize sort links.
            $('.sort-link').each( function() {
                $(this).click( function() {
                   set_sort_condition( $(this).attr('sort_key') );
                   return false;
                });
            });
            
            // Initialize page links.
            $('.page-link > a').each( function() {
                $(this).click( function() {
                   set_page( $(this).attr('page_num') );
                   return false;
                });
            });

            // Initialize categorical filters.
            $('.categorical-filter > a').each( function() {
                $(this).click( function() {
                    set_categorical_filter( $(this).attr('filter_key'), $(this).attr('filter_val') );
                    return false;
                });
            });
            
            // Initialize text filters.
            $('.text-filter-form').each( function() {
                $(this).submit( function() {
                    var column_key = $(this).attr('column_key');
                    var text_input_obj = $('#input-' + column_key + '-filter');
                    var text_input = text_input_obj.val();
                    text_input_obj.val('');
                    add_filter_condition(column_key, text_input, true);
                    return false;
                });
            });
            
            // Initialize autocomplete for text inputs in search UI.
            var t = $("#input-tags-filter");
            if (t.length) {
                t.autocomplete(  "${h.url_for( controller='tag', action='tag_autocomplete_data', item_class='History' )}", 
                                 { selectFirst: false, autoFill: false, highlight: false, mustMatch: false });
            }
 
            var t2 = $("#input-name-filter");
            if (t2.length) {
                t2.autocomplete( "${h.url_for( controller='history', action='name_autocomplete_data' )}",
                                 { selectFirst: false, autoFill: false, highlight: false, mustMatch: false });
            }
            
            // Initialize standard, advanced search toggles.
            $('.advanced-search-toggle').each( function() {
                $(this).click( function() {
                    $("#standard-search").slideToggle('fast');
                    $('#advanced-search').slideToggle('fast');
                    return false;
                });
            });
        }
 
        // Initialize grid elements.
        function init_grid_elements() {
            // Initialize grid selection checkboxes.
            $(".grid").each( function() {
                var checkboxes = $(this).find("input.grid-row-select-checkbox");
                var check_count = $(this).find("span.grid-selected-count");
                var update_checked = function() {
                    check_count.text( $(checkboxes).filter(":checked").length );
                };
                
                $(checkboxes).each( function() {
                    $(this).change(update_checked);
                });
                update_checked();
            });
            
            // Initialize item labels.
            $(".label").each( function() {
                // If href has an operation in it, do operation when clicked. Otherwise do nothing.
                var href = $(this).attr('href');
                if ( href !== undefined && href.indexOf('operation=') != -1 ) {
                    $(this).click( function() {
                        do_operation_from_href( $(this).attr('href') );
                        return false;
                    });   
                }
            });
            
            // Initialize ratings.
            $('.community_rating_star').rating({});
            
            // Initialize item menu operations.
            make_popup_menus();
        }
        
        // Filter values for categorical filters.
        var categorical_filters = {};
        %for column in grid.columns:
            %if column.filterable is not None and not isinstance( column, TextColumn ):
                var ${column.key}_filters = ${ h.to_json_string( dict([ (filter.label, filter.args) for filter in column.get_accepted_filters() ]) ) };
                categorical_filters['${column.key}'] = ${column.key}_filters;
            %endif
        %endfor
            
        // Initialize URL args with filter arguments.
        var url_args_init = ${h.to_json_string( cur_filter_dict )},
            url_args = {};
        
        // Place "f-" in front of all filter arguments.
        
        for (arg in url_args_init) {
            url_args["f-" + arg] = url_args_init[arg];
        }
        
        // Add sort argument to URL args.
        url_args['sort'] = "${sort_key}";
        
        // Add show_item_checkboxes argument to URL args.
        url_args['show_item_checkboxes'] = ("${context.get('show_item_checkboxes', False)}" === "True");
        
        // Add async keyword to URL args.
        url_args['async'] = true;
        
        // Add page to URL args.
        url_args['page'] = ${cur_page_num};
        
        var num_pages = ${num_pages};
        
        // Go back to page one; this is useful when a filter is applied.
        function go_page_one() {
            // Need to go back to page 1 if not showing all.
            var cur_page = url_args['page'];
            if (cur_page !== null && cur_page !== undefined && cur_page != 'all') {
                url_args['page'] = 1;
            }               
        }
        
        // Add a condition to the grid filter; this adds the condition and refreshes the grid.
        function add_filter_condition(name, value, append) {
            // Do nothing is value is empty.
            if (value == "") {
                return false;
            }
            
            // Update URL arg with new condition.            
            if (append) {
                // Update or append value.
                var cur_val = url_args["f-" + name];
                var new_val;
                if (cur_val === null || cur_val === undefined) {
                    new_val = value;
                } else if (typeof(cur_val) == "string") {
                    if (cur_val == "All") {
                        new_val = value;
                    } else {
                        // Replace string with array.
                        var values = [];
                        values[0] = cur_val;
                        values[1] = value;
                        new_val = values;   
                    }
                } else {
                    // Current value is an array.
                    new_val = cur_val;
                    new_val[new_val.length] = value;
                }
                url_args["f-" + name] = new_val;
            } else {
                // Replace value.
                url_args["f-" + name] = value;
            }
            
            // Add button that displays filter and provides a button to delete it.
            var t = $("<span>" + value + "<a href='javascript:void(0);'><span class='delete-search-icon' /></a></span>");
            t.addClass('text-filter-val');
            t.click(function() {
                // Remove filter condition.
 
                // Remove visible element.
                $(this).remove();
                
                // Remove condition from URL args.
                var cur_val = url_args["f-" + name];
                if (cur_val === null || cur_val === undefined) {
                    // Unexpected. Throw error?
                } else if (typeof(cur_val) == "string") {
                    if (cur_val == "All") {
                        // Unexpected. Throw error?
                    } else {
                        // Remove condition.
                        delete url_args["f-" + name];
                    }
                } else {
                    // Current value is an array.
                    var conditions = cur_val;
                    for (var index = 0; index < conditions.length; index++) {
                        if (conditions[index] == value) {
                            conditions.splice(index, 1);
                            break;
                        }
                    }
                }
 
                go_page_one();
                update_grid();
            });
            
            var container = $('#' + name + "-filtering-criteria");
            container.append(t);
            
            go_page_one();
            update_grid();
        }
        
        // Add tag to grid filter.
        function add_tag_to_grid_filter(tag_name, tag_value) {
            // Put tag name and value together.
            var tag = tag_name + (tag_value !== undefined && tag_value != "" ? ":" + tag_value : "");
            $('#advanced-search').show('fast');
            add_filter_condition("tags", tag, true); 
        }
 
        // Set sort condition for grid.
        function set_sort_condition(col_key) {
            // Set new sort condition. New sort is col_key if sorting new column; if reversing sort on
            // currently sorted column, sort is reversed.
            var cur_sort = url_args['sort'];
            var new_sort = col_key;
            if ( cur_sort.indexOf( col_key ) != -1) {                
                // Reverse sort.
                if ( cur_sort.substring(0,1) != '-' ) {
                    new_sort = '-' + col_key;
                } else { 
                    // Sort reversed by using just col_key.
                }
            }
            
            // Remove sort arrows elements.
            $('.sort-arrow').remove();
            
            // Add sort arrow element to new sort column.
            var sort_arrow = (new_sort.substring(0,1) == '-') ? "&uarr;" : "&darr;";
            var t = $("<span>" + sort_arrow + "</span>").addClass('sort-arrow');
            var th = $("#" + col_key + '-header');
            th.append(t);
            
            // Need to go back to page 1 if not showing all.
            var cur_page = url_args['page'];
            if (cur_page !== null && cur_page !== undefined && cur_page != 'all') {
                url_args['page'] = 1;
            }
            // Update grid.
            url_args['sort'] = new_sort;
            go_page_one();
            update_grid();
        }
        
        // Set new value for categorical filter.
        function set_categorical_filter(name, new_value) {
            // Update filter hyperlinks to reflect new filter value.
            var category_filter = categorical_filters[name];
            var cur_value = url_args["f-" + name];
            $("." + name + "-filter").each( function() {
                var text = $.trim( $(this).text() );
                var filter = category_filter[text];
                var filter_value = filter[name];
                if (filter_value == new_value) {
                    // Remove filter link since grid will be using this filter. It is assumed that
                    // this element has a single child, a hyperlink/anchor with text.
                    $(this).empty();
                    $(this).addClass("current-filter");
                    $(this).append(text);
                } else if (filter_value == cur_value) {
                    // Add hyperlink for this filter since grid will no longer be using this filter. It is assumed that
                    // this element has a single child, a hyperlink/anchor.
                    $(this).empty();
                    var t = $("<a href='#'>" + text + "</a>");
                    t.click(function() {
                        set_categorical_filter( name, filter_value ); 
                    });
                    $(this).removeClass("current-filter");
                    $(this).append(t);
                }
            });
            
            // Update grid.
            url_args["f-" + name] = new_value;
            go_page_one();
            update_grid();
        }
        
        // Set page to view.
        function set_page(new_page) {
            // Update page hyperlink to reflect new page.
            $(".page-link").each( function() {
               var id = $(this).attr('id');
               var page_num = parseInt( id.split("-")[2] ); // Id has form 'page-link-<page_num>
               var cur_page = url_args['page'];
               if (page_num == new_page) {
                   // Remove link to page since grid will be on this page. It is assumed that
                   // this element has a single child, a hyperlink/anchor with text.
                   var text = $(this).children().text();
                   $(this).empty();
                   $(this).addClass("inactive-link");
                   $(this).text(text);
               } else if (page_num == cur_page) {
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
 
            var maintain_page_links = true;
            if (new_page == "all") {
                url_args['page'] = new_page;
                maintain_page_links = false;
            } else {
                url_args['page'] = parseInt(new_page);
            }
            update_grid(maintain_page_links);
        }
        
        // Perform a grid operation.
        function do_operation(webapp, operation, item_ids) {
            operation = operation.toLowerCase();
            
            // Update URL args.
            url_args["webapp"] = webapp;
            url_args["operation"] = operation;
            url_args["id"] = item_ids;
            
            // If operation cannot be performed asynchronously, redirect to location. Otherwise do operation.
            var no_async = ( async_ops[operation] === undefined || async_ops[operation] === null);
            if (no_async) {
                go_to_URL();
            } else {
                update_grid(true);
                delete url_args['webapp'];
                delete url_args['operation'];
                delete url_args['id'];
            }
        }
        
        // Perform a hyperlink click that initiates an operation. If there is no operation, ignore click.
        function do_operation_from_href(href) {
            // Get operation, id in hyperlink's href.
            var href_parts = href.split("?");
            if (href_parts.length > 1) {
                var href_parms_str = href_parts[1];
                var href_parms = href_parms_str.split("&");
                var operation = null;
                var id = -1;
                var webapp = 'galaxy';
                for (var index = 0; index < href_parms.length; index++) {
                    if (href_parms[index].indexOf('operation') != -1) {
                        // Found operation parm; get operation value. 
                        operation = href_parms[index].split('=')[1];
                    } else if (href_parms[index].indexOf('id') != -1) {
                        // Found id parm; get id value.
                        id = href_parms[index].split('=')[1];
                    } else if (href_parms[index].indexOf('webapp') != -1) {
                        // Found webapp parm; get webapp value.
                        webapp = href_parms[index].split('=')[1];
                    }
                }
                // Do operation.
                do_operation(webapp, operation, id);
                return false;
            }
        }
        
        // Navigate window to the URL defined by url_args. This method should be used to short-circuit grid AJAXing.
        function go_to_URL() {
            // Not async request.
            url_args['async'] = false;
            
            // Build argument string.
            var arg_str = "";
            for (var arg in url_args) {
                arg_str = arg_str + arg + "=" + url_args[arg] + "&";
            }
            
            // Go.
            window.location = encodeURI( "${h.url_for()}?" + arg_str );
        }
        
        // Update grid.
        function update_grid(maintain_page_links) {
            ## If grid is not using async, then go to URL.
            %if not grid.use_async:
                 go_to_URL();
                 return;
            %endif
            
            // If there's an operation in the args, do POST; otherwise, do GET.
            var operation = url_args['operation'];
            var method = (operation !== null && operation !== undefined ? "POST" : "GET" );
            $('.loading-elt-overlay').show(); // Show overlay to indicate loading and prevent user actions.
            $.ajax({
                type: method,
                url: "${h.url_for()}",
                data: url_args,
                error: function() { alert( "Grid refresh failed" ); },
                success: function(response_text) {
                    // HACK: use a simple string to separate the elements in the
                    // response: (1) table body; (2) number of pages in table; and (3) message.
                    var parsed_response_text = response_text.split("*****");
                    
                    // Update grid body and footer.
                    $('#grid-table-body').html(parsed_response_text[0]);
                    $('#grid-table-footer').html(parsed_response_text[1]);
                    
                    // Trigger custom event to indicate grid body has changed.
                    $('#grid-table-body').trigger('update');
                    
                    // Init grid.
                    init_grid_elements();
                    init_operation_buttons();
                    make_popup_menus();
                    
                    // Hide loading overlay.
                    $('.loading-elt-overlay').hide();
                    
                    // Show message if there is one.
                    var message = $.trim( parsed_response_text[2] );
                    if (message != "") {
                        $('#grid-message').html( message ).show();
                        setTimeout( function() { $('#grid-message').hide(); }, 5000);
                    }
                }
            });    
        }
        
        function check_all_items() {
            var chk_all = document.getElementById('check_all');
            var checks = document.getElementsByTagName('input');
            //var boxLength = checks.length;
            var total = 0;
            if ( chk_all.checked == true ) {
                for ( i=0; i < checks.length; i++ ) {
                    if ( checks[i].name.indexOf( 'id' ) != -1) {
                       checks[i].checked = true;
                       total++;
                    }
                }
            }
            else {
                for ( i=0; i < checks.length; i++ ) {
                    if ( checks[i].name.indexOf( 'id' ) != -1) {
                       checks[i].checked = false
                    }
                }
            }
            init_grid_elements();
        }
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
        <input type="hidden" name="webapp" value="${webapp}"/>
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
                        <span class='page-link'><a href="${url( page=1 )}" page_num="1">1</a></span> ...
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
                        <span class='page-link'><a href="${url( page=num_pages )}" page_num="${num_pages}">${num_pages}</a></span>
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

