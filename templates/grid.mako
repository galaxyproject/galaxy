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
        });
        
    </script>
</%def>

<%def name="stylesheets()">
    <link href="${h.url_for('/static/style/base.css')}" rel="stylesheet" type="text/css" />
    <style>
        ## Not generic to all grids -- move to base?
        .count-box {
            width: 1.1em;
            max-width: 5em;
            padding: 5px;
            border-width: 1px;
            border-style: solid;
            text-align: center;
        }
    </style>
</%def>


<div class="grid-header">
    <h2>${grid.title}</h2>
    <span class="title">Filter:</span>
    %for i, filter in enumerate( grid.standard_filters ):
        %if i > 0:    
            <span>|</span>
        %endif
        <span class="filter"><a href="${url( filter.get_url_args() )}">${filter.label}</a></span>
    %endfor
</div>

<form name="history_actions" action="${h.url_for()}" method="post" >

    <input type="hidden" name="sort" value="${sort_key}">
    
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
                        <th \
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
                <td style="width: 1.5em;"><input type="checkbox" name="id" value=${item.id} class="grid-row-select-checkbox"></input></td>
                
                ## Data columns
                %for column in grid.columns:
                    %if column.visible:
                        <%
                            # Link
                            if column.link and column.link( item ):
                                href = url( **column.link( item ) )
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
                                    extra = '<a id="grid-%d-popup" class="popup-arrow" style="display: none;">&#9660;</a>' % i
                                else:
                                    extra = ""
                            %>
                        
                            %if href:                    
                                <td><a href="${href}">${v}</a>&nbsp;${extra}</td>
                            %else:
                                <td >${v}${extra}</td>
                            %endif    
                            </td>
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
        </tfoot>
        
    </table>

  </form>



