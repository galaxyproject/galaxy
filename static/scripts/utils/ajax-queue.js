define("utils/ajax-queue", ["exports"], function(exports) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });

    function _possibleConstructorReturn(self, call) {
        if (!self) {
            throw new ReferenceError("this hasn't been initialised - super() hasn't been called");
        }

        return call && (typeof call === "object" || typeof call === "function") ? call : self;
    }

    var _get = function get(object, property, receiver) {
        if (object === null) object = Function.prototype;
        var desc = Object.getOwnPropertyDescriptor(object, property);

        if (desc === undefined) {
            var parent = Object.getPrototypeOf(object);

            if (parent === null) {
                return undefined;
            } else {
                return get(parent, property, receiver);
            }
        } else if ("value" in desc) {
            return desc.value;
        } else {
            var getter = desc.get;

            if (getter === undefined) {
                return undefined;
            }

            return getter.call(receiver);
        }
    };

    function _inherits(subClass, superClass) {
        if (typeof superClass !== "function" && superClass !== null) {
            throw new TypeError("Super expression must either be null or a function, not " + typeof superClass);
        }

        subClass.prototype = Object.create(superClass && superClass.prototype, {
            constructor: {
                value: subClass,
                enumerable: false,
                writable: true,
                configurable: true
            }
        });
        if (superClass) Object.setPrototypeOf ? Object.setPrototypeOf(subClass, superClass) : subClass.__proto__ = superClass;
    }

    function _classCallCheck(instance, Constructor) {
        if (!(instance instanceof Constructor)) {
            throw new TypeError("Cannot call a class as a function");
        }
    }

    var _createClass = function() {
        function defineProperties(target, props) {
            for (var i = 0; i < props.length; i++) {
                var descriptor = props[i];
                descriptor.enumerable = descriptor.enumerable || false;
                descriptor.configurable = true;
                if ("value" in descriptor) descriptor.writable = true;
                Object.defineProperty(target, descriptor.key, descriptor);
            }
        }

        return function(Constructor, protoProps, staticProps) {
            if (protoProps) defineProperties(Constructor.prototype, protoProps);
            if (staticProps) defineProperties(Constructor, staticProps);
            return Constructor;
        };
    }();

    var AjaxQueue = function() {
        function AjaxQueue(initialFunctions) {
            _classCallCheck(this, AjaxQueue);

            /** the main deferred for the entire queue - note: also sends notifications of progress */
            this.deferred = jQuery.Deferred();
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


        _createClass(AjaxQueue, [{
            key: "init",
            value: function init(initialFunctions) {
                var _this = this;

                initialFunctions.forEach(function(fn) {
                    _this.add(fn);
                });
            }
        }, {
            key: "add",
            value: function add(fn) {
                var _this2 = this;

                var index = this.queue.length;
                this.numToProcess += 1;

                this.queue.push(function() {
                    var fnIndex = index;
                    var xhr = fn();
                    // if successful, notify using the deferred to allow tracking progress
                    xhr.done(function(response) {
                        _this2.deferred.notify({
                            curr: fnIndex,
                            total: _this2.numToProcess,
                            response: response
                        });
                    });
                    // (regardless of previous error or success) if not last ajax call, shift and call the next
                    //  if last fn, resolve deferred
                    xhr.always(function(response) {
                        _this2.responses.push(response);
                        if (_this2.queue.length) {
                            _this2.queue.shift()();
                        } else {
                            _this2.stop();
                        }
                    });
                });
                return this;
            }
        }, {
            key: "start",
            value: function start() {
                if (this.queue.length) {
                    this.running = true;
                    this.queue.shift()();
                }
                return this;
            }
        }, {
            key: "stop",
            value: function stop(causeFail, msg) {
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
                this.deferred = jQuery.Deferred();
                return this;
            }
        }, {
            key: "done",
            value: function done(fn) {
                return this.deferred.done(fn);
            }
        }, {
            key: "fail",
            value: function fail(fn) {
                return this.deferred.fail(fn);
            }
        }, {
            key: "always",
            value: function always(fn) {
                return this.deferred.always(fn);
            }
        }, {
            key: "progress",
            value: function progress(fn) {
                return this.deferred.progress(fn);
            }
        }], [{
            key: "create",
            value: function create(initialFunctions) {
                return new AjaxQueue(initialFunctions).deferred;
            }
        }]);

        return AjaxQueue;
    }();

    var NamedAjaxQueue = function(_AjaxQueue) {
        _inherits(NamedAjaxQueue, _AjaxQueue);

        function NamedAjaxQueue(initialFunctions) {
            _classCallCheck(this, NamedAjaxQueue);

            var _this3 = _possibleConstructorReturn(this, (NamedAjaxQueue.__proto__ || Object.getPrototypeOf(NamedAjaxQueue)).call(this, initialFunctions));

            _this3.names = {};
            return _this3;
        }

        /** add the obj.fn to the queue if obj.name hasn't been used before */


        _createClass(NamedAjaxQueue, [{
            key: "add",
            value: function add(obj) {
                if (!(obj.hasOwnProperty("name") && obj.hasOwnProperty("fn"))) {
                    throw new Error("NamedAjaxQueue.add requires an object with both \"name\" and \"fn\": " + JSON.stringify(obj));
                }
                if (this.names.hasOwnProperty(obj.name)) {
                    //console.warn( 'name has been used:', obj.name );
                    return;
                }
                this.names[obj.name] = true;
                return _get(NamedAjaxQueue.prototype.__proto__ || Object.getPrototypeOf(NamedAjaxQueue.prototype), "add", this).call(this, obj.fn);
            }
        }, {
            key: "clear",
            value: function clear() {
                this.names = {};
                return this;
            }
        }], [{
            key: "create",
            value: function create(initialFunctions) {
                return new NamedAjaxQueue(initialFunctions).deferred;
            }
        }]);

        return NamedAjaxQueue;
    }(AjaxQueue);

    exports.default = {
        AjaxQueue: AjaxQueue,
        NamedAjaxQueue: NamedAjaxQueue
    };
});
//# sourceMappingURL=../../maps/utils/ajax-queue.js.map
