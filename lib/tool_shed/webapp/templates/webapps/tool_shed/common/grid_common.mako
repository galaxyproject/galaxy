<%!
    from galaxy.webapps.reports.framework.grids import TextColumn, StateColumn, GridColumnFilter
    from galaxy.web.framework.helpers import iff
%>

## Render a filter UI for a grid column. Filter is rendered as a table row.
<%def name="render_grid_column_filter( grid, column )">
    <tr>
        <%
            column_label = column.label
            if column.filterable == "advanced":
                column_label = column_label.lower()
        %>
        %if column.filterable == "advanced":
            <td align="left" style="padding-left: 10px">${column_label}:</td>
        %endif
        <td style="padding: 0;">
            %if isinstance(column, TextColumn):
                <form class="text-filter-form" column_key="${column.key}" action="${url(dict())}" method="get" >
                    ## Carry forward filtering criteria with hidden inputs.
                    %for temp_column in grid.columns:
                        %if temp_column.key in cur_filter_dict:
                            <% value = cur_filter_dict[ temp_column.key ] %>
                            %if value != "All":
                                <%
                                    if isinstance( temp_column, TextColumn ):
                                        value = h.dumps( value )
                                %>
                                <input type="hidden" id="${temp_column.key}" name="f-${temp_column.key}" value='${value}'/>
                            %endif
                        %endif
                    %endfor
                    ## Print current filtering criteria and links to delete.
                    <span id="${column.key}-filtering-criteria">
                        %if column.key in cur_filter_dict:
                            <% column_filter = cur_filter_dict[column.key] %>
                            %if isinstance( column_filter, basestring ):
                                %if column_filter != "All":
                                    <span class='text-filter-val'>
                                        ${cur_filter_dict[column.key]}
                                        <% filter_all = GridColumnFilter( "", { column.key : "All" } ) %>
                                        <a href="${url(filter_all.get_url_args())}"><span class="delete-search-icon" /></a>
                                    </span>
                                %endif
                            %elif isinstance( column_filter, list ):
                                %for i, filter in enumerate( column_filter ):
                                    %if i > 0:
                                        ,
                                    %endif
                                    <span class='text-filter-val'>${filter}
                                        <%
                                            new_filter = list( column_filter )
                                            del new_filter[ i ]
                                            new_column_filter = GridColumnFilter( "", { column.key : h.dumps( new_filter ) } )
                                        %>
                                        <a href="${url(new_column_filter.get_url_args())}"><span class="delete-search-icon" /></a>
                                    </span>
                                %endfor
                            %endif
                        %endif
                    </span>
                    ## Print input field for column.
                    <span class="search-box">
                        <% 
                            # Set value, size of search input field. Minimum size is 20 characters.
                            value = iff( column.filterable == "standard", column.label.lower(), "") 
                            size = len( value )
                            if size < 20:
                                size = 20
                            # +4 to account for search icon/button.
                            size = size + 4
                        %>
                        <input class="search-box-input" id="input-${column.key}-filter" name="f-${column.key}" type="text" value="${value}" size="${size}"/>
                        <button type="submit" title='Search' style="background: transparent; border: none; padding: 4px; margin: 0px;">
                            <i class="fa fa-search"></i>
                        </button>
                    </span>
                </form>
            %else:
                <span id="${column.key}-filtering-criteria">
                    %for i, filter in enumerate( column.get_accepted_filters() ):
                        <% 
                            # HACK: we know that each filter will have only a single argument, so get that single argument.
                            for key, arg in filter.args.items():
                                filter_key = key
                                filter_arg = arg
                        %>
                        %if i > 0:
                            |
                        %endif
                        %if column.key in cur_filter_dict and column.key in filter.args and cur_filter_dict[column.key] == filter.args[column.key]:
                            <span class="categorical-filter ${column.key}-filter current-filter">${filter.label}</span>
                        %else:
                            <span class="categorical-filter ${column.key}-filter">
                                <a href="${url(filter.get_url_args())}" filter_key="${filter_key}" filter_val="${filter_arg}">${filter.label}</a>
                            </span>
                        %endif
                    %endfor
                </span>
            %endif
        </td>
    </tr>
</%def>

## Print grid search/filtering UI.
<%def name="render_grid_filters( grid, render_advanced_search=True )">
    <%
        # Show advanced search if flag set or if there are filters for advanced search fields.
        advanced_search_display = "none"
        if 'advanced-search' in kwargs and kwargs['advanced-search'] in ['True', 'true']:
            advanced_search_display = "block"

        for column in grid.columns:
            if column.filterable == "advanced":
                ## Show div if current filter has value that is different from the default filter.
                if column.key in cur_filter_dict and column.key in default_filter_dict and \
                    cur_filter_dict[column.key] != default_filter_dict[column.key]:
                        advanced_search_display = "block"

        # do not show standard search if showing adv.
        standard_search_display = "block"
        if advanced_search_display == "block":
            standard_search_display = "none"
    %>
    ## Standard search.
    <div id="standard-search" style="display: ${standard_search_display};">
        <table>
            <tr><td style="padding: 0;">
                <table>
                %for column in grid.columns:
                    %if column.filterable == "standard":
                       ${render_grid_column_filter( grid, column )}
                    %endif
                %endfor
                </table>
            </td></tr>
            <tr><td>
                ## Clear the standard search.
                ##|
                ##<% filter_all = GridColumnFilter( "", { column.key : "All" } ) %>
                ##<a href="${url(filter_all.get_url_args())}">Clear All</a>
                
                ## Only show advanced search if there are filterable columns.
                <%
                    show_advanced_search_link = False
                    if render_advanced_search:
                        for column in grid.columns:
                            if column.filterable == "advanced":
                                show_advanced_search_link = True
                                break
                            endif
                %>
                %if show_advanced_search_link:
                    <% args = { "advanced-search" : True } %>
                    <a href="${url(args)}" class="advanced-search-toggle">Advanced Search</a>
                %endif
            </td></tr>
        </table>
    </div>
    
    ## Advanced search.
    <div id="advanced-search" style="display: ${advanced_search_display}; margin-top: 5px; border: 1px solid #ccc;">
        <table>
            <tr><td style="text-align: left" colspan="100">
                <% args = { "advanced-search" : False } %>
                <a href="${url(args)}" class="advanced-search-toggle">Close Advanced Search</a>
                ## Link to clear all filters.
                ##|
                ##<%
                ##    no_filter = GridColumnFilter("Clear All", default_filter_dict)
                ##%>
                ##<a href="${url(no_filter.get_url_args())}">${no_filter.label}</a>
            </td></tr>
            %for column in grid.columns:            
                %if column.filterable == "advanced":
                    ## Show div if current filter has value that is different from the default filter.
                    %if column.key in cur_filter_dict and column.key in default_filter_dict and \
                        cur_filter_dict[column.key] != default_filter_dict[column.key]:
                        <script type="text/javascript">
                            $('#advanced-search').css("display", "block");
                        </script>
                    %endif
            
                    ${render_grid_column_filter( grid, column )}
                %endif
            %endfor
        </table>
    </div>
</%def>
