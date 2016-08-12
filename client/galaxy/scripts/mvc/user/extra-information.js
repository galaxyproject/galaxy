/** Get extra information */
define(['mvc/user/manage-user-information'], function( Manage ) {

var ExtraInformation = Backbone.View.extend({
    initialize: function ( data ) {
        this.render( data );
    },

    /** renders the markup of extra information */
    render: function( data_plugin ) {
        var template = "",
            self = this,
            item_object = null,
            model = null,
            data = {},
            plugins = {},
            plugin_name = "",
            is_plugin_empty = false;

        $( '.user-pref' ).hide();
        $( '.donemessage' ).hide();
        $( '.errormessage' ).hide();

        data = data_plugin["config"];
        
        plugins = ( Object.keys( data_plugin["plugins"]).length === 0 ) ? {} : JSON.parse( data_plugin["plugins"] );
        
        template = template + '<div class="extra-information-section"> <h2>Extra Information</h2>';
        template = template + '<ul class="manage-table-actions"> <li>' +
                              '<a class="action-button back-user-pref" target="galaxy_main">User preferences</a>' +
                              '</li></ul>';

        if( data === null || data === undefined || data["preferences"] === null ||  data["preferences"] === undefined ) {
            template = template + "<div>No plugins available. Please contact your administrator.</div>";
        }
        else {
            template = template + '<div class="toolForm">' +
                       '<form name="extra_information" id="extra_information">' +
                       '<div class="toolFormTitle">Extra Information</div>';
            for( var item in data["preferences"] ) {

                item_object = data["preferences"][item];
                // sets the model for each plugin data and 
                // values to each input field
                var input_val = "";
                if( Object.keys(plugins).length !== 0 ) {
                    plugin_name = item_object["name"];
                    model = plugins[plugin_name];
                }
                else {
                    is_plugin_empty = true;
                }

                template = template + '<div class="form-row '+ item_object["name"] +' ">';
                template = template + "<label>" + item_object["description"] + ":</label>";

                for( var i = 0; i < item_object["inputs"].length; i++ ) {
                    var input_object = item_object["inputs"][i];
                    input_val = ( is_plugin_empty ? "" : ( !model ? "" : model[input_object.name] ) );
                    template = template + '<div class="form-row">';
                    template = template + "<label>" + input_object.label + ':</label><input type="'+ input_object.type +
                               '" name="'+ input_object.name +'" value="'+ input_val +'" '
                               + (input_object.required ? 'required': '') + '/>';
                    template = template + '</div>';
                }
                template = template + '</div>';
            }
        
            template = template + '<div class="form-row">' +
            '<input type="button" class="save-extra-info action-button" name="save_extra_information" value="Save"/>';
            template = template + '</div></div></form></div>';
        }

        template = template + '</div>';
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
            is_form_valid = true;

        $(".form-row input").each( function( item ) {
            if( $(this).attr('type') === 'text' || $(this).attr('type') === 'password' ) {
                var section_name = $($(this).parent().parent()[0]).attr("class").split(" ")[1],
                    element = {};
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
            $.getJSON( url, {'plugin_data' : JSON.stringify(data)}, function( response ) {
                messageBar.renderDone( response["message"] );
            });
        }
    }      
});

return {
    ExtraInformation: ExtraInformation
};

});

