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
            var historyPanel = new HistoryPanel( options );
            var toolPanel = new ToolPanel( options );
            var centerPanel = new CenterPanel();

            // append panel content
            this.$('#right-panel').append( historyPanel.$el );
            this.$('#left-panel').append( toolPanel.$el );
            this.$('#center-panel').append( centerPanel.$el );

            // add upload plugin
            Galaxy.upload = new Upload( options );
        },

        _template: function() {
            return  '<div id="everything" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;">' +
                        //'<div id="background"/>' +
                        '<div id="masthead" class="navbar navbar-fixed-top navbar-inverse"/>' +
                        //'<div id="messagebox"/>' +
                        //'<div id="inactivebox" class="panel-warning-message"/>' +
                        '<div id="left-panel"/>' +
                        '<div id="center-panel" class="inbound"/>' +
                        '<div id="right-panel"/>' +
                    '</div>';
        }
    });
});
