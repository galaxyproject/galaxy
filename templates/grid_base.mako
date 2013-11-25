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
<%namespace file="./grid_common.mako" import="*" />
<%namespace file="/refresh_frames.mako" import="handle_refresh_frames" />
<%namespace file="/display_common.mako" import="get_class_plural" />

<%def name="load(embedded = False)">
<%
    self.grid_javascripts()
    if embedded:
        self.init()
        self.stylesheets()
        self.render_grid_header( grid, False )
        self.render_grid_table( grid, show_item_checkboxes=show_item_checkboxes )
    else:
        self.make_grid( grid )
    endif
%>
</%def>

<%def name="init()">
<%
    self.has_left_panel         = False
    self.has_right_panel        = False
    self.message_box_visible    = False
    self.overlay_visible        = False
    self.active_view            = 'user'

    self.grid_config = {
        'title'                         : grid.title,
        'url_base'                      : trans.request.path_url,
        'async'                         : grid.use_async,
        'async_ops'                     : [],
        'categorical_filters'           : {},
        'filters'                       : cur_filter_dict,
        'sort_key'                      : sort_key,
        'show_item_checkboxes'          : context.get('show_item_checkboxes', False),
        'cur_page_num'                  : cur_page_num,
        'num_pages'                     : num_pages,
        'history_tag_autocomplete_url'  : url( controller='tag', action='tag_autocomplete_data', item_class='History' ),
        'history_name_autocomplete_url' : url( controller='history', action='name_autocomplete_data' ),
        'status'                        : status,
        'message'                       : util.restore_text(message),
        'global_actions'                : [],
        'operations'                    : [],
        'items'                         : [],
        'columns'                       : [],
        'multiple_item_ops_exist'       : None,
        'get_class_plural'              : get_class_plural( grid.model_class ).lower(),
        'use_paging'                    : grid.use_paging,
        'legend'                        : grid.legend,
        'current_item_id'               : False,
        'use_panels'                    : context.get('use_panels')
    }

    ## add current item if exists
    if current_item:
        self.grid_config['current_item_id'] = current_item.id
    endif

    ## column
    for column in grid.columns:
        
        ## add column sort links
        href = None
        extra = ''
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

        ## add to configuration
        self.grid_config['columns'].append({
            'key'               : column.key,
            'visible'           : column.visible,
            'nowrap'            : column.nowrap,
            'attach_popup'      : column.attach_popup,
            'label_id_prefix'   : column.label_id_prefix,
            'sortable'          : column.sortable,
            'label'             : column.label,
            'href'              : href,
            'extra'             : extra
        })
    endfor
    
    ## operations
    for operation in grid.operations:
        self.grid_config['operations'].append({
            'allow_multiple'        : operation.allow_multiple,
            'allow_popup'           : operation.allow_popup,
            'target'                : operation.target,
            'label'                 : operation.label,
            'confirm'               : operation.confirm,
            'inbound'               : operation.inbound,
            'global_operation'      : False
        })
        if operation.allow_multiple:
            self.grid_config['multiple_item_ops_exist'] = True
            
        if operation.global_operation:
            self.grid_config['global_operation'] = url( ** (operation.global_operation()) )
    endfor

    ## global actions
    for action in grid.global_actions:
        self.grid_config['global_actions'].append({
            'url_args'  : url(**action.url_args),
            'label'     : action.label,
            'inbound'   : action.inbound
        })
    endfor

    ## Operations that are async (AJAX) compatible.
    for operation in [op for op in grid.operations if op.async_compatible]:
        self.grid_config['async_ops'].append(operation.label.lower());
    endfor

    ## Filter values for categorical filters.
    for column in grid.columns:
        if column.filterable is not None and not isinstance( column, TextColumn ):
            self.grid_config['categorical_filters'][column.key] = dict([ (filter.label, filter.args) for filter in column.get_accepted_filters() ])
        endif
    endfor

    # items
    for i, item in enumerate( query ):
        item_dict = {
            'id'                    : item.id,
            'encode_id'             : trans.security.encode_id(item.id),
            'link'                  : [],
            'operation_config'      : {},
            'column_config'         : {}
        }

        ## data columns
        for column in grid.columns:
            if column.visible:
                ## get link
                link = column.get_link(trans, grid, item)
                if link:
                    link = url(**link)
                else:
                    link = None
                endif

                ## inbound
                inbound = column.inbound

                ## get value
                value = column.get_value( trans, grid, item )

                # Handle non-ascii chars.
                if isinstance(value, str):
                    value = unicode(value, 'utf-8')

                    # escape string
                    value = value.replace('/', '//')
                endif

                ## Item dictionary
                item_dict['column_config'][column.label] = {
                    'link'      : link,
                    'value'     : value,
                    'inbound'  : inbound
                }
            endif
        endfor
        ## add operation details to item
        for operation in grid.operations:
            item_dict['operation_config'][operation.label] = {
                'allowed'   : operation.allowed(item),
                'url_args'  : url( **operation.get_url_args( item ) )
            }
        endfor

        ## add item to list
        self.grid_config['items'].append(item_dict)
    endfor
%>
</%def>

##
## Override methods from base.mako and base_panels.mako
##

<%def name="center_panel()">
    ${self.grid_body()}
</%def>

## Render the grid's basic elements. Each of these elements can be subclassed.
<%def name="body()">
    ${self.grid_body()}
</%def>

## Because body() is special and always exists even if not explicitly defined,
## it's not possible to override body() in the topmost template in the chain.
## Because of this, override grid_body() instead.
<%def name="grid_body()">
    ${self.load()}
</%def>

<%def name="title()">${self.grid_config['title']}</%def>

<%def name="grid_javascripts()">
    ${h.js("libs/jquery/jquery.autocomplete", "galaxy.autocom_tagging", "libs/jquery/jquery.rating" )}

    <script type="text/javascript">
        var gridView = null;
        function add_tag_to_grid_filter (tag_name, tag_value)
        {
            // Put tag name and value together.
            var tag = tag_name + (tag_value !== undefined && tag_value !== "" ? ":" + tag_value : "");
            $('#advanced-search').show('fast');
            gridView.add_filter_condition("tags", tag, true);
        };
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
            overflow: auto;
        }
        %endif
    </style>
</%def>

<%def name="make_grid( grid )">
    <div class="loading-elt-overlay"></div>
    <table>
        <tr>
            <td width="75%">${self.render_grid_header( grid )}</td>
            <td></td>
            <td></td>
        </tr>
        <tr>
            <td width="100%" id="grid-message" valign="top">
                %if message:
                    <p>
                        <div class="${self.grid_config['status']}message transient-message">${self.grid_config['message']}</div>
                        <div style="clear: both"></div>
                    </p>
                %endif
            </td>
            <td></td>
            <td></td>
        </tr>
    </table>

    ${self.render_grid_table( grid, show_item_checkboxes )}
</%def>

<%def name="grid_title()">
    <h2>${self.grid_config['title']}</h2>
</%def>

## Render grid header.
<%def name="render_grid_header( grid, render_title=True)">
    <div class="grid-header">
        %if render_title:
            ${self.grid_title()}
        %endif

        %if self.grid_config['global_actions']:
            <ul class="manage-table-actions">
                <%
                    show_popup = len( self.grid_config['global_actions'] ) >= 3
                %>
                %if show_popup:
                    <li><a class="action-button" id="popup-global-actions" class="menubutton">Actions</a></li>
                    <div popupmenu="popup-global-actions">
                %endif
                %for action in self.grid_config['global_actions']:
                    <%
                        label_cls = ""
                        if action['inbound']:
                            label_cls = "use-inbound"
                        else:
                            label_cls = "use-outbound"
                        endif
                    %>
                    <li><a class="action-button ${label_cls}" href="${action['url_args']}" onclick="return false;">${action['label']}</a></li>
                %endfor
                %if show_popup:
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
        # get configuration
        show_item_checkboxes = self.grid_config['show_item_checkboxes']
        multiple_item_ops_exist = self.grid_config['multiple_item_ops_exist']
        sort_key = self.grid_config['sort_key']

        # Show checkboxes if flag is set or if multiple item ops exist.
        if show_item_checkboxes or multiple_item_ops_exist:
            show_item_checkboxes = True
    %>
    <form method="post" onsubmit="return false;">
        <table id="grid-table" class="grid">
            <thead id="grid-table-header">
                <tr>
                    %if show_item_checkboxes:
                        <th>
                            %if len(self.grid_config['items']) > 0:
                                <input type="checkbox" id="check_all" name=select_all_checkbox value="true" onclick='gridView.check_all_items(1);'><input type="hidden" name=select_all_checkbox value="true">
                            %endif
                        </th>
                    %endif
                    %for column in self.grid_config['columns']:
                        %if column['visible']:
                            <th\
                            id="${column['key']}-header"
                            >
                                %if column['href']:
                                    <a href="${column['href']}" class="sort-link" sort_key="${column['key']}">${column['label']}</a>
                                %else:
                                    ${column['label']}
                                %endif
                                <span class="sort-arrow">${column['extra']}</span>
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
        %if len(self.grid_config['items']) == 0:
            ## No results.
            <tr><td colspan="100"><em>No Items</em></td></tr>
            <% num_rows_rendered = 1 %>
        %endif
        %for i, item in enumerate( self.grid_config['items'] ):
            <% encoded_id = item['encode_id'] %>
            <% popupmenu_id = "grid-" + str(i) + "-popup" %>
            <tr \
            %if self.grid_config['current_item_id'] == item['id']:
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
                %for column in self.grid_config['columns']:
                    %if column['visible']:
                        <%
                            ## Nowrap
                            nowrap = ""
                            if column['nowrap']:
                                nowrap = 'style="white-space:nowrap;"'

                            # get column settings
                            column_settings = item['column_config'][column['label']]
                            
                            # load attributes
                            link = column_settings['link']
                            value = column_settings['value']
                            inbound = column_settings['inbound']
                            
                            # check if formatting is defined
                            value = str(value).replace('//', '/')
                            
                            # Attach popup menu?
                            id = ""
                            cls = ""
                            if column['attach_popup']:
                                id = 'grid-%d-popup' % i
                                cls = "menubutton"
                                if link:
                                    cls += " split"
                                endif
                                cls += " popup"
                            endif
                        %>
                        <td ${nowrap}>
                        %if link:
                            %if len(self.grid_config['operations']) != 0:
                                <div id="${id}" class="${cls}" style="float: left;">
                            %endif

                            <%
                                label_class = ""
                                if inbound:
                                    label_class = "use-inbound"
                                else:
                                    label_class = "use-outbound"
                                endif
                            %>
                            <a class="label ${label_class}" href="${link}" onclick="return false;">${value}</a>
                            %if len(self.grid_config['operations']) != 0:
                                </div>
                            %endif
                        %else:
                            <div id="${id}" class="${cls}"><label id="${column['label_id_prefix']}${encoded_id}" for="${encoded_id}">${value}</label></div>
                        %endif
                        </td>
                    %endif
                %endfor
            </tr>
            <% num_rows_rendered += 1 %>
        %endfor

        ## update configuration
        <script type="text/javascript">
        $(function() {
            require(['galaxy.grids'], function(mod_grids) {
                ## get configuration
                var grid_config = ${ h.to_json_string( self.grid_config ) };
                
                // Create grid.
                var grid = new mod_grids.Grid(grid_config);
                
                // strip protocol and domain
                var url = grid.get('url_base');
                url = url.replace(/^.*\/\/[^\/]+/, '');
                grid.set('url_base', url);

                // Create view.
                if (!gridView)
                    gridView = new mod_grids.GridView(grid);
                else
                    gridView.init_grid(grid);
            });
        });
        </script>
        
        ${handle_refresh_frames()}
</%def>

## Render grid table footer contents.
<%def name="render_grid_table_footer_contents(grid, show_item_checkboxes=False)">
    <%
        items_plural = self.grid_config['get_class_plural']
        num_pages = self.grid_config['num_pages']
        cur_page_num = self.grid_config['cur_page_num']
    %>
    %if self.grid_config['use_paging'] and num_pages > 1:
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
                        <span class='page-link' id="page-link-1"><a href="${url( page=1 )}" page_num="1" onclick="return false;">1</a></span> ...
                    % endif
                    %for page_index in range(min_page, max_page + 1):
                        %if page_index == cur_page_num:
                            <span class='page-link inactive-link' id="page-link-${page_index}">${page_index}</span>
                        %else:
                            <% args = { 'page' : page_index } %>
                            <span class='page-link' id="page-link-${page_index}"><a href="${url( args )}" onclick="return false;" page_num='${page_index}'>${page_index}</a></span>
                        %endif
                    %endfor
                    %if max_page < num_pages:
                        ...
                        <span class='page-link' id="page-link-${num_pages}"><a href="${url( page=num_pages )}" onclick="return false;" page_num="${num_pages}">${num_pages}</a></span>
                    %endif
                </span>
                
                ## Show all link
                <span class='page-link' id='show-all-link-span'> | <a href="${url( page='all' )}" onclick="return false;" page_num="all">Show All</a></span>
            </td>
        </tr>    
    %endif
    ## Grid operations for multiple items.
    %if show_item_checkboxes:
        <tr>
            ## place holder for multiple operation commands
            <input type="hidden" id="operation" name="operation" value="">
            <td></td>
            <td colspan="100">
                For <span class="grid-selected-count"></span> selected ${items_plural}:
                %for operation in self.grid_config['operations']:
                    %if operation['allow_multiple']:
                        <input type="button" value="${operation['label']}" class="action-button" onclick="gridView.submit_operation(this, '${operation['confirm']}')">
                    %endif
                %endfor
            </td>
        </tr>
    %endif
    %if len([o for o in self.grid_config['operations'] if o['global_operation']]) > 0:
    <tr>
        <td colspan="100">
            %for operation in self.grid_config['operations']:
                %if operation['global_operation']:
                    <a class="action-button" href="${operation['global_operation']}">${operation['label']}</a>
                %endif
            %endfor
        </td>
    </tr>
    %endif
    %if self.grid_config['legend']:
        <tr>
            <td colspan="100">
                ${self.grid_config['legend']}
            </td>
         </tr>
    %endif
</%def>

