var jQuery = require( 'jquery' ),
    $ = jQuery,
    GalaxyApp = require( 'galaxy' ).GalaxyApp,
    QUERY_STRING = require( 'utils/query-string-parsing' ),
    ToolPanel = require( './panels/tool-panel' ),
    HistoryPanel = require( './panels/history-panel' ),
    Page = require( 'layout/page' ),
    ToolForm = require( 'mvc/tool/tool-form' ),
    UserPreferences = require( 'mvc/user/user-preferences' ),
    CustomBuilds = require( 'mvc/user/user-custom-builds' ),
    Tours = require( 'mvc/tours' ),
    GridView = require( 'mvc/grid/grid-view' ),
    GridShared = require( 'mvc/grid/grid-shared' ),
    Workflows = require( 'mvc/workflow/workflow' ),
    HistoryList = require( 'mvc/history/history-list' ),
    WorkflowsConfigureMenu = require( 'mvc/workflow/workflow-configure-menu' ),
    ToolFormComposite = require( 'mvc/tool/tool-form-composite' ),
    Utils = require( 'utils/utils' ),
    Ui = require( 'mvc/ui/ui-misc' );

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
    Galaxy.params = Galaxy.config.params;

    var routingMessage = Backbone.View.extend({
        initialize: function(options) {
            this.message = options.message || "Undefined Message";
            this.msg_status = options.type || 'info';
            this.render();
		},
        render: function(){
            this.$el.html(_.escape(this.message)).addClass(this.msg_status + "message");
        }
    });

    /** Routes */
    var Router = Backbone.Router.extend({
        // TODO: not many client routes at this point - fill and remove from server.
        // since we're at root here, this may be the last to be routed entirely on the client.
        initialize : function( page, options ){
            this.page = page;
            this.options = options;
        },

        /** helper to push a new navigation state */
        push: function( url, data ) {
            data = data || {};
            data.__identifer = Math.random().toString( 36 ).substr( 2 );
            if ( !$.isEmptyObject( data ) ) {
                url += url.indexOf( '?' ) == -1 ? '?' : '&';
                url += $.param( data , true );
            }
            this.navigate( url, { 'trigger': true } );
        },

        /** override to parse query string into obj and send to each route */
        execute: function( callback, args, name ){
            Galaxy.debug( 'router execute:', callback, args, name );
            var queryObj = QUERY_STRING.parse( args.pop() );
            args.push( queryObj );
            if( callback ){
                if ( this.authenticate( args, name ) ) {
                    callback.apply( this, args );
                } else {
                    this.loginRequired();
                }
            }
        },

        routes : {
            '(/)' : 'home',
            '(/)root*' : 'home',
            '(/)tours(/)(:tour_id)' : 'show_tours',
            '(/)user(/)' : 'show_user',
            '(/)user(/)(:form_id)' : 'show_user_form',
            '(/)workflow(/)' : 'show_workflows',
            '(/)workflow/run(/)' : 'show_run',
            '(/)pages(/)(:action_id)' : 'show_pages',
            '(/)visualizations/(:action_id)' : 'show_visualizations',
            '(/)workflows/list_published(/)' : 'show_workflows_published',
            '(/)histories(/)(:action_id)' : 'show_histories',
            '(/)datasets(/)list(/)' : 'show_datasets',
            '(/)workflow/configure_menu(/)' : 'show_configure_menu',
            '(/)workflow/import_workflow' : 'show_import_workflow',
            '(/)custom_builds' : 'show_custom_builds'
        },

        require_login: [
            'show_user',
            'show_user_form',
            'show_workflows',
            'show_configure_menu'
        ],

        loginRequired: function() {
            this.page.display( new routingMessage({type: 'error', message: "You must be logged in to make this request."}) );
        },

        authenticate: function( args, name ) {
            return ( Galaxy.user && Galaxy.user.id ) || this.require_login.indexOf( name ) == -1;
        },

        show_tours : function( tour_id ){
            if ( tour_id ){
                Tours.giveTour( tour_id );
            } else {
                this.page.display( new Tours.ToursView() );
            }
        },

        show_user : function(){
            this.page.display( new UserPreferences.View() );
        },

        show_user_form : function( form_id ) {
            this.page.display( new UserPreferences.Forms( { form_id: form_id, user_id: Galaxy.params.id } ) );
        },

        show_visualizations : function( action_id ) {
            this.page.display( new GridShared.View( { action_id: action_id, plural: 'Visualizations', item: 'visualization' } ) );
        },

        show_workflows_published : function() {
            this.page.display( new GridView( { url_base: Galaxy.root + 'workflow/list_published', dict_format: true } ) );
        },

        show_histories : function( action_id ) {
            this.page.display( new HistoryList.View( { action_id: action_id } ) );
        },

        show_datasets : function() {
            this.page.display( new GridView( { url_base: Galaxy.root + 'dataset/list', dict_format: true } ) );
        },

        show_pages : function( action_id ) {
            this.page.display( new GridShared.View( { action_id: action_id, plural: 'Pages', item: 'page' } ) );
        },

        show_workflows : function(){
            this.page.display( new Workflows.View() );
        },

        show_run : function() {
            this._loadWorkflow();
        },

        show_import_workflow : function() {
            this.page.display( new Workflows.ImportWorkflowView() );
        },

        show_configure_menu : function(){
            this.page.display( new WorkflowsConfigureMenu.View() );
        },

        show_custom_builds : function() {
            var self = this;
            var historyPanel = this.page.historyPanel.historyView;
            if ( !historyPanel || !historyPanel.model || !historyPanel.model.id ) {
                window.setTimeout(function() { self.show_custom_builds() }, 500)
                return;
            }
            this.page.display( new CustomBuilds.View() );
        },

        /**  */
        home : function( params ){
            // TODO: to router, remove Globals
            // load a tool by id (tool_id) or rerun a previous tool execution (job_id)
            if( params.tool_id || params.job_id ) {
                if ( params.tool_id === 'upload1' ) {
                    this.page.toolPanel.upload.show();
                    this._loadCenterIframe( 'welcome' );
                } else {
                    this._loadToolForm( params );
                }
            } else {
                // show the workflow run form
                if( params.workflow_id ){
                    this._loadWorkflow();
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
            params.id = decodeURIComponent( params.tool_id );
            this.page.display( new ToolForm.View( params ) );
        },

        /** load the center panel iframe using the given url */
        _loadCenterIframe : function( url, root ){
            root = root || Galaxy.root;
            url = root + url;
            this.page.$( '#galaxy_main' ).prop( 'src', url );
        },

        /** load workflow by its url in run mode */
        _loadWorkflow: function() {
            var self = this;
            Utils.get({
                url: Galaxy.root + 'api/workflows/' + Utils.getQueryString( 'id' ) + '/download',
                data: { 'style': 'run' },
                success: function( response ) {
                    self.page.display( new ToolFormComposite.View( response ) );
                },
                error: function( response ) {
                    var error_msg = "Error occurred while loading the resource.",
                        options = { 'message': error_msg, 'status': 'error', 'persistent': true, 'cls': 'errormessage' };
                    self.page.display( new Ui.Message( options ) );
                }
            });
        }
    });

    // render and start the router
    $(function(){

        Galaxy.page = new Page.View( _.extend( options, {
            Left   : ToolPanel,
            Right  : HistoryPanel,
            Router : Router
        } ) );

        // start the router - which will call any of the routes above
        Backbone.history.start({
            root        : Galaxy.root,
            pushState   : true,
        });
    });
};
