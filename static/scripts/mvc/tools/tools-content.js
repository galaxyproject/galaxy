define(['utils/utils'], function(Utils){
    return Backbone.Model.extend({
        // initialize
        initialize: function(app) {
            this.summary = {};
        },
        
        /** Add new content elements
        */
        add: function(content_list) {
            // add/update content in summary list
            for (var i in content_list) {
                for (var j in content_list[i]) {
                    var c = content_list[i][j];
                    this.summary[c.id + '_' + c.src] = c;
                }
            }
        },
        
        /** Returns matched content from summary.
        */
        get: function(options) {
            return _.findWhere(this.summary, options) || {};
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
        }
    });
});