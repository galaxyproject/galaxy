/**
 *  This class renders the chart configuration form.
 */
define( [ 'mvc/ui/ui-table', 'mvc/ui/ui-misc', 'mvc/form/form-view', 'mvc/form/form-repeat', 'utils/utils' ], function( Table, Ui, Form, Repeat, Utils ) {
    var GroupView = Backbone.View.extend({
        initialize: function( app, options ) {
            var self = this;
            this.app = app;
            this.chart = app.chart;
            this.group = options.group;
            this.setElement( $( '<div/>' ) );
            this.chart.on( 'change:dataset_id change:type', function() { self.render() } );
            this.group.on( 'change', function() { self.form && self.form.data.set( self.group ) } );
            this.render();
        },

        render: function() {
            var self = this;
            var inputs = this.chart.definition.series && this.chart.definition.series.slice() || [];
            _.each( this.chart.definition.columns, function( column, name ) {
                inputs.push( { name: name, label: column.title, type: 'select' } );
            });
            this.form = new Form( {
                inputs  : inputs,
                cls     : 'ui-portlet-plain'
            } );
            this.$el.empty().append( this.form.$el );
            var dataset_id = this.chart.get( 'dataset_id' );
            var chart_type = this.chart.get( 'type' );
            var chart_definition = this.chart.definition;
            if ( dataset_id && chart_type ) {
                this.chart.state( 'wait', 'Loading metadata...' );
                this.app.deferred.execute( function( process ) {
                    self.app.datasets.request({
                        id      : dataset_id,
                        success : function( dataset ) {
                            for ( var id in chart_definition.columns ) {
                                var index = self.form.data.match( id );
                                if ( index ) {
                                    var columns = [];
                                    var select = self.form.field_list[ index ];
                                    var input_def = chart_definition.columns[ id ];
                                    input_def.is_auto && columns.push( { 'label': 'Column: Row Number', 'value': 'auto' } );
                                    input_def.is_zero && columns.push( { 'label' : 'Column: None', 'value' : 'zero' } );
                                    var meta = dataset.metadata_column_types;
                                    for ( var key in meta ) {
                                        var valid = ( [ 'int', 'float' ].indexOf( meta[ key ] ) != -1 && input_def.is_numeric ) || input_def.is_text || input_def.is_label;
                                        valid && columns.push( { 'label' : 'Column: ' + ( parseInt( key ) + 1 ), 'value' : key } );
                                    }
                                    select.update( columns );
                                    self.group.set( id, select.value( self.group.get( id ) ) );
                                }
                            }
                            self.chart.state( 'ok', 'Metadata initialized...' );
                            self.form.data.set( self.group );
                            self.form.setOnChange( function() {
                                self.group.set( self.form.data.create() );
                                self.chart.set( 'modified', true );
                            });
                            process.resolve();
                        }
                    });
                });
            }
        }
    });

    return Backbone.View.extend({
        initialize: function( app ) {
            var repeat = new Repeat.View({
                title       : 'Data series',
                title_new   : 'Data series',
                min         : 1,
                onnew       : function() { app.chart.groups.add( { id : Utils.uid() } ) }
            });
            this.setElement( repeat.$el );
            app.chart.groups.on( 'add remove reset', function() { app.chart.set( 'modified', true ) } )
                            .on( 'remove', function( group ) { repeat.del( group.id ) } )
                            .on( 'reset', function() { repeat.delAll() } )
                            .on( 'add', function( group ) {
                                repeat.add({
                                    id      : group.id,
                                    cls     : 'ui-portlet-panel',
                                    $el     : ( new GroupView( app, { group: group } ) ).$el,
                                    ondel   : function() { app.chart.groups.remove( group ) }
                                });
                            });
        }
    });
});