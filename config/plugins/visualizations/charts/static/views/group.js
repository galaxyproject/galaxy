// dependencies
define(['plugin/library/ui-table', 'plugin/library/ui', 'utils/utils'],
        function(Table, Ui, Utils) {

// widget
return Backbone.View.extend(
{
    // columns
    columns: [],
    
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
            onchange: function() {
                self.group.set('key', self.group_key.value());
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
    
    // update dataset
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
        var chart_settings = this.app.types.get(chart_type);
    
        // reset table
        this.table.removeAll();
        
        // load list
        var list = {};
        for (var id in chart_settings.columns) {
            // initialize
            var value = this.group.get(id);
            if (!value) {
                this.group.set(id, 0);
            }
            
            // create select field
            var data_def = chart_settings.columns[id];
            var select = new Ui.Select.View({
                id   : 'select_' + id,
                gid  : id,
                onchange : function(value) {
                    self.group.set(this.gid, value);
                    self.chart.set('modified', true);
                },
                value : value,
                wait  : true
            });
    
            // add row to table
            this.table.add(data_def.title, '25%');
            this.table.add(select.$el);
            this.table.append(id);
            
            // add select field to list
            list[id] = select;
        }
        
        // loading
        this.chart.state('wait', 'Loading metadata...');
        
        // register process
        var process_id = this.chart.deferred.register();
        
        // get dataset
        this.app.datasets.request({id : dataset_id}, function(dataset) {
            // configure columns
            self.columns = [];
            var meta = dataset.metadata_column_types;
            for (var key in meta) {
                // check type
                if(meta[key] == 'int' || meta[key] == 'float') {
                    // add to selection
                    self.columns.push({
                        'label' : 'Column: ' + (parseInt(key) + 1) + ' [' + meta[key] + ']',
                        'value' : key
                    });
                }
            }
            
            // update select fields
            for (var key in list) {
                list[key].update(self.columns);
                list[key].show();
            }
            
            // loading
            self.chart.state('wait', 'Metadata initialized...');
            
            // unregister
            self.chart.deferred.done(process_id);
        });
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