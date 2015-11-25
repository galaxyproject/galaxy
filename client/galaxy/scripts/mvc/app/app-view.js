/**
    This is the entrance point for the Galaxy UI.
*/
define(['utils/utils', 'galaxy.masthead', 'galaxy.menu', 'galaxy.frame',
        'mvc/ui/ui-portlet', 'mvc/ui/ui-misc', 'mvc/ui/ui-modal',
        'mvc/user/user-quotameter', 'mvc/app/app-login', 'mvc/app/app-analysis'],
    function( Utils, Masthead, Menu, Frame, Portlet, Ui, Modal, QuotaMeter, Login, Analysis ) {
    return Backbone.View.extend({
        initialize: function( options ) {
            this.options = Utils.merge( options, {} );
            this.setElement( this._template( options ) );

            // register this view
            Galaxy.app = this;

            // url request parameters
            Galaxy.params = this.options.params;

            // shared backbone router
            Galaxy.router = new Backbone.Router();

            // configure body
            $( 'body' ).append( this.$el );
            ensure_dd_helper();

            // adjust parent container
            var $container = $( this.$el.parent() ).attr( 'scroll', 'no' ).addClass( 'full-content' );
            if ( this.options.message_box_visible ) {
                $container.addClass( 'has-message-box' );
                this.$( '#messagebox' ).show();
            }
            if ( this.options.show_inactivity_warning ) {
                $container.addClass( 'has-inactivity-box' );
                this.$( '#inactivebox' ).show();
            }

            // load global galaxy objects
            if ( !Galaxy.masthead ) {
                Galaxy.masthead = new Masthead.GalaxyMasthead( this.options );
                Galaxy.modal = new Modal.View();
                Galaxy.frame = new Frame.GalaxyFrame();

                // construct default menu options
                Galaxy.menu = new Menu.GalaxyMenu({
                    masthead    : Galaxy.masthead,
                    config      : this.options
                });

                // set up the quota meter (And fetch the current user data from trans)
                // add quota meter to masthead
                Galaxy.quotaMeter = new QuotaMeter.UserQuotaMeter({
                    model       : Galaxy.user,
                    el          : Galaxy.masthead.$( '.quota-meter-container' )
                }).render();
            }

            // build page
            if ( Galaxy.config.require_login && !Galaxy.user.id ) {
                this.build( Login );
            } else {
                this.build( Analysis );
            }
        },

        /** Display content */
        display: function ( view, target ) {
            // TODO: Remove this line after select2 update
            $( '.select2-hidden-accessible' ).remove();
            this.panels && this.panels[ target || 'center' ].display( view );
        },

        /** Build all panels **/
        build: function( Views ) {
            this.panels = [];
            var options = $.extend( true, {}, this.options );
            var panel_ids = [ 'center', 'left', 'right' ];
            for ( var i in panel_ids ) {
                var id = panel_ids[ i ];
                this.$( '#' + id ).remove();
                if ( !Views[ id ] ) {
                    this.$( '#center' ).css( id, '0' );
                    continue;
                }
                var view = this.panels[ id ] = new Views[ id ]( options );
                if ( id == 'center' ) {
                    this.$el.append( $( '<div id="' + id + '"/>' ).addClass( 'inbound' ).append( view.$el ) );
                } else {
                    var components = Utils.merge( view.components, {
                        header  : {
                            title   : '',
                            cls     : '',
                            buttons : []
                        },
                        body    : {
                            cls     : ''
                        }
                    });
                    var $panel = $( this._templatePanel( id ) );
                    $panel.find('.panel-header-text').html( components.header.title );
                    $panel.find('.unified-panel-header-inner').addClass( components.header.cls );
                    for ( var i in components.header.buttons ) {
                        $panel.find('.panel-header-buttons').append( components.header.buttons[ i ].$el );
                    }
                    $panel.find('.unified-panel-body').addClass( components.body.cls ).append( view.$el );
                    var panel = new Panel( {
                        center  : this.$( '#center' ),
                        panel   : $panel,
                        drag    : $panel.find('.unified-panel-footer > .drag' ),
                        toggle  : $panel.find('.unified-panel-footer > .panel-collapse' ),
                        right   : id == 'right'
                    } );
                    this.$el.append( $panel );
                }
            }
        },

        /** Template for left/right panel */
        _templatePanel: function( id ) {
            return  '<div id="' + id + '">' +
                        '<div class="unified-panel-header" unselectable="on">' +
                            '<div class="unified-panel-header-inner">' +
                                '<div class="panel-header-buttons" style="float: right"/>' +
                                '<div class="panel-header-text"/>' +
                            '</div>' +
                        '</div>' +
                        '<div class="unified-panel-body"/>' +
                        '<div class="unified-panel-footer">' +
                            '<div class="panel-collapse ' + id + '"/>' +
                            '<div class="drag"/>' +
                        '</div>' +
                    '</div>';
        },

        /** Main template **/
        _template: function() {
            return  '<div id="everything" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;">' +
                        '<div id="background"/>' +
                        '<div id="messagebox" class="panel-' + Galaxy.config.message_box_class + '-message" style="display: none;">' +
                            Galaxy.config.message_box_content +
                        '</div>' +
                        '<div id="inactivebox" class="panel-warning-message" style="display: none;">' +
                            Galaxy.config.inactivity_box_content +
                                ' <a href="' + Galaxy.root + 'user/resend_verification">Resend verification.</a>' +
                        '</div>' +
                    '</div>';
        }
    });
});