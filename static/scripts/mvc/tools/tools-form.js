define(['mvc/ui/ui-portlet', 'mvc/ui/ui-table', 'mvc/ui/ui-misc',
        'mvc/citation/citation-model', 'mvc/citation/citation-view',
        'mvc/tools', 'mvc/tools/tools-template', 'mvc/tools/tools-datasets'],
    function(Portlet, Table, Ui, CitationModel, CitationView,
             Tools, ToolTemplate, ToolDatasets) {

    // create tool model
    var Model = Backbone.Model.extend({
        initialize: function (options) {
            this.url = galaxy_config.root + 'api/tools/' + options.id + '?io_details=true';
        }
    });

    // create form view
    var View = Backbone.View.extend({
        // base element
        main_el: 'body',
        
        // initialize
        initialize: function(options) {
            // link this
            var self = this;
            
            // link options
            this.options = options;
            
            // load tool model
            this.model = new Model({
                id : options.id
            });
            
            // initialize datasets
            this.datasets = new ToolDatasets({
                success: function() {
                    self._initializeToolForm();
                }
            });
        },
        
        // initialize tool form
        _initializeToolForm: function() {
            // fetch model and render form
            var self = this;
            this.model.fetch({
                success: function() {
                    // inputs
                    self.inputs = self.model.get('inputs');
            
                    // create portlet
                    self.portlet = new Portlet.View({
                        icon : 'fa-wrench',
                        title: '<b>' + self.model.get('name') + '</b> ' + self.model.get('description'),
                        buttons: {
                            execute: new Ui.ButtonIcon({
                                icon     : 'fa-check',
                                tooltip  : 'Execute the tool',
                                title    : 'Execute',
                                floating : 'clear',
                                onclick  : function() {
                                }
                            })
                        }
                    });
                    
                    // create table
                    self.table = new Table.View();
                    
                    // create message
                    self.message = new Ui.Message();
                    self.portlet.append(self.message.$el);
                    
                    // append form
                    $(self.main_el).append(self.portlet.$el);
                    
                    // append help
                    if (self.options.help != '') {
                        $(self.main_el).append(ToolTemplate.help(self.options.help));
                    }
                    
                    // append citations
                    if (self.options.citations) {
                        // append html
                        $(self.main_el).append(ToolTemplate.citations());
            
                        // fetch citations
                        var citations = new CitationModel.ToolCitationCollection();
                        citations.tool_id = self.options.id;
                        var citation_list_view = new CitationView.CitationListView({ collection: citations } );
                        citation_list_view.render();
                        citations.fetch();
                    }
                    
                    // configure portlet and form table
                    self.setElement(self.portlet.content());
                    self.portlet.append(self.table.$el);
                    self.render();
                }
            });
        },
        
        // update
        render: function() {
            // reset table
            this.table.delAll();
            
            // reset list
            this.list = [];
            
            // model
            var data = new Backbone.Model();
            
            // load settings elements into table
            for (var id in this.inputs) {
                this._add(this.inputs[id], data);
            }
            
            // trigger change
            for (var id in this.list) {
                this.list[id].trigger('change');
            }
        },
        
        // add table row
        _add: function(inputs_def, data) {
            // link this
            var self = this;
            
            // get id
            var id = inputs_def.name;
            
            // field wrapper
            var field = null;
            console.log(inputs_def);
            // create select field
            var type = inputs_def.type;
            switch(type) {
                // text input field
                case 'text' :
                    field = this.field_text(inputs_def, data);
                    break;
                    
                // select field
                case 'select' :
                    field = this.field_select(inputs_def, data);
                    break;
                    
                // radiobox field
                case 'radiobutton' :
                    field = this.field_radio(inputs_def, data);
                    break;
                
                // dataset
                case 'data':
                    field = this.field_data(inputs_def, data);
                    break;
                
                // dataset column
                case 'data_column':
                    field = this.field_column(inputs_def, data);
                    break;
                
                // text area field
                case 'textarea' :
                    field = this.field_textarea(inputs_def, data);
                    break;

                // default
                default:
                    field = new Ui.Input({
                        id          : 'field-' + id,
                        placeholder : inputs_def.placeholder,
                        type        : inputs_def.type,
                        onchange    : function() {
                            data.set(id, field.value());
                        }
                    });
            }
            
            // set value
            if (!data.get(id)) {
                data.set(id, inputs_def.value);
            }
            field.value(data.get(id));
            
            // add list
            this.list[id] = field;
            
            // combine field and info
            var $input = $('<div/>');
            $input.append(field.$el);
            if (inputs_def.info) {
                $input.append('<div class="ui-table-form-info">' + inputs_def.info + '</div>');
            }
            
            // add row to table
            this.table.add('<span class="ui-table-form-title">' + inputs_def.label + '</span>', '25%');
            this.table.add($input);
            
            // add to table
            this.table.append(id);
            
            // show/hide
            if (inputs_def.hide) {
                this.table.get(id).hide();
            }
        },
        
        // text input field
        field_text : function(inputs_def, data) {
            var id = inputs_def.name;
            return new Ui.Input({
                id          : 'field-' + id,
                value       : data.get(id),
                onchange    : function(value) {
                    data.set(id, value);
                }
            });
        },
        
        // text area
        field_textarea : function(inputs_def, data) {
            var id = inputs_def.name;
            return new Ui.Textarea({
                id          : 'field-' + id,
                onchange    : function() {
                    data.set(id, field.value());
                }
            });
        },
        
        // data input field
        field_data : function(inputs_def, data) {
            // link this
            var self = this;
            
            // get element id
            var id = inputs_def.name;
            
            // get datasets
            var datasets = this.datasets.filterType();
            
            // configure options fields
            var options = [];
            for (var i in datasets) {
                options.push({
                    label: datasets[i].get('name'),
                    value: datasets[i].get('id')
                });
            }
            
            // find referenced columns
            var column_list = _.where(this.inputs, {
                data_ref    : id,
                type        : 'data_column'
            });
            
            // select field
            return new Ui.Select.View({
                id          : 'field-' + id,
                data        : options,
                value       : options[0].value,
                onchange    : function(value) {
                    // update value
                    data.set(id, value);
                    
                    // find selected dataset
                    var dataset = self.datasets.filter(value);
        
                    // check dataset
                    if (dataset && column_list.length > 0) {
                        // log selection
                        console.debug('tool-form::field_data() - Selected dataset ' + value + '.');
                    
                        // get meta data
                        var meta = dataset.get('metadata_column_types');
                    
                        // check meta data
                        if (!meta) {
                            console.debug('tool-form::field_data() - FAILED: Could not find metadata for dataset ' + value + '.');
                        }
                        
                        // load column options
                        var columns = [];
                        for (var key in meta) {
                            // add to selection
                            columns.push({
                                'label' : 'Column: ' + (parseInt(key) + 1) + ' [' + meta[key] + ']',
                                'value' : key
                            });
                        }
                
                        // update referenced columns
                        for (var i in column_list) {
                            var column_field = self.list[column_list[i].name]
                            if (column_field) {
                                column_field.update(columns);
                                column_field.value(column_field.first());
                            }
                        }
                    } else {
                        // log failure
                        console.debug('tool-form::field_data() - FAILED: Could not find dataset ' + value + '.');
                    }
                }
            });
        },
        
        // select field
        field_column : function (inputs_def, data) {
            // configure options fields
            var options = [];
            for (var i in inputs_def.options) {
                var option = inputs_def.options[i];
                options.push({
                    label: option[0],
                    value: option[1]
                });
            }
            
            // select field
            var id = inputs_def.name;
            return new Ui.Select.View({
                id          : 'field-' + id,
                data        : options,
                value       : data.get(id),
                onchange    : function(value) {
                    data.set(id, value);
                }
            });
        },

        // select field
        field_select : function (inputs_def, data) {
            // configure options fields
            var options = [];
            for (var i in inputs_def.options) {
                var option = inputs_def.options[i];
                options.push({
                    label: option[0],
                    value: option[1]
                });
            }
            
            // identify display type
            var SelectClass = Ui.Select;
            if (inputs_def.display == 'checkboxes') {
                SelectClass = Ui.Checkbox;
            }
            
            // select field
            var id = inputs_def.name;
            return new SelectClass.View({
                id          : 'field-' + id,
                data        : options,
                value       : data.get(id),
                onchange    : function(value) {
                    data.set(id, value);
                }
            });
        },
        
        // radio field
        field_radio : function(inputs_def, data) {
            var id = inputs_def.name;
            return new Ui.RadioButton({
                id          : 'field-' + id,
                data        : inputs_def.data,
                value       : data.get(id),
                onchange    : function(value) {
                    data.set(id, value);
                }
            });
        }
    });

    return {
        View: View
    };
});
