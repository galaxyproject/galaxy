define([
    'layout/masthead',
    'layout/panel',
    'mvc/ui/ui-modal',
    'mvc/base-mvc'
], function( Masthead, Panel, Modal, BaseMVC ) {

// ============================================================================
var PageLayoutView = Backbone.View.extend( BaseMVC.LoggableMixin ).extend({
    _logNamespace : 'layout',

    el : 'body',
    className : 'full-content',

    _panelIds : [
        'left', 'center', 'right'
    ],

    defaultOptions : {
        message_box_visible     : false,
        message_box_content     : '',
        message_box_class       : 'info',
        show_inactivity_warning : false,
        inactivity_box_content  : ''
    },

    initialize : function( options ) {
        // TODO: remove globals
        this.log( this + '.initialize:', options );
        _.extend( this, _.pick( options, this._panelIds ) );
        this.options = _.defaults( _.omit( options, this._panelIds ), this.defaultOptions );
        Galaxy.modal = this.modal = new Modal.View();
        this.masthead = new Masthead.View( this.options.config );
        this.$el.attr( 'scroll', 'no' );
        this.$el.append( this._template() );
        this.$el.append( this.masthead.$el );
        this.$el.append( this.modal.$el );
        this.$messagebox = this.$( '#messagebox' );
        this.$inactivebox = this.$( '#inactivebox' );
    },

    render : function() {
        // TODO: Remove this line after select2 update
        $( '.select2-hidden-accessible' ).remove();
        this.log( this + '.render:' );
        this.masthead.render();
        this.renderMessageBox();
        this.renderInactivityBox();
        this.renderPanels();
        return this;
    },

    /** Render message box */
    renderMessageBox : function() {
        if ( this.options.message_box_visible ){
            var content = this.options.message_box_content || '';
            var level = this.options.message_box_class || 'info';
            this.$el.addClass( 'has-message-box' );
            this.$messagebox
                .attr( 'class', 'panel-' + level + '-message' )
                .html( content )
                .toggle( !!content )
                .show();
        } else {
            this.$el.removeClass( 'has-message-box' );
            this.$messagebox.hide();
        }
        return this;
    },

    /** Render inactivity warning */
    renderInactivityBox : function() {
        if( this.options.show_inactivity_warning ){
            var content = this.options.inactivity_box_content || '';
            var verificationLink = $( '<a/>' ).attr( 'href', Galaxy.root + 'user/resend_verification' ).html( 'Resend verification.' );
            this.$el.addClass( 'has-inactivity-box' );
            this.$inactivebox
                .html( content )
                .append( ' ' + verificationLink )
                .toggle( !!content )
                .show();
        } else {
            this.$el.removeClass( 'has-inactivity-box' );
            this.$inactivebox.hide();
        }
        return this;
    },

    /** Render panels */
    renderPanels : function() {
        var page = this;
        this._panelIds.forEach( function( panelId ){
            if( _.has( page, panelId ) ){
                page[ panelId ].setElement( '#' + panelId );
                page[ panelId ].render();
            } else if ( panelId !== 'center' ) {
                page.center.$el.css( panelId, 0 );
            }
        });
        return this;
    },

    /** body template */
    _template: function() {
        return [
            '<div id="everything">',
                '<div id="background"/>',
                '<div id="messagebox"/>',
                '<div id="inactivebox" class="panel-warning-message"/>',
                '<div id="left"/>',
                '<div id="center" class="inbound"/>',
                '<div id="right"/>',
            '</div>',
            '<div id="dd-helper"/>',
            '<noscript>',
                '<div class="overlay overlay-background noscript-overlay">',
                    '<div>',
                        '<h3 class="title">Javascript Required for Galaxy</h3>',
                        '<div>',
                            'The Galaxy analysis interface requires a browser with Javascript enabled.<br>',
                            'Please enable Javascript and refresh this page',
                        '</div>',
                    '</div>',
                '</div>',
            '</noscript>'
        ].join('');
    },

    toString : function() { return 'PageLayoutView' }
});

// ============================================================================
    return {
        PageLayoutView: PageLayoutView
    };
});
