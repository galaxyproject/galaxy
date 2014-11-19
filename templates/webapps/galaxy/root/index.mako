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
    
    $(function(){
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
        <div class="unified-panel-header-inner history-panel-header">
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
                %if trans.user:
                <a id="history-view-multi-button" class='panel-header-button'
                   href="${h.url_for( controller='history', action='view_multiple' )}"
                   title="${ _( 'View all histories' ) }">
                    <span class="fa fa-caret-square-o-right"></span>
                </a>
                %endif
            </div>
            <div class="panel-header-text">${_('History')}</div>
        </div>
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
            require([ 'mvc/history/options-menu' ], function( optionsMenu ){
                $(function(){
                    //##TODO: Galaxy is not reliably available here since index doesn't use app
                    var popupmenu = optionsMenu( $( "#history-options-button" ), {
                            anonymous    : ${ 'true' if not trans.user else 'false' },
                            purgeAllowed : ${ 'true' if trans.app.config.allow_user_dataset_purge else 'false' },
                            root         : '${ h.url_for( "/" ) }'
                        });
                    Galaxy.historyOptionsMenu = popupmenu;
                });
            });
        </script>
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
                    currPanel.connectToQuotaMeter( Galaxy.quotaMeter );
                    currPanel.loadCurrentHistory();
                    Galaxy.currHistoryPanel = currPanel;
                });
            });
        </script>
    </div>
</%def>
