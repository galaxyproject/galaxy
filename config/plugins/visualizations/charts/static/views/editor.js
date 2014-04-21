// dependencies
define(['mvc/ui/ui-tabs', 'plugin/library/ui-table', 'plugin/library/ui', 'mvc/ui/ui-portlet', 'utils/utils',
        'plugin/models/chart', 'plugin/models/group',
        'plugin/views/group', 'plugin/views/settings'],
    function(Tabs, Table, Ui, Portlet, Utils, Chart, Group, GroupView, SettingsView) {

// widget
return Backbone.View.extend(
{
    // defaults options
    optionsDefault: {
        header  : true,
        content : 'No content available.'
    },
    
    // initialize
    initialize: function(app, options)
    {
        // link this
        var self = this;
        
        // link application
        this.app = app;
        
        // get current chart object
        this.chart = this.app.chart;
        
        // configure options
        this.options = Utils.merge(options, this.optionsDefault);
        
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
                        // show viewport
                        self.app.go('viewer');
                        
                        // save chart
                        self._saveChart();
                    }
                }),
                'back'  : new Ui.ButtonIcon({
                    icon    : 'fa-caret-left',
                    tooltip : 'Return to Viewer',
                    title   : 'Return',
                    onclick : function() {
                        // show viewport
                        self.app.go('viewer');
                        
                        // reset chart
                        self.app.storage.load();
                    }
                })
            }
        });
        
        //
        // table with chart types
        //
        this.table = new Table.View({
            header : false,
            onchange : function(type) {
                // reset type relevant chart content
                self.chart.settings.clear();
                
                // update chart type
                self.chart.set({type: type});
                
                // set modified flag
                self.chart.set('modified', true);
            },
            ondblclick  : function(chart_id) {
                self.tabs.show('settings');
            },
            content: 'No chart types available'
        });
        
        // make table header
        this.table.addHeader('No.');
        this.table.addHeader('Type');
        this.table.addHeader('Library');
        this.table.addHeader('Processing*');
        this.table.appendHeader();
        
        // load chart types into table
        var types_n = 0;
        var types = app.types.attributes;
        for (var id in types){
            var chart_type = types[id];
            this.table.add (++types_n + '.');
            this.table.add(chart_type.title);
            this.table.add(chart_type.library, '10%');
            if (chart_type.execute) {
                this.table.add(new Ui.Icon({icon: 'fa-check'}).$el, '10%', 'center');
            } else {
                this.table.add('');
            }
            this.table.append(id);
        }
        
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
        $main.append(Utils.wrap((new Ui.Label({ title : 'Select a chart type:'})).$el));
        $main.append(Utils.wrap(this.table.$el));
        $main.append(new Ui.Text({
            title: '*Certain chart types pre-process data before rendering the visualization. The pre-processing is done using the chartskit available in the Toolshed.',
            cls: 'toolParamHelp'
        }).$el);
        
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
            self.table.value(chart.get('type'));
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
    
    // update
    _refreshGroupKey: function() {
        var self = this;
        var counter = 0;
        this.chart.groups.each(function(group) {
            var title = group.get('key', '');
            if (title == '') {
                title = 'Chart data';
            }
            self.tabs.title(group.id, ++counter + ': ' + title);
        });
    },
    
    // new group
    _addGroupModel: function() {
        var group = new Group({
            id : Utils.uuid()
        });
        this.chart.groups.add(group);
        return group;
    },

    // add group
    _addGroup: function(group) {
        // link this
        var self = this;
        
        // create view
        var group_view = new GroupView(this.app, {group: group});
        
        // number of groups
        var count = self.chart.groups.length;
        
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
        this.chart.set('type', 'nvd3_bardiagram');
        this.chart.set('dataset_id', this.app.options.config.dataset_id);
        this.chart.set('title', 'New Chart');
        
        // reset back button
        this.portlet.hideOperation('back');
    },
    
    // create chart
    _saveChart: function() {
        // update chart data
        this.chart.set({
            type        : this.table.value(),
            title       : this.title.value(),
            date        : Utils.time()
        });
        
        // ensure that data group is available
        if (this.chart.groups.length == 0) {
            this._addGroupModel();
        }
        
        // wait until chart is ready
        var self = this;
        this.chart.deferred.execute(function() {
            // save
            self.app.storage.save();
            
            // trigger redraw
            self.chart.trigger('redraw');
        });
    }
});

});