/** This class renders the chart type selection grid. */
define( [ 'utils/utils', 'mvc/ui/ui-misc' ], function( Utils, Ui ) {
    return Backbone.View.extend({
        events : {
            'click .item'    : '_onclick',
            'dblclick .item' : '_ondblclick'
        },

        initialize : function( app, options ) {
            var self = this;
            this.app = app;
            this.options = Utils.merge( options, this.optionsDefault );
            this.setElement( $( '<div/>' ) );
            this.render();
        },

        render: function() {
            var self = this;
            this.index = [];
            this.first = null;
            _.each( this.app.types, function( type, type_id ) {
                if ( !type.datatypes || type.datatypes.indexOf( self.app.dataset.file_ext ) != -1  ) {
                    self.index.push( {
                        id          : type_id,
                        title       : ( type.zoomable ? '<span class="fa fa-search-plus"/>' : '' ) + type.title + ' (' + type.library + ')',
                        description : type.description || type.category,
                        url         : remote_root + 'src/visualizations/' + self.app.split( type_id ) + '/logo.png'
                    });
                }
            });
            this.index.sort( function( a, b ) { return a.id < b.id ? -1 : 1 } );
            this.first = this.index[ 0 ].id;
            var $el = $( '<div/>' ).addClass( 'charts-grid' );
            _.each( this.index, function( d, i ) {
                $el.append( self._templateType( d ) );
            });
            this.$el.empty().append( $el );
        },

        /** Set/Get selected chart type */
        value: function( new_value ) {
            if ( new_value == '__first' ) {
                new_value = this.first;
            }
            var before = this.$( '.current' ).attr( 'chart_id' );
            if ( new_value !== undefined ) {
                this.$( '.current' ).removeClass( 'current' );
                this.$( '[chart_id="' + new_value + '"]' ).addClass( 'current' );
            }
            var after = this.$( '.current' ).attr( 'chart_id' );
            if( after !== undefined ) {
                if ( after != before && this.options.onchange ) {
                    this.options.onchange( after );
                }
                return after;
            }
        },

        /** Add click handler */
        _onclick: function( e ) {
            this.value( $( e.target ).closest( '.item' ).attr( 'chart_id' ) );
        },

        /** Add double click handler */
        _ondblclick: function( e ) {
            this.options.ondblclick && this.options.ondblclick( this.value() );
        },

        /** Header template */
        _templateHeader: function( options ) {
            return  '<div class="header ui-margin-top">' +
                        '&bull; ' + options.title +
                    '<div>';
        },

        /* Chart type template with image */
        _templateType: function( options ) {
            return  '<div class="item" chart_id="' + options.id + '">' +
                        '<table>' +
                            '<tr>' +
                                '<td>' +
                                    '<img class="image" src="' + options.url + '">' +
                                '</td>' +
                                '<td>' +
                                    '<div class="charts-description-title ui-form-info">' + options.title + '</div>' +
                                    '<div class="charts-description-text ui-form-info">' + options.description + '</div>' +
                                '</td>' +
                            '</tr>' +
                    '<div>';
        }
    });
});
