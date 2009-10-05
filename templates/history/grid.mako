<%! from galaxy.web.framework.helpers.grids import GridColumnFilter %>

<%inherit file="/base.mako"/>
<%def name="title()">${grid.title}</%def>

%if message:
    <p>
        <div class="${message_type}message transient-message">${message}</div>
        <div style="clear: both"></div>
    </p>
%endif

<%def name="javascripts()">
    ${parent.javascripts()}
	${h.js("jquery.autocomplete", "autocomplete_tagging" )}
    <script type="text/javascript">        
        ## TODO: generalize and move into galaxy.base.js
        $(document).ready(function() {
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
            
            // Set up autocomplete for tag filter input.
            var t = $("#input-tag-filter");
            t.keyup( function( e ) 
            {
                if ( e.keyCode == 27 ) 
        	    {
        	        // Escape key
        	        $(this).trigger( "blur" );
        	    } else if (
        		        ( e.keyCode == 13 ) || // Return Key
        		        ( e.keyCode == 188 ) || // Comma
        		        ( e.keyCode == 32 ) // Space
        		        )
        	    {
            	    //
            	    // Check input.
            	    //

            	    new_value = this.value;

            	    // Do nothing if return key was used to autocomplete.
            	    if (return_key_pressed_for_autocomplete == true)
            	    {
            	        return_key_pressed_for_autocomplete = false;
            	        return false;
            	    }

            	    // Suppress space after a ":"
            	    if ( new_value.indexOf(": ", new_value.length - 2) != -1)
            	    {
            	        this.value = new_value.substring(0, new_value.length-1);
            	        return false;
            	    }

            	    // Remove trigger keys from input.
            	    if ( (e.keyCode == 188) || (e.keyCode == 32) )
            	        new_value = new_value.substring( 0 , new_value.length - 1 );

            	    // Trim whitespace.
            	    new_value = new_value.replace(/^\s+|\s+$/g,"");

            	    // Too short?
            	    if (new_value.length < 3)
            	        return false;

            	    //
            	    // New tag OK.
            	    //
            	}
        	});
            
            // Add autocomplete to input.
            var format_item_func = function(key, row_position, num_rows, value, search_term) 
            {
                tag_name_and_value = value.split(":");
                return (tag_name_and_value.length == 1 ? tag_name_and_value[0] :tag_name_and_value[1]);
                //var array = new Array(key, value, row_position, num_rows,
                //search_term ); return "\"" + array.join("*") + "\"";
            }
            var autocomplete_options = 
                { selectFirst: false, formatItem : format_item_func, autoFill: false, highlight: false, mustMatch: true };

            t.autocomplete("${h.url_for( controller='tag', action='tag_autocomplete_data', item_class='History' )}", autocomplete_options);

            
            $("#page-select").change(navigate_to_page);
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
        // Add a tag to the current grid filter; this adds the tag to the filter and then issues a request to refresh the grid.
        //
        function add_tag_to_grid_filter(tag_name, tag_value)
        {
            // Use tag as a filter: replace TAGNAME with tag_name and issue query.
            <%
                url_args = {}
                if "tags" in cur_filter_dict and cur_filter_dict["tags"] != "All":
                    url_args["f-tags"] = cur_filter_dict["tags"].encode("utf-8") + ", TAGNAME"
                else:
                    url_args["f-tags"] = "TAGNAME"
            %>
            var url_base = "${url( url_args )}";
            var url = url_base.replace("TAGNAME", tag_name);
            self.location = url;
        }
        
        //
        // Initiate navigation when user selects a page to view.
        //
        function navigate_to_page()
        {
            page_num = $(this).val();
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

<div class="grid-header">
    <h2>${grid.title}</h2>

    ## Print grid filter.
    <form name="history_actions" action="javascript:add_tag_to_grid_filter($('#input-tag-filter').attr('value'))" method="get" >
        <strong>Filter:&nbsp;&nbsp;&nbsp;</strong>
        %for column in grid.columns:
            %if column.filterable:
                <span> by ${column.label.lower()}:</span>
                ## For now, include special case to handle tags.
                %if column.key == "tags":
                    %if cur_filter_dict[column.key] != "All":
                        <span class="filter" "style='font-style: italic'">
                            ${cur_filter_dict[column.key]}
                        </span>
                        <span>|</span>
                    %endif
                    <input id="input-tag-filter" name="f-tags" type="text" value="" size="15"/>
                    <span>|</span>
                %endif
        
                ## Handle other columns.
                %for i, filter in enumerate( column.get_accepted_filters() ):
                    %if i > 0:
                        <span>|</span>
                    %endif
                    %if cur_filter_dict[column.key] == filter.args[column.key]:
                        <span class="filter" "style='font-style: italic'">${filter.label}</span>
                    %else:
                        <span class="filter"><a href="${url( filter.get_url_args() )}">${filter.label}</a></span>
                    %endif
                %endfor
                <span>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span>
            %endif
        %endfor
        
        ## Link to clear all filters. TODO: this should be the default filter or an empty filter.
        <%
            args = { "deleted" : "False", "tags" : "All" }
            no_filter = GridColumnFilter("Clear Filter", args)
        %>
        <span><a href="${url( no_filter.get_url_args() )}">${no_filter.label}</a></span>
    </form>
</div>
<form name="history_actions" action="${url()}" method="post" >
    <input type="hidden" name="page" value="${cur_page_num}">
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
                                    # Attach popup menu?
                                    if column.attach_popup and cellnum == 0:
                                        extra = '<a id="grid-%d-popup" class="arrow" style="display: none;"><span>&#9660;</span></a>' % i
                                    else:
                                        extra = ""
                                %>
                                %if href:                    
                                    <td><div class="menubutton split" style="float: left;"><a class="label" href="${href}">${v}${extra}</a> </td>
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
                                    <a class="action-button" href="${url( operation=operation.label, id=item.id )}">${operation.label}</a>
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
                        <select id="page-select" onchange="navigate_to_page()">
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
            %if grid.operations:
                <tr>
                    <td></td>
                    <td colspan="100">
                        For <span class="grid-selected-count"></span> selected histories:
                        %for operation in grid.operations:
                            %if operation.allow_multiple:
                                <input type="submit" name="operation" value="${operation.label}" class="action-button">
                            %endif
                        %endfor
                    </td>
                </tr>
            %endif
        </tfoot>
    </table>
</form>
