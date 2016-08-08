/** Set default permissions view */
define(['mvc/user/manage-user-information'], function( Manage ) {
var ChangePermissions = Backbone.View.extend({

    initialize: function ( data ) {
        this.render( data );
    },

    /** renders the error message when view is rebuilt */
    renderMessage: function( msg, status ) {
        return '<div class="'+ ( status === "" ? 'done': status ) +'message'+ ( status === "error" ? " validate" : "" ) + '">'+ msg +'</div>';
    },

    /** registers the click and submit events */
    renderJS: function() {
        $( '.role_add_button' ).click( function() {
            var action = this.id.substring( 0, this.id.lastIndexOf( '_add_button' ) ),
                in_select = '#' + action + '_in_select',
                out_select = '#' + action + '_out_select';
            return !$( out_select + ' option:selected' ).remove().appendTo( in_select );
        });
        $( '.role_remove_button' ).click( function() {
            var action = this.id.substring( 0, this.id.lastIndexOf( '_remove_button' ) ),
                in_select = '#' + action + '_in_select',
                out_select = '#' + action + '_out_select';
            return !$( in_select + ' option:selected' ).remove().appendTo( out_select );
        });
        $( '.update-roles-button' ).click( function() {
           $( '.in_select option' ).each(function( i ) {
                $( this ).attr( "selected", "selected" );
           });
        });
        // Temporary removal of select2 for all permissions forms
        $('#edit_role_associations select').select2("destroy");
    },

    /** builds the select list boxes */
    renderSelect: function( current_action, action_key, action, description, in_roles, out_roles, data_access ) {
        var template = "";
            template = template + "<p>" +
                       "<b>" + action +  ":</b> " + description;
        if ( action === data_access ) {
            template = template + '<br/> NOTE: Users must have every role associated with this dataset in order to access it';
        }
        template = template + '</p>';
        template = template + '<div style="width: 100%; white-space: nowrap;">' + 
                              '<div style="float: left; width: 50%;">' +
                              'Roles associated:<br />' +
                              '<select name="'+ action_key +'_in" id="'+ action_key +'_in_select" class="in_select" ' + 
                              'style="max-width:  98%; width: 98%; height: 150px; font-size: 100%;" multiple>';
        for( var item in in_roles ) {
            template = template + '<option value="'+ in_roles[item]["id"] + '">' + in_roles[item]["name"] + '</option>';
        }
        template = template + '</select> <br />';
        template = template + '<div style="width: 98%; text-align: right"><input type="submit" id="'+ 
                              action_key +'_remove_button" class="role_remove_button" value=">>"/></div></div>';

        template = template + '<div style="width: 50%;">' +
                              'Roles not associated:<br />' +
                              '<select name="'+ action_key +'_out" id="'+ action_key +'_out_select" ' + 
                              'style="max-width:  98%; width: 98%; height: 150px; font-size: 100%;" multiple>';
        for( var item in out_roles ) {
            template = template + '<option value="'+ out_roles[item]["id"] + '">' + out_roles[item]["name"] + '</option>';
        }
        template = template + '</select> <br />';
        template = template + '<input type="submit" id="'+ action_key + '_add_button" class="role_add_button" value="<<"/></div></div>';
        return template;
    },

    /** builds the html for the change permission view */
    render: function( data ) {
        var template = "",
            self = this;
        Manage.ManageUserInformation.prototype.hideErrorDoneMessage();
        if( data["message"] && data["message"].length > 0 ) {
            template = this.renderMessage( data["message"], data['status'] );
        }
        template = template + '<div class="change-permissions-section"> <h2>Change default permissions</h2>';
        template = template + '<ul class="manage-table-actions">' +
                   '<li>' +
                       '<a class="action-button back-user-info" target="galaxy_main">User preferences</a>' +
                   '</li></ul>';
        if( data["userid"] !== null ) {
            template = template + '<div class="toolForm">' +
                       '<div class="toolFormTitle">Manage ' + data["obj_type"] + ' permissions on ' + data["obj_str"] + '</div>' +
                       '<div class="toolFormBody">' +
                       '<form name="edit_role_associations" id="edit_role_associations">' +
                       '<div class="form-row"></div>';
            for( var item in data["permitted_actions"] ) {
                var item_object = data["permitted_actions"][item];
                template = template + '<div class="form-row">';
                // ## LIBRARY_ACCESS is a special case because we need to render all roles instead of
                // ## roles derived from the roles associated with LIBRARY_ACCESS.
                template = template + this.renderSelect( data["current_actions"], item_object["action_key"], item_object["action"], 
                                      item_object["description"], item_object["in_roles"], item_object["out_roles"], data["data_access"] );
                template = template + '</div>';
            }
            template = template + '<div class="form-row">' +
                       '<input type="button" class="update-roles-button action-button" name="update_roles_button" value="Save"/>' +
                       '</div>';
            template = template + '</form></div></div>';
        }
      
        // end of outermost div section
        template = template + "</div>";
        $('.user-preferences-all').append( template );
        self.renderJS();
        $('.back-user-info').on( 'click', function( e ) {
            e.preventDefault();
            $( ".user-pref" ).show();
            $( ".change-permissions-section" ).remove();
            Manage.ManageUserInformation.prototype.hideErrorDoneMessage();
        });
        $('.update-roles-button').on( 'click', function( e ){ self.savePermission( self, e ); });
    },

    /** saves the permissions */
    savePermission: function( self, e ) {
        var url = Galaxy.root + 'api/user_preferences/set_default_permissions',
            data = {},
            messageBar = Manage.ManageUserInformation.prototype,
            selected_list = $(".in_select");
        data = { 'update_roles_button': true };
        // builds the json data to be posted for the values in the select boxes
        for ( var counter = 0; counter < selected_list.length; counter++ ) {
            if( $(selected_list[counter]).find('option').length > 0 ) {
                var attr_name = $(selected_list[counter]).attr("name"),
                    attr_value = $(selected_list[counter]).find('option').attr("value");
                data[attr_name] = attr_value;
            }
        }
        // saves the permission setting changes
        $.getJSON( url, data, function( response ) {
             if( response["status"] === 'error' ) {
                  messageBar.renderError( response["message"] );
             }
             else {
                  $('.change-permissions-section').remove();
                  messageBar.renderDone( response["message"] );
                  $( '.user-pref' ).show();
             }    
        });
    },
});

return {
    ChangePermissions  : ChangePermissions
};

});

