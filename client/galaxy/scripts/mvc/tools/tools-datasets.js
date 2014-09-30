define([ 'mvc/history/history-contents', 'utils/utils' ], function( HistoryContents, Utils ){
    return Backbone.Model.extend({
        // initialize
        initialize: function(options) {
            // create history contents container
            this.currHistoryContents = new HistoryContents.HistoryContents({});
            
            // identify current history id
            this.currHistoryContents.historyId = options.history_id;
            
            // prepare datatype structure
            this.typedict = {};
            
            // link this
            var self = this;
            
            // request datatypes
            Utils.get(galaxy_config.root + 'api/datatypes/mapping',
                // success
                function(typedict) {
                    // backup datatype dictionary
                    self.typedict = typedict;
                    
                    // make request
                    var xhr = self.currHistoryContents.fetchAllDetails()
                        .done( function(){
                            // log request success
                            console.debug('tools-datasets::initialize() - Completed.');
                            
                            // callback
                            options.success && options.success();
                        })
                        .fail( function(){
                            // log request failure
                            console.debug('tools-datasets::initialize() - Ajax request for history datasets failed.');
                        });
                },
                // error
                function(response) {
                    // log request failure
                    console.debug('tools-datasets::initialize() - Ajax request for datatype dictionary failed.');
                }
            );
        },
        
        /** Filters datasets by data type.
        */
        filterType: function(options) {
            options = options || {};
            var self = this;
            return this.currHistoryContents.filter(function(content){
                // match datatypes
                var found = false;
                for (var i in options.data_types) {
                    if (self._matchType(content.get('data_type'), options.data_types[i])) {
                        found = true;
                        break;
                    }
                }
                
                // final match result
                return  (content.get('history_content_type') === options.content_type || !options.content_type) &&
                        (found || !options.data_types) && !content.get('deleted');
            });
        },
        
        /** Filter datasets by id.
        */
        filter: function(filter_id) {
            return _.first( this.currHistoryContents.filter( function( content ){ return content.get( 'id' ) === filter_id; }) );
        },
        
        /** Check if datatypes match
        */
        _matchType: function(reference, target) {
            // check if target class is available
            var target_class = this.typedict.ext_to_class_name[target];
            if (!target_class) {
                console.debug('tools-datasets::_matchType() - Specific target class unavailable. Accepting all formats.');
                return true;
            }
            
            // check reference group
            var reference_group = this.typedict.class_to_classes[reference];
            if (reference_group[target_class]) {
                return true;
            }
            
            // classes do not match
            return false;
        }
    });
});