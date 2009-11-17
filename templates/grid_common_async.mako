<%! from galaxy.web.framework.helpers.grids import TextColumn, GridColumnFilter %>

## Render an AJAX filter UI for a grid column. Filter is rendered as a table row.
<%def name="render_ajax_grid_column_filter(column)">
    <tr>
        <%
            column_label = column.label
            if column.filterable == "advanced":
                column_label = column_label.lower()
        %>
        <td align="left" style="padding-left: 10px">${column_label}:</td>
        <td>
        %if isinstance(column, TextColumn):
            <form action="${url( dict() )}" id="form-filter-${column.key}"
            ## Move this to doc.ready() 
            ##onsubmit="var text_input=$('#input-${column.key}-filter').val();$('#input-${column.key}-filter').val('');add_filter_condition('${column.key}',text_input,true);return false;"       
            onsubmit="var text_input=$('#input-${column.key}-filter').val();$('#input-${column.key}-filter').val('');add_filter_condition('${column.key}',text_input,true);return false;"          
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
                <span id="${column.key}-filtering-criteria">
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
                </span>
                
                ## Print input field for column.
                <span><input id="input-${column.key}-filter" name="f-${column.key}" type="text" value="" size="15"/></span>
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
                    <span class="${column.key}-filter">${filter.label}</span>
                %else:
                    <span class="${column.key}-filter">
                        <a href="${url( filter.get_url_args() )}" 
                        onclick="set_categorical_filter($(this), '${column.key}','${filter_arg}'); return false;">${filter.label}</a>
                    </span>
                %endif
            %endfor
            </span>
        %endif
        </td>
    </tr>
</%def>

## Print grid search/filtering UI.
<%def name="render_grid_filters()">
    ## Standard search.
    <div>
        <table><tr>
            <td>
                <table>
                %for column in grid.columns:
                    %if column.filterable == "standard":
                       ${render_ajax_grid_column_filter(column)}
                    %endif
                %endfor
                </table>
            </td>
            <td>
                ## Clear the standard search.
                ##|
                ##<% filter_all = GridColumnFilter( "", { column.key : "All" } ) %>
                ##<a href="${url( filter_all.get_url_args() )}">Clear All</a>
                
                ## Only show advanced search if there are filterable columns.
                <%
                    show_advanced_search = False
                    for column in grid.columns:
                        if column.filterable == "advanced":
                            show_advanced_search = True
                            break
                        endif
                %>
                %if show_advanced_search:
                    | <a href="" onclick="javascript:$('#more-search-options').slideToggle('fast');return false;">Advanced Search</a>
                %endif
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
            
                    ${render_ajax_grid_column_filter(column)}
                %endif
            %endfor
        </table>
    </div>
</%def>