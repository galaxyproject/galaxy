// dependencies
define(['library/portlet', 'library/table', 'library/ui', 'library/utils'], function(Portlet, Table, Ui, Utils) {

// chart config
return Backbone.View.extend(
{
    // initialize
    initialize: function(app, options) {
        // link app
        this.app = app;
    
        // get current chart object
        this.chart = this.app.chart;
        
        // table
        this.table = new Table({
            content     : 'Add data columns to this table.',
            ondblclick  : function(group_id) {
                // get group
                var group = self.app.chart.groups.get(group_id);
                
                // show edit
                self.app.chart_view.$el.hide();
                self.app.group_view.show();
                self.app.group_view.group.set(group.attributes);
            }
        });
        
        // add table to portlet
        var self = this;
        this.portlet = new Portlet({
            icon : '',
            label : 'Select data columns:',
            height : 100,
            operations : {
                'new'   : new Ui.ButtonIcon({
                            icon : 'fa-plus',
                            tooltip: 'Create',
                            onclick: function() {
                                self.app.group.reset();
                                self.app.chart_view.$el.hide();
                                self.app.group_view.show();
                            }
                        }),
                'edit'  : new Ui.ButtonIcon({
                            icon : 'fa-pencil',
                            tooltip: 'Edit',
                            onclick: function() {
                                // check if element has been selected
                                var group_id = self.table.value();
                                if (!group_id) {
                                    return;
                                }
                                
                                // get group
                                var group = self.app.chart.groups.get(group_id);
                                
                                // show edit
                                self.app.chart_view.$el.hide();
                                self.app.group_view.show();
                                self.app.group_view.group.set(group.attributes);
                            }
                        }),
                'delete' : new Ui.ButtonIcon({
                            icon : 'fa-minus',
                            tooltip: 'Delete',
                            onclick: function() {
                                // check if element has been selected
                                var id = self.table.value();
                                if (!id) {
                                    return;
                                }
                                // remove group from chart
                                self.chart.groups.remove(id);
                            }
                        })
            }
        });
        this.portlet.append(this.table.$el);
        
        // add element
        this.setElement(this.portlet.$el);
        
        // change
        var self = this;
        this.chart.on('change', function() {
            self._refresh();
        });
        this.chart.on('reset', function() {
            self._removeGroupAll();
        });
        this.chart.on('change:type', function() {
            self.app.group_view.trigger('change');
        });
        this.chart.groups.on('add', function(group) {
            self._addGroup(group);
        });
        this.chart.groups.on('remove', function(group) {
            self._removeGroup(group);
        });
        this.chart.groups.on('reset', function(group) {
            self._removeGroupAll();
        });
        this.chart.groups.on('change', function(group) {
            self._removeGroup(group);
            self._addGroup(group);
        });
    },
    
    // refresh
    _refresh: function() {
        this._removeGroupAll();
        var self = this;
        var groups = this.chart.groups;
        if (groups) {
            groups.each(function(group) { self._addGroup(group); });
        }
    },
    
    // add
    _addGroup: function(group) {
        // make custom info string
        var info = '[';
        var chart_type = this.chart.get('type');
        if (chart_type) {
            var chart_settings = this.app.types.get(chart_type);
            for (var key in chart_settings.data) {
                info += key + '=' + group.get(key) + ', '
            }
        }
        info = info.substring(0, info.length - 2) + ']';
        
        // add to table
        this.table.add(group.get('label'));
        this.table.add(info);
        this.table.add('Last changed: ' + group.get('date'));
        this.table.prepend(group.id);
        this.table.value(group.id);
    },
    
    // remove
    _removeGroup: function(group) {
        // remove from to table
        this.table.remove(group.id);
    },
    
    // data config reset
    _removeGroupAll: function() {
        // reset options table
        this.table.removeAll();
    }
});

});