define(['mvc/tools', 'mvc/ui/ui-portlet', 'mvc/ui/ui-table', 'mvc/ui/ui-misc'], function(Tools, Portlet, Table, Ui) {

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
            
            // load tool model
            this.model = new Model({
                id : options.id
            });
            
            // fetch model and render form
            this.model.fetch({
                success: function() {
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
                    
                    // table
                    self.table = new Table.View();
                    
                    // add message
                    self.message = new Ui.Message();
                    self.portlet.append(self.message.$el);
                    
                    // append portlet
                    $(self.main_el).append(self.portlet.$el);
                    self.setElement(self.portlet.content());
                    self.portlet.append(self.table.$el);
                    self.render();
                }
            });
        },
        
        // update
        render: function() {
            // inputs
            var settings = this.model.get('inputs');
        
            // reset table
            this.table.delAll();
            
            // reset list
            this.list = [];
            
            // model
            var data = new Backbone.Model();
            
            // load settings elements into table
            for (var id in settings) {
                this._add(settings[id], data);
            }
            
            // trigger change
            for (var id in this.list) {
                this.list[id].trigger('change');
            }
        },
        
        // add table row
        _add: function(settings_def, data) {
            // link this
            var self = this;
            
            // get id
            var id = settings_def.name;
            
            // log
            console.debug(settings_def);
            
            // field wrapper
            var field = null;
            
            // create select field
            var type = settings_def.type;
            switch(type) {
                // text input field
                case 'text' :
                    field = this.field_text(settings_def, data);
                    break;
                    
                // select field
                case 'select' :
                    field = this.field_select(settings_def, data);
                    break;
                    
                // radiobox field
                case 'radiobutton' :
                    field = this.field_radio(settings_def, data);
                    break;
                
                // dataset
                case 'data':
                    field = this.field_select(settings_def, data);
                    break;
                
                // slider input field
                case 'textarea' :
                    field = this.field_textarea(settings_def, data);
                    break;

                // default
                default:
                    field = new Ui.Input({
                        id          : 'field-' + id,
                        placeholder : settings_def.placeholder,
                        type        : settings_def.type,
                        onchange    : function() {
                            data.set(id, field.value());
                        }
                    });
            }
            
            // set value
            if (!data.get(id)) {
                data.set(id, settings_def.value);
            }
            field.value(data.get(id));
            
            // add list
            this.list[id] = field;
            
            // combine field and info
            var $input = $('<div/>');
            $input.append(field.$el);
            if (settings_def.info) {
                $input.append('<div class="ui-table-form-info">' + settings_def.info + '</div>');
            }
            
            // add row to table
            if (this.options.style == 'bold') {
                this.table.add(new Ui.Label({title: settings_def.title, cls: 'form-label'}).$el);
                this.table.add($input);
            } else {
                this.table.add('<span class="ui-table-form-title">' + settings_def.label + '</span>', '25%');
                this.table.add($input);
            }
        
            // add to table
            this.table.append(id);
            
            // show/hide
            if (settings_def.hide) {
                this.table.get(id).hide();
            }
        },
        
        // text input field
        field_text : function(settings_def, data) {
            var id = settings_def.name;
            return new Ui.Input({
                id          : 'field-' + id,
                value       : data.get(id),
                onchange    : function(value) {
                    data.set(id, value);
                }
            });
        },
        
        // text area
        field_textarea : function(settings_def, data) {
            var id = settings_def.name;
            return new Ui.Textarea({
                id          : 'field-' + id,
                onchange    : function() {
                    data.set(id, field.value());
                }
            });
        },
        
        // select field
        field_select : function (settings_def, data) {
            // configure options fields
            var options = [];
            for (var i in settings_def.options) {
                var option = settings_def.options[i];
                options.push({
                    label: option[0],
                    value: option[1]
                });
            }
            
            // select field
            var id = settings_def.name;
            return new Ui.Select.View({
                id          : 'field-' + id,
                data        : options,
                value       : data.get(id),
                onchange    : function(value) {
                    // set new value
                    data.set(id, value);
                    
                    // find selected dictionary
                    var dict = _.findWhere(options, {value: value});
                    if (dict && dict.operations) {
                        var operations = dict.operations;
                        for (var i in operations.show) {
                            var target = operations.show[i];
                            self.table.get(target).show();
                        }
                        for (var i in operations.hide) {
                            var target = operations.hide[i];
                            self.table.get(target).hide();
                        }
                    }
                }
            });
        },
        
        // radio field
        field_radio : function(settings_def, data) {
            var id = settings_def.name;
            return new Ui.RadioButton({
                id          : 'field-' + id,
                data        : settings_def.data,
                value       : data.get(id),
                onchange    : function(value) {
                    // set new value
                    data.set(id, value);
                    
                    // find selected dictionary
                    var dict = _.findWhere(settings_def.data, {value: value});
                    if (dict && dict.operations) {
                        var operations = dict.operations;
                        for (var i in operations.show) {
                            var target = operations.show[i];
                            self.table.get(target).show();
                        }
                        for (var i in operations.hide) {
                            var target = operations.hide[i];
                            self.table.get(target).hide();
                        }
                    }
                }
            });
        }
    });

    return {
        View: View
    };
});
