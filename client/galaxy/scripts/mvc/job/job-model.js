define([
    "mvc/history/history-contents",
    "mvc/dataset/states",
    "utils/ajax-queue",
    "mvc/base-mvc",
    "utils/localization"
], function( HISTORY_CONTENTS, STATES, AJAX_QUEUE, BASE_MVC, _l ){
//==============================================================================
var searchableMixin = BASE_MVC.SearchableModelMixin;
/** @class Represents a job running or ran on the server job handlers.
 */
var Job = Backbone.Model.extend( BASE_MVC.LoggableMixin ).extend(
        BASE_MVC.mixin( searchableMixin, /** @lends Job.prototype */{

    /** logger used to record this.log messages, commonly set to console */
    //logger              : console,

    /** default attributes for a model */
    defaults : {
        model_class : 'Job',

        tool_id     : null,
        exit_code   : null,

        inputs      : {},
        outputs     : {},
        params      : {},

        create_time : null,
        update_time : null,
        state       : STATES.NEW
    },

    /** override to parse params on incomming */
    parse : function( response, options ){
        response.params = this.parseParams( response.params );
        return response;
    },

    /** override to treat param values as json */
    parseParams : function( params ){
        var newParams = {};
        _.each( params, function( value, key ){
            newParams[ key ] = JSON.parse( value );
        });
        return newParams;
    },

    /** instance vars and listeners */
    initialize : function( attributes, options ){
        this.debug( this + '(Job).initialize', attributes, options );

        this.set( 'params', this.parseParams( this.get( 'params' ) ), { silent: true });

        this.outputCollection = attributes.outputCollection || new HISTORY_CONTENTS.HistoryContents([]);
        this._setUpListeners();
    },

    /** set up any event listeners
     *  event: state:ready  fired when this DA moves into/is already in a ready state
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
    /** Is this job in a 'ready' state; where 'Ready' states are states where no
     *      processing is left to do on the server.
     */
    inReadyState : function(){
        return _.contains( STATES.READY_STATES, this.get( 'state' ) );
    },

    /** Does this model already contain detailed data (as opposed to just summary level data)? */
    hasDetails : function(){
        //?? this may not be reliable
        return !_.isEmpty( this.get( 'outputs' ) );
    },

    // ........................................................................ ajax
    /** root api url */
    urlRoot : (( window.galaxy_config && galaxy_config.root )?( galaxy_config.root ):( '/' )) + 'api/jobs',
    //url : function(){ return this.urlRoot; },

    // ........................................................................ searching
    // see base-mvc, SearchableModelMixin
    /** what attributes of an Job will be used in a text search */
    //searchAttributes : [
    //    'tool'
    //],

    // ........................................................................ misc
    /** String representation */
    toString : function(){
        return [ 'Job(', this.get( 'id' ), ':', this.get( 'tool_id' ), ')' ].join( '' );
    }
}));


//==============================================================================
/** @class Backbone collection for Jobs.
 */
var JobCollection = Backbone.Collection.extend( BASE_MVC.LoggableMixin ).extend(
/** @lends JobCollection.prototype */{
    model : Job,

    /** logger used to record this.log messages, commonly set to console */
    //logger              : console,

    /** root api url */
    urlRoot : (( window.galaxy_config && galaxy_config.root )?( galaxy_config.root ):( '/' )) + 'api/jobs',
    url : function(){ return this.urlRoot; },

    intialize : function( models, options ){
        console.debug( models, options );
    },

    // ........................................................................ common queries
    /** Get the ids of every item in this collection
     *  @returns array of encoded ids
     */
    ids : function(){
        return this.map( function( item ){ return item.get( 'id' ); });
    },

    /** Get jobs that are not ready
     *  @returns array of content models
     */
    notReady : function(){
        return this.filter( function( job ){
            return !job.inReadyState();
        });
    },

    /** return true if any jobs don't have details */
    haveDetails : function(){
        return this.all( function( job ){ return job.hasDetails(); });
    },

    // ........................................................................ ajax
    /** fetches all details for each job in the collection using a queue */
    queueDetailFetching : function(){
        var collection = this,
            queue = new AJAX_QUEUE.AjaxQueue( this.map( function( job ){
                return function(){
                    return job.fetch({ silent: true });
                };
            }));
        queue.done( function(){
            collection.trigger( 'details-loaded' );
        });
        return queue;
    },

    //toDAG : function(){
    //    return new JobDAG( this.toJSON() );
    //},

    // ........................................................................ sorting/filtering
    /** return a new collection of jobs whose attributes contain the substring matchesWhat */
    matches : function( matchesWhat ){
        return this.filter( function( job ){
            return job.matches( matchesWhat );
        });
    },

    // ........................................................................ misc
    /** override to get a correct/smarter merge when incoming data is partial */
    set : function( models, options ){
        // arrrrrrrrrrrrrrrrrg...
        //  (e.g. stupid backbone)
        //  w/o this partial models from the server will fill in missing data with model defaults
        //  and overwrite existing data on the client
        // see Backbone.Collection.set and _prepareModel
        var collection = this;
        models = _.map( models, function( model ){
            if( !collection.get( model.id ) ){ return model; }

            // merge the models _BEFORE_ calling the superclass version
            var merged = existing.toJSON();
            _.extend( merged, model );
            return merged;
        });
        // now call superclass when the data is filled
        Backbone.Collection.prototype.set.call( this, models, options );
    },

    /** String representation. */
    toString : function(){
         return ([ 'JobCollection(', this.length, ')' ].join( '' ));
    }

//----------------------------------------------------------------------------- class vars
}, {
    /** class level fn for fetching the job details for all jobs in a history */
    fromHistory : function( historyId ){
        console.debug( this );
        var Collection = this,
            collection = new Collection([]);
        collection.fetch({ data: { history_id: historyId }})
            .done( function(){
                window.queue = collection.queueDetailFetching();

            });
        return collection;
    }
});


//=============================================================================
    return {
        Job             : Job,
        JobCollection   : JobCollection
    };
});
