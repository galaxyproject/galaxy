/*
 * jStore - Persistent Client-Side Storage
 *
 * Copyright (c) 2009 Eric Garside (http://eric.garside.name)
 * 
 * Dual licensed under:
 * 	MIT: http://www.opensource.org/licenses/mit-license.php
 *	GPLv3: http://www.opensource.org/licenses/gpl-3.0.html
 *//**
 * Javascript Class Framework
 * 
 * Copyright (c) 2008 John Resig (http://ejohn.org/blog/simple-javascript-inheritance/)
 * Inspired by base2 and Prototype
 */
(function(){
  var initializing = false, fnTest = /xyz/.test(function(){xyz;}) ? /\b_super\b/ : /.*/;

  // The base Class implementation (does nothing)
  this.Class = function(){};
 
  // Create a new Class that inherits from this class
  Class.extend = function(prop) {
    var _super = this.prototype;
   
    // Instantiate a base class (but only create the instance,
    // don't run the init constructor)
    initializing = true;
    var prototype = new this();
    initializing = false;
   
    // Copy the properties over onto the new prototype
    for (var name in prop) {
      // Check if we're overwriting an existing function
      prototype[name] = typeof prop[name] == "function" &&
        typeof _super[name] == "function" && fnTest.test(prop[name]) ?
        (function(name, fn){
          return function() {
            var tmp = this._super;
           
            // Add a new ._super() method that is the same method
            // but on the super-class
            this._super = _super[name];
           
            // The method only need to be bound temporarily, so we
            // remove it when we're done executing
            var ret = fn.apply(this, arguments);       
            this._super = tmp;
           
            return ret;
          };
        })(name, prop[name]) :
        prop[name];
    }
   
    // The dummy class constructor
    function Class() {
      // All construction is actually done in the init method
      if ( !initializing && this.init )
        this.init.apply(this, arguments);
    }
   
    // Populate our constructed prototype object
    Class.prototype = prototype;
   
    // Enforce the constructor to be what we expect
    Class.constructor = Class;

    // And make this class extendable
    Class.extend = arguments.callee;
   
    return Class;
  };
})();
/*
 * jStore Delegate Framework
 * Copyright (c) 2009 Eric Garside (http://eric.garside.name)
 */
(function($){
	
	this.jStoreDelegate = Class.extend({
		init: function(parent){
			// The Object this delgate operates for
			this.parent = parent;
			// Container for callbacks to dispatch.
			// eventType => [ callback, callback, ... ]
			this.callbacks = {};
		},
		bind: function(event, callback){
			if ( !$.isFunction(callback) ) return this;
			if ( !this.callbacks[ event ] ) this.callbacks[ event ] = [];
			
			this.callbacks[ event ].push(callback);
			
			return this;
		},
		trigger: function(){
			var parent = this.parent,
				args = [].slice.call(arguments),
				event = args.shift(),
				handlers = this.callbacks[ event ];

			if ( !handlers ) return false;
			
			$.each(handlers, function(){ this.apply(parent, args) });
			return this;
		}
	});
	
})(jQuery);/**
 * jStore-jQuery Interface
 * Copyright (c) 2009 Eric Garside (http://eric.garside.name)
 */
(function($){
	
	// Setup the jStore namespace in jQuery for options storage
	$.jStore = {};
	
	// Seed the options in
	$.extend($.jStore, {
		EngineOrder: [],
		// Engines should put their availability tests within jStore.Availability
		Availability: {},
		// Defined engines should enter themselves into the jStore.Engines
		Engines: {},
		// Instanciated engines should exist within jStore.Instances
		Instances: {},
		// The current engine to use for storage
		CurrentEngine: null,
		// Provide global settings for overwriting
		defaults: {
			project: null,
			engine: null,
			autoload: true,
			flash: 'jStore.Flash.html'
		},
		// Boolean for ready state handling
		isReady: false,
		// Boolean for flash ready state handling
		isFlashReady: false,
		// An event delegate
		delegate: new jStoreDelegate($.jStore)
			.bind('jStore-ready', function(engine){
				$.jStore.isReady = true;
				if ($.jStore.defaults.autoload) engine.connect();
			})
			.bind('flash-ready', function(){
				$.jStore.isFlashReady = true;
			})			
	});
	
	// Enable ready callback for jStore
	$.jStore.ready = function(callback){
		if ($.jStore.isReady) callback.apply($.jStore, [$.jStore.CurrentEngine]);
		else $.jStore.delegate.bind('jStore-ready', callback);
	}
	
	// Enable failure callback registration for jStore
	$.jStore.fail = function(callback){
		$.jStore.delegate.bind('jStore-failure', callback);
	}
	
	// Enable ready callback for Flash
	$.jStore.flashReady = function(callback){
		if ($.jStore.isFlashReady) callback.apply($.jStore, [$.jStore.CurrentEngine]);
		else $.jStore.delegate.bind('flash-ready', callback);
	}
	
	// Enable and test an engine
	$.jStore.use = function(engine, project, identifier){
		project = project || $.jStore.defaults.project || location.hostname.replace(/\./g, '-') || 'unknown';
		
		var e = $.jStore.Engines[engine.toLowerCase()] || null,
			name = (identifier ? identifier + '.' : '') + project + '.' + engine;
		
		if ( !e ) throw 'JSTORE_ENGINE_UNDEFINED';

		// Instanciate the engine
		e = new e(project, name);
		
		// Prevent against naming conflicts
		if ($.jStore.Instances[name]) throw 'JSTORE_JRI_CONFLICT';
		
		// Test the engine
		if (e.isAvailable()){
			$.jStore.Instances[name] = e;	// The Easy Way
			if (!$.jStore.CurrentEngine){
				$.jStore.CurrentEngine = e;
			}
			$.jStore.delegate.trigger('jStore-ready', e);
		} else {
			if (!e.autoload)				// Not available
				throw 'JSTORE_ENGINE_UNAVILABLE';
			else { 							// The hard way
				e.included(function(){
					if (this.isAvailable()) { // Worked out
						$.jStore.Instances[name] = this;
						// If there is no current engine, use this one
						if (!$.jStore.CurrentEngine){
							$.jStore.CurrentEngine = this;
						} 
						$.jStore.delegate.trigger('jStore-ready', this);
					}
					else $.jStore.delegate.trigger('jStore-failure', this);
				}).include();
			}
		}
	}
	
	// Set the current storage engine
	$.jStore.setCurrentEngine = function(name){
		if (!$.jStore.Instances.length )				// If no instances exist, attempt to load one
			return $.jStore.FindEngine();
			
		if (!name && $.jStore.Instances.length >= 1) { // If no name is specified, use the first engine
			$.jStore.delegate.trigger('jStore-ready', $.jStore.Instances[0]);
			return $.jStore.CurrentEngine = $.jStore.Instances[0];
		}
			
		if (name && $.jStore.Instances[name]) { // If a name is specified and exists, use it
			$.jStore.delegate.trigger('jStore-ready', $.jStore.Instances[name]);
			return $.jStore.CurrentEngine = $.jStore.Instances[name];
		}
		
		throw 'JSTORE_JRI_NO_MATCH';
	}
	
	// Test all possible engines for straightforward useability
	$.jStore.FindEngine = function(){
		$.each($.jStore.EngineOrder, function(k){
			if ($.jStore.Availability[this]()){ // Find the first, easiest option and use it.
				$.jStore.use(this, $.jStore.defaults.project, 'default');
				return false;
			}
		})
	}
	
	// Provide a simple interface for storing/getting values
	$.jStore.store = function(key, value){
		if (!$.jStore.CurrentEngine) return false;
		
		if ( !value ) // Executing a get command
			return $.jStore.CurrentEngine.get(key);
		// Executing a set command
			return $.jStore.CurrentEngine.set(key, value);
	}
	// Provide a simple interface for storing/getting values
	$.jStore.remove = function(key){
		if (!$.jStore.CurrentEngine) return false;
		
		return $.jStore.CurrentEngine.rem(key);
	}
	
	// Provide a chainable interface for storing values/getting a value at the end of a chain
	$.fn.store = function(key, value){
		if (!$.jStore.CurrentEngine) return this;
		
		var result = $.jStore.store(key, value);
		
		return !value ? result : this;
	}
	
	// Provide a chainable interface for removing values
	$.fn.removeStore = function(key){
		$.jStore.remove(key);
		
		return this;
	}
	
	// Provide a way for users to call for auto-loading
	$.jStore.load = function(){
		if ($.jStore.defaults.engine)
			return $.jStore.use($.jStore.defaults.engine, $.jStore.defaults.project, 'default');
			
		// Attempt to find a valid engine, and catch any exceptions if we can't
		try {
			$.jStore.FindEngine();
		} catch (e) {}
	}
	
})(jQuery);
/**
 * jStore Engine Core
 * Copyright (c) 2009 Eric Garside (http://eric.garside.name)
 */
(function($){
	
	this.StorageEngine = Class.extend({
		init: function(project, name){
			// Configure the project name
			this.project = project;
			// The JRI name given by the manager
			this.jri = name;
			// Cache the data so we can work synchronously
			this.data = {};
			// The maximum limit of the storage engine
			this.limit = -1;
			// Third party script includes
			this.includes = [];
			// Create an event delegate for users to subscribe to event triggers
			this.delegate = new jStoreDelegate(this)
				.bind('engine-ready', function(){
					this.isReady = true;
				})
				.bind('engine-included', function(){
					this.hasIncluded = true;
				});
			// If enabled, the manager will check availability, then run include(), then check again
			this.autoload = false; // This should be changed by the engines, if they have required includes
			// When set, we're ready to transact data
			this.isReady = false;
			// When the includer is finished, it will set this to true
			this.hasIncluded = false;
		},
		// Performs all necessary script includes
		include: function(){
			var self = this,
				total = this.includes.length,
				count = 0;
				
			$.each(this.includes, function(){
				$.ajax({type: 'get', url: this, dataType: 'script', cache: true, 
					success: function(){
						count++;
						if (count == total)	self.delegate.trigger('engine-included');
					}
				})
			});
		},
		// This should be overloaded with an actual functionality presence check
		isAvailable: function(){
			return false;
		},
		/** Event Subscription Shortcuts **/
		ready: function(callback){
			if (this.isReady) callback.apply(this);
			else this.delegate.bind('engine-ready', callback);
			return this;
		},
		included: function(callback){
			if (this.hasIncluded) callback.apply(this);
			else this.delegate.bind('engine-included', callback);
			return this;
		},
		/** Cache Data Access **/
		get: function(key){
			return this.data[key] || null;
		},
		set: function(key, value){
			this.data[key] = value;
			return value;
		},
		rem: function(key){
			var beforeDelete = this.data[key];
			this.data[key] = null;
			return beforeDelete;			
		}
	});
	
})(jQuery);
/*
 * jStore DOM Storage Engine
 * Copyright (c) 2009 Eric Garside (http://eric.garside.name)
 */
(function($){
	
	// Set up a static test function for this instance
	var sessionAvailability = $.jStore.Availability.session = function(){
			return !!window.sessionStorage;
		},
		localAvailability = $.jStore.Availability.local = function(){
			return !!(window.localStorage || window.globalStorage);
		};

	this.jStoreDom = StorageEngine.extend({
		init: function(project, name){			
			// Call the parental init object
			this._super(project, name);
			
			// The type of storage engine
			this.type = 'DOM';
			
			// Set the Database limit
			this.limit = 5 * 1024 * 1024;
		},
		connect: function(){
			// Fire our delegate to indicate we're ready for data transactions
			this.delegate.trigger('engine-ready');
		},
		get: function(key){
			var out = this.db.getItem(key);
			// Gecko's getItem returns {value: 'the value'}, WebKit returns 'the value'
			return out && out.value ? out.value : out
		},
		set: function(key, value){
			this.db.setItem(key,value); 
			return value;
		},
		rem: function(key){
			var out = this.get(key); 
			this.db.removeItem(key); 
			return out
		}
	})
	
	this.jStoreLocal = jStoreDom.extend({
		connect: function(){
			// Gecko uses a non-standard globalStorage[ www.example.com ] DOM access object for persistant storage.
			this.db = !window.globalStorage ? window.localStorage : window.globalStorage[location.hostname];
			this._super();
		},
		isAvailable: localAvailability
	})
	
	this.jStoreSession = jStoreDom.extend({
		connect: function(){
			this.db = sessionStorage;
			this._super();
		},
		isAvailable: sessionAvailability
	})

	$.jStore.Engines.local = jStoreLocal;
	$.jStore.Engines.session = jStoreSession;

	// Store the ordering preference
	$.jStore.EngineOrder[ 1 ] = 'local';

})(jQuery);
/*
 * jStore Flash Storage Engine
 * Copyright (c) 2009 Eric Garside (http://eric.garside.name)
 * jStore.swf Copyright (c) 2008 Daniel Bulli (http://www.nuff-respec.com)
 */
(function($){
	
	// Set up a static test function for this instance
	var avilability = $.jStore.Availability.flash = function(){
		return !!($.jStore.hasFlash('8.0.0'));
	}
	
	this.jStoreFlash = StorageEngine.extend({
		init: function(project, name){			
			// Call the parental init object
			this._super(project, name);
			
			// The type of storage engine
			this.type = 'Flash';
			
			// Bind our flashReady function to the jStore Delegate
			var self = this;
			$.jStore.flashReady(function(){ self.flashReady() });
		},
		connect: function(){
			var name = 'jstore-flash-embed-' + this.project;
			
			// To make Flash Storage work on IE, we have to load up an iFrame
			// which contains an HTML page that embeds the object using an
			// object tag wrapping an embed tag. Of course, this is unnecessary for
			// all browsers except for IE, which, to my knowledge, is the only browser
			// in existance where you need to complicate your code to fix bugs. Goddamnit. :(
			$(document.body)
				.append('<iframe style="height:1px;width:1px;position:absolute;left:0;top:0;margin-left:-100px;" ' + 
					'id="jStoreFlashFrame" src="' +$.jStore.defaults.flash + '"></iframe>');
		},
		flashReady: function(e){
			var iFrame = $('#jStoreFlashFrame')[0];
			
			// IE
			if (iFrame.Document && $.isFunction(iFrame.Document['jStoreFlash'].f_get_cookie)) this.db = iFrame.Document['jStoreFlash'];
			// Safari && Firefox
			else if (iFrame.contentWindow && iFrame.contentWindow.document){
				var doc = iFrame.contentWindow.document;
				// Safari
				if ($.isFunction($('object', $(doc))[0].f_get_cookie)) this.db = $('object', $(doc))[0];
				// Firefox
				else if ($.isFunction($('embed', $(doc))[0].f_get_cookie)) this.db = $('embed', $(doc))[0];
			}

			// We're ready to process data
			if (this.db) this.delegate.trigger('engine-ready');
		},
		isAvailable: avilability,
		get: function(key){
			var out = this.db.f_get_cookie(key);
			return out == 'null' ? null : out;
		},
		set: function(key, value){
			this.db.f_set_cookie(key, value);
			return value;
		},
		rem: function(key){
			var beforeDelete = this.get(key);
			this.db.f_delete_cookie(key);
			return beforeDelete;
		}
	})

	$.jStore.Engines.flash = jStoreFlash;

	// Store the ordering preference
	$.jStore.EngineOrder[ 2 ] = 'flash';

	/**
 	 * Flash Detection functions copied from the jQuery Flash Plugin
 	 * Copyright (c) 2006 Luke Lutman (http://jquery.lukelutman.com/plugins/flash)
 	 * Dual licensed under the MIT and GPL licenses.
 	 * 	http://www.opensource.org/licenses/mit-license.php
 	 * 	http://www.opensource.org/licenses/gpl-license.php 
 	 */
	$.jStore.hasFlash = function(version){
		var pv = $.jStore.flashVersion().match(/\d+/g),
			rv = version.match(/\d+/g);

		for(var i = 0; i < 3; i++) {
			pv[i] = parseInt(pv[i] || 0);
			rv[i] = parseInt(rv[i] || 0);
			// player is less than required
			if(pv[i] < rv[i]) return false;
			// player is greater than required
			if(pv[i] > rv[i]) return true;
		}
		// major version, minor version and revision match exactly
		return true;
	}
	
	$.jStore.flashVersion = function(){
		// ie
		try {
			try {
				// avoid fp6 minor version lookup issues
				// see: http://blog.deconcept.com/2006/01/11/getvariable-setvariable-crash-internet-explorer-flash-6/
				var axo = new ActiveXObject('ShockwaveFlash.ShockwaveFlash.6');
				try { axo.AllowScriptAccess = 'always';	} 
				catch(e) { return '6,0,0'; }				
			} catch(e) {}
				return new ActiveXObject('ShockwaveFlash.ShockwaveFlash').GetVariable('$version').replace(/\D+/g, ',').match(/^,?(.+),?$/)[1];
		// other browsers
		} catch(e) {
			try {
				if(navigator.mimeTypes["application/x-shockwave-flash"].enabledPlugin){
					return (navigator.plugins["Shockwave Flash 2.0"] || navigator.plugins["Shockwave Flash"]).description.replace(/\D+/g, ",").match(/^,?(.+),?$/)[1];
				}
			} catch(e) {}		
		}
		return '0,0,0';
	}

})(jQuery);

// Callback fired when ExternalInterface is established
function flash_ready(){
	$.jStore.delegate.trigger('flash-ready');
}
/*
 * jStore Google Gears Storage Engine
 * Copyright (c) 2009 Eric Garside (http://eric.garside.name)
 */
(function($){
	
	// Set up a static test function for this instance
	var avilability = $.jStore.Availability.gears = function(){
		return !!(window.google && window.google.gears)
	}
	
	this.jStoreGears = StorageEngine.extend({
		init: function(project, name){			
			// Call the parental init object
			this._super(project, name);
			
			// The type of storage engine
			this.type = 'Google Gears';
			
			// Add required third-party scripts
			this.includes.push('http://code.google.com/apis/gears/gears_init.js');
			
			// Allow Autoloading on fail
			this.autoload = true;
		},
		connect: function(){
			// Create our database connection
			var db = this.db = google.gears.factory.create('beta.database');
			db.open( 'jstore-' + this.project );
			db.execute( 'CREATE TABLE IF NOT EXISTS jstore (k TEXT UNIQUE NOT NULL PRIMARY KEY, v TEXT NOT NULL)' );
			
			// Cache the data from the table
			this.updateCache();
		},
		updateCache: function(){
			// Read the database into our cache object
			var result = this.db.execute( 'SELECT k,v FROM jstore' );
			while (result.isValidRow()){
				this.data[result.field(0)] = result.field(1);
				result.next();
			} result.close();
			
			// Fire our delegate to indicate we're ready for data transactions
			this.delegate.trigger('engine-ready');
		},
		isAvailable: avilability,
		set: function(key, value){
			// Update the database
			var db = this.db;
			db.execute( 'BEGIN' );
			db.execute( 'INSERT OR REPLACE INTO jstore(k, v) VALUES (?, ?)', [key,value] );
			db.execute( 'COMMIT' );
			return this._super(key, value);
		},
		rem: function(key){
			// Update the database
			var db = this.db;
			db.execute( 'BEGIN' );
			db.execute( 'DELETE FROM jstore WHERE k = ?', [key] );
			db.execute( 'COMMIT' );
			return this._super(key);
		}
	})

	$.jStore.Engines.gears = jStoreGears;
	
	// Store the ordering preference
	$.jStore.EngineOrder[ 3 ] = 'gears';

})(jQuery);
/*
 * jStore HTML5 Specification Storage Engine
 * Copyright (c) 2009 Eric Garside (http://eric.garside.name)
 */
(function($){
	
	// Set up a static test function for this instance
	var avilability = $.jStore.Availability.html5 = function(){
		return !!window.openDatabase
	}
	
	this.jStoreHtml5 = StorageEngine.extend({
		init: function(project, name){			
			// Call the parental init object
			this._super(project, name);
			
			// The type of storage engine
			this.type = 'HTML5';
			
			// Set the Database limit
			this.limit = 1024 * 200;
		},
		connect: function(){
			// Create our database connection
			var db = this.db = openDatabase('jstore-' + this.project, '1.0', this.project, this.limit);
			if (!db) throw 'JSTORE_ENGINE_HTML5_NODB';
			db.transaction(function(db){
				db.executeSql( 'CREATE TABLE IF NOT EXISTS jstore (k TEXT UNIQUE NOT NULL PRIMARY KEY, v TEXT NOT NULL)' );
			});
			
			// Cache the data from the table
			this.updateCache();
		},
		updateCache: function(){
			var self = this;
			// Read the database into our cache object
			this.db.transaction(function(db){
				db.executeSql( 'SELECT k,v FROM jstore', [], function(db, result){
					var rows = result.rows, i = 0, row;
					for (; i < rows.length; ++i){
						row = rows.item(i);
						self.data[row.k] = row.v;
					}
					
					// Fire our delegate to indicate we're ready for data transactions
					self.delegate.trigger('engine-ready');
				});
			});
		},
		isAvailable: avilability,
		set: function(key, value){
			// Update the database
			this.db.transaction(function(db){
				db.executeSql( 'INSERT OR REPLACE INTO jstore(k, v) VALUES (?, ?)', [key,value]);
			});
			return this._super(key, value);
		},
		rem: function(key){
			// Update the database
			this.db.transaction(function(db){
				db.executeSql( 'DELETE FROM jstore WHERE k = ?', [key] )
			})
			return this._super(key);
		}
	})

	$.jStore.Engines.html5 = jStoreHtml5;

	// Store the ordering preference
	$.jStore.EngineOrder[ 0 ] = 'html5';

})(jQuery);
/*
 * jStore IE Storage Engine
 * Copyright (c) 2009 Eric Garside (http://eric.garside.name)
 */
(function($){
	
	// Set up a static test function for this instance
	var avilability = $.jStore.Availability.ie = function(){
		return !!window.ActiveXObject;
	}
	
	this.jStoreIE = StorageEngine.extend({
		init: function(project, name){			
			// Call the parental init object
			this._super(project, name);
			
			// The type of storage engine
			this.type = 'IE';
			
			// Allow Autoloading on fail
			this.limit = 64 * 1024;
		},
		connect: function(){
			// Create a hidden div to store attributes in
			this.db = $('<div style="display:none;behavior:url(\'#default#userData\')" id="jstore-' + this.project + '"></div>')
						.appendTo(document.body).get(0);
			// Fire our delegate to indicate we're ready for data transactions
			this.delegate.trigger('engine-ready');
		},
		isAvailable: avilability,
		get: function(key){
			this.db.load(this.project);
			return this.db.getAttribute(key);
		},
		set: function(key, value){
			this.db.setAttribute(key, value);
			this.db.save(this.project);
			return value;
		},
		rem: function(key){
			var beforeDelete = this.get(key);
			this.db.removeAttribute(key);
			this.db.save(this.project);
			return beforeDelete;
		}
	})

	$.jStore.Engines.ie = jStoreIE;
	
	// Store the ordering preference
	$.jStore.EngineOrder[ 4 ] = 'ie';

})(jQuery);
