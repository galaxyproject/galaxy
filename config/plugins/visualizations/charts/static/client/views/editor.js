/**
 *  The charts editor holds the tabs for selecting chart types, chart configuration
 *  and data group selections.
 */
define( [ 'mvc/ui/ui-tabs', 'mvc/ui/ui-misc', 'mvc/ui/ui-portlet', 'mvc/ui/ui-thumbnails', 'utils/utils', 'plugin/views/settings', 'plugin/views/groups' ],
    function( Tabs, Ui, Portlet, Thumbnails, Utils, SettingsView, GroupsView ) {
    return Backbone.View.extend({
        initialize: function( app, options ){
            var self = this;
            this.app = app;
            this.chart = this.app.chart;
            this.message = new Ui.Message( { cls: 'ui-margin-bottom' } );
            this.portlet = new Portlet.View({
                icon : 'fa-bar-chart-o',
                title: 'Editor',
                operations      : {
                    'draw'  : new Ui.ButtonIcon({
                        icon    : 'fa-line-chart',
                        tooltip : 'Render Visualization',
                        title   : 'Visualize',
                        onclick : function() {
                            self._drawChart();
                        }
                    }),
                    'back'  : new Ui.ButtonIcon({
                        icon    : 'fa-caret-left',
                        tooltip : 'Return to Viewer',
                        title   : 'Cancel',
                        onclick : function() {
                            self.app.go( 'viewer' );
                            self.chart.load();
                        }
                    })
                }
            });

            // grid with chart types
            this.types = new Thumbnails.View({
                title_default   : 'Suggested visualizations',
                title_list      : 'List of available visualizations',
                collection      : _.map( this.app.types, function( type, type_id ) {
                    return {
                        id          : type_id,
                        keywords    : type.keywords,
                        title       : type.title + ' (' + type.library + ')',
                        title_icon  : type.zoomable && 'fa-search-plus',
                        image_src   : repository_root + '/visualizations/' + self.app.split( type_id ) + '/logo.png',
                        description : type.description
                    }
                }),
                ondblclick      : function( chart_type ) { self._drawChart() },
                onchange        : function( chart_type ) {
                    var chart_definition = self.app.types[ chart_type ];
                    if ( !chart_definition ) {
                        self.tabs.hideTab( 'settings' );
                        self.tabs.hideTab( 'groups' );
                        self.portlet.hideOperation( 'draw' );
                        console.debug( 'editor::onchange() - Chart type not found.' );
                        self.message.update( { message: 'The requested visualization type could not be found. Please select a new type from below or contact us.', status: 'danger', persistent: true } );
                    } else {
                        self.tabs.showTab( 'settings' );
                        self.tabs.showTab( 'groups' );
                        self.portlet.showOperation( 'draw' );
                        self.chart.definition = chart_definition;
                        self.chart.set( { type : chart_type, modified : true } );
                        self.message.model.set( 'message', '' );
                        console.debug( 'editor::onchange() - Switched visualization type.' );
                    }
                }
            });

            // input field for chart title
            this.title = new Ui.Input({
                placeholder: 'Chart title',
                onchange: function() {
                    self.chart.set( 'title', self.title.value() );
                }
            });

            // create tabs
            this.tabs = new Tabs.View( {} );
            this.tabs.add({
                id      : 'main',
                title   : 'Start',
                icon    : 'fa fa-bars',
                tooltip : 'Start by selecting a visualization.',
                $el     : $( '<div/>' ).append( ( new Ui.Label( { title : 'Provide a title:' } ).$el ) )
                                       .append( this.title.$el )
                                       .append( $( '<div/>' ).addClass( 'ui-form-info ui-margin-bottom' ).html( 'This title will appear in the list of \'Saved Visualizations\'.' ) )
                                       .append( ( new Ui.Label( { title : 'Select a visualization:' } ).$el.addClass( 'ui-margin-top' ) ) )
                                       .append( this.types.$el )
            });
            this.tabs.add({
                id      : 'settings',
                title   : 'Customize',
                icon    : 'fa-gear',
                tooltip : 'Customize the visualization.',
                $el     : ( new SettingsView( this.app ) ).$el
            });
            this.tabs.add({
                id      : 'groups',
                title   : 'Select data',
                icon    : 'fa-database',
                tooltip : 'Specify data options.',
                $el     : ( new GroupsView( this.app ) ).$el
            });

            // set elements
            this.portlet.append( this.message.$el );
            this.portlet.append( this.tabs.$el.addClass( 'ui-margin-top-large' ) );
            this.portlet.hideOperation( 'back' );
            this.setElement( this.portlet.$el );

            // chart events
            this.listenTo( this.chart, 'change:title', function( chart ) { self._refreshTitle() } );
            this.listenTo( this.chart, 'change:type', function( chart ) { self.types.value( chart.get( 'type' ) ) } );
            this.listenTo( this.chart, 'redraw', function( chart ) { self.portlet.showOperation( 'back' ) } );
            this.chart.reset();
        },

        /** Show editor */
        show: function() {
            this.$el.show();
        },

        /** Hide editor */
        hide: function() {
            this.$el.hide();
        },

        /** Refresh title handler */
        _refreshTitle: function() {
            var title = this.chart.get( 'title' );
            this.portlet.title( title );
            this.title.value( title );
        },

        /** Draw chart data */
        _drawChart: function() {
            var self = this;
            this.chart.set({
                type        : this.types.value(),
                title       : this.title.value(),
                date        : Utils.time()
            });
            if ( this.chart.groups.length == 0 ) {
                this.message.update( { message: 'Please specify data options before rendering the visualization.', persistent: false } );
                this.tabs.show( 'groups' );
                return;
            }
            var valid = true;
            var chart_def = this.chart.definition;
            this.chart.groups.each( function( group ) {
                if ( valid ) {
                    _.each( group.get( '__data_columns' ), function( data_columns, name ) {
                        if ( group.attributes[ name ] === null ) {
                            self.message.update( { status: 'danger', message: 'This visualization type requires column types not found in your tabular file.', persistent: false } );
                            self.tabs.show( 'groups' );
                            valid = false;
                        }
                    });
                }
            });
            if ( valid ) {
                this.app.go( 'viewer' );
                this.app.deferred.execute( function() {
                    self.chart.trigger( 'redraw' );
                });
            }
        }
    });
});