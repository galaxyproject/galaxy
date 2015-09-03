/**
    This is the entrance point for the Galaxy UI.
*/
define(['utils/utils', 'mvc/ui/ui-portlet', 'mvc/ui/ui-misc',
        'galaxy.masthead', 'galaxy.menu', 'mvc/ui/ui-modal', 'galaxy.frame',
        'mvc/user/user-model','mvc/user/user-quotameter',
        'mvc/app/app-panel-history', 'mvc/app/app-panel-tool', 'mvc/app/app-panel-center'],
    function( Utils, Portlet, Ui, Masthead, Menu, Modal, Frame, User, QuotaMeter, HistoryPanel, ToolPanel, CenterPanel) {
    return Backbone.View.extend({
        initialize: function( options ) {
            this.options = Utils.merge( options, {} );
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
            this._buildPanel( 'left', toolPanel );
            this._buildPanel( 'right', historyPanel );
            this.$('#center').append( centerPanel.$el );
        },

        _buildPanel: function( id, view ) {
            var components = Utils.merge( view.components, {
                header  : {
                    title   : '',
                    cls     : '',
                    buttons : []
                }
            });
            var $panel = $( this._templatePanel( id ) );
            $panel.find('.panel-header-text').html( components.header.title );
            $panel.find('.unified-panel-header-inner').addClass( components.header.cls );
            for ( var i in components.header.buttons ) {
                $panel.find('.panel-header-buttons').append( components.header.buttons[ i ].$el );
            }
            $panel.find('.unified-panel-body').append( view.$el );
            var panel = new Panel( {
                center  : this.$( '#center' ),
                panel   : $panel,
                drag    : $panel.find('.unified-panel-footer > .drag' ),
                toggle  : $panel.find('.unified-panel-footer > .panel-collapse' ),
                right   : id == 'right'
            } );
            this.$el.append( $panel );
        },

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

        _template: function() {
            return  '<div id="everything" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;">' +
                        //'<div id="background"/>' +
                        //'<div id="masthead" class="navbar navbar-fixed-top navbar-inverse"/>' +
                        //'<div id="messagebox"/>' +
                        //'<div id="inactivebox" class="panel-warning-message"/>' +
                        '<div id="center" class="inbound"/>' +
                    '</div>';
        }
    });
});
