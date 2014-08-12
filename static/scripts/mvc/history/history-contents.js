define([
    "mvc/history/history-content-model",
    "mvc/history/hda-model",
    "mvc/history/hdca-model",
    "mvc/base-mvc",
    "utils/localization"
], function( HISTORY_CONTENT, HDA_MODEL, HDCA_MODEL, BASE_MVC, _l ){
//==============================================================================
/** @class Backbone collection for history content.
 *      NOTE: history content seems like a dataset collection, but differs in that it is mixed:
 *          each element can be either an HDA (dataset) or a DatasetCollection and co-exist on
 *          the same level.
 *      Dataset collections on the other hand are not mixed and (so far) can only contain either
 *          HDAs or child dataset collections on one level.
 *      This is why this does not inherit from any of the DatasetCollections (currently).
 */
var HistoryContents = Backbone.Collection.extend( BASE_MVC.LoggableMixin ).extend(
/** @lends HistoryContents.prototype */{
//TODO:?? may want to inherit from some MixedModelCollection
//TODO:?? also consider inheriting from a 'DatasetList'
//TODO: can we decorate the mixed models using the model fn below (instead of having them build their own type_id)?

    /** logger used to record this.log messages, commonly set to console */
    // comment this out to suppress log output
    //logger              : console,

    /** since history content is a mix, override model fn into a factory, creating based on history_content_type */
    model : function( attrs, options ) {
        //console.debug( 'HistoryContents.model:', attrs, options );

//TODO: can we move the type_id stuff here?
        //attrs.type_id = typeIdStr( attrs );

        if( attrs.history_content_type === "dataset" ) {
            return new HDA_MODEL.HistoryDatasetAssociation( attrs, options );
        
        } else if( attrs.history_content_type === "dataset_collection" ) {
            switch( attrs.collection_type ){
                case 'list':
                    return new HDCA_MODEL.HistoryListDatasetCollection( attrs, options );
                case 'paired':
                    return new HDCA_MODEL.HistoryPairDatasetCollection( attrs, options );
                case 'list:paired':
                    return new HDCA_MODEL.HistoryListPairedDatasetCollection( attrs, options );
            }
            throw new TypeError( 'Unknown collection_type: ' + attrs.collection_type );
        }
        // TODO: Handle unknown history_content_type...
        throw new TypeError( 'Unknown history_content_type: ' + attrs.history_content_type );
    },

    /** Set up.
     *  @see Backbone.Collection#initialize
     */
    initialize : function( models, options ){
        options = options || {};
        this.historyId = options.historyId;
        //this._setUpListeners();

        this.on( 'all', function(){
            this.debug( this + '.event:', arguments );
        });
    },

    /** root api url */
    urlRoot : galaxy_config.root + 'api/histories',
    /** complete api url */
    url : function(){
        return this.urlRoot + '/' + this.historyId + '/contents';
    },

    // ........................................................................ common queries
    /** Get the ids of every hda in this collection
     *  @returns array of encoded ids
     */
    ids : function(){
        return this.map( function( hda ){ return hda.get('id'); });
    },

    /** Get hdas that are not ready
     *  @returns array of HDAs
     */
    notReady : function(){
        return this.filter( function( hda ){
            return !hda.inReadyState();
        });
    },

    /** Get the id of every hda in this collection not in a 'ready' state (running).
     *  @returns an array of hda ids
     *  @see HistoryDatasetAssociation#inReadyState
     */
    running : function(){
        var idList = [];
        this.each( function( item ){
            var isRunning = !item.inReadyState();
            if( isRunning ){
                idList.push( item.get( 'id' ) );
            }
        });
        return idList;
    },

    /** Get the hda with the given hid
     *  @param {Int} hid the hid to search for
     *  @returns {HistoryDatasetAssociation} the hda with the given hid or undefined if not found
     */
    getByHid : function( hid ){
        return _.first( this.filter( function( hda ){ return hda.get( 'hid' ) === hid; }) );
    },

    /** Get every 'shown' hda in this collection based on show_deleted/hidden
     *  @param {Boolean} show_deleted are we showing deleted hdas?
     *  @param {Boolean} show_hidden are we showing hidden hdas?
     *  @returns array of hda models
     *  @see HistoryDatasetAssociation#isVisible
     */
    getVisible : function( show_deleted, show_hidden, filters ){
        filters = filters || [];
        //this.debug( 'filters:', filters );
        // always filter by show deleted/hidden first
        this.debug( 'checking isVisible' );
        var filteredHdas = new HistoryContents( this.filter( function( item ){
            return item.isVisible( show_deleted, show_hidden );
        }));

        _.each( filters, function( filter_fn ){
            if( !_.isFunction( filter_fn ) ){ return; }
            filteredHdas = new HistoryContents( filteredHdas.filter( filter_fn ) );
        });
        return filteredHdas;
    },

    /** return true if any hdas don't have details */
    haveDetails : function(){
        return this.all( function( hda ){ return hda.hasDetails(); });
    },

    // ........................................................................ ajax
    /** fetch detailed model data for all HDAs in this collection */
    fetchAllDetails : function( options ){
        options = options || {};
        var detailsFlag = { details: 'all' };
        options.data = ( options.data )?( _.extend( options.data, detailsFlag ) ):( detailsFlag );
        return this.fetch( options );
    },

    /** using a queue, perform hdaAjaxFn on each of the hdas in this collection */
    ajaxQueue : function( hdaAjaxFn, options ){
        var deferred = jQuery.Deferred(),
            startingLength = this.length,
            responses = [];

        if( !startingLength ){
            deferred.resolve([]);
            return deferred;
        }

        // use reverse order (stylistic choice)
        var ajaxFns = this.chain().reverse().map( function( hda, i ){
            return function(){
                var xhr = hdaAjaxFn.call( hda, options );
                // if successful, notify using the deferred to allow tracking progress
                xhr.done( function( response ){
                    deferred.notify({ curr: i, total: startingLength, response: response, model: hda });
                });
                // (regardless of previous error or success) if not last ajax call, shift and call the next
                //  if last fn, resolve deferred
                xhr.always( function( response ){
                    responses.push( response );
                    if( ajaxFns.length ){
                        ajaxFns.shift()();
                    } else {
                        deferred.resolve( responses );
                    }
                });
            };
        }).value();
        // start the queue
        ajaxFns.shift()();

        return deferred;
    },

    // ........................................................................ sorting/filtering
    /** return a new collection of HDAs whose attributes contain the substring matchesWhat */
    matches : function( matchesWhat ){
        return this.filter( function( hda ){
            return hda.matches( matchesWhat );
        });
    },

    // ........................................................................ misc
    set : function( models, options ){
        // arrrrrrrrrrrrrrrrrg...
        // override to get a correct/smarter merge when incoming data is partial (e.g. stupid backbone)
        //  w/o this partial models from the server will fill in missing data with model defaults
        //  and overwrite existing data on the client
        // see Backbone.Collection.set and _prepareModel
        var collection = this;
        models = _.map( models, function( model ){
            var attrs = model.attributes || model,
                typeId = HISTORY_CONTENT.typeIdStr( attrs.history_content_type, attrs.id ),
                existing = collection.get( typeId );
            if( !existing ){ return model; }

            // merge the models _BEFORE_ calling the superclass version
            var merged = existing.toJSON();
            _.extend( merged, model );
            return merged;
        });
        // now call superclass when the data is filled
        Backbone.Collection.prototype.set.call( this, models, options );
    },

    /** Convert this ad-hoc collection of HDAs to a formal collection tracked
        by the server.
    **/
    promoteToHistoryDatasetCollection : function _promote( history, collection_type, options ){
//TODO: seems like this would be better in mvc/collections
        options = options || {};
        options.url = this.url();
        options.type = "POST";
        var full_collection_type = collection_type;
        var element_identifiers = [],
            name = null;

        // This mechanism is rough - no error handling, allows invalid selections, no way
        // for user to pick/override element identifiers. This is only really meant
        if( collection_type === "list" ) {
            this.chain().each( function( hda ) {
                // TODO: Handle duplicate names.
                var name = hda.attributes.name;
                var id = hda.get('id');
                var content_type = hda.attributes.history_content_type;
                if( content_type === "dataset" ) {
                    if( full_collection_type !== "list" ) {
                        this.log( "Invalid collection type" );
                    }
                    element_identifiers.push( { name: name, src: "hda", id: id } );
                } else {
                    if( full_collection_type === "list" ) {
                        full_collection_type = "list:" + hda.attributes.collection_type;
                    } else {
                        if( full_collection_type !== "list:" + hda.attributes.collection_type ) {
                            this.log( "Invalid collection type" );
                        }
                    }
                    element_identifiers.push( { name: name, src: "hdca", id: id } );
                }
            });
            name = "New Dataset List";
        } else if( collection_type === "paired" ) {
            var ids = this.ids();
            if( ids.length !== 2 ){
                // TODO: Do something...
            }
            element_identifiers.push( { name: "forward", src: "hda", id: ids[ 0 ] } );
            element_identifiers.push( { name: "reverse", src: "hda", id: ids[ 1 ] } );
            name = "New Dataset Pair";
        }
        options.data = {
            type: "dataset_collection",
            name: name,
            collection_type: full_collection_type,
            element_identifiers: JSON.stringify( element_identifiers )
        };

        var xhr = jQuery.ajax( options );
        xhr.done( function( message, status, responseObj ){
            history.refresh( );
        });
        xhr.fail( function( xhr, status, message ){
            if( xhr.responseJSON && xhr.responseJSON.error ){
                error = xhr.responseJSON.error;
            } else {
                error = xhr.responseJSON;
            }
            xhr.responseText = error;
            // Do something?
        });
        return xhr;
    },

    /** debugging */
    print : function(){
        var contents = this;
        contents.each( function( c ){
            contents.debug( c );
            if( c.elements ){
                contents.debug( '\t elements:', c.elements );
            }
        });
    },

    /** String representation. */
    toString : function(){
         return ([ 'HistoryContents(', [ this.historyId, this.length ].join(), ')' ].join( '' ));
    }
});


//==============================================================================
    return {
        HistoryContents : HistoryContents
    };
});
