
var jQuery = require( 'jquery' ),
    $ = jQuery,
    QUERY_STRING = require( 'utils/query-string-parsing' ),
    PANEL = require( 'layout/panel' ),
    ToolPanel = require( './tool-panel' ),
    HistoryPanel = require( './history-panel' ),
    PAGE = require( 'layout/page' ),
    ToolsForm = require( 'mvc/tool/tools-form' );

window.app = function app( options, bootstrapped ){
    Galaxy.debug( 'building app:', options, bootstrapped );

    // .................................................... panels and page
    var toolPanel = new ToolPanel({
            el              : '#left',
            userIsAnonymous : Galaxy.user.isAnonymous(),
            require_login   : options.config.require_login,
            spinner_url     : options.config.spinner_url,
            search_url      : options.config.search_url,
            toolbox         : options.config.toolbox,
            toolbox_in_panel: options.config.toolbox_in_panel,
            stored_workflow_menu_entries : options.config.stored_workflow_menu_entries,
        }),
        centerPanel = new PANEL.CenterPanel({
            el              : '#center'
        }),
        historyPanel = new HistoryPanel({
            el              : '#right',
            galaxyRoot      : Galaxy.root,
            userIsAnonymous : Galaxy.user.isAnonymous(),
            allow_user_dataset_purge: Galaxy.config.allow_user_dataset_purge,
        }),
        analysisPage = new PAGE.PageLayoutView( _.extend( options, {
            el              : 'body',
            left            : toolPanel,
            center          : centerPanel,
            right           : historyPanel,
        }));

    // .................................................... decorate the galaxy object
    // TODO: most of this is becoming unnecessary as we move to apps
    Galaxy.page = analysisPage;
    Galaxy.params = Galaxy.config.params;

    // add tool panel to Galaxy object
    Galaxy.toolPanel = toolPanel.tool_panel;
    Galaxy.upload = toolPanel.uploadButton;


    Galaxy.currHistoryPanel = historyPanel.historyView;
    Galaxy.currHistoryPanel.connectToQuotaMeter( Galaxy.quotaMeter );
    Galaxy.currHistoryPanel.listenToGalaxy( Galaxy );

    //HACK: move to router/App
    Galaxy.app = {
        display : function( view, target ){
            // TODO: Remove this line after select2 update
            $( '.select2-hidden-accessible' ).remove();
            centerPanel.display( view );
        },
    };

    /**  */
    var router = new ( Backbone.Router.extend({
        /**  */
        initialize : function( options ){
            this.options = options;
        },

        /**  */
        execute: function( callback, args, name ){
            Galaxy.debug( 'router execute:', callback, args, name );
            var queryObj = QUERY_STRING.parse( args.pop() );
            args.push( queryObj );
            if( callback ){
                callback.apply( this, args );
            }
        },

        /**  */
        routes : {
            '(/)' : 'home',
            // TODO: remove annoying 'root' from root urls
            '(/)root*' : 'home',
            // '(/root)?m_c=:controller&m_a=:action*' : 'navigateCenter',
            // '(/root)?tool_id=:id*' : 'toolForm',

            // TODO: as we add client-based routes, add them here
        },

        /**  */
        home : function( params ){
            // TODO: to router, remove Globals
            if( ( params.tool_id || params.job_id ) && params.tool_id !== 'upload1' ){
                this._loadToolForm( params );

            } else {
                if( params.workflow_id ){
                    this._loadCenterIframe( Galaxy.root + 'workflow/run?id=' + params.workflow_id );
                } else if( params.m_c ){
                    this._loadCenterIframe( Galaxy.root + params.m_c + '/' + params.m_a );
                } else {
                    this._loadCenterIframe( Galaxy.root + 'root/welcome' );
                }
            }
        },

        /**  */
        _loadToolForm : function( params ){
            //TODO: load tool form code async
            params.id = params.tool_id;
            centerPanel.display( new ToolsForm.View( params ) );
        },

        /**  */
        _loadCenterIframe : function( url ){
            centerPanel.$( '#galaxy_main' ).prop( 'src', url );
        },

    }))( options );

    $(function(){
        analysisPage
            .render()
            .right.historyView.loadCurrentHistory();

        // start the router - which will call any of the routes above
        Backbone.history.start({
            root        : Galaxy.root,
            pushState   : true,
        });
    });
};
