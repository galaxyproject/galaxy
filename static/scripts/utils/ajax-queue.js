define([], function() {
    function AjaxQueue(initialFunctions) {
        var self = this;
        return self.deferred = jQuery.Deferred(), self.queue = [], self.responses = [], 
        self.numToProcess = 0, self.running = !1, self.init(initialFunctions || []), self.start(), 
        self;
    }
    function NamedAjaxQueue(initialFunctions) {
        var self = this;
        return self.names = {}, AjaxQueue.call(this, initialFunctions), self;
    }
    return AjaxQueue.prototype.init = function(initialFunctions) {
        var self = this;
        initialFunctions.forEach(function(fn) {
            self.add(fn);
        });
    }, AjaxQueue.prototype.add = function(fn) {
        var self = this, index = this.queue.length;
        this.numToProcess += 1, this.queue.push(function() {
            var fnIndex = index, xhr = fn();
            xhr.done(function(response) {
                self.deferred.notify({
                    curr: fnIndex,
                    total: self.numToProcess,
                    response: response
                });
            }), xhr.always(function(response) {
                self.responses.push(response), self.queue.length ? self.queue.shift()() : self.stop();
            });
        });
    }, AjaxQueue.prototype.start = function() {
        this.queue.length && (this.running = !0, this.queue.shift()());
    }, AjaxQueue.prototype.stop = function(causeFail, msg) {
        return this.running = !1, this.queue = [], causeFail ? this.deferred.reject(msg) : this.deferred.resolve(this.responses), 
        this.numToProcess = 0, this.deferred = jQuery.Deferred(), this;
    }, AjaxQueue.prototype.done = function(fn) {
        return this.deferred.done(fn);
    }, AjaxQueue.prototype.fail = function(fn) {
        return this.deferred.fail(fn);
    }, AjaxQueue.prototype.always = function(fn) {
        return this.deferred.always(fn);
    }, AjaxQueue.prototype.progress = function(fn) {
        return this.deferred.progress(fn);
    }, AjaxQueue.create = function(initialFunctions) {
        return new AjaxQueue(initialFunctions).deferred;
    }, NamedAjaxQueue.prototype = new AjaxQueue(), NamedAjaxQueue.prototype.constructor = NamedAjaxQueue, 
    NamedAjaxQueue.prototype.add = function(obj) {
        if (!obj.hasOwnProperty("name") || !obj.hasOwnProperty("fn")) throw new Error('NamedAjaxQueue.add requires an object with both "name" and "fn": ' + JSON.stringify(obj));
        this.names.hasOwnProperty(obj.name) || (this.names[obj.name] = !0, AjaxQueue.prototype.add.call(this, obj.fn));
    }, NamedAjaxQueue.prototype.clear = function() {
        this.names = {};
    }, NamedAjaxQueue.create = function(initialFunctions) {
        return new NamedAjaxQueue(initialFunctions).deferred;
    }, {
        AjaxQueue: AjaxQueue,
        NamedAjaxQueue: NamedAjaxQueue
    };
});