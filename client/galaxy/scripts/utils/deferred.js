// dependencies
define(['utils/utils'], function(Utils) {

/**
 *  This class provides an alternative way to handle deferred processes. It makes it easy to handle multiple and overlapping sets of deferred processes.
 */
return Backbone.Model.extend({
    // callback queue
    queue: [],
    
    // list of currently registered processes
    process: {},
    
    // process counter
    counter: 0,
    
    /** Initialize
    */
    initialize: function(){
        this.on('refresh', function() {
            if (this.queue.length > 0 && this.ready()) {
                var callback = this.queue[0];
                this.queue.splice(0, 1);
                callback && callback();
            }
        });
    },
    
    /** This executes a callback once all processes are unregistered
     *  The callback is expected to register/unregister new processes
    */
    execute: function(callback) {
        this.queue.push(callback);
        this.trigger('refresh');
    },
    
    /** This is called to register a new process
    */
    register: function() {
        var id = Utils.uuid();
        this.process[id] = true;
        this.counter++;
        console.debug('Deferred:register() - Registering ' + id);
        return id;
    },
    
    /** This is called to unregister a particular process
    */
    done: function(id) {
        if (this.process[id]) {
            delete this.process[id];
            this.counter--;
            console.debug('Deferred:done() - Unregistering ' + id);
            this.trigger('refresh');
        }
    },
    
    /** Removes all callbacks from the current queue
    */
    reset: function() {
        this.queue = [];
    },
    
    /** Returns true if no processes are currently executed
    */
    ready: function() {
        return (this.counter == 0);
    }
});

});