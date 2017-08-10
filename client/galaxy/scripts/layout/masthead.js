define([
    'utils/utils',
    'layout/menu',
    'layout/scratchbook',
    'mvc/user/user-quotameter',
], function( Utils, Menu, Scratchbook, QuotaMeter ) {

/** Masthead **/
var View = Backbone.View.extend({
    initialize : function( options ) {
        var self = this;
        this.options = options;
        this.setElement( this._template() );
        this.$navbarBrandLink   = this.$( '.navbar-brand-link' );
        this.$navbarBrandImage  = this.$( '.navbar-brand-image' );
        this.$navbarBrandTitle  = this.$( '.navbar-brand-title' );
        this.$navbarTabs        = this.$( '.navbar-tabs' );
        this.$quoteMeter        = this.$( '.quota-meter-container' );

        // build tabs
        this.collection = new Menu.Collection();
        this.collection.on( 'add', function( model ) {
            self.$navbarTabs.append( new Menu.Tab( { model : model } ).render().$el );
        }).on( 'reset', function() {
            self.$navbarTabs.empty();
        }).on( 'dispatch', function( callback ) {
            self.collection.each( function ( m ) { callback( m ) });
        }).fetch( this.options );

        // scratchbook
        Galaxy.frame = this.frame = new Scratchbook( { collection: this.collection } );

        // set up the quota meter (And fetch the current user data from trans)
        // add quota meter to masthead
        Galaxy.quotaMeter = this.quotaMeter = new QuotaMeter.UserQuotaMeter({
            model   : Galaxy.user,
            el      : this.$quoteMeter
        });

        // loop through beforeunload functions if the user attempts to unload the page
        $( window ).on( 'click', function( e ) {
            var $download_link = $( e.target ).closest( 'a[download]' );
            if ( $download_link.length == 1 ) {
                if( $( 'iframe[id=download]' ).length === 0 ) {
                    $( 'body' ).append( $( '<iframe/>' ).attr( 'id', 'download' ).hide() );
                }
                $( 'iframe[id=download]' ).attr( 'src', $download_link.attr( 'href' ) );
                e.preventDefault();
            }
        }).on( 'beforeunload', function() {
            var text = '';
            self.collection.each( function( model ) {
                var q = model.get( 'onbeforeunload' ) && model.get( 'onbeforeunload' )();
                q && ( text += q + ' ' );
            });
            if ( text !== '' ) {
                return text;
            }
        });
    },

    render: function() {
        this.$navbarBrandTitle.html( 'Galaxy ' + ( this.options.brand && '/ ' + this.options.brand || '' ) );
        this.$navbarBrandLink.attr( 'href', this.options.logo_url );
        this.$navbarBrandImage.attr( 'src', this.options.logo_src );
        this.quotaMeter.render();
        return this;
    },

    /** body template */
    _template: function() {
        return  '<div id="masthead" class="navbar navbar-fixed-top navbar-inverse">' +
                    '<div class="navbar-header">' +
                        '<div class="navbar-tabs"/>' +
                    '</div>' +
                    '<div class="navbar-brand">' +
                        '<a class="navbar-brand-link">' +
                            '<img class="navbar-brand-image"/>' +
                            '<span class="navbar-brand-title"/>' +
                        '</a>' +
                    '</div>' +
                    '<div class="quota-meter-container"/>' +
                    '<div class="navbar-icons"/>' +
                '</div>';
    }
});

return {
    View: View
};

});
