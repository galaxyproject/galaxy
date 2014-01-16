// dependencies
define(['library/portlet', 'library/table', 'library/ui', 'library/utils', 'models/chart', 'groups'],
    function(Portlet, Table, Ui, Utils, Chart, Groups) {

// widget
return Backbone.View.extend(
{
    // defaults options
    optionsDefault: {
        header  : true,
        content : 'No content available.'
    },

    // current chart
    chart : null,

    // initialize
    initialize: function(app, options)
    {
        // link application
        this.app = app;
        
        // get current chart object
        this.chart = this.app.chart;
        
        // configure options
        this.options = Utils.merge(options, this.optionsDefault);
        
        // main elements
        this.message = new Ui.Message();
        this.title = new Ui.Input({placeholder: 'Chart title'});
        this.dataset = new Ui.Input({value : app.options.dataset.id, disabled: true, visible: false});
        
        // configure dataset
        this.groups = new Groups(this.app);
        
        // table
        var self = this;
        this.table = new Table({
            header : false,
            onconfirm : function(type) {
                if (self.chart.groups.length > 0) {
                    // show modal
                    self.app.modal.show({
                        title   : 'Switching the chart type?',
                        body    : 'You configured data sources. If you switch chart types your configurations will be removed.',
                        buttons : {
                            'Cancel'    : function() {
                                // hide modal
                                self.app.modal.hide();
                            },
                            'Continue'  : function() {
                                // hide modal
                                self.app.modal.hide();
                                
                                // confirm
                                self.table.confirm(type);
                            }
                        }
                    });
                } else {
                    // confirm
                    self.table.confirm(type);
                }
            },
            onchange : function(type) {
                // update chart type
                self.chart.set({type: type});
                    
                // reset groups
                self.chart.groups.reset();
            },
            content: 'No chart types available'
        });
        
        // add types
        var types_n = 0;
        var types = app.types.attributes;
        for (var id in types){
            var chart_type = types[id];
            this.table.add (++types_n + '.');
            this.table.add (chart_type.title);
            this.table.append(id);
        }
                        
        // add table to portlet
        var self = this;
        this.portlet = new Portlet({
            icon : 'fa-edit',
            label : 'Create a new chart:',
            operations : {
                'save'      : new Ui.ButtonIcon({
                                icon    : 'fa-save',
                                tooltip : 'Save Chart',
                                onclick : function() {
                                    self._saveChart();
                                }
                            }),
                'back'      : new Ui.ButtonIcon({
                                icon    : 'fa-list',
                                tooltip : 'Show Charts',
                                onclick : function() {
                                    self.$el.hide();
                                    self.app.main.$el.show();
                                }
                            })
            }
        });
        this.portlet.append(this.message.$el);
        this.portlet.append(this.dataset.$el);
        this.portlet.append((new Ui.Label({ label : 'Provide a chart title:'})).$el);
        this.portlet.append(this.title.$el);
        this.portlet.append((new Ui.Label({ label : 'Select a chart type:'})).$el);
        this.portlet.append(this.table.$el);
        this.portlet.append(this.groups.$el);

        // elements
        this.setElement(this.portlet.$el);
        
        // events
        var self = this;
        this.chart.on('change:title', function(chart) {
            self.title.value(chart.get('title'));
        });
        this.chart.on('change:type', function(chart) {
            self.table.value(chart.get('type'));
        });
    },

    // reset
    reset: function() {
        this.chart.reset();
        this.chart.set('id', Utils.uuid());
        this.chart.set('dataset_id', this.app.options.dataset.id);
        this.chart.set('type', 'bardiagram');
        this.chart.set('title', 'Chart title');
    },
    
    // set chart
    setChart: function(new_chart) {
        this.chart.copy(new_chart);
    },
    
    // create chart
    _saveChart: function() {
        // update chart data
        this.chart.set({
            type        : this.table.value(),
            title       : this.title.value(),
            dataset_id  : this.dataset.value(),
            date        : Utils.time()
        });
        
        // validate
        if (!this.chart.get('title')) {
            this.message.update({message : 'Please enter a title for your chart.'});
            return;
        }
        
        if (!this.chart.get('type')) {
            this.message.update({message : 'Please select a chart type.'});
            return;
        }

        if (this.chart.groups.length == 0) {
            this.message.update({message : 'Please configure at least one data source.'});
            return;
        }
        
        // create/get chart
        var current = this.app.charts.get(this.chart.id);
        if (!current) {
            current = this.chart.clone();
            this.app.charts.add(current);
        }
                
        // update chart model
        current.copy(this.chart);
        
        // hide
        this.$el.hide();
        
        // update main
        this.app.main.$el.show();
    }
});

});