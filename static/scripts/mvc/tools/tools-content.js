define(['utils/utils'], function(Utils){
    return Backbone.Model.extend({
        // initialize
        initialize: function(options) {
            // backup basic url
            this.base_url = galaxy_config.root + 'api/histories/' + options.history_id + '/contents';
            
            // prepare content obects
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
                        url     : self.base_url + '?deleted=false',
                        success : function(response) {
                            // backup summary
                            self.summary = response;
                            
                            // log
                            console.debug('tools-content::initialize() - Completed.');
                            
                            // callback
                            options.success && options.success();
                        },
                        error   : function(response) {
                            // log request failure
                            console.debug('tools-content::initialize() - Ajax request for summary failed.');
                            console.debug(response);
                        }
                    });
                },
                error   : function(response) {
                    // log request failure
                    console.debug('tools-content::initialize() - Ajax request for datatypes failed.');
                    console.debug(response);
                }
            });
        },
        
        /**
         * Filters contents by data type.
        */
        filterType: function(options) {
            // initialize parameters
            options = options || {};
            var result = [];
            
            // identify content type
            var history_content_type = 'dataset';
            if (options.src== 'hdca') {
                history_content_type = 'dataset_collection';
            }
            
            // search in summary
            for (var i in this.summary) {
                var content = this.summary[i];
                
                // match datatypes
                var found = false;
                for (var i in options.extensions) {
                    if (this._matchType(options.extensions[i], content.extension)) {
                        found = true;
                        break;
                    }
                }
                
                // final match result
                if ((content.history_content_type === history_content_type) && (found || !options.extensions)) {
                    result.push(content);
                }
            }
            return result;
        },
        
        /** Get details of a content by id.
        */
        getDetails: function(options) {
            // check id
            if (!options.id || options.id === 'null') {
                options.success && options.success();
                return;
            }
            
            // create url
            var api_url = this.base_url + '/datasets/' + options.id;
            if (options.src == 'hdca') {
                api_url = this.base_url + '/dataset_collections/' + options.id;
            }
            
            // request details
            Utils.get({
                url     : api_url,
                success : function(response) {
                    options.success && options.success(response);
                },
                error   : function(response) {
                    options.success && options.success();
                    console.debug('tools-content::getDetails() - Ajax request for content failed.');
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
                console.debug('tools-content::_matchType() - Specific target class unavailable. Accepting all formats.');
                return true;
            }
            
            // check if reference class is available
            var reference_class = this.datatypes.ext_to_class_name[reference];
            if (!reference_class) {
                console.debug('tools-content::_matchType() - Specific reference class unavailable. Accepting all formats.');
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