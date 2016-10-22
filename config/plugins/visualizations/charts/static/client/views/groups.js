/** This class renders the chart data selection form with repeats. */
define( [ 'utils/utils', 'mvc/ui/ui-misc', 'mvc/form/form-view', 'mvc/form/form-repeat', 'mvc/form/form-data', 'plugin/views/description' ],
    function( Utils, Ui, Form, Repeat, FormData, Description ) {
    var GroupView = Backbone.View.extend({
        initialize: function( app, options ) {
            var self = this;
            this.app    = app;
            this.chart  = app.chart;
            this.group  = options.group;
            this.setElement( $( '<div/>' ) );
            this.listenTo( this.chart, 'change:dataset_id change:type', function() { self.render() } );
            this.render();
        },

        render: function() {
            var self = this;
            var inputs = this.chart.definition.groups ? Utils.clone( this.chart.definition.groups ) : {};
            var dataset_id = this.chart.get( 'dataset_id' );
            var chart_type = this.chart.get( 'type' );
            var chart_definition = this.chart.definition;
            if ( dataset_id && chart_type ) {
                this.chart.state( 'wait', 'Loading metadata...' );
                this.app.deferred.execute( function( process ) {
                    Utils.get({
                        url     : Galaxy.root + 'api/datasets/' + dataset_id,
                        cache   : true,
                        success : function( dataset ) {
                            var data_columns = {};
                            FormData.visitInputs( inputs, function( input, prefixed ) {
                                if ( input.type == 'data_column' ) {
                                    data_columns[ prefixed ] = Utils.clone( input );
                                    var columns = [];
                                    input.is_auto && columns.push( { 'label': 'Column: Row Number', 'value': 'auto' } );
                                    input.is_zero && columns.push( { 'label' : 'Column: None', 'value' : 'zero' } );
                                    var meta = dataset.metadata_column_types;
                                    for ( var key in meta ) {
                                        var valid = ( [ 'int', 'float' ].indexOf( meta[ key ] ) != -1 && input.is_numeric ) || input.is_label;
                                        valid && columns.push( { 'label' : 'Column: ' + ( parseInt( key ) + 1 ), 'value' : key } );
                                    }
                                    input.data = columns;
                                }
                                var model_value = self.group.get( prefixed );
                                model_value !== undefined && !input.hidden && ( input.value = model_value );
                            });
                            inputs[ '__data_columns' ] = { name: '__data_columns', type: 'hidden', hidden: true, value: data_columns };
                            self.chart.state( 'ok', 'Metadata initialized...' );
                            self.form = new Form( {
                                inputs  : inputs,
                                cls     : 'ui-portlet-plain',
                                onchange: function() {
                                    self.group.set( self.form.data.create() );
                                    self.chart.set( 'modified', true );
                                }
                            } );
                            self.group.set( self.form.data.create() );
                            self.$el.empty().append( self.form.$el );
                            process.resolve();
                        }
                    });
                });
            }
        }
    });

    return Backbone.View.extend({
        initialize: function( app ) {
            var self    = this;
            this.app    = app;
            this.chart  = app.chart;
            this.repeat = new Repeat.View({
                title       : 'Data series',
                title_new   : 'Data series',
                min         : 1,
                onnew       : function() { self.chart.groups.add( { id : Utils.uid() } ) }
            });
            this.description = new Description( this.app );
            this.message = new Ui.Message( { message : 'There are no options for this visualization type.', persistent : true, status : 'info' } );
            this.setElement( $( '<div/>' ).append( this.description.$el )
                                          .append( this.repeat.$el.addClass( 'ui-margin-bottom' ) )
                                          .append( this.message.$el.addClass( 'ui-margin-bottom' ) ) );
            this.listenTo( this.chart, 'change', function() { self.render() } );
            this.listenTo( this.chart.groups, 'add remove reset', function() { self.chart.set( 'modified', true ) } );
            this.listenTo( this.chart.groups, 'remove', function( group ) { self.repeat.del( group.id ) } );
            this.listenTo( this.chart.groups, 'reset', function() { self.repeat.delAll() } );
            this.listenTo( this.chart.groups, 'add', function( group ) {
                self.repeat.add({
                     id      : group.id,
                     cls     : 'ui-portlet-panel',
                     $el     : ( new GroupView( self.app, { group: group } ) ).$el,
                     ondel   : function() { self.chart.groups.remove( group ) }
                });
            });
        },

        render: function() {
            if ( _.size( this.chart.definition.groups ) > 0 ) {
                this.repeat.$el.show();
                this.message.$el.hide();
            } else {
                this.repeat.$el.hide();
                this.message.$el.show();
            }
        }
    });
});