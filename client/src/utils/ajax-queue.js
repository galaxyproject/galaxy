import $ from "jquery";

//=============================================================================
/** @class AjaxQueue
 *  Class that allows queueing functions that return jQuery promises (such
 *  as ajax calls). Each function waits for the previous to complete before
 *  being called
 *
 *  @constructor accepts a list of functions and automatically begins
 *      processing them
 */
class AjaxQueue {
    constructor(initialFunctions) {
        /** the main deferred for the entire queue - note: also sends notifications of progress */
        this.deferred = $.Deferred();
        /** the queue array of functions */
        this.queue = [];
        /** cache the response from each deferred call - error or success */
        this.responses = [];
        /** total number of fn's to process */
        this.numToProcess = 0;
        /** is the queue processing/waiting for any calls to return? */
        this.running = false;

        this.init(initialFunctions || []);
        this.start();
    }

    /** add all fns in initialFunctions (if any) to the queue */
    init(initialFunctions) {
        initialFunctions.forEach((fn) => {
            this.add(fn);
        });
    }

    add(fn) {
        var index = this.queue.length;
        this.numToProcess += 1;

        this.queue.push(() => {
            var fnIndex = index;
            var xhr = fn();
            // if successful, notify using the deferred to allow tracking progress
            xhr.done((response) => {
                this.deferred.notify({
                    curr: fnIndex,
                    total: this.numToProcess,
                    response: response,
                });
            });
            // (regardless of previous error or success) if not last ajax call, shift and call the next
            //  if last fn, resolve deferred
            xhr.always((response) => {
                this.responses.push(response);
                if (this.queue.length) {
                    this.queue.shift()();
                } else {
                    this.stop();
                }
            });
        });
        return this;
    }

    start() {
        if (this.queue.length) {
            this.running = true;
            this.queue.shift()();
        }
        return this;
    }

    /** stop the queue
     *  @param {boolean} causeFail  cause an error/fail on the main deferred
     *  @param {String} msg         message to send when rejecting the main deferred
     */
    stop(causeFail, msg) {
        //TODO: doesn't abort current call
        this.running = false;
        this.queue = [];
        if (causeFail) {
            //TODO: spliced args instead
            this.deferred.reject(msg);
        } else {
            this.deferred.resolve(this.responses);
        }
        this.numToProcess = 0;
        this.deferred = $.Deferred();
        return this;
    }

    // only a handful of the deferred interface for now - possible YAGNI
    /** implement done from the jq deferred interface */
    done(fn) {
        return this.deferred.done(fn);
    }

    /** implement fail from the jq deferred interface */
    fail(fn) {
        return this.deferred.fail(fn);
    }

    /** implement always from the jq deferred interface */
    always(fn) {
        return this.deferred.always(fn);
    }

    /** implement progress from the jq deferred interface */
    progress(fn) {
        return this.deferred.progress(fn);
    }

    /** shortcut constructor / fire and forget
     *  @returns {Deferred} the queue's main deferred
     */
    static create(initialFunctions) {
        return new AjaxQueue(initialFunctions).deferred;
    }
}

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
class NamedAjaxQueue extends AjaxQueue {
    constructor(initialFunctions) {
        super(initialFunctions);
        this.names = {};
    }

    /** add the obj.fn to the queue if obj.name hasn't been used before */
    add(obj) {
        if (!(Object.prototype.hasOwnProperty.call(obj, "name") && Object.prototype.hasOwnProperty.call(obj, "fn"))) {
            throw new Error(`NamedAjaxQueue.add requires an object with both "name" and "fn": ${JSON.stringify(obj)}`);
        }
        if (Object.prototype.hasOwnProperty.call(this.names, obj.name)) {
            //console.warn( 'name has been used:', obj.name );
            return;
        }
        this.names[obj.name] = true;
        return super.add(obj.fn);
    }

    clear() {
        this.names = {};
        return this;
    }

    /** shortcut constructor / fire and forget
     *  @returns {Deferred} the queue's main deferred
     */
    static create(initialFunctions) {
        return new NamedAjaxQueue(initialFunctions).deferred;
    }
}

//=============================================================================
export default {
    AjaxQueue: AjaxQueue,
    NamedAjaxQueue: NamedAjaxQueue,
};
