/**
    This is the entrance point for the Galaxy UI.
*/
define(['utils/utils', 'mvc/ui/ui-portlet', 'mvc/ui/ui-misc',
        'galaxy.masthead', 'galaxy.menu', 'mvc/ui/ui-modal', 'galaxy.frame',
        'mvc/upload/upload-view', 'mvc/user/user-model','mvc/user/user-quotameter',
        'mvc/app/app-panel-history', 'mvc/app/app-panel-tool', 'mvc/app/app-panel-center'],
    function( Utils, Portlet, Ui, Masthead, Menu, Modal, Frame, Upload, User, QuotaMeter, HistoryPanel, ToolPanel, CenterPanel) {

    // create form view
    return Backbone.View.extend({
        // initialize
        initialize: function( options ) {
            // configure options
            this.options = Utils.merge( options, {} );

            // log options
            console.debug( this.options );

            // set element
            this.setElement( this._template( options ) );
            ensure_dd_helper();
            $('body').append( this.$el );

            // set user
            if( !Galaxy.currUser ) {
                Galaxy.currUser = new User.User( options.user.json );
            }

            // load global galaxy objects
            if (! Galaxy.masthead ) {
                Galaxy.masthead = new Masthead.GalaxyMasthead( options );
                Galaxy.modal = new Modal.View();
                Galaxy.frame = new Frame.GalaxyFrame();

                // construct default menu options
                Galaxy.menu = new Menu.GalaxyMenu({
                    masthead    : Galaxy.masthead,
                    config      : options
                });

                // set up the quota meter (And fetch the current user data from trans)
                // add quota meter to masthead
                Galaxy.quotaMeter = new QuotaMeter.UserQuotaMeter({
                    model       : Galaxy.currUser,
                    el          : Galaxy.masthead.$( '.quota-meter-container' )
                }).render();
            }

            // build panel content
            var toolPanel = new ToolPanel( options );
            var historyPanel = new HistoryPanel( options );
            var centerPanel = new CenterPanel();

            // append panel content
            this._buildPanel( '#right', historyPanel );
            this.$('#left').append( toolPanel.$el.children() );
            this.$('#center').append( centerPanel.$el );

            // add upload plugin
            Galaxy.upload = new Upload( options );

            // left/right panel
            var lp = new Panel( {
                center  : this.$( '#center' ),
                panel   : this.$( '#left' ),
                drag    : this.$( '#left .unified-panel-footer > .drag' ),
                toggle  : this.$( '#left .unified-panel-footer > .panel-collapse' )
            } );

        },

        _buildPanel: function( id, view ) {
            var $el = this.$( id );
            var components = view.components;
            $el.find('.panel-header-text').html( components.header.title );
            for ( var i in components.header.buttons ) {
                $el.find('.panel-header-buttons').append( components.header.buttons[ i ].$el );
            }
            $el.find('.unified-panel-body').append( view.$el );
            new Panel( {
                center  : this.$( '#center' ),
                panel   : this.$( id ),
                drag    : this.$( id + '.unified-panel-footer > .drag' ),
                toggle  : this.$( id + '.unified-panel-footer > .panel-collapse' ),
                right   : true
            } );
        },

        _template: function() {
            return  '<div id="everything" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;">' +
                        //'<div id="background"/>' +
                        '<div id="masthead" class="navbar navbar-fixed-top navbar-inverse"/>' +
                        //'<div id="messagebox"/>' +
                        //'<div id="inactivebox" class="panel-warning-message"/>' +
                        '<div id="left"/>' +
                        '<div id="center" class="inbound"/>' +
                        '<div id="right">' +
                            '<div class="unified-panel-header" unselectable="on">' +
                                '<div class="unified-panel-header-inner history-panel-header">' +
                                    '<div class="panel-header-buttons" style="float: right"/>' +
                                    '<div class="panel-header-text"/>' +
                                '</div>' +
                            '</div>' +
                            '<div class="unified-panel-body"/>' +
                            '<div class="unified-panel-footer">' +
                                '<div class="panel-collapse right"/>' +
                                '<div class="drag"/>' +
                            '</div>' +
                        '</div>' +
                    '</div>';
        }
    });
});
