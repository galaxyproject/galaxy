
var jQuery = require( 'jquery' ),
    $ = jQuery,
    GalaxyApp = require( 'galaxy' ).GalaxyApp,
    QUERY_STRING = require( 'utils/query-string-parsing' ),
    PANEL = require( 'layout/panel' ),
    ToolPanel = require( './tool-panel' ),
    HistoryPanel = require( './history-panel' ),
    PAGE = require( 'layout/page' ),
    ToolForm = require( 'mvc/tool/tool-form' ),
    UserPreferences = require( 'mvc/user/user-preferences' );
    Tours = require( 'mvc/tours' );

/** define the 'Analyze Data'/analysis/main/home page for Galaxy
 *  * has a masthead
 *  * a left tool menu to allow the user to load tools in the center panel
 *  * a right history menu that shows the user's current data
 *  * a center panel
 *  Both panels (generally) persist while the center panel shows any
 *  UI needed for the current step of an analysis, like:
 *      * tool forms to set tool parameters,
 *      * tables showing the contents of datasets
 *      * etc.
 */
window.app = function app( options, bootstrapped ){
    window.Galaxy = new GalaxyApp( options, bootstrapped );
    Galaxy.debug( 'analysis app' );
    // TODO: use router as App base (combining with Galaxy)

    // .................................................... panels and page
    var config = options.config,
        toolPanel = new ToolPanel({
            el                  : '#left',
            userIsAnonymous     : Galaxy.user.isAnonymous(),
            toolbox             : config.toolbox,
            toolbox_in_panel    : config.toolbox_in_panel,
            stored_workflow_menu_entries : config.stored_workflow_menu_entries,
            nginx_upload_path   : config.nginx_upload_path,
            ftp_upload_site     : config.ftp_upload_site,
            default_genome      : config.default_genome,
            default_extension   : config.default_extension,
        }),
        centerPanel = new PANEL.CenterPanel({
            el              : '#center'
        }),
        historyPanel = new HistoryPanel({
            el              : '#right',
            galaxyRoot      : Galaxy.root,
            userIsAnonymous : Galaxy.user.isAnonymous(),
            allow_user_dataset_purge: config.allow_user_dataset_purge,
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
    Galaxy.currHistoryPanel.listenToGalaxy( Galaxy );

    //HACK: move there
    Galaxy.app = {
        display : function( view, target ){
            // TODO: Remove this line after select2 update
            $( '.select2-hidden-accessible' ).remove();
            centerPanel.display( view );
        },
    };

    // .................................................... routes
    /**  */
    Galaxy.router = new ( Backbone.Router.extend({
        // TODO: not many client routes at this point - fill and remove from server.
        // since we're at root here, this may be the last to be routed entirely on the client.
        initialize : function( options ){
            this.options = options;
        },

        /** override to parse query string into obj and send to each route */
        execute: function( callback, args, name ){
            Galaxy.debug( 'router execute:', callback, args, name );
            var queryObj = QUERY_STRING.parse( args.pop() );
            args.push( queryObj );
            if( callback ){
                callback.apply( this, args );
            }
        },

        routes : {
            '(/)' : 'home',
            // TODO: remove annoying 'root' from root urls
            '(/)root*' : 'home',
            '(/)tours(/)(:tour_id)' : 'show_tours',
            '(/)users(/)' : 'show_users',
        },

        show_tours : function( tour_id ){
            if ( tour_id ){
                Tours.giveTour( tour_id );
            } else {
                centerPanel.display( new Tours.ToursView() );
            }
        },

        show_users : function(){
            centerPanel.display( new UserPreferences.View() );
        },

        /**  */
        home : function( params ){
            // TODO: to router, remove Globals
            // load a tool by id (tool_id) or rerun a previous tool execution (job_id)
            if( params.tool_id || params.job_id ) {
                if ( params.tool_id === 'upload1' ) {
                    Galaxy.upload.show();
                    this._loadCenterIframe( 'welcome' );
                } else {
                    this._loadToolForm( params );
                }
            } else {
                // show the workflow run form
                if( params.workflow_id ){
                    this._loadCenterIframe( 'workflow/run?id=' + params.workflow_id );
                // load the center iframe with controller.action: galaxy.org/?m_c=history&m_a=list -> history/list
                } else if( params.m_c ){
                    this._loadCenterIframe( params.m_c + '/' + params.m_a );
                // show the workflow run form
                } else {
                    this._loadCenterIframe( 'welcome' );
                }
            }
        },

        /** load the center panel with a tool form described by the given params obj */
        _loadToolForm : function( params ){
            //TODO: load tool form code async
            params.id = params.tool_id;
            centerPanel.display( new ToolForm.View( params ) );
        },

        /** load the center panel iframe using the given url */
        _loadCenterIframe : function( url, root ){
            root = root || Galaxy.root;
            url = root + url;
            centerPanel.$( '#galaxy_main' ).prop( 'src', url );
        },

    }))( options );

    // .................................................... when the page is ready
    // render and start the router
    $(function(){
        analysisPage.render();
        analysisPage.right.historyView.loadCurrentHistory();

        // use galaxy to listen to history size changes and then re-fetch the user's total size (to update the quota meter)
        // TODO: we have to do this here (and after every page.render()) because the masthead is re-created on each
        // page render. It's re-created each time because there is no render function and can't be re-rendered without
        // re-creating it.
        Galaxy.listenTo( analysisPage.right.historyView, 'history-size-change', function(){
            // fetch to update the quota meter adding 'current' for any anon-user's id
            Galaxy.user.fetch({ url: Galaxy.user.urlRoot() + '/' + ( Galaxy.user.id || 'current' ) });
        });
        analysisPage.right.historyView.connectToQuotaMeter( analysisPage.masthead.quotaMeter );

        // start the router - which will call any of the routes above
        Backbone.history.start({
            root        : Galaxy.root,
            pushState   : true,
        });
    });
};
