/**
 *  This class renders the data group selection fields.
 */
define([ 'mvc/ui/ui-table', 'mvc/ui/ui-misc', 'utils/utils' ], function( Table, Ui, Utils ) {
    return Backbone.View.extend({
        initialize: function( app, options ) {
            var self = this;
            this.app = app;
            this.chart = this.app.chart;
            this.group = options.group;
            this.group_key = new Ui.Input({
                placeholder: 'Data label',
                onchange: function( value ) {
                    self.group.set( 'key', value );
                }
            });
            this.table = new Table.View( { content: 'No data column.' } );
            this.setElement($('<div/>').append( ( new Ui.Label( { title: 'Provide a label:' } ) ).$el )
                                       .append( this.group_key.$el.addClass( 'ui-margin-bottom' ) )
                                       .append( ( new Ui.Label( { title: 'Select columns:' } ) ).$el.addClass( 'ui-margin-top' ) )
                                       .append( this.table.$el.addClass( 'ui-margin-bottom' ) ) );
            this.chart.on( 'change:dataset_id', function() { self._refreshTable() } );
            this.chart.on( 'change:type', function() { self._refreshTable() } );
            this.group.on( 'change:key', function() { self._refreshGroupKey() } );
            this.group.on( 'change', function() { self._refreshGroup() } );
            this._refreshTable();
            this._refreshGroupKey();
            this._refreshGroup();
        },

        /** Update group selection table */
        _refreshTable: function() {
            var self = this;
            var dataset_id = this.chart.get( 'dataset_id' );
            var chart_type = this.chart.get( 'type' );
            var chart_definition = this.chart.definition;
            if ( !dataset_id || !chart_type ) {
                return;
            }
            this.table.delAll();
            var select_list = {};
            for ( var id in chart_definition.columns ) {
                var data_def = chart_definition.columns[ id ];
                if ( !data_def ) {
                    console.debug( 'Group::_refreshTable() - Skipping column definition.' );
                    continue;
                }
                var select = new Ui.Select.View( { id : 'select_' + id } );
                var title = data_def.title;
                if ( data_def.is_unique ) {
                    title += '&nbsp;(all data labels)';
                }
                this.table.add( title, '25%' );
                this.table.add( select.$el );
                this.table.append( id );
                select_list[ id ] = select;
            }
            this.chart.state( 'wait', 'Loading metadata...' );
            this.app.deferred.execute( function( process ) {
                self.app.datasets.request({
                    id      : dataset_id,
                    success : function( dataset ) {
                        for ( var id in select_list ) {
                            self._addRow( id, dataset, select_list, chart_definition.columns[ id ] )
                        }
                        self.chart.state( 'ok', 'Metadata initialized...' );
                        process.resolve();
                    }
                });
            });
        },

        /** Add row */
        _addRow: function( id, dataset, select_list, column_definition ) {
            var self = this;
            var is_label    = column_definition.is_label;
            var is_auto     = column_definition.is_auto;
            var is_numeric  = column_definition.is_numeric;
            var is_unique   = column_definition.is_unique;
            var is_zero     = column_definition.is_zero;
            var is_text     = column_definition.is_text;
            var columns = [];
            var select = select_list[ id ];
            if ( is_auto ) {
                columns.push({
                    'label' : 'Column: Row Number',
                    'value' : 'auto'
                });
            }
            if ( is_zero ) {
                columns.push({
                    'label' : 'Column: None',
                    'value' : 'zero'
                });
            }
            var meta = dataset.metadata_column_types;
            for ( var key in meta ) {
                var valid = false;
                if ( meta[ key ] == 'int' || meta[ key ] == 'float' ) {
                    valid = is_numeric;
                } else {
                    valid = is_text || is_label;
                }
                if ( valid ) {
                    columns.push({
                        'label' : 'Column: ' + ( parseInt( key ) + 1 ),
                        'value' : key
                    });
                }
            }
            select.update( columns );
            if ( is_unique && this.chart.groups.first() ) {
                this.group.set( id, this.chart.groups.first().get( id ) );
            }
            if ( !select.exists( this.group.get( id ) ) ) {
                var first = select.first();
                console.debug( 'Group()::_addRow() - Switching model value from "' + this.group.get( id ) + '" to "' + first + '".' );
                this.group.set( id, first );
            }
            select.value( this.group.get( id ) );
            this.group.off( 'change:' + id ).on( 'change:' + id, function() {
                select.value( self.group.get( id ) );
            });
            select.setOnChange( function( value ) {
                if ( is_unique ) {
                    self.chart.groups.each( function( group ) {
                        group.set( id, value );
                    });
                } else {
                    self.group.set( id, value );
                }
                self.chart.set( 'modified', true );
            });
            select.show();
        },

        /** Update group attributes */
        _refreshGroup: function() {
            this.group.set( 'date', Utils.time() );
        },

        /** Update group key */
        _refreshGroupKey: function() {
            var key_text = this.group.get( 'key' );
            key_text === undefined ? '' : key_text;
            if ( key_text != this.group_key.value() ) {
                this.group_key.value( key_text );
            }
        }
    });
});
