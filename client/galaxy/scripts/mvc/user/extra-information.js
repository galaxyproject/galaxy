/** Get extra information */
define(['mvc/user/manage-user-information'], function( Manage ) {

var ExtraInformation = Backbone.View.extend({
    initialize: function ( data ) {
        this.render( data );
    },

    /** renders the markup of extra information */
    render: function( data_plugin ) {
        data = data_plugin["config"],
        plugins = data_plugin["plugins"];
        var template = "",
            self = this,
            item_object = null,
            model = null;
        $( '.user-pref' ).hide();
        $( '.donemessage' ).hide();
        $( '.errormessage' ).hide();
        template = template + '<div class="extra-information-section"> <h2>Extra Information</h2>';
        template = template + '<ul class="manage-table-actions"> <li>' +
                              '<a class="action-button back-user-pref" target="galaxy_main">User preferences</a>' +
                       '</li></ul>';

        template = template + '<div class="toolForm">' +
                   '<form name="extra_information" id="extra_information">' +
                       '<div class="toolFormTitle">Extra Information</div>';
        for( var item in data["preferences"] ) {
            item_object = data["preferences"][item];
            // sets the model for each plugin data and 
            // values to each input field
            if( item_object["name"] === "section_apollo_url" ) {
                model = plugins["apollo"];
            }
            else if( item_object["name"] === "section_openstack_account" ) {
                 model = plugins["openstack"];
            }

            template = template + '<div class="form-row '+ item_object["name"] +' ">';
            template = template + "<label>" + item_object["description"] + ":</label>";
            for( var i = 0; i < item_object["inputs"].length; i++ ) {
                var input_object = item_object["inputs"][i];
                template = template + '<div class="form-row">';
                template = template + "<label>" + input_object.label + ':</label><input type="'+ input_object.type +
                           '" name="'+ input_object.name +'" value="'+ model[input_object.name] +'" '
                           + (input_object.required ? 'required': '') + '/>';
                template = template + '</div>';
            }
            template = template + '</div>';
        }
        
        template = template + '<div class="form-row">' +
            '<input type="button" class="save-extra-info action-button" name="save_extra_information" value="Save"/>';
        template = template + '</div></div></form></div></div>';
        $('.user-preferences-all').append( template );
        $('.save-extra-info').on( 'click', function( e ) { self.saveExtraInformation( self, e ) } );
        $('.back-user-pref').on( 'click', function( e ) {
             $('.extra-information-section').remove();
             $( '.donemessage' ).hide();
             $( '.errormessage' ).hide();
             $( '.user-pref' ).show();
        });
    },

    /** saves extra user information */
    saveExtraInformation: function( self, e ) {
        var url = Galaxy.root + 'api/user_preferences/save_extra_preferences/',
            username = $( "input[name='username']" ).val(),
            password = $( "input[name='password']" ).val(),
            userurl = $( "input[name='url']" ).val(),
            data = {},
            messageBar = Manage.ManageUserInformation.prototype,
            section_name = "",
            element = {},
            is_form_valid = true;

        $(".form-row input").each( function( item ) {
            if( $(this).attr('type') === 'text' || $(this).attr('type') === 'password' ) {
                section_name = $($(this).parent().parent()[0]).attr("class").split(" ")[1];
                attrname = $(this).attr('name');
                attrvalue = $(this).val();

                // checks if the required fields are left empty
                if( $( this ).attr("required") && attrvalue === "" ) {
                    messageBar.renderError( "Please fill the "+ attrname +" required field" );
                    is_form_valid = false;
                    return;
                }
                // builds the JSON object
                element[ $(this).attr('name') ] = attrvalue;

                if( data[section_name] ) {
                    data[section_name][attrname] = attrvalue;
                }
                else {
                    data[section_name] = element;
                }
            }
        });
        if( is_form_valid ) {
            $.getJSON( url, data, function( response ) {
                messageBar.renderDone( response["message"] );
            });
        }
    }      
});

return {
    ExtraInformation: ExtraInformation
};

});

