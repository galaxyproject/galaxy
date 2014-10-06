define([ 'mvc/history/history-contents' ], function( HISTORY_CONTENTS ){
    return Backbone.Model.extend({
        // initialize
        initialize: function(options) {
            // create history contents container
            this.currHistoryContents = new HISTORY_CONTENTS.HistoryContents({});
            
            // identify current history id
            this.currHistoryContents.historyId = options.history_id;
            
            // make request
            var self = this;
            var xhr = this.currHistoryContents.fetchAllDetails()
                .done( function(){
                    // log request success
                    console.debug('tools-datasets::initialize() - Completed.');
                    
                    // callback
                    options.success && options.success();
                })
                .fail( function(){
                    // log request failure
                    console.debug('tools-datasets::initialize() - Ajax request failed.');
                });
        },
        
        // filter datasets by data type
        filterType: function(options) {
            options = options || {};
            return this.currHistoryContents.filter(function(content){
                // match datatypes
                var found = false;
                for (var i in options.data_types) {
                    if (content.get('data_type').indexOf(options.data_types[i]) != -1) {
                        found = true;
                        break;
                    }
                }
                
                // final match result
                return  (content.get('history_content_type') === options.content_type || !options.content_type) &&
                        (found || !options.data_types) && !content.get('deleted');
            });
        },
        
        // filter datasets by id
        filter: function(filter_id) {
            return _.first( this.currHistoryContents.filter( function( content ){ return content.get( 'id' ) === filter_id; }) );
        }
    });
});