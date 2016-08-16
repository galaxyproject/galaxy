/** This class creates a ui component which enables the dynamic creation of portlets */
define( [ 'utils/utils', 'mvc/ui/ui-portlet', 'mvc/ui/ui-misc' ],
function( Utils, Portlet, Ui ) {
    var View = Backbone.View.extend({
        initialize: function( options ) {
            this.list = {};
            this.options = Utils.merge( options, {
                title       : 'Repeat',
                empty_text  : 'Not available.',
                max         : null,
                min         : null
            });
            this.button_new = new Ui.ButtonIcon({
                icon    : 'fa-plus',
                title   : 'Insert ' + this.options.title,
                tooltip : 'Add new ' + this.options.title + ' block',
                floating: 'clear',
                cls     : 'ui-button-icon form-repeat-add',
                onclick : function() { options.onnew && options.onnew() }
            });
            this.setElement( $( '<div/>' ).append( this.$list = $( '<div/>' ) )
                                          .append( $( '<div/>' ).append( this.button_new.$el ) ) );
        },

        /** Number of repeat blocks */
        size: function() {
            return _.size( this.list );
        },

        /** Add new repeat block */
        add: function( options ) {
            if ( !options.id || this.list[ options.id ] ) {
                Galaxy.emit.debug( 'form-repeat::add()', 'Duplicate or invalid repeat block id.' );
                return;
            }
            var button_delete = new Ui.ButtonIcon({
                icon    : 'fa-trash-o',
                tooltip : 'Delete this repeat block',
                cls     : 'ui-button-icon-plain form-repeat-delete',
                onclick : function() { options.ondel && options.ondel() }
            });
            var portlet = new Portlet.View({
                id              : options.id,
                title           : 'placeholder',
                cls             : options.cls || 'ui-portlet-repeat',
                operations      : { button_delete: button_delete }
            });
            portlet.append( options.$el );
            portlet.$el.addClass( 'section-row' ).hide();
            this.list[ options.id ] = portlet;
            this.$list.append( portlet.$el.fadeIn( 'fast' ) );
            this.options.max > 0 && this.size() >= this.options.max && this.button_new.disable();
            this._refresh();
        },

        /** Delete repeat block */
        del: function( id ) {
            if ( !this.list[ id ] ) {
                Galaxy.emit.debug( 'form-repeat::del()', 'Invalid repeat block id.' );
                return;
            }
            this.$list.find( '#' + id ).remove();
            delete this.list[ id ];
            this.button_new.enable();
            this._refresh();
        },

        /** Remove all */
        delAll: function() {
            for( var id in this.list ) {
                this.del( id );
            }
        },

        /** Hides add/del options */
        hideOptions: function() {
            this.button_new.$el.hide();
            _.each( this.list, function( portlet ) { portlet.hideOperation( 'button_delete' ) } );
            _.isEmpty( this.list ) && this.$el.append( $( '<div/>' ).addClass( 'ui-form-info' ).html( this.options.empty_text ) );
        },

        /** Refresh view */
        _refresh: function() {
            var index = 0;
            for ( var id in this.list ) {
                var portlet = this.list[ id ];
                portlet.title( ++index + ': ' + this.options.title );
                portlet[ this.size() > this.options.min ? 'showOperation' : 'hideOperation' ]( 'button_delete' );
            }
        }
    });

    return {
        View : View
    }
});
