// dependencies
define(['mvc/ui/ui-tabs', 'mvc/ui/ui-misc', 'mvc/ui/ui-portlet', 'utils/utils',
        'plugin/models/chart', 'plugin/models/group',
        'plugin/views/group', 'plugin/views/settings', 'plugin/views/types'],
    function(Tabs, Ui, Portlet, Utils, Chart, Group, GroupView, SettingsView, TypesView) {

/**
 *  The charts editor holds the tabs for selecting chart types, chart configuration
 *  and data group selections.
 */
return Backbone.View.extend({
    // initialize
    initialize: function(app, options){
        // link this
        var self = this;
        
        // link application
        this.app = app;
        
        // get current chart object
        this.chart = this.app.chart;
        
        // message element
        this.message = new Ui.Message();
        
        // create portlet
        this.portlet = new Portlet.View({
            icon : 'fa-bar-chart-o',
            title: 'Editor',
            operations      : {
                'save'  : new Ui.ButtonIcon({
                    icon    : 'fa-save',
                    tooltip : 'Draw Chart',
                    title   : 'Draw',
                    onclick : function() {
                        self._saveChart();
                    }
                }),
                'back'  : new Ui.ButtonIcon({
                    icon    : 'fa-caret-left',
                    tooltip : 'Return to Viewer',
                    title   : 'Cancel',
                    onclick : function() {
                        // show viewer/viewport
                        self.app.go('viewer');
                        
                        // reset chart
                        self.app.storage.load();
                    }
                })
            }
        });
        
        //
        // grid with chart types
        //
        this.types = new TypesView(app, {
            onchange   : function(chart_type) {
                // get chart definition
                var chart_definition = self.app.types.get(chart_type);
                if (!chart_definition) {
                    console.debug('FAILED - Editor::onchange() - Chart type not supported.');
                }
        
                // parse chart definition
                self.chart.definition = chart_definition;
        
                // reset type relevant chart content
                self.chart.settings.clear();
                
                // update chart type
                self.chart.set({type: chart_type});
                
                // set modified flag
                self.chart.set('modified', true);
                
                // log
                console.debug('Editor::onchange() - Switched chart type.');
            },
            ondblclick  : function(chart_id) {
                self._saveChart();
            }
        });
        
        //
        // tabs
        //
        this.tabs = new Tabs.View({
            title_new       : 'Add Data',
            onnew           : function() {
                var group = self._addGroupModel();
                self.tabs.show(group.id);
            }
        });
        
        //
        // main/default tab
        //
        
        // construct elements
        this.title = new Ui.Input({
            placeholder: 'Chart title',
            onchange: function() {
                self.chart.set('title', self.title.value());
            }
        });
        
        // append element
        var $main = $('<div/>');
        $main.append(Utils.wrap((new Ui.Label({ title : 'Provide a chart title:'})).$el));
        $main.append(Utils.wrap(this.title.$el));
        $main.append(Utils.wrap(this.types.$el));
        
        // add tab
        this.tabs.add({
            id      : 'main',
            title   : 'Start',
            $el     : $main
        });
        
        //
        // main settings tab
        //
        
        // create settings view
        this.settings = new SettingsView(this.app);
        
        // add tab
        this.tabs.add({
            id      : 'settings',
            title   : 'Configuration',
            $el     : this.settings.$el
        });
        
        // append tabs
        this.portlet.append(this.message.$el);
        this.portlet.append(this.tabs.$el);
        
        // elements
        this.setElement(this.portlet.$el);
        
        // hide back button on startup
        this.tabs.hideOperation('back');
        
        // chart events
        var self = this;
        this.chart.on('change:title', function(chart) {
            self._refreshTitle();
        });
        this.chart.on('change:type', function(chart) {
            self.types.value(chart.get('type'));
        });
        this.chart.on('reset', function(chart) {
            self._resetChart();
        });
        this.app.chart.on('redraw', function(chart) {
            self.portlet.showOperation('back');
        });
        
        // groups events
        this.app.chart.groups.on('add', function(group) {
            self._addGroup(group);
        });
        this.app.chart.groups.on('remove', function(group) {
            self._removeGroup(group);
        });
        this.app.chart.groups.on('reset', function(group) {
            self._removeAllGroups();
        });
        this.app.chart.groups.on('change:key', function(group) {
            self._refreshGroupKey();
        });
        
        // reset
        this._resetChart();
    },

    // hide
    show: function() {
        this.$el.show();
    },
    
    // hide
    hide: function() {
        this.$el.hide();
    },

    // refresh title
    _refreshTitle: function() {
        var title = this.chart.get('title');
        this.portlet.title(title);
        this.title.value(title);
    },
    
    // refresh group
    _refreshGroupKey: function() {
        var self = this;
        var counter = 0;
        this.chart.groups.each(function(group) {
            var title = group.get('key', '');
            if (title == '') {
                title = 'Data label';
            }
            self.tabs.title(group.id, ++counter + ': ' + title);
        });
    },
    
    // add group model
    _addGroupModel: function() {
        var group = new Group({
            id : Utils.uuid()
        });
        this.chart.groups.add(group);
        return group;
    },

    // add group tab
    _addGroup: function(group) {
        // link this
        var self = this;
        
        // create view
        var group_view = new GroupView(this.app, {group: group});
        
        // add new tab
        this.tabs.add({
            id              : group.id,
            $el             : group_view.$el,
            ondel           : function() {
                self.chart.groups.remove(group.id);
            }
        });
        
        // update titles
        this._refreshGroupKey();
        
        // reset
        this.chart.set('modified', true);
    },
    
    // remove group
    _removeGroup: function(group) {
        this.tabs.del(group.id);
        
        // update titles
        this._refreshGroupKey();
        
        // reset
        this.chart.set('modified', true);
    },

    // remove group
    _removeAllGroups: function(group) {
        this.tabs.delRemovable();
    },
    
    // reset
    _resetChart: function() {
        // reset chart details
        this.chart.set('id', Utils.uuid());
        this.chart.set('type', 'nvd3_bar');
        this.chart.set('dataset_id', this.app.options.config.dataset_id);
        this.chart.set('title', 'New Chart');
        
        // reset back button
        this.portlet.hideOperation('back');
    },
    
    // create chart
    _saveChart: function() {
        // update chart data
        this.chart.set({
            type        : this.types.value(),
            title       : this.title.value(),
            date        : Utils.time()
        });
        
        // make sure that at least one data group is available
        if (this.chart.groups.length == 0) {
            this.message.update({message: 'Please select data columns before drawing the chart.'});
            var group = this._addGroupModel();
            this.tabs.show(group.id);
            return;
        }
        
        // make sure that all necessary columns are assigned
        var self = this;
        var valid = true;
        var chart_def = this.chart.definition;
        this.chart.groups.each(function(group) {
            if (!valid) {
                return;
            }
            for (var key in chart_def.columns) {
                if (group.attributes[key] == 'null') {
                    self.message.update({status: 'danger', message: 'This chart type requires column types not found in your tabular file.'});
                    self.tabs.show(group.id);
                    valid = false;
                    return;
                }
            }
        });
        
        // validate if columns have been selected
        if (!valid) {
            return;
        }
        
        // show viewport
        this.app.go('viewer');
        
        // wait until chart is ready
        var self = this;
        this.app.deferred.execute(function() {
            // save
            self.app.storage.save();
            
            // trigger redraw
            self.chart.trigger('redraw');
        });
    }
});

});