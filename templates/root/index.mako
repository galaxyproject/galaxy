<%inherit file="/webapps/galaxy/base_panels.mako"/>

<%def name="late_javascripts()">
    ${parent.late_javascripts()}
    <script type="text/javascript">
    // Set up GalaxyAsync object.
    var galaxy_async = new GalaxyAsync();
    galaxy_async.set_func_url(galaxy_async.set_user_pref, "${h.url_for( controller='user', action='set_user_pref_async' )}");
    
    $(function(){
        // Init history options.
        $("#history-options-button").css( "position", "relative" );
        make_popupmenu( $("#history-options-button"), {
            "${_("History Lists")}": null,
            "${_("Saved Histories")}": function() {
                galaxy_main.location = "${h.url_for( controller='history', action='list')}";
            },
            "${_("Histories Shared with Me")}": function() {
                galaxy_main.location = "${h.url_for( controller='history', action='list_shared')}";
            },
            "${_("Current History")}": null,
            "${_("Create New")}": function() {
                galaxy_history.location = "${h.url_for( controller='root', action='history_new' )}";
            },
            "${_("Clone")}": function() {
                galaxy_main.location = "${h.url_for( controller='history', action='clone')}";
            },
            "${_("Copy Datasets")}": function() {
                galaxy_main.location = "${h.url_for( controller='dataset', action='copy_datasets' )}";
            },
            "${_("Share or Publish")}": function() {
                galaxy_main.location = "${h.url_for( controller='history', action='sharing' )}";
            },
            "${_("Extract Workflow")}": function() {
                galaxy_main.location = "${h.url_for( controller='workflow', action='build_from_current_history' )}";
            },
            "${_("Dataset Security")}": function() {
                galaxy_main.location = "${h.url_for( controller='root', action='history_set_default_permissions' )}";
            },
            "${_("Show Deleted Datasets")}": function() {
                galaxy_history.location = "${h.url_for( controller='root', action='history', show_deleted=True)}";
            },
            "${_("Show Hidden Datasets")}": function() {
                galaxy_history.location = "${h.url_for( controller='root', action='history', show_hidden=True)}";
            },
            "${_("Purge Deleted Datasets")}": function() {
                if ( confirm( "Really delete all deleted datasets permanently? This cannot be undone." ) ) {
                    galaxy_main.location = "${h.url_for( controller='history', action='purge_deleted_datasets' )}";
                }
            },
            "${_("Show Structure")}": function() {
                galaxy_main.location = "${h.url_for( controller='history', action='display_structured' )}";
            },
            "${_("Export to File")}": function() {
                galaxy_main.location = "${h.url_for( controller='history', action='export_archive' )}";
            },
            "${_("Delete")}": function() {
                if ( confirm( "Really delete the current history?" ) ) {
                    galaxy_main.location = "${h.url_for( controller='history', action='delete_current' )}";
                }
            },
            "${_("Delete Permanently")}": function() {
                if ( confirm( "Really delete the current history permanently? This cannot be undone." ) ) {
                    galaxy_main.location = "${h.url_for( controller='history', action='delete_current', purge=True )}";
                }
            },
            "${_("Other Actions")}": null,
            "${_("Import from File")}": function() {
                galaxy_main.location = "${h.url_for( controller='history', action='import_archive' )}";
            }
        });
        
        var menu_options = {}; // Holds dictionary of { label: toggle_fn }
        
        SHOW_TOOL = "${_("Show Tool Search")}";
        HIDE_TOOL = "${_("Hide Tool Search")}";
        SHOW_RECENT = "${_("Show Recently Used")}";
        HIDE_RECENT = "${_("Hide Recently Used")}";
        
        var toggle_tool_search_fn = function() {
            // Show/hide menu and update vars, user preferences.
            var menu = $("#galaxy_tools").contents().find('#tool-search'),
                pref_value, menu_option_text, old_text;
            if (menu.is(":visible")) {
                // Hide menu.
                pref_value = "False";
                menu_option_text = SHOW_TOOL;
                old_text = HIDE_TOOL;
                
                // Reset search.
                reset_tool_search(true);
            } else {
                // Show menu.
                pref_value = "True";
                menu_option_text = HIDE_TOOL;
                old_text = SHOW_TOOL;
            }
            menu.toggle();
    
            // Update menu option.
            delete menu_options[old_text];
            
            var new_menu_options = {}; 
            // Because we always want tool menu to be the first link in the dropdown,
            // we re-create the menu_options dictionary by creating a new
            // dict and then appending the old dict to it
            new_menu_options[menu_option_text] = toggle_tool_search_fn;
            menu_options = $.extend( new_menu_options, menu_options );
            make_popupmenu( $("#tools-options-button"), menu_options );
            galaxy_async.set_user_pref("show_tool_search", pref_value);
        };
        
        var toggle_recently_used_fn = function() {
            // Show/hide menu.
            var ru_menu = $('#galaxy_tools').contents().find('#recently_used_wrapper'),
                ru_menu_body = ru_menu.find(".toolSectionBody"),
                pref_value, old_text, menu_option_text;
            if (ru_menu.hasClass("user_pref_visible")) {
                // Hide menu.
                ru_menu_body.slideUp();
                ru_menu.slideUp();
                
                // Set vars used below and in tool menu frame.
                pref_value = "False";
                old_text = HIDE_RECENT;
                menu_option_text = SHOW_RECENT;
            } else {
                // "Show" menu.
                if (!$('#galaxy_tools').contents().find('#tool-search-query').hasClass("search_active")) {
                    // Default.
                    ru_menu.slideDown();
                } else {
                    // Search active: tf there are matching tools in RU menu, show menu.
                    if ( ru_menu.find(".toolTitle.search_match").length !== 0 ) {
                        ru_menu.slideDown();
                        ru_menu_body.slideDown();
                    }
                }
                // Set vars used below and in tool menu frame.
                pref_value = "True";
                old_text = SHOW_RECENT;
                menu_option_text = HIDE_RECENT;
            }
            
            // Update menu class and option.
            ru_menu.toggleClass("user_pref_hidden user_pref_visible");
            delete menu_options[old_text];
            menu_options[menu_option_text] = toggle_recently_used_fn;
            make_popupmenu( $("#tools-options-button"), menu_options );
            galaxy_async.set_user_pref("show_recently_used_menu", pref_value);
        };
        
        // Init tool options.
        ## Search tools menu item.
        %if trans.app.toolbox_search.enabled:
            <% 
                show_tool_search = True
                if trans.user:
                    show_tool_search = trans.user.preferences.get( "show_tool_search", "False" ) == "True"
                    
                if show_tool_search:
                    action = "HIDE_TOOL"
                else:
                    action = "SHOW_TOOL"
            %>
            menu_options[ ${action} ] = toggle_tool_search_fn;
        %endif
        ## Recently used tools menu.
        %if trans.user:
            <%
                if trans.user.preferences.get( 'show_recently_used_menu', 'False' ) == 'True':
                    action = "HIDE_RECENT"
                else:
                    action = "SHOW_RECENT"
            %>
            // TODO: make compatible with new tool menu.
            //menu_options[ ${action} ] = toggle_recently_used_fn;
        %endif
        
        
        make_popupmenu( $("#tools-options-button"), menu_options );
    });
    </script>
</%def>

<%def name="init()">
<%
    self.has_left_panel = True
    self.has_right_panel = True
    self.active_view = "analysis"
%>
%if trans.app.config.require_login and not trans.user:
    <script type="text/javascript">
        if ( window != top ) {
            top.location.href = location.href;
        }
    </script>
%endif
</%def>

<%def name="left_panel()">
    <div class="unified-panel-header" unselectable="on">
        <div class='unified-panel-header-inner'>
            <div style="float: right">
                <a class='panel-header-button' id="tools-options-button" href="#"><span class="ficon large cog"></span></a>
            </div>
            ${n_('Tools')}
        </div>
    </div>
    <div class="unified-panel-body" style="overflow: hidden;">
        <iframe name="galaxy_tools" id="galaxy_tools" src="${h.url_for( controller='root', action='tool_menu' )}" frameborder="0" style="position: absolute; margin: 0; border: 0 none; height: 100%; width: 100%;"> </iframe>
    </div>
</%def>

<%def name="center_panel()">

    ## If a specific tool id was specified, load it in the middle frame
    <%
    if trans.app.config.require_login and not trans.user:
        center_url = h.url_for( controller='user', action='login' )
    elif tool_id is not None:
        center_url = h.url_for( 'tool_runner', tool_id=tool_id, from_noframe=True )
    elif workflow_id is not None:
        center_url = h.url_for( controller='workflow', action='run', id=workflow_id )
    elif m_c is not None:
        center_url = h.url_for( controller=m_c, action=m_a )
    else:
        center_url = h.url_for( '/static/welcome.html' )
    %>
    
    <iframe name="galaxy_main" id="galaxy_main" frameborder="0" style="position: absolute; width: 100%; height: 100%;" src="${center_url}"></iframe>

</%def>

<%def name="right_panel()">
    <div class="unified-panel-header" unselectable="on">
        <div class="unified-panel-header-inner">
            <div style="float: right">
                <a id="history-options-button" class='panel-header-button' href="${h.url_for( controller='root', action='history_options' )}" target="galaxy_main"><span class="ficon large cog"></span></a>
            </div>
            <div class="panel-header-text">${_('History')}</div>
        </div>
    </div>
    <div class="unified-panel-body" style="overflow: hidden;">
        <iframe name="galaxy_history" width="100%" height="100%" frameborder="0" style="position: absolute; margin: 0; border: 0 none; height: 100%;" src="${h.url_for( controller='root', action='history' )}"></iframe>
    </div>
</%def>
