define([
    'layout/masthead',
    'layout/panel',
    'mvc/ui/ui-modal',
    'mvc/base-mvc'
], function( MASTHEAD, PANEL, MODAL, BASE_MVC ) {

// ============================================================================
var PageLayoutView = Backbone.View.extend( BASE_MVC.LoggableMixin ).extend({
    _logNamespace : 'layout',

    el : 'body',
    className : 'full-content',

    _panelIds : [
        'left', 'center', 'right'
    ],

    defaultOptions : {
        message_box_visible : false,
        message_box_content : '',
        message_box_class   : 'info',

        show_inactivity_warning : false,
        inactivity_box_content  : '',
    },

    initialize : function( options ){
        this.log( this + '.initialize:', options );
        _.extend( this, _.pick( options, this._panelIds ) );
        this.options = _.defaults( _.omit( options, this._panelIds ), this.defaultOptions );

        // TODO: remove globals
        Galaxy.modal = this.modal = new MODAL.View();
    },

    /**  */
    $everything : function(){
        return this.$( '#everything' );
    },

    render : function(){
        this.log( this + '.render:' );
        this.$el.attr( 'scroll', 'no' );
        this.$el.html( this.template( this.options ) );

        //TODO: no render on masthead, needs init each time
        Galaxy.masthead = this.masthead = new MASTHEAD.GalaxyMasthead( _.extend( this.options.config, {
            el: this.$( '#masthead' ).get(0)
        }));

        if( this.options.message_box_visible ){
            this.messageBox( this.options.message_box_content, this.options.message_box_class );
        }
        if( this.options.show_inactivity_warning ){
            this.inactivityWarning( this.options.inactivity_box_content );
        }

        this.renderPanels();
        return this;
    },

    /**  */
    messageBox : function( content, level ){
        content = content || '';
        level = level || 'info';
        this.$el.addClass( 'has-message-box' );
        this.$( '#messagebox' )
            .attr( 'class', 'panel-' + level + '-message' )
            .html( content )
            .toggle( !!content );
        return this;
    },

    /**  */
    inactivityWarning : function( content ){
        var verificationLink = '<a href="' + Galaxy.root + 'user/resend_verification">Resend verification.</a>';
        this.$el.addClass( 'has-inactivity-box' );
        this.$( '#inactivebox' )
            .html( content )
            .append( ' ' + verificationLink )
            .toggle( !!content );
        return this;
    },

    /**  */
    renderPanels : function(){
        var page = this;
        // TODO: Remove this line after select2 update
        $( '.select2-hidden-accessible' ).remove();
        this._panelIds.forEach( function( panelId ){
            if( _.has( page, panelId ) ){
                var panelView = page[ panelId ];
                panelView.setElement( '#' + panelId );
                panelView.render();
            }
        });
        if( !this.left ){
            this.center.$el.css( 'left', 0 );
        }
        if( !this.right ){
            this.center.$el.css( 'right', 0 );
        }
        return this;
    },

    /** body template */
    //TODO: to underscore
    template: function( options ){
        //TODO: remove inline styling
        return [
            '<div id="everything" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;">',
                '<div id="background"/>',
                '<div id="masthead" class="navbar navbar-fixed-top navbar-inverse"></div>',
                '<div id="messagebox" style="display: none;"></div>',
                '<div id="inactivebox" class="panel-warning-message" style="display: none;"></div>',
                // content here
                // TODO: wrapping div
                this.left?   '<div id="left"/>' : '',
                this.center? '<div id="center" class="inbound"/>' : '',
                this.right?  '<div id="right"/>' : '',
            '</div>',
            // a dropdown overlay for capturing clicks/drags
            '<div id="dd-helper" style="display: none;"></div>',
            // display message when js is disabled
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

    hideSidePanels : function(){
        if( this.left ){
            this.left.hide();
        }
        if( this.right ){
            this.right.hide();
        }
    },

    toString : function(){ return 'PageLayoutView'; }
});

// ============================================================================
    return {
        PageLayoutView: PageLayoutView
    };
});
