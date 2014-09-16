<%inherit file="/webapps/galaxy/base_panels.mako"/>

<%namespace file="/root/tool_menu.mako" import="*" />

<%def name="stylesheets()">
    ${parent.stylesheets()}
    ${h.css("tool_menu")}
    <style>
        #right .unified-panel-body {
            background: none repeat scroll 0 0 #DFE5F9;
            overflow: auto;
            padding: 0;
        }
    </style>
</%def>

<%def name="javascripts()">
    ${parent.javascripts()}
    ${tool_menu_javascripts()}
</%def>

<%def name="late_javascripts()">
    ${parent.late_javascripts()}

    <script type="text/javascript">
    // Set up GalaxyAsync object.
    var galaxy_async = new GalaxyAsync();
    galaxy_async.set_func_url( galaxy_async.set_user_pref,
        "${h.url_for( controller='user', action='set_user_pref_async' )}");
    
    // set up history options menu
    $(function(){
        // Init history options.
        //$("#history-options-button").css( "position", "relative" );
        var popupmenu = PopupMenu.make_popupmenu( $("#history-options-button"), {
            "${_("History Lists")}": null,
            "${_("Saved Histories")}": function() {
                galaxy_main.location = "${h.url_for( controller='history', action='list')}";
            },
            "${_("Histories Shared with Me")}": function() {
                galaxy_main.location = "${h.url_for( controller='history', action='list_shared')}";
            },
            "${_("Current History")}": null,
            "${_("Create New")}": function() {
                if( Galaxy && Galaxy.currHistoryPanel ){
                    Galaxy.currHistoryPanel.createNewHistory();
                }
            },
            "${_("Copy History")}": function() {
                galaxy_main.location = "${h.url_for( controller='history', action='copy')}";
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
            "${_("Resume Paused Jobs")}": function() {
                galaxy_main.location = "${h.url_for( controller='history', action='resume_paused_jobs', current=True)}";
            },
            "${_("Collapse Expanded Datasets")}": function() {
                if( Galaxy && Galaxy.currHistoryPanel ){
                    Galaxy.currHistoryPanel.collapseAll();
                }
            },
            "${_("Include Deleted Datasets")}": function( clickEvent, thisMenuOption ) {
                if( Galaxy && Galaxy.currHistoryPanel ){
                    thisMenuOption.checked = Galaxy.currHistoryPanel.toggleShowDeleted();
                }
            },
            "${_("Include Hidden Datasets")}": function( clickEvent, thisMenuOption ) {
                if( Galaxy && Galaxy.currHistoryPanel ){
                    thisMenuOption.checked = Galaxy.currHistoryPanel.toggleShowHidden();
                }
            },
            "${_("Unhide Hidden Datasets")}": function() {
                if ( confirm( "Really unhide all hidden datasets?" ) ) {
                    galaxy_main.location = "${h.url_for( controller='history', action='unhide_datasets', current=True )}";
                }
            },
            "${_("Delete Hidden Datasets")}": function() {
                if ( confirm( "Really delete all hidden datasets?" ) ) {
                    galaxy_main.location = "${h.url_for( controller='history', action='delete_hidden_datasets')}";
                }
            },
            "${_("Purge Deleted Datasets")}": function() {
                if ( confirm( "Really delete all deleted datasets permanently? This cannot be undone." ) ) {
                    galaxy_main.location = "${h.url_for( controller='history', action='purge_deleted_datasets' )}";
                    // update the user disk size when the purge page loads
                    $( '#galaxy_main' ).load( function(){
                        Galaxy.user.fetch();
                    })
                }
            },
            "${_("Show Structure")}": function() {
                galaxy_main.location = "${h.url_for( controller='history', action='display_structured' )}";
            },            
            "${_("Export Citations")}": function() {
                galaxy_main.location = "${h.url_for( controller='history', action='citations' )}";
            },
            "${_("Export to File")}": function() {
                galaxy_main.location = "${h.url_for( controller='history', action='export_archive', preview=True )}";
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
        Galaxy.historyOptionsMenu = popupmenu;

        // Fix iFrame scrolling on iOS
        if( navigator.userAgent.match( /(iPhone|iPod|iPad)/i ) ) {
            $("iframe").parent().css( {
                "overflow": "scroll",
                "-webkit-overflow-scrolling": "touch"
            })
        }

    });
    </script>
</%def>

<%def name="init()">
<%
    self.has_left_panel = True
    self.has_right_panel = True
    self.active_view = "analysis"
    self.require_javascript = True
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
            ${n_('Tools')}
        </div>
    </div>
    <div class="unified-panel-body" style="overflow: auto">
        ${render_tool_menu()}
    </div>
</%def>

<%def name="center_panel()">

    ## If a specific tool id was specified, load it in the middle frame
    <%
    if trans.app.config.require_login and not trans.user:
        center_url = h.url_for( controller='user', action='login' )
    elif tool_id is not None:
        center_url = h.url_for( 'tool_runner', tool_id=tool_id, from_noframe=True, **params )
    elif workflow_id is not None:
        center_url = h.url_for( controller='workflow', action='run', id=workflow_id )
    elif m_c is not None:
        center_url = h.url_for( controller=m_c, action=m_a )
    else:
        center_url = h.url_for( controller="root", action="welcome" )
    %>
    
    <div style="position: absolute; width: 100%; height: 100%">
        <iframe name="galaxy_main" id="galaxy_main" frameborder="0"
                style="position: absolute; width: 100%; height: 100%;" src="${center_url}"></iframe>
    </div>

</%def>

<%def name="right_panel()">
    <!-- current history panel -->
    <div class="unified-panel-header" unselectable="on">
        <div class="unified-panel-header-inner">
            <div style="float: right">
                <a id="history-refresh-button" class='panel-header-button' href="javascript:void(0)"
                   title="${ _( 'Refresh history' ) }">
                    <span class="fa fa-refresh"></span>
                </a>
                <a id="history-options-button" class='panel-header-button'
                   href="${h.url_for( controller='root', action='history_options' )}" target="galaxy_main"
                   title="${ _( 'History options' ) }">
                    <span class="fa fa-cog"></span>
                </a>
            </div>
            <div class="panel-header-text">${_('History')}</div>
        </div>
    </div>
    <div class="unified-panel-body">
        <div id="current-history-panel" class="history-panel"></div>
        ## Don't bootstrap data here - confuses the browser history: load via API
        <script type="text/javascript">
        require([ "mvc/history/history-panel-edit-current" ], function( historyPanel ){
            $(function(){
                var currPanel = new historyPanel.CurrentHistoryPanel({
                    el              : $( "#current-history-panel" ),
                    purgeAllowed    : Galaxy.config.allow_user_dataset_purge,
                    linkTarget      : 'galaxy_main',
                    $scrollContainer: function(){ return this.$el.parent(); }
                });
                currPanel
                    .connectToQuotaMeter( Galaxy.quotaMeter )
                    .connectToOptionsMenu( Galaxy.historyOptionsMenu );
                currPanel.loadCurrentHistory();
                Galaxy.currHistoryPanel = currPanel;
            });
        });
        </script>
        <script type="text/javascript">
            $(function(){
                $( '#history-refresh-button' )
                    .on( 'click', function(){
                        if( top.Galaxy && top.Galaxy.currHistoryPanel ){
                            top.Galaxy.currHistoryPanel.loadCurrentHistory();
                            inside_galaxy_frameset = true;
                        }
                    });
            });
        </script>
    </div>
</%def>
