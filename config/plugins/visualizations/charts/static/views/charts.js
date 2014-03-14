// dependencies
define(['mvc/ui/ui-portlet', 'plugin/library/ui-table', 'plugin/library/ui', 'utils/utils', 'plugin/models/group', 'plugin/views/viewport',], function(Portlet, Table, Ui, Utils, Group, ViewportView) {

// widget
return Backbone.View.extend(
{
    // initialize
    initialize: function(app, options)
    {
        // link app
        this.app = app;
        
        // create viewport
        this.viewport_view = new ViewportView(app);
        
        // table
        this.table = new Table({
            content     : 'Add charts to this table.',
            ondblclick  : function(chart_id) {
                // get chart
                var chart = self.app.charts.get(chart_id);
                self.app.chart.copy(chart);
                
                // hide this element
                self.hide();
                
                // show chart view
                self.app.chart_view.$el.show();
            },
            onchange : function(chart_id) {
                // get chart
                var chart = self.app.charts.get(chart_id);
                
                // update main title
                self.app.config.set('title', chart.get('title'));
        
                // show viewport
                self.viewport_view.showChart(chart_id);
            }
        });
        
        // add table to portlet
        var self = this;
        this.portlet = new Portlet.View({
            icon : 'fa-list',
            title : 'List of created charts:',
            height : 100,
            operations : {
                'new'   : new Ui.ButtonIcon({
                            icon : 'fa-magic',
                            tooltip: 'Create a new Chart',
                            title: 'New',
                            onclick: function() {
                                self.hide();
                                self.app.chart.reset();
                                self.app.chart_view.$el.show();
                            }
                        }),
                'delete' : new Ui.ButtonIcon({
                    icon : 'fa-trash-o',
                    tooltip: 'Delete this Chart',
                    title: 'Delete',
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
        
        // append portlet with table
        if (!this.app.options.config.widget) {
            this.$el.append(this.portlet.$el);
        }
        
        // append view port
        this.$el.append(Utils.wrap(''));
        this.$el.append(this.viewport_view.$el);
        
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
            self._changeChart(chart);
        });
    },
    
    // hide
    hide: function() {
        $('.tooltip').hide();
        this.$el.hide();
    },
    
    // add
    _addChart: function(chart) {
        // add title to table
        var title = chart.get('title');
        if (title == '') {
            title = 'Untitled';
        }
        this.table.add(title);
        
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
        
        // check if table is empty
        if (this.table.size() == 0) {
            this.hide();
            this.app.chart.reset();
            this.app.chart_view.$el.show();
        } else {
            // select available chart
            this.table.value(this.app.charts.last().id);
        }
    },
    
    // change
    _changeChart: function(chart) {
        if (chart.get('type')) {
            // add chart
            this._addChart(chart);
        
            // select available chart
            this.table.value(chart.id);
        }
    }
});

});