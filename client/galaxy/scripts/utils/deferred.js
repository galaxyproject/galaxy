/**
 *  This class defines a queue to ensure that multiple deferred callbacks are executed sequentially.
 */
import $ from "jquery";
import Backbone from "backbone";
import Utils from "utils/utils";
import { getGalaxyInstance } from "app";

export default Backbone.Model.extend({
    initialize: function() {
        this.active = {};
        this.last = null;
    },

    /** Adds a callback to the queue. Upon execution a deferred object is parsed to the callback i.e. callback( deferred ).
     *  If the callback does not take any arguments, the deferred is resolved instantly.
     */
    execute: function(callback) {
        var self = this;
        var id = Utils.uid();
        var has_deferred = callback.length > 0;
        let Galaxy = getGalaxyInstance();

        // register process
        this.active[id] = true;

        // deferred process
        var process = $.Deferred();
        process.promise().always(function() {
            delete self.active[id];
            has_deferred &&
                Galaxy.emit.debug(
                    "deferred::execute()",
                    `${this.state()
                        .charAt(0)
                        .toUpperCase() + this.state().slice(1)} ${id}`
                );
        });

        // deferred queue
        $.when(this.last).always(() => {
            if (self.active[id]) {
                has_deferred && Galaxy.emit.debug("deferred::execute()", `Running ${id}`);
                callback(process);
                !has_deferred && process.resolve();
            } else {
                process.reject();
            }
        });
        this.last = process.promise();
    },

    /** Resets the promise queue. All currently queued but unexecuted callbacks/promises will be rejected.
     */
    reset: function() {
        let Galaxy = getGalaxyInstance();
        Galaxy.emit.debug("deferred::execute()", "Reset");
        for (var i in this.active) {
            this.active[i] = false;
        }
    },

    /** Returns true if all processes are done.
     */
    ready: function() {
        return $.isEmptyObject(this.active);
    }
});
