// dependencies
define(['utils/utils', 'plugin/models/chart', 'plugin/models/group'], function(Utils, Chart, Group) {

// collection
return Backbone.Model.extend(
{
    // viz model
    vis: null,
    
    // initialize
    initialize: function(app) {
        // link app
        this.app = app;
        
        // link chart
        this.chart = this.app.chart;
        
        // link options
        this.options = this.app.options;
        
        // initialize parameters
        this.id = this.options.id;
        
        // create visualization
        this.vis = new Visualization({
            type        : 'charts',
            config  : {
                dataset_id  : this.options.config.dataset_id,
                chart_dict  : {}
            }
        });
        
        // add visualization id
        if (this.id) {
            this.vis.id = this.id;
        }
        
        // add charts
        var chart_dict = this.options.config.chart_dict;
        if (chart_dict) {
            this.vis.get('config').chart_dict = chart_dict;
        }
    },
    
    // pack and save nested chart model
    save: function() {
    
        // link chart
        var chart = this.app.chart;
        
        // reset
        this.vis.get('config').chart_dict = {};
        
        // set title
        var title = chart.get('title');
        if (title != '') {
            this.vis.set('title', title);
        }
        
        // create chart dictionary
        var chart_dict = {
            attributes : chart.attributes,
            settings   : chart.settings.attributes,
            groups     : []
        };
        
        // append groups
        chart.groups.each(function(group) {
            chart_dict.groups.push(group.attributes);
        });
        
        // add chart to charts array
        this.vis.get('config').chart_dict = chart_dict;
        
        // save visualization
        var self = this;
        this.vis.save()
            .fail(function(xhr, status, message) {
               console.error(xhr, status, message);
            })
            .then(function(response) {
                if (response && response.id) {
                    self.id = response.id;
                }
            });
    },
    
    // load nested models/collections from packed dictionary
    load: function() {
        // get charts array
        var chart_dict = this.vis.get('config').chart_dict;
        
        // check
        if (!chart_dict.attributes) {
            return false;
        }
        
        // main
        this.chart.set(chart_dict.attributes);
        
        // set state
        this.chart.state('ok', 'Loading saved visualization...');
        
        // get settings
        this.chart.settings.set(chart_dict.settings);
        
        // get groups
        for (var j in chart_dict.groups) {
            this.chart.groups.add(new Group(chart_dict.groups[j]));
        }
        
        // reset modified flag
        this.chart.set('modified', false);
        
        // return
        return true;
    }
});

});