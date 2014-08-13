// dependencies
define(['mvc/ui/ui-table', 'mvc/ui/ui-misc', 'utils/utils'],
        function(Table, Ui, Utils) {

/**
 *  This class renders the data group selection fields.
 */
return Backbone.View.extend({
    // initialize
    initialize: function(app, options) {
        // link app
        this.app = app;
        
        // link this
        var self = this;
        
        // get current chart object
        this.chart = this.app.chart;
        
        // access group
        this.group = options.group;
        
        // ui elements
        this.group_key = new Ui.Input({
            placeholder: 'Data label',
            onchange: function(value) {
                self.group.set('key', value);
            }
        });
        this.table = new Table.View({content: 'No data column.'});
        
        // create element
        var $view = $('<div/>');
        $view.append(Utils.wrap((new Ui.Label({title: 'Provide a label:'})).$el));
        $view.append(Utils.wrap(this.group_key.$el));
        $view.append(Utils.wrap((new Ui.Label({title: 'Select columns:'})).$el));
        $view.append(Utils.wrap(this.table.$el));
        
        // add element
        this.setElement($view);
        
        // change
        var self = this;
        this.chart.on('change:dataset_id', function() {
            self._refreshTable();
        });
        this.chart.on('change:type', function() {
            self._refreshTable();
        });
        this.group.on('change:key', function() {
            self._refreshGroupKey();
        });
        this.group.on('change', function() {
            self._refreshGroup();
        });
        
        // refresh
        this._refreshTable();
        this._refreshGroupKey();
        this._refreshGroup();
    },
    
    // update group selection table
    _refreshTable: function() {
        // identify datasets
        var dataset_id = this.chart.get('dataset_id');
        var chart_type = this.chart.get('type');
        
        // check if dataset is available
        if (!dataset_id || !chart_type) {
            return;
        }
        
        // link this
        var self = this;
        
        // configure chart type
        var chart_definition = this.chart.definition;
        
        // reset table
        this.table.delAll();
        
        // load list for select fields
        var select_list = {};
        for (var id in chart_definition.columns) {
            // get definition
            var data_def = chart_definition.columns[id];
            if (!data_def) {
                console.debug('Group::_refreshTable() - Skipping column definition.');
                continue;
            }

            // create select field
            var select = new Ui.Select.View({
                id      : 'select_' + id,
                wait    : true
            });
            
            // title
            var title = data_def.title;
            
            // is unique
            if (data_def.is_unique) {
                title += '&nbsp;(all data labels)';
            }
            
            // add row to table
            this.table.add(title, '25%');
            this.table.add(select.$el);
            this.table.append(id);
            
            // add select field to list
            select_list[id] = select;
        }
        
        // loading
        this.chart.state('wait', 'Loading metadata...');
        
        // register process
        var process_id = this.app.deferred.register();
        
        // request dictionary
        var request_dictionary = {
            id      : dataset_id,
            success : function(dataset) {
                // update select fields
                for (var id in select_list) {
                    self._addRow(id, dataset, select_list, chart_definition.columns[id])
                }
                
                // loading
                self.chart.state('ok', 'Metadata initialized...');
                
                // unregister
                self.app.deferred.done(process_id);
            }
        };
        
        // get dataset
        this.app.datasets.request(request_dictionary);
    },
    
    // add row
    _addRow: function(id, dataset, select_list, column_definition) {
        // link this
        var self = this;
        
        // is a numeric number required
        var is_label    = column_definition.is_label;
        var is_auto     = column_definition.is_auto;
        var is_numeric  = column_definition.is_numeric;
        var is_unique   = column_definition.is_unique;
        var is_zero     = column_definition.is_zero;
        
        // configure columns
        var columns = [];
        
        // get select
        var select = select_list[id];
        
        // add auto selection column
        if (is_auto) {
            columns.push({
                'label' : 'Column: Row Number',
                'value' : 'auto'
            });
        }
        
        // add zero selection column
        if (is_zero) {
            columns.push({
                'label' : 'Column: None',
                'value' : 'zero'
            });
        }
        
        // meta data
        var meta = dataset.metadata_column_types;
        for (var key in meta) {
            // check type
            var valid = false;
            if (meta[key] == 'int' || meta[key] == 'float') {
                valid = is_numeric;
            } else {
                valid = is_label;
            }
            
            // check type
            if (valid) {
                // add to selection
                columns.push({
                    'label' : 'Column: ' + (parseInt(key) + 1) + ' [' + meta[key] + ']',
                    'value' : key
                });
            }
        }
    
        // update selection list
        select.update(columns);
        
        // set initial value
        if (is_unique && this.chart.groups.first()) {
            this.group.set(id, this.chart.groups.first().get(id));
        }
        
        // update current value
        if (!select.exists(this.group.get(id))) {
            // get first value
            var first = select.first();
            
            // log
            console.debug('Group()::_addRow() - Switching model value from "' + this.group.get(id) + '" to "' + first + '".');
            
            // update model value
            this.group.set(id, first);
        }
        
        // set group value
        select.value(this.group.get(id));
        
        // link group with select field
        this.group.off('change:' + id);
        this.group.on('change:' + id, function(){
            select.value(self.group.get(id));
        });
        
        // link select field with group
        select.setOnChange(function(value) {
            // update model value
            if (is_unique) {
                // update all groups
                self.chart.groups.each(function(group) {
                    group.set(id, value);
                });
            } else {
                // only change this group
                self.group.set(id, value);
            }
            self.chart.set('modified', true);
        });
        
        // show select field
        select.show();
    },
    
    // update
    _refreshGroup: function() {
        this.group.set('date', Utils.time());
    },
    
    // update group key
    _refreshGroupKey: function() {
        var key_text = this.group.get('key');
        if (key_text === undefined) {
            key_text = '';
        }
        this.group_key.value(key_text);
    }
});

});