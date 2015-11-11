define(['utils/utils', 'mvc/tools', 'mvc/upload/upload-view', 'mvc/ui/ui-misc',
        'mvc/history/options-menu', 'mvc/history/history-panel-edit-current', 'mvc/tools/tools-form'],
    function( Utils, Tools, Upload, Ui, optionsMenu, HistoryPanel, ToolsForm ) {

    /* Builds the center panel */
    var CenterPanel = Backbone.View.extend({
        initialize: function( options ) {
            this.options = Utils.merge( options, {} );
            this.setElement( this._template() );
            var self = this;
            this.$( '#galaxy_main' ).on( 'load', function() {
                var location = this.contentWindow && this.contentWindow.location;
                if ( location && location.host ) {
                    $( this ).show();
                    self.prev && self.prev.remove();
                    self.$( '#center-panel' ).hide();
                    Galaxy.trigger( 'galaxy_main:load', {
                        fullpath: location.pathname + location.search + location.hash,
                        pathname: location.pathname,
                        search  : location.search,
                        hash    : location.hash
                    });
                }
            });
            var params = $.extend( {}, Galaxy.params );
            if ( params.tool_id !== 'upload1' && ( params.tool_id || params.job_id ) ) {
                params.tool_id && ( params.id = params.tool_id );
                this.display( new ToolsForm.View( params ) );
            } else {
                this.$( '#galaxy_main' ).prop( 'src', Galaxy.root + (
                    ( params.workflow_id && ( 'workflow/run?id=' + params.workflow_id ) ) ||
                    ( params.m_c && ( params.m_c + '/' + params.m_a ) ) ||
                    'root/welcome'
                ));
            }
        },
        display: function( view ) {
            this.prev && this.prev.remove();
            this.prev = view;
            this.$( '#galaxy_main' ).hide();
            this.$( '#center-panel' ).scrollTop( 0 ).append( view.$el ).show();
        },
        _template: function() {
            return  '<div style="position: absolute; width: 100%; height: 100%">' +
                        '<iframe name="galaxy_main" id="galaxy_main" frameborder="0" style="position: absolute; width: 100%; height: 100%;"/>' +
                        '<div id="center-panel" style="position: absolute; width: 100%; height: 100%; padding: 10px; overflow: auto;"/>' +
                    '</div>';
        }
    });

    /* Builds the tool panel on the left */
    var LeftPanel = Backbone.View.extend({
        initialize: function( options ) {
            this.options = Utils.merge( options, {} );
            this.setElement( this._template() );
            // create tool search, tool panel, and tool panel view.
            if ( Galaxy.user.id || !Galaxy.config.require_login ) {
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
                this.$el.prepend( tool_panel_view.$el );

                // add internal workflow list
                this.$( '#internal-workflows' ).append( this._templateTool({
                    title   : 'All workflows',
                    href    : 'workflow/list_for_run'
                }) )
                for ( var i in options.stored_workflow_menu_entries ) {
                    var m = options.stored_workflow_menu_entries[ i ];
                    this.$( '#internal-workflows' ).append( this._templateTool({
                        title : m.stored_workflow.name,
                        href  : 'workflow/run?id=' + m.encoded_stored_workflow_id
                    }) );
                }

                // minsize init hint
                this.$( 'a[minsizehint]' ).click( function() {
                    if ( parent.handle_minwidth_hint ) {
                        parent.handle_minwidth_hint( $( this ).attr( 'minsizehint' ) );
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

        _templateTool: function( options ) {
            return  '<div class="toolTitle">' +
                        '<a href="' + Galaxy.root + options.href + '" target="galaxy_main">' + options.title + '</a>' +
                    '</div>';
        },

        _template: function() {
            return  '<div class="toolMenuContainer">' +
                        '<div class="toolMenu" style="display: none">' +
                            '<div id="search-no-results" style="display: none; padding-top: 5px">' +
                                '<em><strong>Search did not match any tools.</strong></em>' +
                            '</div>' +
                        '</div>' +
                        '<div class="toolSectionPad"/>' +
                        '<div class="toolSectionPad"/>' +
                        '<div class="toolSectionTitle" id="title_XXinternalXXworkflow">' +
                            '<span>Workflows</span>' +
                        '</div>' +
                        '<div id="internal-workflows" class="toolSectionBody">' +
                            '<div class="toolSectionBg"/>' +
                        '</div>' +
                    '</div>';
        }
    });

    /* Builds the history panel on the right */
    var RightPanel = Backbone.View.extend({
        initialize: function(options) {
            this.options = Utils.merge( options, {} );
            this.setElement( this._template() );

            var headerButtons = [];
            // this button re-fetches the history and contents and re-renders the history panel
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
            headerButtons.push( buttonRefresh );

            // opens a drop down menu with history related functions (like view all, delete, share, etc.)
            var buttonOptions = new Ui.ButtonLink({
                id      : 'history-options-button',
                title   : 'History options',
                cls     : 'panel-header-button',
                target  : 'galaxy_main',
                icon    : 'fa fa-cog',
                href    : Galaxy.root + 'root/history_options'
            });
            headerButtons.push( buttonOptions );

            // goes to a page showing all the users histories in panel form (for logged in users)
            if( !Galaxy.user.isAnonymous() ){
                var buttonViewMulti = new Ui.ButtonLink({
                    id      : 'history-view-multi-button',
                    title   : 'View all histories',
                    cls     : 'panel-header-button',
                    icon    : 'fa fa-columns',
                    href    : Galaxy.root + 'history/view_multiple'
                });
                headerButtons.push( buttonViewMulti );
            }

            // define components (is used in app-view.js)
            this.components = {
                header  : {
                    title   : 'History',
                    cls     : 'history-panel-header',
                    buttons : headerButtons
                },
                body    : {
                    cls     : 'unified-panel-body-background',
                }
            };

            // build history options menu
            Galaxy.historyOptionsMenu = optionsMenu( buttonOptions.$el, {
                anonymous    : Galaxy.user.isAnonymous(),
                purgeAllowed : Galaxy.config.allow_user_dataset_purge,
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
    };
});