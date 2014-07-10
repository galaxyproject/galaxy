// dependencies
define(['utils/utils'], function(Utils) {

/**
 *  This class handles deferred processes. It makes it easy to handle multiple and overlapping sets of deferred processes.
 */
return Backbone.Model.extend({
    // queue
    queue: [],
    
    // list of currently registered processes
    process: {},
    
    // process counter
    counter: 0,
    
    // initialize
    initialize: function(){
        // loop through queue and check states
        this.on('refresh', function() {
            for (var index in this.queue) {
                if (this.counter == 0) {
                    // get callback
                    var callback = this.queue[index];
                
                    // remove callback
                    this.queue.splice(index, 1);
                
                    // execute callback
                    callback();
                }
            }
        });
    },
    
    // executes callback once all processes are unregistered
    execute: function(callback) {
        // add wrapper to queue
        this.queue.push(callback);
        
        // trigger change
        this.trigger('refresh');
    },
    
    // register process
    register: function() {
        // create unique id
        var id = Utils.uuid();
        
        // add process to queue
        this.process[id] = true;
        
        // increase process counter
        this.counter++;
        
        // log
        console.debug('Deferred:register() - Registering ' + id);
        
        // return unique id
        return id;
    },
    
    // unregister process
    done: function(id) {
        if (this.process[id]) {
            // delete tag
            delete this.process[id];
            
            // decrease process counter
            this.counter--;
            
            // log
            console.debug('Deferred:done() - Unregistering ' + id);
            
            // trigger change
            this.trigger('refresh');
        }
    },
    
    // ready
    ready: function() {
        return (this.counter == 0);
    }
});

});