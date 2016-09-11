/** Add and Edit address */
define( [ 'mvc/form/form-view', 'mvc/ui/ui-misc' ], function( Form, Ui ) {
    var AddEditAddress = Backbone.View.extend({
        initialize: function ( $el, app, options ) {
            var self = this;
            this.model = options && options.model || new Backbone.Model( options );
            this.addressform = new Form({
                title   : options ? 'Edit address' : 'Add new address',
                inputs  : [{ name: 'short_desc', label: 'Short Description:', type: 'text', value: options ? options.address_obj["desc"] : "",
                             help: 'Required' },
                           { name: 'name', label: 'Name:', type: 'text',value: options ? options.address_obj["name"] : "", help: 'Required' },
                           { name: 'institution', label: 'Institution:', type: 'text', value: options ? options.address_obj["institution"] : "",
                             help: 'Required' },
                           { name: 'address', label: 'Address:', type: 'text', value: options ? options.address_obj["address"] : "",
                             help: 'Required' },
                           { name: 'city', label: 'City:', type: 'text', value: options ? options.address_obj["city"] : "", help: 'Required' },
                           { name: 'state', label: 'State/Province/Region:', type: 'text', value: options ? options.address_obj["state"] : "",
                             help: 'Required' },
                           { name: 'postal_code', label: 'Postal Code:', type: 'text', value: options ? options.address_obj["postal_code"] : "",
                             help: 'Required' },
                           { name: 'country', label: 'Country:', type: 'text', value: options ? options.address_obj["country"] : "",
                             help: 'Required' },
                           { name: 'phone', label: 'Phone:', type: 'text', value: options ? options.address_obj["phone"] : "" }
                          ],
                operations : {
                    'back' : new Ui.ButtonIcon({
                        icon    : 'fa-caret-left',
                        tooltip : 'Return to manage user information',
                        title   : 'Return to manage user information',
                        onclick : function() {
                            self.addressform.$el.remove();
                            app.callManageInfo();
                        }
                    })
                },
                buttons : {
                    'save' : new Ui.Button({
                        tooltip : 'Save',
                        title   : 'Save',
                        cls     : 'ui-button btn btn-primary',
                        floating: 'clear',
                        onclick : function() { self._saveAddress( self, app, options ) }
                    })
                }
            });
            $el.append( self.addressform.$el );
        },

        /** save the address */
        _saveAddress: function( self, app, options ) {
            var url = "",
                data = {};
            // save the address after edit
            if( options ) {
                url = Galaxy.root + 'api/user_preferences/edit_address/';
                data = self.addressform.data.create();
                data.edit_address_button = true;
                data.address_id = options.address_id;
            }
            else { // saves new address
                url = Galaxy.root + 'api/user_preferences/new_address/';
                data = self.addressform.data.create();
            }
            $.getJSON( url, data, function( response ) {
                // show error in the same form
                if( response.status === 'error' ) {
                    self.addressform.message.update({
                        message : response.message,
                        status  : response.status === 'error' ? 'danger' : 'success',
                    });
                }
                else {
                    // if success, redirect to manage user information page
                    self.addressform.$el.remove();
                    app.callManageInfo( { message: response.message, status: response.status } );
                }
            });
        },
    });

    return {
        AddEditAddress: AddEditAddress
    };
});

