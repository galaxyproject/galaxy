// dependencies
define(['mvc/ui/ui-portlet', 'plugin/library/table', 'plugin/library/ui', 'utils/utils'],
        function(Portlet, Table, Ui, Utils) {

// chart config
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
        this.label = new Ui.Input({
            placeholder: 'Data label',
            onchange: function() {
                self.group.set('label', self.label.value());
            }
        });
        this.table = new Table({content: 'No data column.'});
        
        // add table to portlet
        var $view = $('<div/>');
        $view.append(Utils.wrap((new Ui.Label({title: 'Provide a label:'})).$el));
        $view.append(Utils.wrap(this.label.$el));
        $view.append(Utils.wrap((new Ui.Label({title: 'Select columns:'})).$el));
        $view.append(Utils.wrap(this.table.$el));
        
        // add element
        this.setElement($view);
        
        // change
        var self = this;
        this.chart.on('change:dataset_id', function() {
            self._refreshDataset();
        });
        this.chart.on('change:type', function() {
            self._refreshType();
        });
        this.group.on('change:label', function() {
            self._refreshLabel();
        });
        this.group.on('change', function() {
            self._refreshGroup();
        });
        
        // refresh
        this._refresh();
    },
    
    // render
    _refresh: function() {
        this._refreshDataset();
        this._refreshType();
        this._refreshLabel();
        this._refreshGroup();
    },
    
    // update dataset
    _refreshDataset: function() {
        // identify datasets
        var dataset_id = this.chart.get('dataset_id');
        
        // check if dataset is available
        if (!dataset_id) {
            return;
        }
        
        // get dataset
        var dataset = this.app.datasets.get({id : dataset_id});
        
        // check
        if (!dataset) {
            this.app.log('Group::_refreshDataset()', 'Failed to retrieve dataset.');
            return;
        }
        
        // configure columns
        this.columns = [];
        var meta = dataset.metadata_column_types;
        for (var key in meta){
            this.columns.push({
                'label' : key + ' [' + meta[key] + ']',
                'value' : key
            });
        }
        
        // update select fields
        for (var key in this.list) {
            this.list[key].update(this.columns);
        }
    },
    
    // update
    _refreshType: function() {
        // configure chart type
        var self = this;
        var chart_type = this.chart.get('type');
        if (chart_type) {
            var chart_settings = this.app.types.get(chart_type);
        
            // table
            this.table.removeAll();
            this.list = {};
            for (var id in chart_settings.data) {
                // create select field
                var data_def = chart_settings.data[id];
                var select = new Ui.Select({
                    id   : 'select_' + id,
                    gid  : id,
                    data : this.columns,
                    onchange : function(value) {
                        self.group.set(this.gid, value);
                    },
                    value : this.group.get(id)
                });
                
                // set model value
                this.group.set(id, select.value());
                
                // add row to table
                this.table.add(data_def.title);
                this.table.add(select.$el);
                this.table.append(id);
                
                // add select field to list
                this.list[id] = select;
            }
        }
    },
    
    // update
    _refreshGroup: function() {
        this.group.set('date', Utils.time());
    },
    
    // update label
    _refreshLabel: function() {
        var label_text = this.group.get('label');
        if (label_text === undefined) {
            label_text = '';
        }
        this.label.value(label_text);
    }
});

});