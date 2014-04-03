// dependencies
define(['plugin/library/ui-table', 'plugin/library/ui', 'utils/utils'],
        function(Table, Ui, Utils) {

// widget
var View = Backbone.View.extend(
{
    // elements
    list: [],
    
    // initialize
    initialize: function(options) {
        // ui elements
        this.table_title = new Ui.Label({title: options.title});
        this.table = new Table.View({content: options.content});
        
        // create element
        var $view = $('<div/>');
        $view.append(Utils.wrap(this.table_title.$el));
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
        this.table.removeAll();
        
        // reset list
        this.list = [];
        
        // load settings elements into table
        for (var id in settings) {
            this._add(id, settings[id], model);
        }
        
        // trigger change
        for (var id in this.list) {
            var onchange = this.list[id].options.onchange;
            if (onchange) {
                onchange();
            }
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
                            id          : id,
                            placeholder : settings_def.placeholder,
                            onchange    : function() {
                                model.set(id, field.value());
                            }
                        });
                break;
            // select field
            case 'select' :
                field = new Ui.Select.View({
                            id          : id,
                            data        : settings_def.data,
                            onchange    : function() {
                                // set new value
                                var selected = field.value();
                                model.set(id, selected);
                                
                                // find selected dictionary
                                var dict = _.findWhere(settings_def.data, {value: selected});
                                if (dict) {
                                    if (dict.show) {
                                        self.$el.find('#' + dict.show).fadeIn('fast');
                                    }
                                    if (dict.hide) {
                                        self.$el.find('#' + dict.hide).fadeOut('fast');
                                    }
                                }
                            }
                        });
                break;
            // slider input field
            case 'separator' :
                field = $('<div/>');
                break;
            // skip unkown types
            default:
                console.log('ui-table-form:_add', 'Unknown setting type (' + settings_def.type + ')');
                return;
        
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
            $input.append('<div class="toolParamHelp"  style="font-size: 0.9em;">' + settings_def.info + '</div>');
            
            // add row to table
            this.table.add('<span style="white-space: nowrap;">' + settings_def.title + '</span>', '25%');
            this.table.add($input);
        } else {
            this.table.add('<h6 style="white-space: nowrap;">' + settings_def.title + ':<h6/>');
            this.table.add($('<div/>'));
        }
        
        // add to table
        this.table.append(id);
    }
});

return {
    View : View
}

});