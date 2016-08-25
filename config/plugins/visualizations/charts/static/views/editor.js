/**
 *  The charts editor holds the tabs for selecting chart types, chart configuration
 *  and data group selections.
 */
define( [ 'mvc/ui/ui-tabs', 'mvc/ui/ui-misc', 'mvc/ui/ui-portlet', 'utils/utils', 'plugin/views/settings', 'plugin/views/groups', 'plugin/views/types' ],
    function( Tabs, Ui, Portlet, Utils, SettingsView, GroupsView, TypesView ) {
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
                    'save'  : new Ui.ButtonIcon({
                        icon    : 'fa-save',
                        tooltip : 'Draw Chart',
                        title   : 'Save and Draw',
                        onclick : function() {
                            self._saveChart();
                        }
                    }),
                    'back'  : new Ui.ButtonIcon({
                        icon    : 'fa-caret-left',
                        tooltip : 'Return to Viewer',
                        title   : 'Cancel',
                        onclick : function() {
                            self.app.go( 'viewer' );
                            self.app.storage.load();
                        }
                    })
                }
            });

            // grid with chart types
            this.types = new TypesView( app, {
                onchange   : function( chart_type ) {
                    var chart_definition = self.app.types[ chart_type ];
                    !chart_definition && console.debug( 'FAILED - Editor::onchange() - Chart type not supported.' );
                    self.chart.definition = chart_definition;
                    self.chart.set( { type : chart_type, modified : true } );
                    console.debug( 'Editor::onchange() - Switched chart type.' );
                },
                ondblclick  : function( chart_id ) {
                    self._saveChart();
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
                tooltip : 'Start by selecting a chart type.',
                $el     : $( '<div/>' ).append( ( new Ui.Label( { title : 'Provide a chart title:' } ).$el ) )
                                       .append( this.title.$el )
                                       .append( $( '<div/>' ).addClass( 'ui-form-info ui-margin-bottom' ).html( 'This title will appear in the list of \'Saved Visualizations\'. Charts are saved upon creation.' ) )
                                       .append( ( new Ui.Label( { title : 'Select a chart type:' } ).$el.addClass( 'ui-margin-top' ) ) )
                                       .append( this.types.$el )
            });
            this.tabs.add({
                id      : 'settings',
                title   : 'Customize',
                icon    : 'fa-gear',
                tooltip : 'Customize chart options.',
                $el     : ( new SettingsView( this.app ) ).$el
            });
            this.tabs.add({
                id      : 'groups',
                title   : 'Select data',
                icon    : 'fa-database',
                tooltip : 'Specify your data options.',
                $el     : ( new GroupsView( this.app ) ).$el
            });

            // set elements
            this.portlet.append( this.message.$el );
            this.portlet.append( this.tabs.$el.addClass( 'ui-margin-top-large' ) );
            this.portlet.hideOperation( 'back' );
            this.setElement( this.portlet.$el );
            this.tabs.hideOperation( 'back' );

            // chart events
            this.chart.on( 'change:title', function( chart ) { self._refreshTitle() } );
            this.chart.on( 'change:type', function( chart ) { self.types.value( chart.get( 'type' ) ) } );
            this.chart.on( 'redraw', function( chart ) { self.portlet.showOperation( 'back' ) } );
            this.chart.reset( this.app.options );
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

        /** Save chart data */
        _saveChart: function() {
            var self = this;
            this.chart.set({
                type        : this.types.value(),
                title       : this.title.value(),
                date        : Utils.time()
            });
            if ( this.chart.groups.length == 0 ) {
                this.message.update( { message: 'Please specify data options before drawing the chart.' } );
                this.tabs.show( 'groups' );
                return;
            }
            var valid = true;
            var chart_def = this.chart.definition;
            this.chart.groups.each( function( group ) {
                if ( valid ) {
                    _.each( group.get( '__data_columns' ), function( data_columns, name ) {
                        if ( group.attributes[ name ] === null ) {
                            self.message.update( { status: 'danger', message: 'This chart type requires column types not found in your tabular file.' } );
                            self.tabs.show( 'groups' );
                            valid = false;
                        }
                    });
                }
            });
            if ( valid ) {
                this.app.go( 'viewer' );
                this.app.deferred.execute( function() {
                    self.app.storage.save();
                    self.chart.trigger( 'redraw' );
                });
            }
        }
    });
});