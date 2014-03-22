// dependencies
define(['plugin/models/chart', 'plugin/models/group'], function(Chart, Group) {

// collection
return Backbone.Collection.extend(
{
    // nested chart model contains collections
    model           : Chart,
    
    // viz model
    vis: null,
    
    // initialize
    initialize: function(options, app) {
        // initialize parameters
        this.app            = app;
        this.id             = this.app.options.id;
        
        // create visualization
        this.vis = new Visualization({
            type        : 'charts',
            config  : {
                dataset_id  : this.app.options.config.dataset_id,
                charts      : []
            }
        });
        
        // add visualization id
        if (this.id) {
            this.vis.id = this.id;
        }
        
        // add charts
        var charts_array = this.app.options.config.charts;
        if (charts_array) {
            this.vis.get('config').charts = charts_array;
        }
    },
    
    // pack and save nested chart models
    save: function() {
        // reset
        this.vis.get('config').charts = [];
        
        // pack nested chart models into arrays attributes
        var self = this;
        this.each(function(chart) {
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
            self.vis.get('config').charts.push(chart_dict);
        });
        
        // save visualization
        var self = this;
        this.vis.save()
            .fail(function(xhr, status, message) {
               console.error(xhr, status, message);
               alert( 'Error loading data:\n' + xhr.responseText );
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
        var charts_array = this.vis.get('config').charts;
        
        // unpack chart models
        for (var i in charts_array) {
            // get chart details
            var chart_dict  = charts_array[i];
            
            // construct chart model
            var chart = new Chart();
            
            // main
            chart.set(chart_dict.attributes);
            
            // get settings
            chart.settings.set(chart_dict.settings);
            
            // get groups
            for (var j in chart_dict.groups) {
                chart.groups.add(new Group(chart_dict.groups[j]));
            }
            
            // reset status
            chart.state('ok', 'Loaded previously saved visualization.');

            // add to collection
            this.add(chart);
            
            // trigger
            chart.trigger('redraw', chart);
        }
    }
});

});