define([
    "mvc/history/history-content-base",
    "utils/localization"
], function( historyContent, _l ){
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
var HistoryDatasetAssociation = historyContent.HistoryContent.extend(
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
    return {
        HistoryDatasetAssociation : HistoryDatasetAssociation
    };
});
