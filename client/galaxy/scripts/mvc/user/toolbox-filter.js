/** Save the toolbox filters view */
define( [ 'mvc/form/form-view', 'mvc/ui/ui-misc' ], function( Form, Ui ) {
    var ToolboxFilter = Backbone.View.extend({
        initialize: function ( app, options ) {
            var self = this;
            this.model = options && options.model || new Backbone.Model( options );
            this.form = new Form({
                title   : 'Manage Toolbox Filters',
                name    : 'toolbox_filter',
                id      : 'toolbox_filter',
                inputs  : self._buildFormInputs( options ),
                operations : {
                    'back' : new Ui.ButtonIcon({
                        icon    : 'fa-caret-left',
                        tooltip : 'Return to user preferences',
                        title   : 'Preferences',
                        onclick : function() { self.remove(); app.showPreferences() }
                    })
                },
                buttons : {
                    'savesfilterboxchanges' : new Ui.Button({
                        tooltip : 'Save changes',
                        title   : 'Save changes',
                        cls     : 'ui-button btn btn-primary',
                        floating: 'clear',
                        onclick : function() { self._saveToolboxFilter() }
                    })
                }
            });
            this.setElement( this.form.$el );
        },

        /** build the inputs for each filter */
        _buildFormInputs: function( data ) {
            var all_inputs = [],
                tools = {},
                sections = {},
                labels = {},
                tool_filters = JSON.parse( data["tool_filters"] ),
                label_filters =  JSON.parse( data["label_filters"] ),
                section_filters = JSON.parse( data["section_filters"] );

            if( tool_filters.length > 0 || section_filters.length > 0 || label_filters.length > 0 ) {
                if( tool_filters.length > 0 ) {
                    tools = {  
                        name: 'Edit ToolBox filters :: Tools',
                        type: 'section',
                        label: '',
                        inputs: [],
                        expanded: true
                    }
                    // build inputs for tool filter
                    for( var i = 0; i < tool_filters.length; i++ ) { 
                        var filter = tool_filters[i],
                            helptext = filter['short_desc'] + " " + filter['desc'];
                        tools.inputs.push( { name: "t_" + filter['filterpath'],
                                             type: 'boolean',
                                             label: filter['filterpath'],
                                             help: helptext,
                                             value: filter['checked'] } );
                    }
                    all_inputs.push( tools );
		}
                if( section_filters.length > 0 ) {
                    sections = {  
                        name: 'Edit ToolBox filters :: Sections',
                        type: 'section',
                        label: 'Edit ToolBox filters :: Sections',
                        inputs: [],
                        expanded: true
                    }
                    // build inputs for section filter
                    for( var i = 0; i < section_filters.length; i++ ) { 
                        var filter = section_filters[i],
                            helptext = filter['short_desc'] + " " + filter['desc'];
                        sections.inputs.push( { name: "s_" + filter['filterpath'],
                                                type: 'boolean',
                                                label: filter['filterpath'],
                                                help: helptext,
                                                value: filter['checked'] } );
                    }
                    all_inputs.push( sections );
		}
                if( label_filters.length > 0 ) {
                    labels = {  
                        name: 'Edit ToolBox filters :: Labels',
                        type: 'section',
                        label: 'Edit ToolBox filters :: Labels',
                        inputs: [],
                        expanded: true
                    }
                    // build inputs for label filters
                    for( var i = 0; i < label_filters.length; i++ ) { 
                        var filter = label_filters[i],
                            helptext = filter['short_desc'] + " " + filter['desc'];
                        labels.inputs.push( { name: "l_" + filter['filterpath'],
                                              type: 'boolean',
                                              label: filter['filterpath'],
                                              help: helptext,
                                              value: filter['checked'] } ); 
                    }
                    all_inputs.push( labels );
		}
            }
            return all_inputs;
        },

        /** saves the changes made to the filters */
        _saveToolboxFilter: function() {
            var url = Galaxy.root + 'api/user_preferences/edit_toolbox_filters',
                data = {},
                self = this;
            data = { 'edit_toolbox_filter_button': true, 'checked_filters': JSON.stringify( self.form.data.create() ) };
            $.getJSON( url, data, function( response ) {
                self.form.message.update({
                    message     : response.message,
                    status      : response.status === 'error' ? 'danger' : 'success',
                });
            });
        }
    });

    return {
        ToolboxFilter: ToolboxFilter
    };
});

