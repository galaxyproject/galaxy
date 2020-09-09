/*=============================================================================
TODO:
    while anon: logs saved to 'logs-null' - this will never post
        unless we manually do so at/after login
        OR prepend when userId and localStorage has 'logs-null'
    wire up _delayPost and test

=============================================================================*/
/** @class MetricsLogger
 *
 *  Object to cache, output, and post log/metric messages to the server.
 *  Meant to be attached to the Galaxy object.
 *
 *  Log from objects by either attaching logger directly:
 *      panel.logger.metric( 'user dataset deletion', panel.user.id, hda.toJSON() )
 *  or using the LoggableMixin or addLogging function:
 *      MyBackboneModel.extend( LoggableMixin ).extend({ ... })
 *      addLogging( MyBackboneModel, 'my-backbone-model' )
 *
 *  Log from templates by calling directly from Galaxy object:
 *      Galaxy.logger.metric( 'template loaded', { ownedByUser : true });
 *
 *  If you attempt to log an un-serializable object (circular reference, window, etc.),
 *  that entry will not be cached (or sent). If you set consoleLevel and consoleLogger
 *  appropriately, a warning will be shown when this happens:
 *      > panel.metric( 'something weird with window', { window : window })
 *      !'Metrics logger could not stringify logArguments: ...'
 */
import jQuery from "jquery";

function MetricsLogger(options) {
    options = options || {};
    var self = this;

    ///** get the current user's id from bootstrapped data or options */
    self.userId = window.bootstrapped && window.bootstrapped.user ? window.bootstrapped.user.id : null;
    self.userId = self.userId || options.userId || null;

    /** the (optional) console to emit logs to */
    self.consoleLogger = options.consoleLogger || null;

    self._init(options);
    return self;
}

//----------------------------------------------------------------------------- defaults and constants
// see: python std lib, logging
MetricsLogger.ALL = 0;
MetricsLogger.LOG = 0;
MetricsLogger.DEBUG = 10;
MetricsLogger.INFO = 20;
MetricsLogger.WARN = 30;
MetricsLogger.ERROR = 40;
// metrics levels here?
//MetricsLogger.MinorEvent  = 45;
//MetricsLogger.MajorEvent  = 50;
MetricsLogger.METRIC = 50;
MetricsLogger.NONE = 100;

/** default options - override these through the constructor */
MetricsLogger.defaultOptions = {
    /** if an incoming message has a level >= this, it will be cached - can also be a string (e.g. 'debug') */
    logLevel: MetricsLogger.NONE,
    /** if an incoming message has a level >= this, it will be output to the console */
    consoleLevel: MetricsLogger.NONE,
    /** the default 'namespace' or label associated with an incoming message (if none is passed) */
    defaultNamespace: "Galaxy",
    /** the namespaces output to the console (all namespaces will be output if this is falsy)
     *  note: applies only to the console (not the event/metrics log/cache)
     */
    consoleNamespaceWhitelist: null,
    /** Force all messages into simple strings. */
    consoleFlattenMessages: false,
    /** the prefix attached to client-side logs to distinguish them in the metrics db */
    clientPrefix: "client.",

    /** the maximum number of messages the cache should hold; if exceeded older messages are removed first */
    maxCacheSize: 3000,
    /** the number of messages accumulate before posting to the server; should be <= maxCacheSize */
    postSize: 1000,
    /** T/F whether to add a timestamp to incoming cached messages */
    addTime: true,
    /** string to prefix to userid for cache web storage */
    cacheKeyPrefix: "logs-",

    /** the relative url to post messages to */
    postUrl: "/api/metrics",
    /** delay before trying post again after two failures */
    delayPostInMs: 1000 * 60 * 10,

    /** an (optional) function that should return an object; used to send additional data with the metrics */
    getPingData: undefined,
    /** an (optional) function that will handle the servers response after successfully posting messages */
    onServerResponse: undefined,
};

//----------------------------------------------------------------------------- set up
/** initialize the logger with options, set up instance vars and cache, and add onpageunload to window */
MetricsLogger.prototype._init = function _init(options) {
    var self = this;
    self.options = {};
    for (var k in MetricsLogger.defaultOptions) {
        if (Object.prototype.hasOwnProperty.call(MetricsLogger.defaultOptions, k)) {
            self.options[k] = Object.prototype.hasOwnProperty.call(options, k)
                ? options[k]
                : MetricsLogger.defaultOptions[k];
        }
    }
    self.options.logLevel = self._parseLevel(self.options.logLevel);
    self.options.consoleLevel = self._parseLevel(self.options.consoleLevel);
    //self._emitToConsole( 'debug', 'MetricsLogger', 'MetricsLogger.options:', self.options );

    /** is the logger currently sending? */
    self._sending = false;
    /** the setTimeout id if the logger POST has failed more than once */
    self._waiting = null;
    /** the current number of entries to send in a POST */
    self._postSize = self.options.postSize;

    self._initCache();

    return self;
};

/** initialize the cache */
MetricsLogger.prototype._initCache = function _initCache() {
    try {
        this.cache = new LoggingCache({
            maxSize: this.options.maxCacheSize,
            key: this.options.cacheKeyPrefix + this.userId,
        });
    } catch (err) {
        this._emitToConsole("warn", "MetricsLogger", ["Could not intitialize logging cache:", err]);
        this.options.logLevel = MetricsLogger.NONE;
    }
};

/** return the numeric log level if level in 'none, debug, log, info, warn, error' */
MetricsLogger.prototype._parseLevel = function _parseLevel(level) {
    var type = typeof level;
    if (type === "number") {
        return level;
    }
    if (type === "string") {
        var upper = level.toUpperCase();
        if (Object.prototype.hasOwnProperty.call(MetricsLogger, upper)) {
            return MetricsLogger[upper];
        }
    }
    throw new Error(`Unknown log level: ${level}`);
};

//----------------------------------------------------------------------------- main entry point
/** record a log/message's arguments to the cache and/or the console based on level and namespace */
MetricsLogger.prototype.emit = function emit(level, namespace, logArguments) {
    //this._emitToConsole( 'debug', 'MetricsLogger', [ 'emit:', level, namespace, logArguments ]);
    var self = this;
    namespace = namespace || self.options.defaultNamespace;
    if (!level || !logArguments) {
        return self;
    }
    // add to cache if proper level
    //TODO: respect do not track?
    //if( !navigator.doNotTrack && level >= self.options.logLevel ){
    level = self._parseLevel(level);
    if (level >= self.options.logLevel) {
        self._addToCache(level, namespace, logArguments);
    }
    // also emit to consoleLogger if proper level for that
    if (self.consoleLogger && level >= self.options.consoleLevel) {
        self._emitToConsole(level, namespace, logArguments);
    }
    return self;
};

//----------------------------------------------------------------------------- cache
/** add a message to the cache and if messages.length is high enough post them to the server */
MetricsLogger.prototype._addToCache = function _addToCache(level, namespace, logArguments) {
    this._emitToConsole("debug", "MetricsLogger", [
        "_addToCache:",
        arguments,
        this.options.addTime,
        this.cache.length(),
    ]);
    //this._emitToConsole( 'debug', 'MetricsLogger', [ '\t logArguments:', logArguments ]);
    var self = this;
    // try add to the cache and if we've got _postSize number of entries, attempt to post them to the server
    try {
        var newLength = self.cache.add(self._buildEntry(level, namespace, logArguments));
        if (newLength >= self._postSize) {
            self._postCache();
        }
        // discard entry if an error occurs, but warn if level set to do so
    } catch (err) {
        self._emitToConsole("warn", "MetricsLogger", [
            "Metrics logger could not stringify logArguments:",
            namespace,
            logArguments,
        ]);
        self._emitToConsole("error", "MetricsLogger", [err]);
    }
    return self;
};

/** build a log cache entry object from the given level, namespace, and arguments (optionally adding timestamp */
MetricsLogger.prototype._buildEntry = function _buildEntry(level, namespace, logArguments) {
    this._emitToConsole("debug", "MetricsLogger", ["_buildEntry:", arguments]);
    var entry = {
        level: level,
        namespace: this.options.clientPrefix + namespace,
        args: logArguments,
    };
    if (this.options.addTime) {
        entry.time = new Date().toISOString();
    }
    return entry;
};

/** post _postSize messages from the cache to the server, removing them if successful
 *      if the post fails, wait until maxCacheSize is accumulated instead and try again then
 *      in addition to the messages from the cache ('metrics'), any info from getPingData (if set) will be sent
 *      onServerResponse will be called (if set) with any response from the server
 */
MetricsLogger.prototype._postCache = function _postCache(options) {
    options = options || {};
    this._emitToConsole("info", "MetricsLogger", ["_postCache", options, this._postSize]);

    // short circuit if we're already sending
    if (!this.options.postUrl || this._sending) {
        return jQuery.when({});
    }

    var self = this;
    var postSize = options.count || self._postSize;

    var // do not splice - remove after *successful* post
        entries = self.cache.get(postSize);

    var entriesLength = entries.length;

    var // use the optional getPingData to add any extra info we may want to send
        postData = typeof self.options.getPingData === "function" ? self.options.getPingData() : {};

    //console.debug( postSize, entriesLength );

    // add the metrics and send
    postData.metrics = JSON.stringify(entries);
    //console.debug( postData.metrics );
    self._sending = true;
    return jQuery
        .post(self.options.postUrl, postData)
        .always(() => {
            self._sending = false;
        })
        .fail((xhr, status, message) => {
            // if we failed the previous time, set the next post target to the max num of entries
            self._postSize = self.options.maxCacheSize;
            //TODO:??
            // log this failure to explain any gap in metrics
            self.emit("error", "MetricsLogger", [
                "_postCache error:",
                xhr.readyState,
                xhr.status,
                xhr.responseJSON || xhr.responseText,
            ]);
            //TODO: still doesn't solve the problem that when cache == max, post will be tried on every emit
            //TODO: see _delayPost
        })
        .done((response) => {
            if (typeof self.options.onServerResponse === "function") {
                self.options.onServerResponse(response);
            }
            // only remove if post successful
            self.cache.remove(entriesLength);
            //console.debug( 'removed entries:', entriesLength, 'size now:', self.cache.length() );
            // if we succeeded, reset the post target to the normal num of entries
            self._postSize = self.options.postSize;
        });
    // return the xhr promise
};

/** set _waiting to true and, after delayPostInMs, set it back to false */
MetricsLogger.prototype._delayPost = function _delayPost() {
    //TODO: this won't work between pages
    var self = this;
    self._waiting = window.setTimeout(() => {
        self._waiting = null;
    }, self.options.delayPostInMs);
};

function usefulToString(arg) {
    var asStr = String(arg);
    if (asStr == "[object Object]") {
        try {
            asStr = JSON.stringify(arg);
        } catch (e) {
            // If arg has cyclic reference, return String
            // otherwise rendering stops and we have incomplete page
            console.error(e);
            return String(arg);
        }
    }
    return asStr;
}

//----------------------------------------------------------------------------- console
/** output message to console based on level and consoleLogger type */
MetricsLogger.prototype._emitToConsole = function _emitToConsole(level, namespace, logArguments) {
    //console.debug( '_emitToConsole:', level, namespace, logArguments );
    var self = this;

    var whitelist = self.options.consoleNamespaceWhitelist;
    if (!self.consoleLogger) {
        return self;
    }
    // if a whitelist for namespaces is set, bail if this namespace is not in the list
    if (whitelist && whitelist.indexOf(namespace) === -1) {
        return self;
    }

    var args = Array.prototype.slice.call(logArguments, 0);
    args.unshift(namespace);
    if (self.options.consoleFlattenMessages) {
        args = [args.map(usefulToString).join(" ")];
    }
    //TODO: script location and/or source maps?
    //TODO: branch on navigator.userAgent == AIIEEE - it only has log
    if (level >= MetricsLogger.METRIC && typeof self.consoleLogger.info === "function") {
        return self.consoleLogger.info.apply(self.consoleLogger, args);
    } else if (level >= MetricsLogger.ERROR && typeof self.consoleLogger.error === "function") {
        return self.consoleLogger.error.apply(self.consoleLogger, args);
    } else if (level >= MetricsLogger.WARN && typeof self.consoleLogger.warn === "function") {
        self.consoleLogger.warn.apply(self.consoleLogger, args);
    } else if (level >= MetricsLogger.INFO && typeof self.consoleLogger.info === "function") {
        self.consoleLogger.info.apply(self.consoleLogger, args);
    } else if (level >= MetricsLogger.DEBUG && typeof self.consoleLogger.debug === "function") {
        self.consoleLogger.debug.apply(self.consoleLogger, args);
    } else if (typeof self.consoleLogger.log === "function") {
        self.consoleLogger.log.apply(self.consoleLogger, args);
    }
    return self;
};

//----------------------------------------------------------------------------- shortcuts
// generic functions when logging from non-namespaced object (e.g. templates)
/** log to default namespace */
MetricsLogger.prototype.log = function log() {
    this.emit(1, this.options.defaultNamespace, Array.prototype.slice.call(arguments, 0));
};

/** debug to default namespace */
MetricsLogger.prototype.debug = function debug() {
    this.emit(MetricsLogger.DEBUG, this.options.defaultNamespace, Array.prototype.slice.call(arguments, 0));
};

/** info to default namespace */
MetricsLogger.prototype.info = function info() {
    this.emit(MetricsLogger.INFO, this.options.defaultNamespace, Array.prototype.slice.call(arguments, 0));
};

/** warn to default namespace */
MetricsLogger.prototype.warn = function warn() {
    this.emit(MetricsLogger.WARN, this.options.defaultNamespace, Array.prototype.slice.call(arguments, 0));
};

/** error to default namespace */
MetricsLogger.prototype.error = function error() {
    this.emit(MetricsLogger.ERROR, this.options.defaultNamespace, Array.prototype.slice.call(arguments, 0));
};

/** metric to default namespace */
MetricsLogger.prototype.metric = function metric() {
    this.emit(MetricsLogger.METRIC, this.options.defaultNamespace, Array.prototype.slice.call(arguments, 0));
};

/* ============================================================================
TODO:
    need a performance pass - the JSON un/parsing is a bit much

============================================================================ */
/** @class LoggingCache
 *  Simple implementation of cache wrapping an array.
 *
 *  Formats an entry before it's cached and only keeps options.maxSize number
 *  of entries. Older entries are deleted first.
 */
function LoggingCache(options) {
    var self = this;
    return self._init(options || {});
}

/** default options */
LoggingCache.defaultOptions = {
    /** maximum number of entries to keep before discarding oldest */
    maxSize: 5000,
};

/** initialize with options */
LoggingCache.prototype._init = function _init(options) {
    if (!this._hasStorage()) {
        //TODO: fall back to local storage
        throw new Error("LoggingCache needs localStorage");
    }
    if (!options.key) {
        throw new Error("LoggingCache needs key for localStorage");
    }
    this.key = options.key;
    this._initStorage();

    this.maxSize = options.maxSize || LoggingCache.defaultOptions.maxSize;
    return this;
};

/** tests for localStorage fns */
LoggingCache.prototype._hasStorage = function _hasStorage() {
    //TODO: modernizr
    var test = "test";
    try {
        localStorage.setItem(test, test);
        localStorage.removeItem(test);
        return true;
    } catch (e) {
        return false;
    }
};

/** if no localStorage set for key, initialize to empty array */
LoggingCache.prototype._initStorage = function _initStorage() {
    if (localStorage.getItem(this.key) === null) {
        return this.empty();
    }
    return this;
};

/** add an entry to the cache, removing the oldest beforehand if size >= maxSize */
LoggingCache.prototype.add = function add(entry) {
    var self = this;
    var _cache = self._fetchAndParse();
    var overage = _cache.length + 1 - self.maxSize;
    if (overage > 0) {
        _cache.splice(0, overage);
    }
    _cache.push(entry);
    self._unparseAndStore(_cache);
    return _cache.length;
};

/** get the entries from localStorage and parse them */
LoggingCache.prototype._fetchAndParse = function _fetchAndParse() {
    var self = this;
    return JSON.parse(localStorage.getItem(self.key));
};

/** stringify the entries and put them in localStorage */
LoggingCache.prototype._unparseAndStore = function _unparseAndStore(entries) {
    var self = this;
    return localStorage.setItem(self.key, JSON.stringify(entries));
};

///** process the entry before caching */
//LoggingCache.prototype._preprocessEntry = function _preprocessEntry( entry ){
//    return JSON.stringify( entry );
//};

/** return the length --- oh, getters where are you? */
LoggingCache.prototype.length = function length() {
    return this._fetchAndParse().length;
};

/** get count number of entries starting with the oldest */
LoggingCache.prototype.get = function get(count) {
    return this._fetchAndParse().slice(0, count);
};

/** remove count number of entries starting with the oldest */
LoggingCache.prototype.remove = function remove(count) {
    var _cache = this._fetchAndParse();
    var removed = _cache.splice(0, count);
    this._unparseAndStore(_cache);
    return removed;
};

/** empty/clear the entire cache */
LoggingCache.prototype.empty = function empty() {
    localStorage.setItem(this.key, "[]");
    return this;
};

/** stringify count number of entries (but do not remove) */
LoggingCache.prototype.stringify = function stringify(count) {
    return JSON.stringify(this.get(count));
};

/** outputs entire cache to console */
LoggingCache.prototype.print = function print() {
    // popup? (really, carl? a popup?) - easier to copy/paste
    console.log(JSON.stringify(this._fetchAndParse(), null, "  "));
};

//=============================================================================
export default {
    MetricsLogger: MetricsLogger,
    LoggingCache: LoggingCache,
};
