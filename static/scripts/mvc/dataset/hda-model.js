define([
    "mvc/base-mvc",
    "utils/localization"
], function( baseMVC, _l ){
//==============================================================================
/** @class model for contents related to a history.
 *  @name HistoryContent
 *
 *  @augments Backbone.Model
 *  @borrows LoggableMixin#logger as #logger
 *  @borrows LoggableMixin#log as #log
 *  @constructs
 */
var HistoryContent = Backbone.Model.extend( baseMVC.LoggableMixin ).extend( {
    idAttribute : 'type_id',

    /** fetch location of this HDA's history in the api */
    urlRoot: galaxy_config.root + 'api/histories/',

    constructor : function( attrs, options ){
        attrs.type_id = HistoryContent.typeIdStr( attrs.history_content_type, attrs.id );
        Backbone.Model.apply( this, arguments );
    },

    initialize : function( attrs, options ){
        // assumes type won't change
        this.on( 'change:id', this._createTypeId );
        //TODO: not sure this covers all the bases...
    },

    /** full url spec. for this HDA */
    url : function(){
        return this.urlRoot + this.get( 'history_id' ) + '/contents/' + this.get('history_content_type') + 's/' + this.get( 'id' );
    },

    /** the more common alias of visible */
    hidden : function(){
        return !this.get( 'visible' );
    },

    // ........................................................................ ajax

    /** save this HDA, _Mark_ing it as deleted (just a flag) */
    'delete' : function _delete( options ){
        if( this.get( 'deleted' ) ){ return jQuery.when(); }
        return this.save( { deleted: true }, options );
    },
    /** save this HDA, _Mark_ing it as undeleted */
    undelete : function _undelete( options ){
        if( !this.get( 'deleted' ) || this.get( 'purged' ) ){ return jQuery.when(); }
        return this.save( { deleted: false }, options );
    },

    /** save this HDA as not visible */
    hide : function _hide( options ){
        if( !this.get( 'visible' ) ){ return jQuery.when(); }
        return this.save( { visible: false }, options );
    },
    /** save this HDA as visible */
    unhide : function _uhide( options ){
        if( this.get( 'visible' ) ){ return jQuery.when(); }
        return this.save( { visible: true }, options );
    },

    /** based on show_deleted, show_hidden (gen. from the container control),
     *      would this ds show in the list of ds's?
     *  @param {Boolean} show_deleted are we showing deleted hdas?
     *  @param {Boolean} show_hidden are we showing hidden hdas?
     */
    isVisible : function( show_deleted, show_hidden ){
        var isVisible = true;
        if( ( !show_deleted )
        &&  ( this.get( 'deleted' ) || this.get( 'purged' ) ) ){
            isVisible = false;
        }
        if( ( !show_hidden )
        &&  ( !this.get( 'visible' ) ) ){
            isVisible = false;
        }
        return isVisible;
    },

    /** search the attribute with key attrKey for the string searchFor; T/F if found */
    searchAttribute : function( attrKey, searchFor ){
        var attrVal = this.get( attrKey );
        //console.debug( 'searchAttribute', attrKey, attrVal, searchFor );
        // bail if empty searchFor or unsearchable values
        if( !searchFor
        ||  ( attrVal === undefined || attrVal === null ) ){
            return false;
        }
        // pass to sep. fn for deep search of array attributes
        if( _.isArray( attrVal ) ){ return this._searchArrayAttribute( attrVal, searchFor ); }
        return ( attrVal.toString().toLowerCase().indexOf( searchFor.toLowerCase() ) !== -1 );
    },

    /** deep(er) search for array attributes; T/F if found */
    _searchArrayAttribute : function( array, searchFor ){
        //console.debug( '_searchArrayAttribute', array, searchFor );
        searchFor = searchFor.toLowerCase();
        //precondition: searchFor has already been validated as non-empty string
        //precondition: assumes only 1 level array
        //TODO: could possibly break up searchFor more (CSV...)
        return _.any( array, function( elem ){
            return ( elem.toString().toLowerCase().indexOf( searchFor.toLowerCase() ) !== -1 );
        });
    },

    /** search all searchAttributes for the string searchFor,
     *      returning a list of keys of attributes that contain searchFor
     */
    search : function( searchFor ){
        var model = this;
        return _.filter( this.searchAttributes, function( key ){
            return model.searchAttribute( key, searchFor );
        });
    },

    /** alias of search, but returns a boolean; accepts attribute specifiers where
     *      the attributes searched can be narrowed to a single attribute using
     *      the form: matches( 'genome_build=hg19' )
     *      (the attribute keys allowed can also be aliases to the true attribute key;
     *          see searchAliases above)
     *  @param {String} term   plain text or ATTR_SPECIFIER sep. key=val pair
     *  @returns {Boolean} was term found in (any) attribute(s)
     */
    matches : function( term ){
        var ATTR_SPECIFIER = '=',
            split = term.split( ATTR_SPECIFIER );
        // attribute is specified - search only that
        if( split.length >= 2 ){
            var attrKey = split[0];
            attrKey = this.searchAliases[ attrKey ] || attrKey;
            return this.searchAttribute( attrKey, split[1] );
        }
        // no attribute is specified - search all attributes in searchAttributes
        return !!this.search( term ).length;
    },

    /** an implicit AND search for all terms; IOW, an hda must match all terms given
     *      where terms is a whitespace separated value string.
     *      e.g. given terms of: 'blah bler database=hg19'
     *          an HDA would have to have attributes containing blah AND bler AND a genome_build == hg19
     *      To include whitespace in terms: wrap the term in double quotations.
     */
    matchesAll : function( terms ){
        var model = this;
        // break the terms up by whitespace and filter out the empty strings
        terms = terms.match( /(".*"|\w*=".*"|\S*)/g ).filter( function( s ){ return !!s; });
        return _.all( terms, function( term ){
            term = term.replace( /"/g, '' );
            return model.matches( term );
        });
    },

    _createTypeId : function(){
        this.set( 'type_id', TypeIdModel.typeIdStr( this.get( 'history_content_type' ), this.get( 'id' ) ) );
    },

} );

/** create a type + id string for use in mixed collections */
HistoryContent.typeIdStr = function _typeId( type, id ){
    return [ type, id ].join( '-' );
};

//==============================================================================
/** @class (HDA) model for a Galaxy dataset
 *      related to a history.
 *  @name HistoryDatasetAssociation
 *
 *  @augments HistoryContent
 *  @borrows LoggableMixin#logger as #logger
 *  @borrows LoggableMixin#log as #log
 *  @constructs
 */
var HistoryDatasetAssociation = HistoryContent.extend(
/** @lends HistoryDatasetAssociation.prototype */{
    
    ///** logger used to record this.log messages, commonly set to console */
    //// comment this out to suppress log output
    //logger              : console,
    
    /** default attributes for a model */
    defaults : {
        // ---these are part of an HDA proper:

        // parent (containing) history
        history_id          : null,
        // often used with tagging
        model_class         : 'HistoryDatasetAssociation',
        history_content_type : 'dataset',
        hid                 : 0,
        
        // ---whereas these are Dataset related/inherited

        id                  : null,
        name                : '(unnamed dataset)',
        // one of HistoryDatasetAssociation.STATES
        state               : 'new',

        deleted             : false,
        visible             : true,

        accessible          : true,
        purged              : false,

        // sniffed datatype (sam, tabular, bed, etc.)
        data_type           : '',
        // size in bytes
        file_size           : 0,
        file_ext            : '',

        // array of associated file types (eg. [ 'bam_index', ... ])
        meta_files          : [],

        misc_blurb          : '',
        misc_info           : '',

        tags                : [],
        annotation          : ''
    },

    /** controller urls assoc. with this HDA */
    urls : function(){
        var id = this.get( 'id' );
        if( !id ){ return {}; }
        var urls = {
            'purge'         : galaxy_config.root + 'datasets/' + id + '/purge_async',

            'display'       : galaxy_config.root + 'datasets/' + id + '/display/?preview=True',
            'edit'          : galaxy_config.root + 'datasets/' + id + '/edit',

            'download'      : galaxy_config.root + 'datasets/' + id + '/display?to_ext=' + this.get( 'file_ext' ),
            'report_error'  : galaxy_config.root + 'dataset/errors?id=' + id,
            'rerun'         : galaxy_config.root + 'tool_runner/rerun?id=' + id,
            'show_params'   : galaxy_config.root + 'datasets/' + id + '/show_params',
            'visualization' : galaxy_config.root + 'visualization',

            'annotation': { 'get': galaxy_config.root + 'dataset/get_annotation_async?id=' + id,
                            'set': galaxy_config.root + 'dataset/annotate_async?id=' + id },
            'meta_download' : galaxy_config.root + 'dataset/get_metadata_file?hda_id=' + id + '&metadata_name='
        };
        return urls;
    },

    /** Set up the model, determine if accessible, bind listeners
     *  @see Backbone.Model#initialize
     */
    initialize : function( data ){
        this.log( this + '.initialize', this.attributes );
        this.log( '\tparent history_id: ' + this.get( 'history_id' ) );

        //!! this state is not in trans.app.model.Dataset.states - set it here -
        if( !this.get( 'accessible' ) ){
            this.set( 'state', HistoryDatasetAssociation.STATES.NOT_VIEWABLE );
        }

        this._setUpListeners();
    },

    /** set up any event listeners
     *  event: state:ready  fired when this HDA moves into a ready state
     */
    _setUpListeners : function(){
        // if the state has changed and the new state is a ready state, fire an event
        this.on( 'change:state', function( currModel, newState ){
            this.log( this + ' has changed state:', currModel, newState );
            if( this.inReadyState() ){
                this.trigger( 'state:ready', currModel, newState, this.previous( 'state' ) );
            }
        });
    },

    // ........................................................................ common queries
    /** Is this hda deleted or purged? */
    isDeletedOrPurged : function(){
        return ( this.get( 'deleted' ) || this.get( 'purged' ) );
    },

    /** Is this HDA in a 'ready' state; where 'Ready' states are states where no
     *      processing (for the ds) is left to do on the server.
     */
    inReadyState : function(){
        var ready = _.contains( HistoryDatasetAssociation.READY_STATES, this.get( 'state' ) );
        return ( this.isDeletedOrPurged() || ready );
    },

    /** Does this model already contain detailed data (as opposed to just summary level data)? */
    hasDetails : function(){
        //?? this may not be reliable
        return _.has( this.attributes, 'genome_build' );
    },

    /** Convenience function to match hda.has_data. */
    hasData : function(){
        return ( this.get( 'file_size' ) > 0 );
    },

    // ........................................................................ ajax

    /** save this HDA, _Mark_ing it as deleted (just a flag) */
    'delete' : function _delete( options ){
        if( this.get( 'deleted' ) ){ return jQuery.when(); }
        return this.save( { deleted: true }, options );
    },
    /** save this HDA, _Mark_ing it as undeleted */
    undelete : function _undelete( options ){
        if( !this.get( 'deleted' ) || this.get( 'purged' ) ){ return jQuery.when(); }
        return this.save( { deleted: false }, options );
    },

    /** save this HDA as not visible */
    hide : function _hide( options ){
        if( !this.get( 'visible' ) ){ return jQuery.when(); }
        return this.save( { visible: false }, options );
    },
    /** save this HDA as visible */
    unhide : function _uhide( options ){
        if( this.get( 'visible' ) ){ return jQuery.when(); }
        return this.save( { visible: true }, options );
    },

    /** purge this HDA and remove the underlying dataset file from the server's fs */
//TODO: use, override model.destroy, HDA.delete({ purge: true })
    purge : function _purge( options ){
        if( this.get( 'purged' ) ){ return jQuery.when(); }
        options = options || {};
        //var hda = this,
        //    //xhr = jQuery.ajax( this.url() + '?' + jQuery.param({ purge: true }), _.extend({
        //    xhr = jQuery.ajax( this.url(), _.extend({
        //        type : 'DELETE',
        //        data : {
        //            purge : true
        //        }
        //    }, options ));
        //
        //xhr.done( function( response ){
        //    console.debug( 'response', response );
        //    //hda.set({ deleted: true, purged: true });
        //    hda.set( response );
        //});
        //return xhr;

        options.url = galaxy_config.root + 'datasets/' + this.get( 'id' ) + '/purge_async';

        //TODO: ideally this would be a DELETE call to the api
        //  using purge async for now
        var hda = this,
            xhr = jQuery.ajax( options );
        xhr.done( function( message, status, responseObj ){
            hda.set({ deleted: true, purged: true });
        });
        xhr.fail( function( xhr, status, message ){
            // Exception messages are hidden within error page including:  '...not allowed in this Galaxy instance.'
            // unbury and re-add to xhr
            var error = _l( "Unable to purge dataset" );
            var messageBuriedInUnfortunatelyFormattedError = ( 'Removal of datasets by users '
                + 'is not allowed in this Galaxy instance' );
            if( xhr.responseJSON && xhr.responseJSON.error ){
                error = xhr.responseJSON.error;
            } else if( xhr.responseText.indexOf( messageBuriedInUnfortunatelyFormattedError ) !== -1 ){
                error = messageBuriedInUnfortunatelyFormattedError;
            }
            xhr.responseText = error;
            hda.trigger( 'error', hda, xhr, options, _l( error ), { error: error } );
        });
        return xhr;
    },

    // ........................................................................ sorting/filtering

    // ........................................................................ search
    /** what attributes of an HDA will be used in a text search */
    searchAttributes : [
        'name', 'file_ext', 'genome_build', 'misc_blurb', 'misc_info', 'annotation', 'tags'
    ],

    /** our attr keys don't often match the labels we display to the user - so, when using
     *      attribute specifiers ('name="bler"') in a term, allow passing in aliases for the
     *      following attr keys.
     */
    searchAliases : {
        title       : 'name',
        format      : 'file_ext',
        database    : 'genome_build',
        blurb       : 'misc_blurb',
        description : 'misc_blurb',
        info        : 'misc_info',
        tag         : 'tags'
    },

    // ........................................................................ misc
    /** String representation */
    toString : function(){
        var nameAndId = this.get( 'id' ) || '';
        if( this.get( 'name' ) ){
            nameAndId = this.get( 'hid' ) + ' :"' + this.get( 'name' ) + '",' + nameAndId;
        }
        return 'HDA(' + nameAndId + ')';
    }
});

//------------------------------------------------------------------------------
/** Class level map of possible HDA states to their string equivalents.
 *      A port of galaxy.model.Dataset.states.
 */
HistoryDatasetAssociation.STATES = {
    // NOT ready states
    /** is uploading and not ready */
    UPLOAD              : 'upload',
    /** the job that will produce the dataset queued in the runner */
    QUEUED              : 'queued',
    /** the job that will produce the dataset is running */
    RUNNING             : 'running',
    /** metadata for the dataset is being discovered/set */
    SETTING_METADATA    : 'setting_metadata',

    // ready states
    /** was created without a tool */
    NEW                 : 'new',
    /** has no data */
    EMPTY               : 'empty',
    /** has successfully completed running */
    OK                  : 'ok',

    /** the job that will produce the dataset paused */
    PAUSED              : 'paused',
    /** metadata discovery/setting failed or errored (but otherwise ok) */
    FAILED_METADATA     : 'failed_metadata',
    /** not accessible to the current user (i.e. due to permissions) */
    NOT_VIEWABLE        : 'noPermission',   // not in trans.app.model.Dataset.states
    /** deleted while uploading */
    DISCARDED           : 'discarded',
    /** the tool producing this dataset failed */
    ERROR               : 'error'
};

/** states that are in a final state (the underlying job is complete) */
HistoryDatasetAssociation.READY_STATES = [
    HistoryDatasetAssociation.STATES.OK,
    HistoryDatasetAssociation.STATES.EMPTY,
    HistoryDatasetAssociation.STATES.PAUSED,
    HistoryDatasetAssociation.STATES.FAILED_METADATA,
    HistoryDatasetAssociation.STATES.NOT_VIEWABLE,
    HistoryDatasetAssociation.STATES.DISCARDED,
    HistoryDatasetAssociation.STATES.ERROR
];

/** states that will change (the underlying job is not finished) */
HistoryDatasetAssociation.NOT_READY_STATES = [
    HistoryDatasetAssociation.STATES.UPLOAD,
    HistoryDatasetAssociation.STATES.QUEUED,
    HistoryDatasetAssociation.STATES.RUNNING,
    HistoryDatasetAssociation.STATES.SETTING_METADATA,
    HistoryDatasetAssociation.STATES.NEW
];

//==============================================================================
/** @class Backbone collection of (HDA) models
 *     TODO: Rename HistoryContentCollection
 *
 *  @borrows LoggableMixin#logger as #logger
 *  @borrows LoggableMixin#log as #log
 *  @constructs
 */
var HDACollection = Backbone.Collection.extend( baseMVC.LoggableMixin ).extend(
/** @lends HDACollection.prototype */{
    model : function( attrs, options ) {
        if( attrs.history_content_type == "dataset" ) {
            return new HistoryDatasetAssociation( attrs, options );
        } else if( attrs.history_content_type == "dataset_collection" ) {
            return new HistoryDatasetCollectionAssociation( attrs, options );
        } else {
            // TODO: Handle unknown history_content_type...
        }
    },

    ///** logger used to record this.log messages, commonly set to console */
    //// comment this out to suppress log output
    //logger              : console,

    /** root api url */
    urlRoot : galaxy_config.root + 'api/histories',
    /** complete api url */
    url : function(){
        return this.urlRoot + '/' + this.historyId + '/contents';
    },

    /** Set up.
     *  @see Backbone.Collection#initialize
     */
    initialize : function( models, options ){
        options = options || {};
        this.historyId = options.historyId;
        //this._setUpListeners();
    },

    //_setUpListeners : function(){
    //},

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
            if( !item.inReadyState() ){
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
        //console.debug( 'filters:', filters );
        //TODO:?? why doesn't this return a collection?
        // always filter by show deleted/hidden first
        var filteredHdas = new HDACollection( this.filter( function( item ){
            return item.isVisible( show_deleted, show_hidden );
        }));

        _.each( filters, function( filter_fn ){
            if( !_.isFunction( filter_fn ) ){ return; }
            filteredHdas = new HDACollection( filteredHdas.filter( filter_fn ) );
        });
        //if( filteredHdas.length ){
        //    console.debug( 'filteredHdas:' );
        //    filteredHdas.each( function( hda ){
        //        console.debug( '\t', hda );
        //    });
        //} else {
        //    console.warn( 'no visible hdas' );
        //}
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

    /** using a queue, perform hdaModelAjaxFn on each of the hdas in this collection */
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
            var attrs = model.attributes || model; // Handle raw json or Backbone model.
            var typeId = HistoryContent.typeIdStr( attrs.history_content_type, attrs.id );
            var existing = collection.get( typeId );
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
        options = options || {};
        options.url = this.url();
        options.type = "POST";
        var full_collection_type = collection_type;
        var element_identifiers = [],
            name = null;

        // This mechanism is rough - no error handling, allows invalid selections, no way
        // for user to pick/override element identifiers. This is only really meant 
        if( collection_type == "list" ) {
            this.chain().each( function( hda ) {
                // TODO: Handle duplicate names.
                var name = hda.attributes.name;
                var id = hda.get('id');
                var content_type = hda.attributes.history_content_type;
                if( content_type == "dataset" ) {
                    if( full_collection_type != "list" ) {
                        console.log( "Invalid collection type" );
                    }
                    element_identifiers.push( { name: name, src: "hda", id: id } );
                } else {
                    if( full_collection_type == "list" ) {
                        full_collection_type = "list:" + hda.attributes.collection_type;
                    } else {
                        if( full_collection_type != "list:" + hda.attributes.collection_type ) {
                            console.log( "Invalid collection type" );
                        }                        
                    }
                    element_identifiers.push( { name: name, src: "hdca", id: id } );
                }
            });
            name = "New Dataset List";
        } else if( collection_type == "paired" ) {
            var ids = this.ids();
            if( ids.length != 2 ){
                // TODO: Do something...
            }
            element_identifiers.push( { name: "forward", src: "hda", id: ids[ 0 ] } );
            element_identifiers.push( { name: "reverse", src: "hda", id: ids[ 1 ] } );
            name = "New Dataset Pair";
        }
        options.data = {type: "dataset_collection",
                        name: name,
                        collection_type: full_collection_type,
                        element_identifiers: JSON.stringify(element_identifiers),
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

    /** String representation. */
    toString : function(){
         return ([ 'HDACollection(', [ this.historyId, this.length ].join(), ')' ].join( '' ));
    }
});

var HistoryDatasetCollectionAssociation = HistoryContent.extend(
/** @lends HistoryDatasetCollectionAssociation.prototype */{
    /** default attributes for a model */
    defaults : {
        // parent (containing) history
        history_id          : null,
        // often used with tagging
        model_class         : 'HistoryDatasetCollectionAssociation',
        history_content_type : 'dataset_collection',
        hid                 : 0,
        
        id                  : null,
        name                : '(unnamed dataset collection)',
        // one of HistoryDatasetAssociation.STATES, calling them all 'ok' for now.
        state               : 'ok',

        accessible          : true,
        deleted             : false,
        visible             : true,

        purged              : false, // Purged doesn't make sense for collections - at least right now.

        tags                : [],
        annotation          : ''
    },
    urls : function(){
    },

    inReadyState : function(){
        return true; // TODO
    },

    // ........................................................................ search
    /** what attributes of an collection will be used in a text search */
    searchAttributes : [
        'name'
    ],

    /** our attr keys don't often match the labels we display to the user - so, when using
     *      attribute specifiers ('name="bler"') in a term, allow passing in aliases for the
     *      following attr keys.
     */
    searchAliases : {
        title       : 'name'
        // TODO: Add tag...
    },

});



//==============================================================================
return {
    HistoryDatasetAssociation : HistoryDatasetAssociation,
    HDACollection             : HDACollection
};});
