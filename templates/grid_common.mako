<%! from galaxy.web.framework.helpers.grids import TextColumn, GridColumnFilter %>

## Render a filter UI for a grid column. Filter is rendered as a table row.
<%def name="render_grid_column_filter(column)">
    <tr>
        <%
            column_label = column.label
            if column.filterable == "advanced":
                column_label = column_label.lower()
        %>
        <td align="left" style="padding-left: 10px">${column_label}:</td>
        <td>
        %if isinstance(column, TextColumn):
            <form name="history_actions" action="${url( dict() )}"           
                method="get" >
                ## Carry forward filtering criteria with hidden inputs.
                %for temp_column in grid.columns:
                    %if temp_column.key in cur_filter_dict:
                        <% value = cur_filter_dict[ temp_column.key ] %>
                        %if value != "All":
                            <%
                                if isinstance( temp_column, TextColumn ):
                                    value = h.to_json_string( value )
                            %>
                            <input type="hidden" id="${temp_column.key}" name="f-${temp_column.key}" value='${value}'/>
                        %endif
                    %endif
                %endfor
                
                ## Print current filtering criteria and links to delete.
                %if column.key in cur_filter_dict:
                    <% column_filter = cur_filter_dict[column.key] %>
                    %if isinstance( column_filter, basestring ):
                        %if column_filter != "All":
                            <span style="font-style: italic">${cur_filter_dict[column.key]}</span>
                            <% filter_all = GridColumnFilter( "", { column.key : "All" } ) %>
                            <a href="${url( filter_all.get_url_args() )}"><img src="${h.url_for('/static/images/delete_tag_icon_gray.png')}"/></a>                                
                            |
                        %endif
                    %elif isinstance( column_filter, list ):
                        %for i, filter in enumerate( column_filter ):
                            %if i > 0:
                                ,
                            %endif
                            <span style="font-style: italic">${filter}</span>
                            <%
                                new_filter = list( column_filter )
                                del new_filter[ i ]
                                new_column_filter = GridColumnFilter( "", { column.key : h.to_json_string( new_filter ) } )
                            %>
                            <a href="${url( new_column_filter.get_url_args() )}"><img src="${h.url_for('/static/images/delete_tag_icon_gray.png')}"/></a>                                
                        %endfor
                                
                    %endif
                %endif
                <span><input id="input-${column.key}-filter" name="f-${column.key}" type="text" value="" size="15"/></span>
            </form>
        %else:
            %for i, filter in enumerate( column.get_accepted_filters() ):
                %if i > 0:
                    <span>|</span>
                %endif
                %if cur_filter_dict[column.key] == filter.args[column.key]:
                    <span class="filter" style="font-style: italic">${filter.label}</span>
                %else:
                    <span class="filter"><a href="${url( filter.get_url_args() )}">${filter.label}</a></span>
                %endif
            %endfor
        %endif
        </td>
    </tr>
</%def>

## Print grid search/filtering UI.
<%def name="render_grid_filters()">
    <div class="grid-header">
        <h2>${grid.title}</h2>
    
        ## Default search.
        <div>
            <table><tr>
                <td>
                    <table>
                    %for column in grid.columns:
                        %if column.filterable == "default":
                           ${render_grid_column_filter(column)}
                        %endif
                    %endfor
                    </table>
                </td>
                <td>
                    ##|
                    ##<% filter_all = GridColumnFilter( "", { column.key : "All" } ) %>
                    ##<a href="${url( filter_all.get_url_args() )}">Clear All</a>                                
                    | <a href="" onclick="javascript:$('#more-search-options').slideToggle('fast');return false;">Advanced Search</a>
                </td>
            </tr></table>
        </div>
    
        
        ## Advanced search.
        <div id="more-search-options" style="display: none; padding-top: 5px">
            <table style="border: 1px solid gray;">
                <tr><td style="text-align: left" colspan="100">
                    Advanced Search | 
                    <a href=""# onclick="javascript:$('#more-search-options').slideToggle('fast');return false;">Close</a> |
                    ## Link to clear all filters.
                    <%
                        no_filter = GridColumnFilter("Clear All", default_filter_dict)
                    %>
                    <a href="${url( no_filter.get_url_args() )}">${no_filter.label}</a>
                </td></tr>
                %for column in grid.columns:            
                    %if column.filterable == "advanced":
                        ## Show div if current filter has value that is different from the default filter.
                        %if column.key in cur_filter_dict and column.key in default_filter_dict and \
                            cur_filter_dict[column.key] != default_filter_dict[column.key]:
                            <script type="text/javascript">
                                $('#more-search-options').css("display", "block");
                            </script>
                        %endif
                
                        ${render_grid_column_filter(column)}
                    %endif
                %endfor
            </table>
        </div>
    </div>
</%def>