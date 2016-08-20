/** This class renders the chart configuration form. */
define( [ 'utils/utils', 'mvc/form/form-view', 'mvc/form/form-repeat', 'mvc/form/form-data' ], function( Utils, Form, Repeat, FormData ) {
    var TabularDataView = Backbone.View.extend({
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
            this.setElement( this.repeat.$el );
            this.chart.groups.each( function( group ) { self._add( group ) } );
            this.listenTo( this.chart.groups, 'add remove reset', function() { self.chart.set( 'modified', true ) } );
            this.listenTo( this.chart.groups, 'remove', function( group ) { self.repeat.del( group.id ) } );
            this.listenTo( this.chart.groups, 'reset', function() { self.repeat.delAll() } );
            this.listenTo( this.chart.groups, 'add', function( group ) { self._add( group ) } );
        },

        _add: function( group ) {
            var self = this;
            this.repeat.add({
                 id      : group.id,
                 cls     : 'ui-portlet-panel',
                 $el     : ( new TabularGroupView( self.app, { group: group } ) ).$el,
                 ondel   : function() { self.chart.groups.remove( group ) }
             });
        }
    });

    var TabularGroupView = Backbone.View.extend({
        initialize: function( app, options ) {
            this.app    = app;
            this.chart  = app.chart;
            this.group  = options.group;
            this.setElement( $( '<div/>' ) );
            this.render();
        },

        render: function() {
            var self = this;
            var inputs = this.chart.definition.series ? Utils.clone( this.chart.definition.series ) : [];
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
                            for ( var id in chart_definition.columns ) {
                                var columns = [];
                                var input_def = chart_definition.columns[ id ];
                                input_def.is_auto && columns.push( { 'label': 'Column: Row Number', 'value': 'auto' } );
                                input_def.is_zero && columns.push( { 'label' : 'Column: None', 'value' : 'zero' } );
                                var meta = dataset.metadata_column_types;
                                for ( var key in meta ) {
                                    var valid = ( [ 'int', 'float' ].indexOf( meta[ key ] ) != -1 && input_def.is_numeric ) || input_def.is_text || input_def.is_label;
                                    valid && columns.push( { 'label' : 'Column: ' + ( parseInt( key ) + 1 ), 'value' : key } );
                                }
                                inputs.push( { name: id, label: input_def.title, type: 'select', data: columns } );
                            }
                            self.chart.state( 'ok', 'Metadata initialized...' );
                            self.form = new Form( {
                                inputs  : FormData.populate( inputs, self.group.attributes ),
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
            this.setElement( $( '<div/>' ) );
            this.listenTo( this.chart, 'change:dataset_id change:type', function() { self.render() } );
        },

        render: function() {
            this.$el.empty();
            switch( this.chart.definition && this.chart.definition.datatype ) {
                case 'tabular':
                    this.$el.append( new TabularDataView( this.app ).$el );
                    break;
                default:
                    this.$el.append( $( '<div/>' ).addClass( 'ui-form-info' ).html( 'No dataset options available.' ) );
            }
        }
    });
});