/**
 *  The viewport creates and manages the dom elements used by the visualization plugins to draw the chart.
 *  Additionally, this class creates default request strings and request dictionaries parsed to the visualization plugins.
 *  This is the last class of the charts core classes before handing control over to the visualization plugins.
 */
define( [ 'mvc/ui/ui-portlet', 'mvc/ui/ui-misc', 'utils/utils' ], function( Portlet, Ui, Utils ) {
    return Backbone.View.extend({
        // list of container/canvas elements
        container_list: [],
        canvas_list: [],
        initialize: function( app, options ) {
            var self = this;
            this.app = app;
            this.chart = this.app.chart;
            this.options = options;
            this.setElement( $( '<div/>' ).addClass( 'charts-viewport' )
                                          .append( $( '<div/>' ).addClass( 'info' )
                                                                .append( $( '<span/>' ).addClass( 'icon' ) )
                                                                .append( $( '<span/>' ).addClass( 'text' ) ) ) );
            this.$info = this.$( '.info' );
            this.$icon = this.$( '.icon' );
            this.$text = this.$( '.text' );

            // use full screen for viewer
            this._fullscreen( this.$el, 50 );

            // prevent window scrolling
            var initial_overflow = $( 'body' ).css( 'overflow' );
            this.$el.on( 'mouseover', function() {
                $( 'body' ).css( 'overflow', 'hidden' );
            }).on('mouseout', function() {
                $( 'body' ).css( 'overflow', initial_overflow );
            });

            // create container element
            this._createContainer( 'div' );

            // link redraw trigger
            var self = this;
            this.chart.on( 'redraw', function() {
                self.app.deferred.execute( function( process ) {
                    self._draw( process, self.chart );
                });
            });

            // link status handler
            this.chart.on( 'set:state', function() {
                var $container = self.$el.find( '.charts-viewport-container' );
                var $info = self.$info;
                var $icon = self.$icon;
                var $text = self.$text;
                $icon.removeClass();
                $info.show();
                $text.html( self.chart.get( 'state_info' ) );
                var state = self.chart.get( 'state' );
                switch ( state ) {
                    case 'ok':
                        $info.hide();
                        $container.show();
                        break;
                    case 'failed':
                        $icon.addClass( 'icon fa fa-warning' );
                        $container.hide();
                        break;
                    default:
                        $icon.addClass( 'icon fa fa-spinner fa-spin' );
                        $container.show();
                }
            });
        },

        /** Show rendered chart */
        show: function() {
            this.$el.show();
        },

        /** Hide chart */
        hide: function() {
            this.$el.hide();
        },

        /** Force resize to fullscreen */
        _fullscreen: function( $el, margin ) {
            $el.css( 'height', $( window ).height() - margin );
            $( window ).resize( function() {
                $el.css( 'height', $( window ).height()  - margin );
            });
        },

        /** A chart may contain multiple sub charts/containers which are created here */
        _createContainer: function( tag, n ) {
            n = n || 1;
            for ( var i in this.container_list ) {
                this.container_list[ i ].remove();
            }
            this.container_list = [];
            this.canvas_list = [];
            for ( var i = 0; i < n; i++ ) {
                var container_id = Utils.uid();
                var container_el = $( '<div/>' ).addClass( 'charts-viewport-container' )
                                                .width( parseInt( 100 / n ) + '%' )
                                                .append( $( '<div/>' ).attr( 'id', 'menu' ) )
                                                .append( $( '<' + tag + ' class="charts-viewport-canvas" />' ).attr( 'id', container_id ) );
                this.$el.append( container_el );
                this.container_list[ i ] = container_el;
                this.canvas_list[ i ] = container_id;
            }
        },

        /** Draws a new chart by loading and executing the corresponding chart wrapper */
        _draw: function( process, chart ) {
            var self = this;
            var chart_type = chart.get( 'type' );
            this.chart_definition = chart.definition;
            var n_panels = 1;
            if ( chart.settings.get( 'use_panels' ) === 'true' ) {
                n_panels = chart.groups.length;
            }
            this._createContainer( this.chart_definition.tag, n_panels );
            chart.state( 'wait', 'Please wait...' );
            if ( !this.chart_definition.execute || ( this.chart_definition.execute && chart.get( 'modified' ) ) ) {
                this.app.jobs.cleanup( chart );
                chart.set( 'modified', false );
            }
            require( [ 'plugin/charts/' + this.app.chartPath( chart_type ) + '/wrapper' ], function( ChartView ) {
                if ( self.chart_definition.execute ) {
                    self.app.jobs.request( chart, self._defaultSettingsString( chart ), self._defaultRequestString( chart ),
                        function() {
                            var view = new ChartView( self.app, {
                                process             : process,
                                chart               : chart,
                                request_dictionary  : self._defaultRequestDictionary( chart ),
                                canvas_list         : self.canvas_list
                            });
                        },
                        function() {
                            process.reject();
                        }
                    );
                } else {
                    var view = new ChartView( self.app, {
                        process             : process,
                        chart               : chart,
                        request_dictionary  : self._defaultRequestDictionary( chart ),
                        canvas_list         : self.canvas_list
                    });
                }
            });
        },

        /** Creates default chart request */
        _defaultRequestString: function( chart ) {
            var request_string = '';
            var group_index = 0;
            var self = this;
            chart.groups.each( function( group ) {
                group_index++;
                for ( var key in self.chart_definition.columns ) {
                    request_string += key + '_' + group_index + ':' + ( parseInt( group.get( key ) ) + 1 ) + ', ';
                }
            });
            return request_string.substring( 0, request_string.length - 2 );
        },

        /** Creates default settings string for charts which require a job execution */
        _defaultSettingsString: function( chart ) {
            var settings_string = '';
            for ( key in chart.settings.attributes ) {
                settings_string += key + ':' + chart.settings.get( key ) + ', ';
            };
            return settings_string.substring( 0, settings_string.length - 2 );
        },

        /** Create default data request dictionary */
        _defaultRequestDictionary: function( chart ) {
            var request_dictionary = { groups : [] };
            request_dictionary.id = this.chart_definition.execute ? chart.get( 'dataset_id_job' ) : chart.get( 'dataset_id' );
            var group_index = 0;
            var self = this;
            chart.groups.each( function( group ) {
                var columns = {};
                for ( var column_key in self.chart_definition.columns ) {
                    var column_settings = self.chart_definition.columns[ column_key ];
                    columns[ column_key ] = Utils.merge( { index : group.get( column_key ) }, column_settings );
                }
                request_dictionary.groups.push( Utils.merge({
                    key     : ( ++group_index ) + ':' + group.get( 'key' ),
                    columns : columns
                }, group.attributes ));
            });
            return request_dictionary;
        }
    });
});
