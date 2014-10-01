define(['utils/utils'], function(Utils){
    return Backbone.Model.extend({
        // initialize
        initialize: function(options) {
            // prepare datasets obects
            this.datatypes = {};
            this.summary = {};
            
            // link this
            var self = this;
            
            // request datatypes
            Utils.get({
                url     : galaxy_config.root + 'api/datatypes/mapping',
                cache   : true,
                success : function(response) {
                    // backup datatype dictionary
                    self.datatypes = response;
                    
                    // get history summary
                    Utils.get({
                        url     : galaxy_config.root + 'api/histories/' + options.history_id + '/contents?deleted=false',
                        success : function(response) {
                            // backup summary
                            self.summary = response;
                            
                            // log
                            console.debug('tools-datasets::initialize() - Completed.');
                            
                            // callback
                            options.success && options.success();
                        },
                        error   : function(response) {
                            // log request failure
                            console.debug('tools-datasets::initialize() - Ajax request for summary failed.');
                            console.debug(response);
                        }
                    });
                },
                error   : function(response) {
                    // log request failure
                    console.debug('tools-datasets::initialize() - Ajax request for datatypes failed.');
                    console.debug(response);
                }
            });
        },
        
        /**
         * Filters datasets by data type.
        */
        filterType: function(options) {
            options = options || {};
            var result = [];
            for (var i in this.summary) {
                var dataset = this.summary[i];
                
                // match datatypes
                var found = false;
                for (var i in options.data_types) {
                    if (this._matchType(options.data_types[i], dataset.extension)) {
                        found = true;
                        break;
                    }
                }
                
                // final match result
                if ((dataset.history_content_type === options.content_type || !options.content_type) && (found || !options.data_types)) {
                    result.push(dataset);
                }
            }
            return result;
        },
        
        /** Get details of a dataset by id.
         * @param{String} Dataset id
        */
        getDetails: function(dataset_id, callback) {
            Utils.get({
                url     : galaxy_config.root + 'api/datasets/' + dataset_id,
                success : function(response) {
                    callback && callback(response);
                },
                error   : function(response) {
                    console.debug('tools-datasets::getDetails() - Ajax request for dataset failed.');
                    console.debug(response);
                }
            });
        },
        
        /** Check if datatypes match
        */
        _matchType: function(target, reference) {
            // check if target class is available
            var target_class = this.datatypes.ext_to_class_name[target];
            if (!target_class) {
                console.debug('tools-datasets::_matchType() - Specific target class unavailable. Accepting all formats.');
                return true;
            }
            
            // check if reference class is available
            var reference_class = this.datatypes.ext_to_class_name[reference];
            if (!reference_class) {
                console.debug('tools-datasets::_matchType() - Specific reference class unavailable. Accepting all formats.');
                return true;
            }
            
            // check reference group
            var reference_group = this.datatypes.class_to_classes[reference_class];
            if (reference_group[target_class]) {
                return true;
            }
            
            // classes do not match
            return false;
        }
    });
});