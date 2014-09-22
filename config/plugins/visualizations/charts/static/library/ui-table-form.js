// dependencies
define(['mvc/ui/ui-table', 'mvc/ui/ui-misc', 'utils/utils'],
        function(Table, Ui, Utils) {

/**
 *  This class takes a dictionary as input an creates an input form. It uses the Ui.Table element to organize and format the form elements.
 */
var View = Backbone.View.extend({
    // options
    optionsDefault: {
        title       : '',
        content     : '',
        mode        : ''
    },
    
    // elements
    list: [],
    
    // initialize
    initialize: function(app, options) {
        
        // link app
        this.app = app;
        
        // get options
        this.options = Utils.merge(options, this.optionsDefault);
        
        // ui elements
        this.table_title = new Ui.Label({title: this.options.title});
        this.table = new Table.View({content: this.options.content});

        // create element
        var $view = $('<div class="ui-table-form"/>');
        if (this.options.title) {
            $view.append(Utils.wrap(this.table_title.$el));
        }
        $view.append(Utils.wrap(this.table.$el));
        
        // add element
        this.setElement($view);
    },
    
    // title
    title: function(new_title) {
        this.table_title.title(new_title);
    },
    
    // update
    update: function(settings, model) {
        // reset table
        this.table.delAll();
        
        // reset list
        this.list = [];
        
        // load settings elements into table
        for (var id in settings) {
            this._add(settings[id].id || id, settings[id], model);
        }
        
        // trigger change
        for (var id in this.list) {
            this.list[id].trigger('change');
        }
    },
    
    // add table row
    _add: function(id, settings_def, model) {
        // link this
        var self = this;
        
        // field wrapper
        var field = null;
        
        // create select field
        var type = settings_def.type;
        switch(type) {
            // text input field
            case 'text' :
                field = new Ui.Input({
                    id          : 'field-' + id,
                    placeholder : settings_def.placeholder,
                    value       : model.get(id),
                    onchange    : function(value) {
                        model.set(id, value);
                    }
                });
                break;
            // radiobox field
            case 'radiobutton' :
                field = new Ui.RadioButton.View({
                    id          : 'field-' + id,
                    data        : settings_def.data,
                    value       : model.get(id),
                    onchange    : function(value) {
                        // set new value
                        model.set(id, value);
                        
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
                break;
            // select field
            case 'select' :
                field = new Ui.Select.View({
                    id          : 'field-' + id,
                    data        : settings_def.data,
                    value       : model.get(id),
                    onchange    : function(value) {
                        // set new value
                        model.set(id, value);
                        
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
                break;
            case 'dataset':
                field = new Ui.Select.View({
                    id          : 'field-' + id,
                    onchange    : function(value) {
                        // set new value
                        model.set(id, value);
                    }
                });
                
                // link refresh event
                self.app.datasets.on('all', function() {
                    // identify selectables
                    var selectable = [];
                    self.app.datasets.each(function(dataset) {
                        if (dataset.get('datatype_id') == settings_def.data) {
                            selectable.push({value: dataset.get('id'), label: dataset.get('name')});
                        }
                    });
                    
                    // update select field
                    field.update(selectable);
                    
                    // set value
                    if (!model.get(id)) {
                        model.set(id, field.first());
                    }
                    field.value(model.get(id));
                });
                
                // trigger change
                self.app.datasets.trigger('all.datasets');
                break;
            // slider input field
            case 'textarea' :
                field = new Ui.Textarea({
                    id          : 'field-' + id,
                    onchange    : function() {
                        model.set(id, field.value());
                    }
                });
                break;

            // separator
            case 'separator' :
                field = $('<div/>');
                break;
                
            // default
            default:
                field = new Ui.Input({
                    id          : 'field-' + id,
                    placeholder : settings_def.placeholder,
                    type        : settings_def.type,
                    onchange    : function() {
                        model.set(id, field.value());
                    }
                });
        }
        
        // set value
        if (type != 'separator') {
            if (!model.get(id)) {
                model.set(id, settings_def.init);
            }
            field.value(model.get(id));
            
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
                this.table.add('<span class="ui-table-form-title">' + settings_def.title + '</span>', '25%');
                this.table.add($input);
            }
        } else {
            this.table.add('<div class="ui-table-form-separator">' + settings_def.title + ':<div/>');
            this.table.add($('<div/>'));
        }
        
        // add to table
        this.table.append(id);
        
        // show/hide
        if (settings_def.hide) {
            this.table.get(id).hide();
        }
    }
});

return {
    View : View
}

});