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
        filterType: function(filter_type) {
            // return matched datasets
            return this.currHistoryContents.filter( function( content ){
                // link details
                var history_content_type = content.get( 'history_content_type' );
                var data_type = content.get( 'file_ext');
                
                // apply filter
                return history_content_type === 'dataset';// && (data_type === filter_type || filter_type === '');
            });
        },
        
        // filter datasets by id
        filter: function(filter_id) {
            // return matched datasets
            return _.first( this.currHistoryContents.filter( function( content ){ return content.get( 'id' ) === filter_id; }) );
        }
    });
});