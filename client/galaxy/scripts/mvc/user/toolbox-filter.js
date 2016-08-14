/** Manage toolbox filters view */
define(['mvc/user/manage-user-information'], function( Manage ) {

var ToolboxFilter = Backbone.View.extend({

    initialize: function ( data ) {
        this.render( data );
    },

    /** renders the error message when toolbox filters view is rebuilt */
    renderMessage: function( msg, status ) {
        return '<div class="'+ ( status === "" ? 'done': status ) +'message'+ ( status === "error" ? " validate" : "" ) + '">'+ msg +'</div>';
    },

    /** renders the markup of toolbox filters feature */
    render: function( data ) {
        var template = "",
            self = this,
            tool_filters = JSON.parse( data["tool_filters"] ),
            label_filters =  JSON.parse( data["label_filters"] ),
            section_filters = JSON.parse( data["section_filters"] );

        $( '.user-pref' ).hide();
        $( '.manage-toolbox-filters-section' ).remove();
        Manage.ManageUserInformation.prototype.hideErrorDoneMessage();
        // builds the template
        if( data["status"] && data["message"].length > 0 ) {
            template = self.renderMessage( data["message"], data["status"] );
        }
        template = template + '<div class="manage-toolbox-filters-section"> <h2>Manage Toolbox Filters</h2>';
        template = template + '<ul class="manage-table-actions">' +
                       '<li>' +
                           '<a class="action-button back-user-pref" target="galaxy_main">User preferences</a>' +
                       '</li></ul>';
        // builds template only if any one type of filter is available
        if(tool_filters.length > 0 || section_filters.length > 0 || label_filters.length > 0 ) {

		template = template + '<div class="toolForm">' +
		       '<form name="toolbox_filter" id="toolbox_filter">';
		if( tool_filters.length > 0 ) {
		    template = template + '<div class="toolFormTitle">Edit ToolBox filters :: Tools</div> <div class="toolFormBody">';
		    for( var i = 0; i < tool_filters.length; i++ ) {
                        var filter = tool_filters[i];
			template = template + '<div class="form-row"><div style="float: left; width: 40px; margin-right: 10px;">';
			if( filter["checked"] ) {
			    template = template + '<input type="checkbox" name="t_'+ filter['filterpath'] +'" checked="checked">';
			}
			else {
			    template = template + '<input type="checkbox" name="t_'+ filter['filterpath'] +'" >';
			}
			template = template + '</div><div style="float: left; margin-right: 10px;">' + 
				   filter['short_desc'] + '<div class="toolParamHelp" style="clear: both;">' + filter['desc'] + '</div></div>' +
				   '<div style="clear: both"></div></div>';
		    }
		    template = template + '</div>';
		}
		if( section_filters.length > 0 ) {
		    template = template + '<div class="toolFormTitle">Edit ToolBox filters :: Sections</div> <div class="toolFormBody">';
		    for( var i=0; i < section_filters.length; i++ ) {
                        var filter = section_filters[i];
			template = template + '<div class="form-row"><div style="float: left; width: 40px; margin-right: 10px;">';
			if( filter["checked"] ) {
			    template = template + '<input type="checkbox" name="s_'+ filter['filterpath'] +'" checked="checked">';
			}
			else {
			    template = template + '<input type="checkbox" name="s_'+ filter['filterpath'] +'" >';
			}
			template = template + '</div><div style="float: left; margin-right: 10px;">' + 
				   filter['short_desc'] + '<div class="toolParamHelp" style="clear: both;">' + filter['desc'] + '</div></div>' +
				   '<div style="clear: both"></div></div>';
		    }
		    template = template + '</div>';
		}
		if( label_filters.length > 0 ) {
		    template = template + '<div class="toolFormTitle">Edit ToolBox filters :: Labels</div> <div class="toolFormBody">';
		     for( var i=0; i < label_filters.length; i++ ) {
                        var filter = label_filters[i];
			template = template + '<div class="form-row"><div style="float: left; width: 40px; margin-right: 10px;">';
			if( filter["checked"] ) {
			    template = template + '<input type="checkbox" name="l_'+ filter['filterpath'] +'" checked="checked">';
			}
			else {
			    template = template + '<input type="checkbox" name="l_'+ filter['filterpath'] +'" >';
			}
			template = template + '</div><div style="float: left; margin-right: 10px;">' + 
				   filter['short_desc'] + '<div class="toolParamHelp" style="clear: both;">' + filter['desc'] + '</div></div>' +
				   '<div style="clear: both"></div></div>';
		    }
		    template = template + '</div>';
		}
		template = template + '<div class="form-row">' +
			   '<input type="button" class="save-toolbox-filter action-button" name="edit_toolbox_filter_button" value="Save changes">' +
			   '</div></form></div>';
        } // end of if
        else {
            template = self.renderMessage("No filters available. Contact your system administrator or check your configuration file.", "info");
        }
        template = template + '</div>';
        $('.user-preferences-all').append( template );
        $('.save-toolbox-filter').on( 'click', function( e ) { self.saveToolboxFilter( self, e ) } );
        $('.back-user-pref').on( 'click', function( e ) {
            $('.manage-toolbox-filters-section').remove();
            Manage.ManageUserInformation.prototype.hideErrorDoneMessage();
            $( '.user-pref' ).show();
        });
    },

    /** saves the changes in toolbox filters */
    saveToolboxFilter: function( self, e ) {
        var url = Galaxy.root + 'api/user_preferences/edit_toolbox_filters',
            data = {},
            checked_filters = [],
            messageBar = Manage.ManageUserInformation.prototype;

        // collects all the checkboxes which are checked
        $( "input[type='checkbox']" ).each(function( item ) {
            var item_obj = $( this );
            if( item_obj.attr("checked") || item_obj.attr("checked") === true ) {
                checked_filters.push( item_obj.attr("name") );
            }
        });
        data = { 'edit_toolbox_filter_button': true, 'checked_filters': JSON.stringify( checked_filters ) };
        $.getJSON( url, data, function( response ) {
             if( response["status"] === 'error' ) {
                  messageBar.renderError( response["message"] );
             }
             else {
                  $('.manage-toolbox-filters-section').remove();
                  $( '.user-pref' ).show();
                  messageBar.renderDone( response["message"] );
             }    
        });
    }
});

return {
    ToolboxFilter: ToolboxFilter
};

});

