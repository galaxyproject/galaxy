// dependencies
define(['library/portlet', 'library/table', 'library/ui', 'library/utils'], function(Portlet, Table, Ui, Utils) {

// widget
return Backbone.View.extend(
{
    // initialize
    initialize: function(app, options)
    {
        // link app
        this.app = app;
        
        // table
        this.table = new Table({
            content     : 'Add charts to this table.',
            ondblclick  : function(chart_id) {
                // get chart
                var chart = self.app.charts.get(chart_id);
                self.app.chart.copy(chart);
                               
                // show edit
                self.$el.hide();
                
                // update model and show create
                self.app.chart_view.$el.show();
            },
            onchange : function(chart_id) {
                self.app.viewport_view.show(chart_id);
            }
        });
        
        // add table to portlet
        var self = this;
        this.portlet = new Portlet({
            icon : 'fa-list',
            label : 'List of created charts:',
            height : 100,
            operations : {
                'new'   : new Ui.ButtonIcon({
                            icon : 'fa-plus',
                            tooltip: 'Create',
                            onclick: function() {
                                self.$el.hide();
                                self.app.chart.reset();
                                self.app.chart_view.$el.show();
                            }
                        }),
                'delete' : new Ui.ButtonIcon({
                    icon : 'fa-minus',
                    tooltip: 'Delete',
                    onclick: function() {
                            
                            // check if element has been selected
                            var chart_id = self.table.value();
                            if (!chart_id) {
                                return;
                            }
                    
                            // title
                            var chart = self.app.charts.get(chart_id);
                    
                            // show modal
                            self.app.modal.show({
                            title   : 'Are you sure?',
                            body    : 'The selected chart "' + chart.get('title') + '" will be irreversibly deleted.',
                            buttons : {
                                'Cancel'    : function() {self.app.modal.hide();},
                                'Delete'    : function() {
                                    // hide modal
                                    self.app.modal.hide();
                                    
                                    // remove chart
                                    self.app.charts.remove(chart_id);
                                }
                            }
                        });
                    }
                }),
            }
        });
        this.portlet.append(this.table.$el);
        
        // append to main
        if (!this.app.options.config.widget) {
            this.$el.append(this.portlet.$el);
        }
        
        // events
        var self = this;
        this.app.charts.on('add', function(chart) {
            // add
            self._addChart(chart);
        });
        this.app.charts.on('remove', function(chart) {
            // remove
            self._removeChart(chart);
        });
        this.app.charts.on('change', function(chart) {
            // replace
            self._removeChart(chart);
            self._addChart(chart);
        });
    },
    
    // append
    append : function($el) {
        this.$el.append(Utils.wrap(''));
        this.$el.append($el);
    },
    
    // add
    _addChart: function(chart) {
        // add title to table
        this.table.add(chart.get('title'));
        
        // get chart type
        var type = this.app.types.get(chart.get('type'));
        this.table.add(type.title);
        
        // add additional columns
        this.table.add('Last change: ' + chart.get('date'));
        this.table.prepend(chart.get('id'));
        this.table.value(chart.get('id'));
    },
    
    // remove
    _removeChart: function(chart) {
        // remove from to table
        this.table.remove(chart.id);
    }
});

});