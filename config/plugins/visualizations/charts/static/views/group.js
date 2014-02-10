// dependencies
define(['library/portlet', 'library/table', 'library/ui', 'library/utils'],
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
    
        // get current chart object
        this.chart = this.app.chart;
        this.group = this.app.group;
        
        // ui elements
        this.message = new Ui.Message();
        this.label = new Ui.Input({placeholder: 'Group label'});
        this.table = new Table({content: 'No data column.'});
        
        // add table to portlet
        var self = this;
        this.portlet = new Portlet({
            icon : 'fa-edit',
            label : 'Define group properties:',
            operations : {
                'save'      : new Ui.ButtonIcon({
                                icon    : 'fa-save',
                                tooltip : 'Save',
                                onclick : function() {
                                    // save/add group
                                    self._saveGroup();
                                }
                            }),
                'back'      : new Ui.ButtonIcon({
                                icon    : 'fa-caret-left',
                                tooltip : 'Return',
                                onclick : function() {
                                    self.$el.hide();
                                    self.app.chart_view.$el.show();
                                }
                            })
            }
        });
        this.portlet.append(this.message.$el);
        this.portlet.append(this.label.$el);
        this.portlet.append(this.table.$el);
        
        // add element
        this.setElement(this.portlet.$el);
        
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
        this.group.on('reset', function() {
            self._resetGroup();
        });
    },
    
    // show
    show: function() {
        this.$el.show();
    },
    
    // reset
    _resetGroup: function() {
        this.group.set('id', Utils.uuid());
        this.group.set('label', 'Group label');
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
            this.app.log('Config::render()', 'Failed to retrieve dataset.');
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
                    }
                });
                
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
        // update select fields
        for (var id in this.list) {
            var col = this.group.get(id);
            if (col === undefined) {
                col = 0;
            }
            this.list[id].value(col);
        }
    },
    
    // update label
    _refreshLabel: function() {
        var label_text = this.group.get('label');
        if (label_text === undefined) {
            label_text = '';
        }
        this.label.value(label_text);
    },
    
    // create group
    _saveGroup: function() {
        // get current chart
        var chart = this.chart;
        
        // update group object
        var group = this.group;
        for (var key in this.list) {
            group.set(key, this.list[key].value());
        }
        
        // add label
        group.set({
            dataset_id  : this.chart.get('dataset_id'),
            label       : this.label.value(),
            date        : Utils.time()
        });
        
        // validate
        if (!group.get('label')) {
            this.message.update({message : 'Please enter a label for your group.'});
            return;
        }
        
        // get groups of current chart
        var groups = this.chart.groups;
        
        // create/update group
        var group_update = groups.get(group.id);
        if (group_update) {
            group_update.set(group.attributes);
        } else {
            groups.add(group.clone());
        }
        
        // hide
        this.$el.hide();
        
        // update main
        this.app.chart_view.$el.show();
    }
});

});