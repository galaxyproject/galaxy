/**
 *  This class renders the chart configuration form.
 */
define( [ 'mvc/ui/ui-table', 'mvc/ui/ui-misc', 'mvc/form/form-parameters', 'utils/utils' ], function( Table, Ui, Parameters, Utils ) {
    return Backbone.View.extend({
        initialize: function( app, options ) {
            var self = this;
            this.app = app;
            this.chart = this.app.chart;
            this.list = [];
            this.parameters = new Parameters();
            this.table_title = new Ui.Label({});
            this.table = new Table.View( { content: 'This chart type does not provide any options.' } );
            this.setElement( $( '<div/>' ).addClass( 'ui-form' )
                                          .append( this.table_title.$el )
                                          .append( this.table.$el ) );
            this.chart.on( 'change', function() { self.render() } );
        },

        render: function() {
            var chart_definition = this.chart.definition;
            if ( chart_definition ) {
                this.table_title.title( chart_definition.category + ' - ' + chart_definition.title + ':' );
                this.table.delAll();
                this.list = [];
                var settings = chart_definition.settings;
                for ( var id in settings ) {
                    this._add( settings[ id ].id || id, settings[ id ], this.chart.settings );
                }
                for ( var id in this.list ) {
                    this.list[ id ].trigger('change');
                }
            }
        },

        /** Add table row */
        _add: function( name, settings_def, model ) {
            var self = this;
            if ( settings_def.type !== 'separator' ) {
                switch( settings_def.type ) {
                    case 'select':
                        settings_def.onchange = function( new_value ) {
                            model.set( name, new_value );
                            var dict = _.findWhere( settings_def.data, { value: new_value } );
                            if ( dict && dict.operations ) {
                                var operations = dict.operations;
                                for ( var i in operations.show ) {
                                    self.table.get( operations.show[ i ] ).fadeIn( 'fast' );
                                }
                                for ( var i in operations.hide ) {
                                    self.table.get( operations.hide[ i ] ).hide();
                                }
                            }
                        };
                        break;
                    default:
                        settings_def.onchange = function( new_value ) { model.set( name, new_value ) };
                }
                settings_def.id = name;
                settings_def.value = model.get( name ) || settings_def.init;
                model.set( name, settings_def.value );
                var field = this.parameters.create( settings_def );
                var $input = $( '<div/>' ).append( field.$el );
                settings_def.info && $input.append( $( '<div/>' ).addClass( 'ui-form-info' ).append( settings_def.info ) );
                this.table.add( $( '<span/>' ).addClass( 'ui-form-title' ).append( settings_def.title ), '20%' );
                this.table.add( $input );
                this.list[ name ] = field;
            } else {
                this.table.add( $( '<div/>' ).addClass( 'ui-form-separator' ).append( settings_def.title + ':' ) );
                this.table.add( $( '<div/>' ) );
            }
            this.table.append( name );
            settings_def.hide && this.table.get( name ).hide();
        }
    });
});