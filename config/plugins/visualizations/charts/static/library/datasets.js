// dependencies
define(['utils/utils'], function(Utils) {

// widget
return Backbone.Collection.extend(
{
    // list of datasets
    list: {},
    
    // initialize
    initialize: function(app, options)
    {
        // link app
        this.app = app;
        
        // configure options
        this.options = Utils.merge(options, this.optionsDefault);
    },
    
    // wait
    request: function(options, success, error) {
        // link this
        var self = this;
        
        // check if column data is requested
        if (options.groups) {
            this._fetch(options, success);
        } else {
            // check if dataset is available from cache
            var dataset = this.list[options.id];
            if (dataset) {
                success(dataset);
                return;
            }
        
            // request dataset
            Utils.request('GET', config.root + 'api/datasets/' + options.id, {}, function(dataset) {
                switch (dataset.state) {
                    case 'error':
                        if (error) {
                            error(dataset);
                        }
                        break;
                    default:
                        self.list[options.id] = dataset;
                        success(dataset);
                }
            });
        }
    },
    
    // fetch data columns into dataset object
    _fetch: function(options, callback) {
        // set offset
        var offset  = options.start ? options.start : 0;
        
        // set limit
        var limit   = Math.abs(options.end - options.start);
        var query_limit = this.app.config.get('query_limit');
        if (!limit || limit > query_limit) {
            limit = query_limit;
        }
        
        // get column indices
        var index_string    = '';
        var index_map       = {};
        var index_count     = 0;
        for (var i in options.groups) {
            var group = options.groups[i];
            for (var key in group.columns) {
                var column = group.columns[key];
                
                // add to index string
                index_string += column + ',';
                
                // add to dictionary
                index_map[column] = index_count;
                
                // increase counter
                index_count++;
            }
        }
        if (index_count == 0) {
            callback({});
            return;
        }
        index_string = index_string.substring(0, index_string.length - 1);

        // initialize result dictionary
        var result = options.groups.slice(0);
        for (var i in result) {
            result[i].values = [];
        }
        
        // make request
        var self = this;
        Utils.request('GET', config.root + 'api/datasets/' + options.id, {
                data_type   : 'raw_data',
                provider    : 'dataset-column',
                limit       : limit,
                offset      : offset,
                indeces     : index_string
            }, function(response) {
                
                // loop through rows
                for (var i in response.data) {
                    // get row
                    var row = response.data[i];
                    
                    // collect all data into the defined groups
                    for (var j in options.groups) {
                        // get group
                        var group = options.groups[j];
                        
                        // initialize value
                        var value = {
                            x : parseInt(i) + offset
                        };
                        
                        // fill value
                        for (var key in group.columns) {
                            // get column
                            var column = group.columns[key];
                      
                            // identify column
                            var index = index_map[column];
                          
                            // read value from row
                            var v = row[index];
                            if(isNaN(v) || !v) {
                                v = 0;
                            }
                      
                            // add value to dictionary
                            value[key] = v;
                        }

                        // add to result
                        result[j].values.push(value);
                    }
                }
                
                // callback
                callback(result);
            });
    }
});

});