define([],function(){function a(a){a=a||{};var b=this;return b.userId=window.bootstrapped&&window.bootstrapped.user?window.bootstrapped.user.id:null,b.userId=b.userId||a.userId||null,b.consoleLogger=a.consoleLogger||null,b._init(a),b}function b(a){var b=this;return b._init(a||{})}return a.ALL=0,a.LOG=0,a.DEBUG=10,a.INFO=20,a.WARN=30,a.ERROR=40,a.METRIC=50,a.NONE=100,a.defaultOptions={logLevel:a.NONE,consoleLevel:a.NONE,defaultNamespace:"Galaxy",consoleNamespaceWhitelist:null,clientPrefix:"client.",maxCacheSize:3e3,postSize:1e3,addTime:!0,cacheKeyPrefix:"logs-",postUrl:"/api/metrics",delayPostInMs:6e5,getPingData:void 0,onServerResponse:void 0},a.prototype._init=function(b){var c=this;c.options={};for(var d in a.defaultOptions)a.defaultOptions.hasOwnProperty(d)&&(c.options[d]=b.hasOwnProperty(d)?b[d]:a.defaultOptions[d]);return c.options.logLevel=c._parseLevel(c.options.logLevel),c.options.consoleLevel=c._parseLevel(c.options.consoleLevel),c._sending=!1,c._waiting=null,c._postSize=c.options.postSize,c._initCache(),c},a.prototype._initCache=function(){try{this.cache=new b({maxSize:this.options.maxCacheSize,key:this.options.cacheKeyPrefix+this.userId})}catch(c){this._emitToConsole("warn","MetricsLogger",["Could not intitialize logging cache:",c]),this.options.logLevel=a.NONE}},a.prototype._parseLevel=function(b){var c=typeof b;if("number"===c)return b;if("string"===c){var d=b.toUpperCase();if(a.hasOwnProperty(d))return a[d]}throw new Error("Unknown log level: "+b)},a.prototype.emit=function(a,b,c){var d=this;return b=b||d.options.defaultNamespace,a&&c?(a=d._parseLevel(a),a>=d.options.logLevel&&d._addToCache(a,b,c),d.consoleLogger&&a>=d.options.consoleLevel&&d._emitToConsole(a,b,c),d):d},a.prototype._addToCache=function(a,b,c){this._emitToConsole("debug","MetricsLogger",["_addToCache:",arguments,this.options.addTime,this.cache.length()]);var d=this;try{var e=d.cache.add(d._buildEntry(a,b,c));e>=d._postSize&&d._postCache()}catch(f){d._emitToConsole("warn","MetricsLogger",["Metrics logger could not stringify logArguments:",b,c]),d._emitToConsole("error","MetricsLogger",[f])}return d},a.prototype._buildEntry=function(a,b,c){this._emitToConsole("debug","MetricsLogger",["_buildEntry:",arguments]);var d={level:a,namespace:this.options.clientPrefix+b,args:c};return this.options.addTime&&(d.time=(new Date).toISOString()),d},a.prototype._postCache=function(a){if(a=a||{},this._emitToConsole("info","MetricsLogger",["_postCache",a,this._postSize]),!this.options.postUrl||this._sending)return jQuery.when({});var b=this,c=a.count||b._postSize,d=b.cache.get(c),e=d.length,f="function"==typeof b.options.getPingData?b.options.getPingData():{};return f.metrics=JSON.stringify(d),b._sending=!0,jQuery.post(b.options.postUrl,f).always(function(){b._sending=!1}).fail(function(a,c,d){b._postSize=b.options.maxCacheSize,b.emit("error","MetricsLogger",["_postCache error:",a.readyState,a.status,a.responseJSON||a.responseText])}).done(function(a){"function"==typeof b.options.onServerResponse&&b.options.onServerResponse(a),b.cache.remove(e),b._postSize=b.options.postSize})},a.prototype._delayPost=function(){var a=this;a._waiting=setTimeout(function(){a._waiting=null},a.options.delayPostInMs)},a.prototype._emitToConsole=function(b,c,d){var e=this,f=e.options.consoleNamespaceWhitelist;if(!e.consoleLogger)return e;if(f&&f.indexOf(c)===-1)return e;var g=Array.prototype.slice.call(d,0);return g.unshift(c),b>=a.METRIC&&"function"==typeof e.consoleLogger.info?e.consoleLogger.info.apply(e.consoleLogger,g):b>=a.ERROR&&"function"==typeof e.consoleLogger.error?e.consoleLogger.error.apply(e.consoleLogger,g):(b>=a.WARN&&"function"==typeof e.consoleLogger.warn?e.consoleLogger.warn.apply(e.consoleLogger,g):b>=a.INFO&&"function"==typeof e.consoleLogger.info?e.consoleLogger.info.apply(e.consoleLogger,g):b>=a.DEBUG&&"function"==typeof e.consoleLogger.debug?e.consoleLogger.debug.apply(e.consoleLogger,g):"function"==typeof e.consoleLogger.log&&e.consoleLogger.log.apply(e.consoleLogger,g),e)},a.prototype.log=function(){this.emit(1,this.options.defaultNamespace,Array.prototype.slice.call(arguments,0))},a.prototype.debug=function(){this.emit(a.DEBUG,this.options.defaultNamespace,Array.prototype.slice.call(arguments,0))},a.prototype.info=function(){this.emit(a.INFO,this.options.defaultNamespace,Array.prototype.slice.call(arguments,0))},a.prototype.warn=function(){this.emit(a.WARN,this.options.defaultNamespace,Array.prototype.slice.call(arguments,0))},a.prototype.error=function(){this.emit(a.ERROR,this.options.defaultNamespace,Array.prototype.slice.call(arguments,0))},a.prototype.metric=function(){this.emit(a.METRIC,this.options.defaultNamespace,Array.prototype.slice.call(arguments,0))},b.defaultOptions={maxSize:5e3},b.prototype._init=function(a){if(!this._hasStorage())throw new Error("LoggingCache needs localStorage");if(!a.key)throw new Error("LoggingCache needs key for localStorage");return this.key=a.key,this._initStorage(),this.maxSize=a.maxSize||b.defaultOptions.maxSize,this},b.prototype._hasStorage=function(){var a="test";try{return localStorage.setItem(a,a),localStorage.removeItem(a),!0}catch(b){return!1}},b.prototype._initStorage=function(){return null===localStorage.getItem(this.key)?this.empty():this},b.prototype.add=function(a){var b=this,c=b._fetchAndParse(),d=c.length+1-b.maxSize;return d>0&&c.splice(0,d),c.push(a),b._unparseAndStore(c),c.length},b.prototype._fetchAndParse=function(){var a=this;return JSON.parse(localStorage.getItem(a.key))},b.prototype._unparseAndStore=function(a){var b=this;return localStorage.setItem(b.key,JSON.stringify(a))},b.prototype.length=function(){return this._fetchAndParse().length},b.prototype.get=function(a){return this._fetchAndParse().slice(0,a)},b.prototype.remove=function(a){var b=this._fetchAndParse(),c=b.splice(0,a);return this._unparseAndStore(b),c},b.prototype.empty=function(){return localStorage.setItem(this.key,"[]"),this},b.prototype.stringify=function(a){return JSON.stringify(this.get(a))},b.prototype.print=function(){console.log(JSON.stringify(this._fetchAndParse(),null,"  "))},{MetricsLogger:a,LoggingCache:b}});
//# sourceMappingURL=../../maps/utils/metrics-logger.js.map