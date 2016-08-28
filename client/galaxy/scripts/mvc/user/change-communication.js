/** Change communication settings view */
define( [ 'mvc/form/form-view', 'mvc/ui/ui-misc' ], function( Form, Ui ) {
    var ChangeCommunication = Backbone.View.extend({
        initialize: function ( app, options ) {
            var self = this;
            this.model = options && options.model || new Backbone.Model( options );
            this.form = new Form({
                title   : 'Enable real-time communication with other Galaxy users',
                inputs  : [ { name: 'change-communication', type: 'boolean', label: 'Enable communication' } ],
                operations      : {
                    'back'  : new Ui.ButtonIcon({
                        icon    : 'fa-caret-left',
                        tooltip : 'Return to user preferences',
                        title   : 'Preferences',
                        onclick : function() { self.remove(); app.showPreferences() }
                    })
                },
            });
            this.setElement( this.form.$el );
            setTimeout( function(){ 
                self.setValue( options );
                $( 'label.ui-option' ).on( 'click', function( e ) { 
                    self.saveCommunicationChanges( self, e );
                });
            });
        },

        /** sets the saved value to the switch button */
        setValue: function( options ) {
            var radioboxes = $('div[tour_id="change-communication"]').find('input[type="radio"]'),
                yesboxparent = $( radioboxes[0] ).parent(),
                noboxparent = $( radioboxes[1] ).parent();

            if( options.activated === "true" ) {
                yesboxparent.addClass( 'active' );
                noboxparent.removeClass( 'active' );
            }
            else {
                yesboxparent.removeClass( 'active' );
                noboxparent.addClass( 'active' );
            }
        },

        /** saves the change in communication setting */
        saveCommunicationChanges: function( self, e ) {
            var self = this,
                data = {},
                activated = null, 
                element = null;
            elementValue = e.toElement ? e.toElement.attributes["value"] : e.target.attributes["value"];
            // skips the click on the already active button
            if( !$(e.currentTarget).hasClass('active') ) {
                if( elementValue ) {
                    activated = elementValue.nodeValue;
                    data = { 'button_comm_server': true, 'enable_communication_server': activated };
                    $.getJSON( Galaxy.root + 'api/user_preferences/change_communication', data, function( response ) {
                        self.setValue( response )
                        self.form.message.update({
                           message     : response.message,
                           status      : response.status === 'error' ? 'danger' : 'success'
                        });
                    });
                }            
            }
        }
    });

    return {
        ChangeCommunication: ChangeCommunication
    };
});

