/** This class creates a ui table element. */
define( [ 'utils/utils' ], function( Utils ) {
    var View = Backbone.View.extend({
        initialize : function(options) {
            this.options = Utils.merge(options, {
                content     : 'No content available.',
                onchange    : null,
                ondblclick  : null,
                onconfirm   : null,
                cls         : 'ui-table',
                selectable  : true,
                cls_tr      : ''
            });
            this.setElement( this._template() );
            this.$thead     = this.$('thead');
            this.$tbody     = this.$('tbody');
            this.$tmessage  = this.$('tmessage');
            this.row = this._row();
            this.row_count = 0;
        },

        events : {
            'click'     : '_onclick',
            'dblclick'  : '_ondblclick'
        },

        /** Add cell to header row */
        addHeader: function( $el ) {
            this.row.append( $( '<th/>' ).append( $el ) );
        },

        /** Append header row to table */
        appendHeader: function() {
            this.$thead.append( this.row );
            this.row = $( '<tr/>' );
        },

        /** Add cell to row */
        add: function($el, width, align) {
            var wrapper = $( '<td/>' );
            if ( width ) {
                wrapper.css( 'width', width );
            }
            if ( align ) {
                wrapper.css( 'text-align', align );
            }
            this.row.append( wrapper.append( $el ) );
        },
        
        /** Append row to table */
        append: function( id, fade ) {
            this._commit( id, fade, false );
        },
        
        /** Prepend row to table */
        prepend: function( id, fade ) {
            this._commit( id, fade, true );
        },
        
        /** Helper to get row element */
        get: function( id ) {
            return this.$( '#' + id );
        },

        /** Delete row by id */
        del: function( id ) {
            var item = this.$tbody.find( '#' + id );
            if ( item.length > 0 ) {
                item.remove();
                this.row_count--;
                this._refresh();
            }
        },

        /** Delete all rows */
        delAll: function() {
            this.$tbody.empty();
            this.row_count = 0;
            this._refresh();
        },

        /** Set a value i.e. selects/highlights a particular row by id */
        value: function( new_value ) {
            if ( this.options.selectable ) {
                this.before = this.$tbody.find( '.current' ).attr( 'id' );
                if ( new_value !== undefined ) {
                    this.$tbody.find( 'tr' ).removeClass( 'current' );
                    if ( new_value ) {
                        this.$tbody.find( '#' + new_value ).addClass( 'current' );
                    }
                }
                var after = this.$tbody.find( '.current' ).attr( 'id' );
                if ( after === undefined ) {
                    return null;
                } else {
                    if ( after != this.before && this.options.onchange ) {
                        this.options.onchange( new_value );
                    }
                    return after;
                }
            }
        },

        /** Return the number of rows */
        size: function() {
            return this.$tbody.find( 'tr' ).length;
        },

        /** Helper to append rows */
        _commit: function( id, fade, prepend ) {
            this.del( id );
            this.row.attr( 'id', id );
            if ( prepend ) {
                this.$tbody.prepend( this.row );
            } else {
                this.$tbody.append( this.row );
            }
            if ( fade ) {
                this.row.hide();
                this.row.fadeIn();
            }
            this.row = this._row();
            this.row_count++;
            this._refresh();
        },

        /** Helper to create new row */
        _row: function() {
            return $( '<tr class="' + this.options.cls_tr + '"></tr>' );
        },

        /** Handles onclick events */
        _onclick: function(e) {
            var old_value = this.value();
            var new_value = $( e.target ).closest( 'tr' ).attr( 'id' );
            if ( new_value != '' ){
                if ( new_value && old_value != new_value ) {
                    if ( this.options.onconfirm ) {
                        this.options.onconfirm( new_value );
                    } else {
                        this.value( new_value );
                    }
                }
            }
        },

        /** Handles ondblclick events */
        _ondblclick: function( e ) {
            var value = this.value();
            if ( value && this.options.ondblclick ) {
                this.options.ondblclick( value );
            }
        },

        /** Refresh helper */
        _refresh: function() {
            if ( this.row_count == 0 ) {
                this.$tmessage.show();
            } else {
                this.$tmessage.hide();
            }
        },

        /** Template */
        _template: function() {
            return  '<div>' +
                        '<table class="' + this.options.cls + '">' +
                            '<thead/>' +
                            '<tbody/>' +
                        '</table>' +
                        '<tmessage>' + this.options.content + '</tmessage>' +
                    '<div>';
        }
    });

    return {
        View: View
    }
});