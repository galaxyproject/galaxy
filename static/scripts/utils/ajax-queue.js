define([
], function(){
//ASSUMES: jquery
//=============================================================================
/** @class AjaxQueue
 *  Class that allows queueing functions that return jQuery promises (such
 *  as ajax calls). Each function waits for the previous to complete before
 *  being called
 *
 *  @constructor accepts a list of functions and automatically begins
 *      processing them
 */
function AjaxQueue( initialFunctions ){
    //TODO: possibly rename to DeferredQueue
    var self = this;
    /** the main deferred for the entire queue - note: also sends notifications of progress */
    self.deferred = jQuery.Deferred();
    /** the queue array of functions */
    self.queue = [];
    /** cache the response from each deferred call - error or success */
    self.responses = [];
    /** total number of fn's to process */
    self.numToProcess = 0;
    /** is the queue processing/waiting for any calls to return? */
    self.running = false;

    self.init( initialFunctions || [] );
    self.start();

    return self;
}

/** add all fns in initialFunctions (if any) to the queue */
AjaxQueue.prototype.init = function init( initialFunctions ){
    var self = this;
    initialFunctions.forEach( function( fn ){
        self.add( fn );
    });
};

/** add a fn to the queue */
AjaxQueue.prototype.add = function add( fn ){
    //console.debug( 'AjaxQueue.prototype.add:', fn );
    var self = this,
        index = this.queue.length;
    this.numToProcess += 1;

    this.queue.push( function(){
        var xhr = fn();
        // if successful, notify using the deferred to allow tracking progress
        xhr.done( function( response ){
            self.deferred.notify({ curr: index, total: self.numToProcess, response: response });
        });
        // (regardless of previous error or success) if not last ajax call, shift and call the next
        //  if last fn, resolve deferred
        xhr.always( function( response ){
            self.responses.push( response );
            if( self.queue.length ){
                self.queue.shift()();
            } else {
                self.stop();
            }
        });
    });
};

/** start processing the queue */
AjaxQueue.prototype.start = function start(){
    if( this.queue.length ){
        this.running = true;
        this.queue.shift()();
    }
};

/** stop the queue
 *  @param {boolean} causeFail  cause an error/fail on the main deferred
 *  @param {String} msg         message to send when rejecting the main deferred
 */
AjaxQueue.prototype.stop = function stop( causeFail, msg ){
    //TODO: doesn't abort current call
    this.running = false;
    this.queue = [];
    if( causeFail ){
        //TODO: spliced args instead
        this.deferred.reject( msg );
    } else {
        this.deferred.resolve( this.responses );
    }
    return this;
};

// only a handful of the deferred interface for now - possible YAGNI
/** implement done from the jq deferred interface */
AjaxQueue.prototype.done = function done( fn ){
    return this.deferred.done( fn );
};
/** implement fail from the jq deferred interface */
AjaxQueue.prototype.fail = function fail( fn ){
    return this.deferred.fail( fn );
};
/** implement always from the jq deferred interface */
AjaxQueue.prototype.always = function always( fn ){
    return this.deferred.always( fn );
};
/** implement progress from the jq deferred interface */
AjaxQueue.prototype.progress = function progress( fn ){
    return this.deferred.progress( fn );
};

/** shortcut constructor / fire and forget
 *  @returns {Deferred} the queue's main deferred
 */
AjaxQueue.create = function create( initialFunctions ){
    return new AjaxQeueue( initialFunctions ).deferred;
};


//=============================================================================
/** @class NamedAjaxQueue
 *  @augments AjaxQueue
 *  Allows associating a name with a deferring fn and prevents adding deferring
 *  fns if the name has already been used. Useful to prevent build up of duplicate
 *  async calls.
 *  Both the array initialFunctions sent to constructor and any added later with
 *  add() should be objects (NOT functions) of the form:
 *  { name: some unique id,
 *    fn:   the deferring fn or ajax call }
 */
function NamedAjaxQueue( initialFunctions ){
    var self = this;
    self.names = {};
    AjaxQueue.call( this, initialFunctions );
    return self;
}
NamedAjaxQueue.prototype = new AjaxQueue();
NamedAjaxQueue.prototype.constructor = NamedAjaxQueue;

/** add the obj.fn to the queue if obj.name hasn't been used before */
NamedAjaxQueue.prototype.add = function add( obj ){
    //console.debug( 'NamedAjaxQueue.prototype.add:', obj );
    if( !( obj.hasOwnProperty( 'name' ) && obj.hasOwnProperty( 'fn' ) ) ){
        throw new Error( 'NamedAjaxQueue.add requires an object with both "name" and "fn": ' + JSON.stringify( obj ) );
    }
    if( this.names.hasOwnProperty( obj.name ) ){
        //console.warn( 'name has been used:', obj.name );
        return;
    }
    this.names[ obj.name ] = true;
    AjaxQueue.prototype.add.call( this, obj.fn );
};

/** shortcut constructor / fire and forget
 *  @returns {Deferred} the queue's main deferred
 */
NamedAjaxQueue.create = function create( initialFunctions ){
    return new NamedAjaxQueue( initialFunctions ).deferred;
};


//=============================================================================
    return {
        AjaxQueue       : AjaxQueue,
        NamedAjaxQueue  : NamedAjaxQueue
    };
});
