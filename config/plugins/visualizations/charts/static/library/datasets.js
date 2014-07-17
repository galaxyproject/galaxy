// dependencies
define(['utils/utils'], function(Utils) {

/**
 *  This class handles, formats and caches datasets.
 */
return Backbone.Collection.extend(
{
    // list of datasets
    list: {},
    
    // cache for datablocks
    cache: {},
    
    // initialize
    initialize: function(app, options){
        // link app
        this.app = app;
        
        // configure options
        this.options = Utils.merge(options, this.optionsDefault);
    },
    
    // request handler
    request: function(request_dictionary) {
        if (request_dictionary.groups) {
            this._get_blocks(request_dictionary);
        } else {
            this._get_dataset(request_dictionary.id, request_dictionary.success, request_dictionary.error)
        }
    },
    
    // multiple request handler
    _get_blocks: function(request_dictionary) {
        // get callbacks
        var success     = request_dictionary.success;
        var progress    = request_dictionary.progress;
        
        // query block size
        var query_size    = this.app.config.get('query_limit');
        var query_timeout = this.app.config.get('query_timeout');
        
        // set range
        var query_start = request_dictionary.start || 0;
        var query_end   = query_start + request_dictionary.query_limit || query_start + this.app.config.get('query_limit');

        // get query limit
        var query_range = Math.abs(query_end - query_start);
        if (query_range <= 0) {
            console.debug('FAILED - Datasets::request() - Invalid query range.');
            return;
        }
        
        // get number of required queries
        var query_number = Math.ceil(query_range / query_size) || 1;
        
        // get query dictionary template
        var query_dictionary_template = $.extend(true, {}, request_dictionary);
        
        // reset query counter
        var query_counter = 0;
        
        // fetch blocks
        var self = this;
        function fetch_blocks (query) {
            self._get(query, function() {
                // copy values from query into request_dictionary
                var done = false;
                for (var group_index in request_dictionary.groups) {
                    // get source/destination
                    destination_group = request_dictionary.groups[group_index];
                    source_group = query.groups[group_index];
                    
                    // check if value fields already exist
                    if (!destination_group.values) {
                        destination_group.values = [];
                    }
                    
                    // concat values
                    destination_group.values = destination_group.values.concat(source_group.values);
                    
                    // validate
                    if (source_group.values.length == 0) {
                        done = true;
                        break;
                    }
                }
                
                // check if for remaining queries
                if (++query_counter < query_number && !done) {
                    // report progress
                    if (progress) {
                        progress(parseInt((query_counter / query_number) * 100));
                    }
                    
                    // next query
                    var start = query.start + query_size;
                    query = $.extend(true, query_dictionary_template, {start: start});
                    fetch_blocks(query);
                } else {
                    success();
                }
            });
        
        };
        
        // prepare query
        var query = $.extend(true, query_dictionary_template, {start: query_start});
        
        // get dataset meta data
        this._get_dataset(request_dictionary.id, function() {
            fetch_blocks(query);
        });
    },
    
    // get dataset
    _get_dataset: function(id, success, error) {
        // check if dataset is available from cache
        var dataset = this.list[id];
        if (dataset) {
            success(dataset);
            return;
        }
    
        // request dataset
        var self = this;
        Utils.request('GET', config.root + 'api/datasets/' + id, {}, function(dataset) {
            switch (dataset.state) {
                case 'error':
                    if (error) {
                        error(dataset);
                    }
                    break;
                default:
                    self.list[id] = dataset;
                    success(dataset);
            }
        });
    },
    
    // get block id
    _block_id: function (options, column) {
        return options.id + '_' + options.start + '_' + options.start + this.app.config.get('query_limit') + '_' + column;
    },
    
    // fills request dictionary with data from cache/response
    _get: function(request_dictionary, callback) {
        // set start
        request_dictionary.start = request_dictionary.start || 0;
        
        // get column indices
        var column_list = [];
        var column_map  = {};
        var column_count = 0;
        for (var i in request_dictionary.groups) {
            var group = request_dictionary.groups[i];
            for (var key in group.columns) {
                // identify column
                var column = group.columns[key].index;
                
                // check if column is in cache
                var block_id = this._block_id(request_dictionary, column);
                if (this.cache[block_id] || column === 'auto' || column === 'zero') {
                    continue;
                }
                
                // add to dictionary
                if (!column_map[column] && column !== undefined) {
                    column_map[column] = column_count;
                    column_list.push(column);
                    column_count++;
                }
            }
        }
        
        // check length of blocks not available in cache
        if (column_list.length == 0) {
            // fill dictionary from cache
            this._fill_from_cache(request_dictionary);
            
            // parse requested data
            callback(request_dictionary);
            
            // return
            return;
        }
        
        // configure dataset request dictionary
        var dataset_request = {
            dataset_id  : request_dictionary.id,
            start       : request_dictionary.start,
            columns     : column_list
        }
        
        // fetch data
        var self = this;
        this._fetch(dataset_request, function(results) {
            // add results to cache
            for (var i in results) {
                var column = column_list[i];
                var block_id = self._block_id(request_dictionary, column);
                self.cache[block_id] = results[i];
            }
            
            // fill dictionary from cache
            self._fill_from_cache(request_dictionary);
            
            // trigger callback
            callback(request_dictionary);
        });
    },
    
    // convert
    _fill_from_cache: function(request_dictionary) {
        // identify start of request
        var start = request_dictionary.start;
        
        // log
        console.debug('Datasets::_fill_from_cache() - Filling request from cache at ' + start + '.');
    
        // identify end of request
        var limit = 0;
        for (var i in request_dictionary.groups) {
            var group = request_dictionary.groups[i];
            for (var key in group.columns) {
                var column = group.columns[key];
                var block_id = this._block_id(request_dictionary, column.index);
                var column_data = this.cache[block_id];
                if (column_data) {
                    limit = Math.max(limit, column_data.length);
                }
            }
        }
        
        // check length
        if (limit == 0) {
            console.debug('Datasets::_fill_from_cache() - Reached data range limit.');
        }
        
        // initialize group values
        for (var i in request_dictionary.groups) {
            // get group
            var group = request_dictionary.groups[i];
            
            // reset group
            group.values = [];
        
            // add values
            for (var j = 0; j < limit; j++) {
                // add default x values
                group.values[j] = {
                    x : parseInt(j) + start
                };
            }
        }
        
        // collect all data into the defined groups
        for (var i in request_dictionary.groups) {
            // get group
            var group = request_dictionary.groups[i];
            
            // fill value
            for (var key in group.columns) {
                // get column
                var column = group.columns[key];
          
                // check if auto block is requested
                switch (column.index) {
                    case 'auto':
                        for (var j = 0; j < limit; j++) {
                            // get value dictionary
                            var value = group.values[j];
                            
                            // add auto value
                            value[key] = parseInt(j) + start;
                        }
                        break;
                    case 'zero':
                        for (var j = 0; j < limit; j++) {
                            // get value dictionary
                            var value = group.values[j];
                            
                            // add zero value
                            value[key] = 0;
                        }
                        break;
                    default:
                        // get block
                        var block_id = this._block_id(request_dictionary, column.index);
                        var column_data = this.cache[block_id];
                    
                        // go through column
                        for (var j = 0; j < limit; j++) {
                            // get value dictionary
                            var value = group.values[j];
                            
                            // get/fix value
                            var v = column_data[j];
                            if (isNaN(v) && !column.is_label) {
                                v = 0;
                            }
                            
                            // add to dict
                            value[key] = v;
                        }
                }
            }
        }
    },
    
    // fetch data columns into dataset object
    _fetch: function(dataset_request, callback) {
        // set offset
        var offset  = dataset_request.start ? dataset_request.start : 0;
        
        // set limit
        var limit = this.app.config.get('query_limit');
        
        // check length
        var n_columns = 0;
        if (dataset_request.columns) {
            n_columns = dataset_request.columns.length;
            console.debug('Datasets::_fetch() - Fetching ' + n_columns + ' column(s) at ' + offset + '.');
        }
        if (n_columns == 0) {
            console.debug('Datasets::_fetch() - No columns requested');
        }
        
        // get column indices
        var column_string    = '';
        for (var i in dataset_request.columns) {
            column_string += dataset_request.columns[i] + ',';
        }
        column_string = column_string.substring(0, column_string.length - 1);
        
        // make request
        var self = this;
        Utils.request('GET', config.root + 'api/datasets/' + dataset_request.dataset_id, {
                data_type   : 'raw_data',
                provider    : 'dataset-column',
                limit       : limit,
                offset      : offset,
                indeces     : column_string
            }, function(response) {
                // initialize result dictionary
                var result = new Array(n_columns);
                for (var i = 0; i < n_columns; i++) {
                    result[i] = [];
                }
                
                // loop through rows
                for (var i in response.data) {
                    // get row
                    var row = response.data[i];
                    
                    // collect all data into the defined groups
                    for (var j in row) {
                        // get group
                        var v = row[j];
                        if (v !== undefined && v != 2147483647) {
                            // add to result
                            result[j].push(v);
                        }
                    }
                }
                
                // log
                console.debug('Datasets::_fetch() - Fetching complete.');
        
                // callback
                callback(result);
            }
        );
    }
});

});