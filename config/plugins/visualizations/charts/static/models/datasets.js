// dependencies
define(['library/utils'], function(Utils) {

// widget
return Backbone.Model.extend(
{
    // options
    optionsDefault : {
        limit : 500,
        pace  : 1000,
        max   : 2
    },

    // list
    list: {},
    
    // initialize
    initialize: function(app, options)
    {
        // link app
        this.app = app;
        
        // configure options
        this.options = Utils.merge(options, this.optionsDefault);
    },

    // get
    get: function(options, callback) {
        // check if dataset already exists
        var dataset = this.list[options.id];
        if (dataset) {
            if (dataset.values) {
                if (dataset.values[options.column]) {
                    if (callback) {
                        callback(dataset);
                    }
                    return dataset;
                }
            }
        } else {
            this.list[options.id] = dataset = this.app.options.dataset;
        }
        
        // initiate fetch cycle
        if (options.column !== undefined) {
            this._fetch(options, callback);
        } else {
            if (callback) {
                callback(dataset);
            }
            return dataset;
        }
        
        // return
        return dataset;
    },
    
    // size
    length: function() {
        return this.list.length;
    },
    
    // request data
    _fetch : function(options, callback) {
        // get dataset
        var dataset = this.list[options.id];
        
        // initialize values for datasets
        if (!dataset.values) {
            dataset.values = {};
        }
        if (!dataset.values[options.column]) {
            dataset.values[options.column] = [];
        }
        
        // initialize page number
        if (options.page === undefined) {
            options.page = 0;
        } else {
            options.page++;
        }
        
        // check max page
        if (options.page > this.options.max) {
            return;
        }
        
        // config limits
        var limit   = this.options.limit;
        var offset  = this.options.limit * options.page;
        
        // make request
        var self = this;
        Utils.request('GET', config.root + 'api/datasets/' + options.id, {
                data_type   : 'raw_data',
                provider    : 'dataset-column',
                limit       : limit,
                offset      : offset,
                indeces     : options.column
            }, function(response) {
                // verify if all data has been fetched
                if (response.data.length > 0) {
                    // add values to dataset
                    for (var key in response.data){
                        var value = response.data[key][0];
                        if (value !== undefined) {
                            dataset.values[options.column].push(value);
                        } else {
                            return dataset;
                        }
                    }
                    
                    // update charts
                    if (callback) {
                        callback(dataset);
                    }
                    
                    // next call
                    setTimeout(function() { self._fetch(options, callback); }, self.options.pace);
                }
            });
    }
});

});