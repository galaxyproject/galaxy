define("utils/deferred", ["exports", "utils/utils"], function(exports, _utils) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });

    var _utils2 = _interopRequireDefault(_utils);

    function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : {
            default: obj
        };
    }

    exports.default = Backbone.Model.extend({
        initialize: function initialize() {
            this.active = {};
            this.last = null;
        },

        /** Adds a callback to the queue. Upon execution a deferred object is parsed to the callback i.e. callback( deferred ).
         *  If the callback does not take any arguments, the deferred is resolved instantly.
         */
        execute: function execute(callback) {
            var self = this;
            var id = _utils2.default.uid();
            var has_deferred = callback.length > 0;

            // register process
            this.active[id] = true;

            // deferred process
            var process = $.Deferred();
            process.promise().always(function() {
                delete self.active[id];
                has_deferred && Galaxy.emit.debug("deferred::execute()", this.state().charAt(0).toUpperCase() + this.state().slice(1) + " " + id);
            });

            // deferred queue
            $.when(this.last).always(function() {
                if (self.active[id]) {
                    has_deferred && Galaxy.emit.debug("deferred::execute()", "Running " + id);
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
        reset: function reset() {
            Galaxy.emit.debug("deferred::execute()", "Reset");
            for (var i in this.active) {
                this.active[i] = false;
            }
        },

        /** Returns true if all processes are done.
         */
        ready: function ready() {
            return $.isEmptyObject(this.active);
        }
    });
});
//# sourceMappingURL=../../maps/utils/deferred.js.map
