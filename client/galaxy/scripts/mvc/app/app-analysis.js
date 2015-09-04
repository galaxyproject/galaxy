define(['utils/utils', 'mvc/tools', 'mvc/upload/upload-view', 'mvc/ui/ui-misc', 'mvc/history/options-menu', 'mvc/history/history-panel-edit-current'],
    function( Utils, Tools, Upload, Ui, optionsMenu, HistoryPanel ) {

    // create form view
    var CenterPanel = Backbone.View.extend({
        // initialize
        initialize: function( options ) {
            this.options = Utils.merge( options, {} );
            this.setElement( this._template() );

            /*if trans.app.config.require_login and not trans.user:
                center_url = h.url_for( controller='user', action='login' )
            elif tool_id is not None:
                center_url = h.url_for( 'tool_runner', tool_id=tool_id, from_noframe=True, **params )
            elif workflow_id is not None:
                center_url = h.url_for( controller='workflow', action='run', id=workflow_id )
            elif m_c is not None:
                center_url = h.url_for( controller=m_c, action=m_a )
            else:
                    center_url = h.url_for( controller="root", action="welcome" )*/

            var src = 'welcome';
            window.console.log(Galaxy.config);
            if ( Galaxy.config.require_login && !Galaxy.user.valid ) {
                src = 'user/login';
            } else {
                if (true ) {
                }
            }
            this.$( '#galaxy_main' ).prop( 'src', galaxy_config.root + src );
        },

        _template: function() {
            return  '<div style="position: absolute; width: 100%; height: 100%">' +
                        '<iframe name="galaxy_main" id="galaxy_main" frameborder="0" style="position: absolute; width: 100%; height: 100%;"/>' +
                    '</div>';
        }
    });

    // create form view
    var LeftPanel = Backbone.View.extend({
        initialize: function( options ) {
            this.options = Utils.merge( options, {} );
            this.setElement( this._template() );

            // create tool search, tool panel, and tool panel view.
            if ( Galaxy.user.valid || !Galaxy.config.require_login ) {
                var tool_search = new Tools.ToolSearch({
                    spinner_url : options.spinner_url,
                    search_url  : options.search_url,
                    hidden      : false
                });
                var tools = new Tools.ToolCollection( options.toolbox );
                var tool_panel = new Tools.ToolPanel({
                    tool_search : tool_search,
                    tools       : tools,
                    layout      : options.toolbox_in_panel
                });
                tool_panel_view = new Tools.ToolPanelView({ model: tool_panel });
            
                // add tool panel to Galaxy object
                Galaxy.toolPanel = tool_panel;

                // if there are tools, render panel and display everything
                if (tool_panel.get( 'layout' ).size() > 0) {
                    tool_panel_view.render();
                    this.$( '.toolMenu' ).show();
                }
                this.$el.append( tool_panel_view.$el );

                // minsize init hint
                this.$( 'a[minsizehint]' ).click( function() {
                    if ( parent.handle_minwidth_hint ) {
                        parent.handle_minwidth_hint( $(this).attr( 'minsizehint' ) );
                    }
                });

                // add upload plugin
                Galaxy.upload = new Upload( options );

                // define components (is used in app-view.js)
                this.components = {
                    header  : {
                        title   : 'Tools',
                        buttons : [ Galaxy.upload ]
                    }
                }
            }
        },

        _template: function() {
            return  '<div class="toolMenuContainer">' +
                        '<div class="toolMenu" style="display: none">' +
                            '<div id="search-no-results" style="display: none; padding-top: 5px">' +
                                '<em><strong>Search did not match any tools.</strong></em>' +
                            '</div>' +
                        '</div>' +
                    '</div>';
            /*%if t.user:
                <div class="toolSectionPad"></div>
                <div class="toolSectionPad"></div>
                <div class="toolSectionTitle" id="title_XXinternalXXworkflow">
                  <span>Workflows</span>
                </div>
                <div id="XXinternalXXworkflow" class="toolSectionBody">
                    <div class="toolSectionBg">
                        %if t.user.stored_workflow_menu_entries:
                            %for m in t.user.stored_workflow_menu_entries:
                                <div class="toolTitle">
                                    <a href="${h.url_for( controller='workflow', action='run', id=trans.security.encode_id(m.stored_workflow_id) )}" target="galaxy_main">${ util.unicodify( m.stored_workflow.name ) | h}</a>
                                </div>
                            %endfor
                        %endif
                        <div class="toolTitle">
                            <a href="${h.url_for( controller='workflow', action='list_for_run')}" target="galaxy_main">All workflows</a>
                        </div>
                    </div>
                </div>
            %endif*/
        }
    });

    var RightPanel = Backbone.View.extend({
        initialize: function(options) {
            this.options = Utils.merge( options, {} );
            this.setElement( this._template() );

            // build buttons
            var buttonRefresh = new Ui.ButtonLink({
                id      : 'history-refresh-button',
                title   : 'Refresh history',
                cls     : 'panel-header-button',
                icon    : 'fa fa-refresh',
                onclick : function() {
                    if( top.Galaxy && top.Galaxy.currHistoryPanel ) {
                        top.Galaxy.currHistoryPanel.loadCurrentHistory();
                    }
                }
            });
            var buttonOptions = new Ui.ButtonLink({
                id      : 'history-options-button',
                title   : 'History options',
                cls     : 'panel-header-button',
                target  : 'galaxy_main',
                icon    : 'fa fa-cog',
                href    : Galaxy.root + 'root/history_options'
            });
            var buttonViewMulti = new Ui.ButtonLink({
                id      : 'history-view-multi-button',
                title   : 'View all histories',
                cls     : 'panel-header-button',
                icon    : 'fa fa-columns',
                href    : Galaxy.root + 'history/view_multiple'
            });

            // define components (is used in app-view.js)
            this.components = {
                header  : {
                    title   : 'History',
                    cls     : 'history-panel-header',
                    buttons : [ buttonRefresh, buttonOptions, buttonViewMulti ]
                },
                body    : {
                    cls     : 'unified-panel-body-background',
                }
            }

            // build history options menu
            Galaxy.historyOptionsMenu = optionsMenu( buttonOptions.$el, {
                anonymous    : options.user.valid && 'true' || 'false',
                purgeAllowed : Galaxy.config.allow_user_dataset_purge && 'true' || 'false',
                root         : Galaxy.root
            });

            // load current history
            Galaxy.currHistoryPanel = new HistoryPanel.CurrentHistoryPanel({
                el              : this.$el,
                purgeAllowed    : Galaxy.config.allow_user_dataset_purge,
                linkTarget      : 'galaxy_main',
                $scrollContainer: function(){ return this.$el.parent(); }
            });
            Galaxy.currHistoryPanel.connectToQuotaMeter( Galaxy.quotaMeter );
            Galaxy.currHistoryPanel.listenToGalaxy( Galaxy );
            Galaxy.currHistoryPanel.loadCurrentHistory();
        },

        // body template
        _template: function() {
            return '<div id="current-history-panel" class="history-panel"/>';
        }
    });

    return {
        left    : LeftPanel,
        center  : CenterPanel,
        right   : RightPanel
    }
});
