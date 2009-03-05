// prevent execution of jamal if included more than once
if(typeof window.jamal == "undefined") {

/* SVN FILE: $Id: jamal.js 65 2009-01-19 21:08:03Z teemow $ */
/**
 * This is the Jamal core. Heavily inspired by jQuery's architecture. 
 *
 * To quote Dave Cardwell: 
 * Built on the shoulders of giants:
 *   * John Resig      - http://jquery.com/
 *
 * jQuery is required
 *
 * Jamal :  Javascript MVC Assembly Layout <http://jamal.moagil.de/>
 * Copyright (c)    2006, Timo Derstappen <http://teemow.com/>
 *
 * Licensed under The MIT License
 * Redistributions of files must retain the above copyright notice.
 *
 * @filesource
 * @copyright        Copyright (c) 2006, Timo Derstappen
 * @link            
 * @package          jamal
 * @subpackage       jamal.core
 * @since            Jamal v 0.1
 * @version          $Revision: 65 $
 * @modifiedby       $LastChangedBy: teemow $
 * @lastmodified     $Date: 2009-01-19 22:08:03 +0100 (Mo, 19. Jan 2009) $
 * @license          http://www.opensource.org/licenses/mit-license.php The MIT License
 */

/**
 * Create a new jamal Object
 *
 * @constructor
 * @private
 * @name jamal
 * @cat core
 */
var jamal = function() {
    // If the context is global, return a new object
    if (window == this) {
        return new jamal();
    }
    
    return this.configure();
};

/**
 * Create the jamal core prototype
 *
 * @public
 * @name jamal
 * @cat core
 */
jamal.fn = jamal.prototype = {
    /* Properties */

    /**
     * The current version of jamal.
     *
     * @private
     * @property
     * @name version
     * @type String
     * @cat core
     */
    version: '0.4.1',

    /**
     * Defines the root element with the jamal configuration class. This is 
     * necessary due to performance. jQuery is a lot faster in finding classes
     * when it knows the holding element.
     *
     * @private
     * @property
     * @name root
     * @type String
     * @cat core
     */
    root: 'body',

    /**
     * Name of the current controller.
     *
     * @public
     * @property
     * @name name
     * @type String
     * @cat core
     */
    name: '',

    /**
     * Name of the current action.
     *
     * @public
     * @property
     * @name action
     * @type String
     * @cat core
     */
    action: '',

    /**
     * Current controller object.
     *
     * @public
     * @property
     * @name controller
     * @type Object
     * @cat core
     */
    current: {},

    /**
     * Map of all available models.
     *
     * @public
     * @property
     * @name m
     * @type Map
     * @cat core
     */
    m: {},

    /**
     * Map of all available views.
     *
     * @public
     * @property
     * @name v
     * @type Map
     * @cat core
     */
    v: {},

    /**
     * Map of all available controllers.
     *
     * @public
     * @property
     * @name c
     * @type Map
     * @cat core
     */
    c: {},

    /**
     * Jamal configuration passed from the root elements class
     *
     * @public
     * @property
     * @name config
     * @type Object
     * @cat core
     */
    config: {},

    /**
     * Debug flag to give more information about jamal in the console.
     *
     * @private
     * @property
     * @name debug
     * @type Boolean
     * @cat core
     */
    debug: false,

    /**
     * Jamal events
     *
     * @public
     * @property
     * @name events
     * @type Object
     * @cat core
     */
    events: {},

    /* Methods */
    
    /**
     * Method description
     *
     * @example jamal.start();
     * @result jamal.current == [ new Controller ]
     *
     * @public
     * @name start
     * @type jamal
     * @cat core
     */
    start: function() {
        this.log('Starting the Jamal application (Version: '+this.version+')...');
        this.log('Browser:');
        this.dir(jQuery.browser);
        this.log('Controller: ' + this.name);
        this.log('Action: ' + this.action);
        if (this.debug === true) {
            window.console.time('Timing');
        }
        var started = this.load();
        if (this.debug === true) {
            window.console.timeEnd('Timing');
        }
        if (jQuery.browser.mozilla) {
            this.log('Jamal size: '+this.toSource().length+' Chars');
        }
        
        // capture errors
        jQuery(window).error(function(message, file, line) {
            var e = {'name':'window.onerror',
                     'message':message,
                     'file':file,
                     'line':line,
                     'stack':''
                    };
            if(jamal.fn === undefined) {
                $j.error('Window error captured!', e);
            } else {
                jamal.fn.error('Window error captured!', e);
            }
            return true;
        });
                    
        return started;
    },

    /**
     * Log messages on the browser console. Firebug is recommended.
     *
     * @example jamal.log('current controller: ' + this.controller);
     *
     * @public
     * @name start
     * @type debug
     * @param String message The message to be displayed on the console
     * @param String message (optional) More messages to be displayed on the console
     * @cat log
     */
    log: function(message) {
        if (this.debug === true) {
            var log = '';
            for (var i=0; i<arguments.length; i++) {
                log += arguments[i];
                if (i !== (arguments.length-1)) {
                    log += ', ';
                }
            }
            window.console.log(log);
        }
    },

    /**
     * Log jamal errors to the console
     *
     * @example jamal.error('Controller not found!');
     *
     * @public
     * @name error
     * @type debug
     * @param String message Error message to be displayed on the console
     * @param Object e (optional) Error object to display the original error
     * @cat log
     */
    error: function(message) {
        if (this.debug === true) {
            if (arguments.length>1) {
                e = arguments[1];
                window.console.error('Jamal Error: '+message, e);
                if(typeof e === "object") {
                    if(typeof e.message === "object") {
                        this.log(e.name+': ');
                        this.dir(e.message);
                    } else {
                        this.log(e.name+': '+e.message);
                    }
                    this.dir(e);
                    this.log('Stack: ' + e.stack);
                } else {
                    this.log(e);
                    this.log('Stack:');
                    this.dir(this.callstack());
                }
            } else {
                window.console.error('Jamal Error: '+message);
            }
        }
    },
    
    /**
     * This function returns an array of objects that contain the 
     * information about call stack.
     *
     * @example callstack = jamal.callstack();
     *
     * @public
     * @name callstack
     * @type debug
     * @cat log
     */
    callstack: function() {
        var re_without_parenthesis = /[(][^)]*[)]/;
        var re_file_line = /(.*):(\d+)$/;
        
        var stack = new Error().stack.split('\n');
        stack.splice(0,2); // remove first two stack frames
        
        var frames = [];
        for(var i in stack) {
            // a stack frame string split into parts
            var frame = stack[i].split('@');
            if(frame && frame.length == 2) {
                frame = {
                    // Stackframe object
                    'name': frame[0],
                    'source': frame[0].replace(re_without_parenthesis, ''),
                    'file': frame[1].match(re_file_line)[1], // first group
                    'line': frame[1].match(re_file_line)[2]  // second group
                };
                this.log('at ' + frame.file + ' (' + frame.name + ': ' + frame.line + ')');
            }
        }
    },
    
    /**
     * Log objects to the console
     *
     * @example jamal.dir(obj);
     * @result [ { prop1: val1, prop2: val2 } ]
     *
     * @public
     * @name dir
     * @type debug
     * @param Object obj The object which should be logged on the console.
     * @cat log
     */
    dir: function(obj) {
        if (this.debug === true) {
            window.console.dir(obj);
        }
    },

    /**
     * Try to configure jamal
     *
     * Currently it is expected that there is a dom element with metadata
     * attached. This data is read via jQuery's metadata plugin.
     *
     * This makes it very easy to use jamal with e.g. CakePHP. Just add
     * <body class="jamal {controller:'<?php echo $this->name; ?>',action:'<?php echo $this->action; ?>'}"> 
     * to your default layout. Now you only need to create and include the 
     * corresponding js files.
     *
     * @example jamal.configure();
     * @before <body class="jamal {controller:'Tests',action:'index'}">
     * @result [ jamal.controller = 'Tests', jamal.action = 'index' ]
     *
     * @private
     * @name configure
     * @type jamal
     * @cat core
     */
    configure: function() {
        try {
            var data = jQuery(this.root+'.jamal').metadata();
        } catch(e) {
            this.debug = true;
            this.error('jQuery Metadata Plugin failed to read the configuration. '+
                       'Probably there is no class="jamal {controller:\'example\',action:\'index\'}" in your markup!', e);
        }
        
        if (typeof(data) !== 'object') {
            this.debug = true;
            this.error('No configuration found!');
            return false;
        } else {
            this.config = data;
            this.name = data.controller;
            this.action = data.action;
            this.debug = data.debug;
            return true;
        }
    },

    /**
     * Try to load the controller action 
     *
     * @example jamal.load();
     *
     * @public
     * @name load
     * @type mvc
     * @cat core
     */
    load: function () {
        var loaded = false;
        if (typeof this.c[this.name] !== 'object') {
            jamal.fn = jamal;
            $j.c({Generic: {}});
            this.name = 'Generic';
        }
        
        // controller
        try {
            this.current = this.c[this.name];
        } catch(e) {
            this.error('Controller error!', e);
        }
        
        // callback before the action
        this.current.beforeAction();
        
        // components
        if(this.current.components) {
            for(var i in this.current.components) {
                try {
                    this[this.current.components[i]]();
                } catch(e) {
                    this.error(this.current.components[i]+' component error!', e);
                }
            }
        }
        
        // action
        if (typeof this.c[this.name][this.action] === 'function') {
            try {
                this.current[this.action]();
                loaded = true;
            } catch(e) {
                this.error('Action couldn\'t be started!', e);
            }
        } else {
            this.log('Action not found!');
        }
        
        // callback after the action
        this.current.afterAction();
        return loaded;
    },

    /**
     * Run this function to give control of the $j variable back
     * to whichever library first implemented it. This helps to make 
     * sure that jamal doesn't conflict with the $j object
     * of other libraries.
     *
     * By using this function, you will only be able to access jamal
     * using the 'jamal' variable. For example, where you used to do
     * $j.json("/example/action"), you now must do jamal.json("/example/action").
     *
     * @example jamal.noConflict();
     * // Do something with jamal
     * jamal.json("/example/action");
     * @desc Maps the original object that was referenced by $j back to $j
     *
     * @name noConflict
     * @type undefined
     * @cat core 
     */
    noConflict: function() {
        if (jamal._$) {
            $j = jamal._$j;
        }
        return jamal;
    }
};

/**
 * Extend one object with one or more others, returning the original,
 * modified, object. This is a great utility for simple inheritance.
 * 
 * @example var settings = { validate: false, limit: 5, name: "foo" };
 * var options = { validate: true, name: "bar" };
 * jamal.extend(settings, options);
 * @result settings == { validate: true, limit: 5, name: "bar" }
 * @desc Merge settings and options, modifying settings
 *
 * @example var defaults = { validate: false, limit: 5, name: "foo" };
 * var options = { validate: true, name: "bar" };
 * var settings = jamal.extend({}, defaults, options);
 * @result settings == { validate: true, limit: 5, name: "bar" }
 * @desc Merge defaults and options, without modifying the defaults
 *
 * @name $.extend
 * @param Object target The object to extend
 * @param Object prop1 The object that will be merged into the first.
 * @param Object propN (optional) More objects to merge into the first
 * @type Object
 * @cat JavaScript
 */
jamal.extend = jamal.fn.extend = function() {
    // copy reference to target object
    var target = arguments[0], a = 1;

    // extend jamal itself if only one argument is passed
    if (arguments.length == 1) {
        target = this;
        a = 0;
    }
    var prop;
    while ((prop = arguments[a++]) != null) {
        // Extend the base object
        for (var i in prop) {
            target[i] = prop[i];
        }
    }

    // Return the modified object
    return target;
};

/* SVN FILE: $Id: jamal.js 22 2007-06-28 00:09:37Z teemow $ */
/**
 * To quote Dave Cardwell: 
 * Built on the shoulders of giants:
 *   * John Resig      - http://jquery.com/
 *
 * Jamal :  Javascript MVC Assembly Layout <http://jamal.moagil.de/>
 * Copyright (c)    2006, Timo Derstappen <http://teemow.com/>
 *
 * Licensed under The MIT License
 * Redistributions of files must retain the above copyright notice.
 *
 * @filesource
 * @copyright        Copyright (c) 2006, Timo Derstappen
 * @link            
 * @package          jamal
 * @subpackage       jamal.core
 * @since            Jamal v 0.1
 * @version          $Revision: 40 $
 * @modifiedby       $LastChangedBy: teemow $
 * @lastmodified     $Date: 2007-08-20 18:24:35 +0200 (Mo, 20. Aug 2007) $
 * @license          http://www.opensource.org/licenses/mit-license.php The MIT License
 */

/**
 * Jamal controller constructor
 *
 * @name jamal.controller
 * @type Object
 * @param String controller Name of the constructed controller
 * @cat controller
 */
/**
 * Inherit a controller from the jamal app controller
 * 
 * @example $j.c({Foos:{
 *     index: function(){
 *         alert('hello world');
 *     }
 * });
 * @desc Merge controller into jamal.c map and inherit everything from jamal.controller
 *
 * @name $j.m
 * @param Object controller The controller that will be merged into the controller map.
 * @type Object
 * @cat core
 * @todo merge jamal.c and jamal.controller with function overloading
 */
jamal.c = jamal.fn.c = function(controller) {
    if(typeof controller === 'object') {
        var inherited;
        for(var i in controller) {
            inherited = new jamal.fn.c(i);
            jamal.extend(inherited, controller[i]);
            
            // add model
            var m = i.substr(0, i.length-1).replace(/ie$/, 'y'); // name is singular
            if(jamal.fn.m[m]) {
                inherited.m = jamal.fn.m[m];
            } else {
                // if no model create one
                inherited.m = jamal.fn.m[m] = new jamal.fn.m(m);
            }
            
            // add view
            if(jamal.fn.v[i]) {
                inherited.v = jamal.fn.v[i];
            } else {
                // if no view create one
                inherited.v = jamal.fn.v[i] = new jamal.fn.v(i);
            }
            
            controller[i] = inherited;
        }
        jamal.extend(jamal.fn.c, controller);
    } else {
        this.name = controller;
    }
};

jamal.fn.extend(jamal.fn.c.prototype, {
    /**
     * Callback which get called before an action
     *
     * Overwrite this method in your own (app)controller
     *
     * @public
     * @name beforeAction
     * @cat controller
     */
    beforeAction: function(){
    },

    /**
     * Callback which get called after an action
     *
     * Overwrite this method in your own (app)controller
     *
     * @public
     * @name beforeAction
     * @cat controller
     */
    afterAction: function(){
    },

    /**
     * (Re-)Initialize a controller
     *
     * @example jamal.controller.init()
     * @desc initializes the current controller action
     *
     * @example filter = $('#list');
     * jamal.controller.init(filter)
     * @desc initializes the current controller action but events are only 
     * bind to elements in #list
     * 
     * @public
     * @name init
     * @param Object filter Dom element which should be reinitialized
     * @cat controller
     */
    init: function(filter){
        jamal.current[jamal.action](filter);
    }
});

/* SVN FILE: $Id: jamal.js 22 2007-06-28 00:09:37Z teemow $ */
/**
 * To quote Dave Cardwell: 
 * Built on the shoulders of giants:
 *   * John Resig      - http://jquery.com/
 *
 * Jamal :  Javascript MVC Assembly Layout <http://jamal.moagil.de/>
 * Copyright (c)    2006, Timo Derstappen <http://teemow.com/>
 *
 * Licensed under The MIT License
 * Redistributions of files must retain the above copyright notice.
 *
 * @filesource
 * @copyright        Copyright (c) 2006, Timo Derstappen
 * @link            
 * @package          jamal
 * @subpackage       jamal.core
 * @since            Jamal v 0.1
 * @version          $Revision: 58 $
 * @modifiedby       $LastChangedBy: teemow $
 * @lastmodified     $Date: 2009-01-19 15:40:09 +0100 (Mo, 19. Jan 2009) $
 * @license          http://www.opensource.org/licenses/mit-license.php The MIT License
 */

/**
 * Jamal model constructor
 *
 * @name jamal.model
 * @type Object
 * @param String model Name of the constructed model
 * @cat core
 */
/**
 * Inherit a model from the jamal app model.
 * 
 * @example $j.m({Foo:{
 *     getBar: function(){
 *         $j.json('/test/', function(response){
 *         });
 *     }
 * });
 * @desc Merge model into jamal.m map and inherit everything from jamal.model
 *
 * @name $j.m
 * @param Object model The model that will be merged into the model map.
 * @type Object
 * @cat core
 * @todo merge jamal.m and jamal.model with function overloading
 */
jamal.m = jamal.fn.m = function(model) {
    if(typeof model === 'object') {
        var inherited;
        for (var i in model) {
            // get the jamal model
            inherited = new jamal.fn.m(i);
            
            // inherit the new model
            jamal.extend(inherited, model[i]);
            model[i] = inherited;
        }
        jamal.extend(jamal.fn.m, model);
    } else {
        this.name = model;
    }
};

jamal.fn.extend(jamal.fn.m.prototype, {
    /**
     * A wrapper for jQuerys ajax
     *
     * We need a wrapper here to add the global callback. Please use jamal.json
     * in your controllers/models.
     *
     * @example jamal.model.json('/test/', 
     *   function(response) {
     *     jamal.dir(response.data);
     *   });
     *
     * @public
     * @name json
     * @param String url The URL of the page to load.
     * @param Function callback A function to be executed whenever the data is loaded.
     * @cat model
     * @todo this method should be moved to a general jamal model class
     */
    json: function(url, callback) {
        var model = this;
        
        var settings = {
            type: 'GET',
            dataType: 'json',
            url: url,
            beforeSend: function(xhr){
                jamal.ajaxSend(xhr);
                return model.beforeSend();
            },
            error: function(xhr, type, exception){
                if(model.error()) {
                    jamal.error('Ajax error: ' + type, exception);
                }
            },
            complete: function(xhr, result){
                model.complete(xhr, result);
            },
            success: function(response) {
                jamal.ajaxSuccess(response);
                if(model.callback(response)) {
                    if(callback) {
                        callback(response);
                    }
                }
            }
        };
        
        jQuery.ajax(settings);
    },
    
    /**
     * A wrapper for jQuerys getJSON
     *
     * We need a wrapper here to add the global callback. Please use jamal.json
     * in your controllers/models.
     *
     * @example jamal.model.json('/test/', 
     *   function(response) {
     *     jamal.dir(response.data);
     *   });
     *
     * @public
     * @name json
     * @param String url The URL of the page to load.
     * @param Function callback A function to be executed whenever the data is loaded.
     * @cat model
     * @todo this method should be moved to a general jamal model class
     */
    post: function(url, data, callback) {
        var model = this;
        
        var settings = {
            type: 'POST',
            dataType: 'json',
            url: url,
            data: data,
            beforeSend: function(xhr){
                jamal.ajaxSend(xhr);
                return model.beforeSend();
            },
            error: function(xhr, type, exception){
                if(model.error()) {
                    jamal.error('Ajax error: ' + type, exception);
                }
            },
            complete: function(xhr, result){
                model.complete(xhr, result);
            },
            success: function(response) {
                if(response.error_code) {
                    $j.error('Response error: ' + response.error_code);
                }
                jamal.ajaxSuccess(response);
                if(model.callback(response)) {
                    if(callback) {
                        callback(response);
                    }
                }
            }
        };
        
        jQuery.ajax(settings);
    },    
    
    /**
     * A pre-callback to modify the XMLHttpRequest object before it is sent. 
     * Use this to set custom headers etc. The XMLHttpRequest is passed as the 
     * only argument.
     *
     * Overwrite this method in your own (app)model
     *
     * @public
     * @name beforeSend
     * @cat model
     */
    beforeSend: function(xhr){
        return true;
    },
    
    /**
     * A function to be called when the request finishes (after success and 
     * error callbacks are executed). The function gets passed two arguments: 
     * The XMLHttpRequest object and a string describing the type of success 
     * of the request. 
     *
     * Overwrite this method in your own (app)model
     *
     * @public
     * @name complete
     * @cat model
     */
    complete: function(xhr, result){
        return true;
    },
    
    /**
     * A function to be called if the request fails. The function gets passed 
     * three arguments: The XMLHttpRequest object, a string describing the type 
     * of error that occurred and an optional exception object, if one occurred.
     *
     * @public
     * @name error
     * @cat model
     */
    error: function(xhr, type, exception){
        return true;
    },
    
    /**
     * A general callback for the model
     *
     * Jamal expects a JSON response like 
     * { 
     *   data: {}
     * }
     *
     * @example jamal.model.callback(response, 
     *   function(response){
     *     jamal.dir(response.data)
     *   });
     *
     * @public
     * @name callback
     * @param Object response JSON response from the server.
     * @cat model
     */
    callback: function(response){
        if(response.error) {
            var error = response.error;
            $j.error(error.error + ' (' + error.code + '): ' + error.description + ' in ' + error.file);
            $j.log('Stack:');
            $j.log(error.stack);
            $j.log('Context:');
            $j.log(error.context);
            $j.log('Listing:');
            $j.dir(error.listing);
            return false;
        }
        return response;
    }
});

/**
 * Bind the jamal ajax callbacks to the jQuery event handling
 *
 * @example jamal.ajaxSend(function() { alert("Hello"); });
 *
 * @name event
 * @type jamal
 * @param Function fn A function to bind to the jamal event
 * @cat model
 */
(function() {
    // Handle ajax event binding
    jamal.fn.ajaxSend = function(f){
        return typeof f === 'function' ? jQuery().bind('j_ajaxSend', f) : jQuery.event.trigger('j_ajaxSend', [f]);
    };
    jamal.fn.ajaxSuccess = function(f){
        return typeof f === 'function' ? jQuery().bind('j_ajaxSuccess', f) : jQuery.event.trigger('j_ajaxSuccess', [f]);
    };
})();

/* SVN FILE: $Id: jamal.js 22 2007-06-28 00:09:37Z teemow $ */
/**
 * To quote Dave Cardwell: 
 * Built on the shoulders of giants:
 *   * John Resig      - http://jquery.com/
 *
 * Jamal :  Javascript MVC Assembly Layout <http://jamal.moagil.de/>
 * Copyright (c)    2006, Timo Derstappen <http://teemow.com/>
 *
 * Licensed under The MIT License
 * Redistributions of files must retain the above copyright notice.
 *
 * @filesource
 * @copyright        Copyright (c) 2006, Timo Derstappen
 * @link            
 * @package          jamal
 * @subpackage       jamal.core
 * @since            Jamal v 0.1
 * @version          $Revision: 40 $
 * @modifiedby       $LastChangedBy: teemow $
 * @lastmodified     $Date: 2007-08-20 18:24:35 +0200 (Mo, 20. Aug 2007) $
 * @license          http://www.opensource.org/licenses/mit-license.php The MIT License
 */

/**
 * Jamal view constructor
 *
 * @name jamal.view
 * @type Object
 * @param String view Name of the constructed view
 * @cat view
 */
/**
 * Inherit a view from the jamal app view.
 * 
 * @example $j.v({Foos:{
 *     removeMessage: function(){
 *         $('div.message').remove();
 *     }
 * });
 * @desc Merge view into jamal.v map and inherit everything from jamal.view
 *
 * @name $j.v
 * @param Object view The view that will be merged into the view map.
 * @type Object
 * @cat core
 * @todo merge jamal.v and jamal.view with function overloading
 */
jamal.v = jamal.fn.v = function(view) {
    if(typeof view === 'object') {
        var inherited;
        for (var i in view) {
            inherited = new jamal.fn.v(i);
            jamal.extend(inherited, view[i]);
            view[i] = inherited;
        }
        jamal.extend(jamal.fn.v, view);
    } else {
        this.name = view;
    }
};

jamal.fn.extend(jamal.fn.v.prototype, {
    /**
     * Add a spinner to an element
     * 
     * @name addSpinner
     * @param Mixed obj Element / jQuery object / css selector of an dom element which should contain the spinner
     * @cat view
     */
    addSpinner: function(obj) {
        // create spinner
        var spinner;
        try {
            spinner = document.createElement('div');
            spinner.className = 'spinner';
        } catch( ex ) {
            jamal.error( 'Cannot create <' + tag + '> element:\n' +
                args.toSource() + '\n' + args );
            spinner = null;
        }
        $(obj).prepend(spinner);
    },
    
    /**
     * Remove all spinner
     * 
     * @name removeSpinner
     * @cat view
     */
    removeSpinner: function() {
        $('div.spinner').remove();
    },
    
    /**
     * Add a (success) message at the top of the current page
     * 
     * @name addMessage
     * @param String message The message that should be displayed
     * @cat view
     */
    addMessage: function(message){
        $('#content').prepend(message);
    },
    
    /**
     * Remove all messages and errors
     *
     * @name removeMessages
     * @cat view
     */
    removeMessages: function() {
        $('div.error').remove();
        $('div.message').remove();
    },
    
    /**
     * Add an error message
     *
     * @name addError
     * @param String message The error message that should be displayed
     * @param Mixed obj Element / jQuery object / css selector of an dom element which should contain the error message
     */
    addError: function(message, obj) {
        $('div.error', obj).remove();
        $(obj).prepend(message);
        $('div.error', obj).show();
    },
    
    /**
     * Decode HTML entities
     *
     * @example jamal.view.decode_html()
     * 
     * @public
     * @name decode_html
     * @type jamal
     * @cat view
     */
    decode_html: function(str) {
        if (typeof str === 'string') {
            var div = document.createElement('div');
            div.innerHTML = str.replace(/<\/?[^>]+>/gi, '');
            return div.childNodes[0] ? div.childNodes[0].nodeValue : '';
        } else {
            return '';
        }
    }
});

/* SVN FILE: $Id: jamal.js 18 2007-06-13 09:07:32Z teemow $ */
/**
 * To quote Dave Cardwell: 
 * Built on the shoulders of giants:
 *   * John Resig      - http://jquery.com/
 *
 * Jamal :  Javascript MVC Assembly Layout <http://jamal-mvc.com/>
 * Copyright (c)    2007, Timo Derstappen <http://teemow.com/>
 *
 * Licensed under The MIT License
 * Redistributions of files must retain the above copyright notice.
 *
 * @filesource
 * @copyright        Copyright (c) 2007, Timo Derstappen
 * @link            
 * @package          jamal
 * @subpackage       jamal.modal
 * @since            Jamal v 0.4
 * @version          $Revision: 40 $
 * @modifiedby       $LastChangedBy: teemow $
 * @lastmodified     $Date: 2007-08-20 18:24:35 +0200 (Mo, 20. Aug 2007) $
 * @license          http://www.opensource.org/licenses/mit-license.php The MIT License
 */

/**
 * Jamal modal component
 *
 * This component offers a modal dialog for jamal applications. eg. if your
 * session timed out you can display a modal login form
 *
 * @public
 * @name jamal
 * @cat modal
 */
jamal.fn.extend({
	/**
     * Create a modal dialog
	 *
	 * @example jamal.modal('<h1>message</h1>');
	 *
	 * @private
	 * @name modal
	 * @type jamal
     * @param String content Content that will be displayed in the modal window
	 * @cat modal
	 */
    modal: function(content) {
        if (content) {
            if (!jamal.modal.active) {
                // deactivate screen
                jQuery('body').css('overflow', 'hidden');
                if (jQuery.browser.msie) {
                    jQuery('select').hide();
                }
                jQuery('#wrapper')
                    .prepend('<div id="jamal_overlay"></div>')
                    .prepend('<div id="jamal_modal"><div class="jamal_size">'+content+'</div></div>');
                
                jQuery('#jamal_overlay')
                    .css({'background-color': '#000',
                          'position': 'absolute',
                          'width': '4000px',
                          'height': '4000px',
                          'float': 'left',
                          'margin-left': '-1500px',
                          'top': '0',
                          'left': '0',
                          'z-index': '80',
                          'filter': 'alpha(opacity=50)',
                          '-moz-opacity': '.50',
                          'opacity': '.50'});
                jQuery('#jamal_size').css('position', 'relative');
                jQuery('#jamal_modal')
                    .css({'position': 'absolute',
                          'background-color': '#fff',
                          'border': '4px solid #ccc',
                          'width': '380px',
                          'height': '305px',
                          'padding': '10px',
                          'z-index': '900'});
                jamal.modal.active = true;
            } else {
                jQuery('div.jamal_size').html(content);
            }
            jamal.modal.resize();
            return true;
        } else {
            return false;
        }
    }
});

jamal.fn.extend(jamal.fn.modal, {
	/**
	 * Flag for modal dialog
	 *
	 * @public
	 * @property
	 * @name jamal.modal.active
	 * @type Boolean
	 * @cat modal
	 */
    active: false,

	/**
     * Resize the current modal dialog
	 *
	 * @example jamal.modal.resize();
	 *
	 * @private
	 * @name resize
	 * @type jamal
	 * @cat modal
	 */
    resize: function() {
        // width
        jQuery('#jamal_modal').css('width', jQuery('div.jamal_size').width()+'px');
        
        var body = jQuery('#wrapper').width();
        var modal = jQuery('#jamal_modal').width();
        jQuery('#jamal_modal').css('margin-left', (body/2-modal/2)+'px');
        
        // height
        jQuery('#jamal_modal').css('height', jQuery('div.jamal_size').height()+'px');
        if (jQuery.browser.msie) {
            var offset = document.documentElement.scrollTop;
            body = document.documentElement.clientHeight;
        } else {
            var offset = window.pageYOffset;
            body = window.innerHeight;
        }
        modal = jQuery('#jamal_modal').height();
        jQuery('#jamal_modal').css('margin-top', (offset + body/2 - modal/2) +'px');
    },
    
	/**
     * Close the current dialog
	 *
	 * @example jamal.close();
	 *
	 * @private
	 * @name close
	 * @type jamal
	 * @cat modal
	 */
    close: function() {
        if (jamal.modal.active) {
            jQuery('#jamal_modal').fadeOut('slow');
            jQuery('#jamal_overlay').remove();
            jQuery('body').css('overflow', 'auto');
            if (jQuery.browser.msie) {
                jQuery('select').show();
            }
            jamal.modal.active = false;
        }
    }
});
/* SVN FILE: $Id: jamal.js 18 2007-06-13 09:07:32Z teemow $ */
/**
 * To quote Dave Cardwell: 
 * Built on the shoulders of giants:
 *   * John Resig      - http://jquery.com/
 *
 * Jamal :  Javascript MVC Assembly Layout <http://jamal-mvc.com/>
 * Copyright (c)    2007, Timo Derstappen <http://teemow.com/>
 *
 * Licensed under The MIT License
 * Redistributions of files must retain the above copyright notice.
 *
 * @filesource
 * @copyright        Copyright (c) 2007, Timo Derstappen
 * @link            
 * @package          jamal
 * @subpackage       jamal.session
 * @since            Jamal v 0.4
 * @version          $Revision: 40 $
 * @modifiedby       $LastChangedBy: teemow $
 * @lastmodified     $Date: 2007-08-20 18:24:35 +0200 (Mo, 20. Aug 2007) $
 * @license          http://www.opensource.org/licenses/mit-license.php The MIT License
 */

/**
 * Jamal session component
 *
 * This requires the modal component.
 *
 * @public
 * @name jamal
 * @cat session
 */
jamal.fn.extend({
    /* Constructor */
	/**
	 * Start the jamal session handling
	 *
     * @example jamal.session();
     * @desc This starts the jamal session handling
	 * @public
	 * @name session
	 * @type Object
	 * @cat session
	 */
    session: function(){
        if(this.config.session) {
            this.log('Session activated');
            this.session.active = true;
            this.session.since = 0;
            
            jamal.ajaxSend(function(xhr){
                if(jamal.session.active){
                    jamal.session.reset();
                }
            });
            
            jamal.ajaxSuccess(function(e, response){
                if(jamal.session.active){
                    if(response.session_timeout) {
                        // session timeout
                        jamal.session.reload();
                    } else {
                        jamal.session.reset();
                    }
                }
            });
            
            this.session.check();
            
            return true;
        }
        return false;
    }
}); 

jamal.fn.extend(jamal.fn.session, {
	/**
	 * Flag for server-side session check
	 *
	 * @public
	 * @property
	 * @name jamal.session.active
	 * @type Boolean
	 * @cat session
	 */
    active: false,
    
	/**
	 * Minutes a session lasts. After this time the user gets logged out and
     * is warned by a notification.
	 *
	 * @public
	 * @property
	 * @name jamal.session.timeout
	 * @type Number
	 * @cat session
	 */
    timeout: 30, // minutes

	/**
	 * Seconds between server-side session checks.
	 *
	 * @public
	 * @property
	 * @name jamal.session.freq
	 * @type Number
	 * @cat session
	 */
    freq: 60, // seconds

	/**
	 * This holds the time of the current session.
	 *
	 * @private
	 * @property
	 * @name jamal.session.since
	 * @type Number
	 * @cat session
	 */
    since: 0, // minutes
    
	/**
     * Check the session on the server side
	 *
	 * @example jamal.session.check();
	 *
	 * @private
	 * @name jamal.session.check
	 * @type Function
	 * @cat session
	 */
    check: function() {
        if (this.since < this.timeout) {
            if (this.since > 0) {
                
                var settings = {
                    url: '/session/',
                    type: 'GET',
                    dataType: 'json',
                    global: 'false',
                    success: function(response) {
                        if(jamal.session.active && response.session_timeout) {
                            jamal.session.destroy();
                        }
                    }
                };
                
                jQuery.ajax(settings);
            }
            this.since += this.freq/60;
            window.setTimeout("jamal.session.check();", this.freq*1000);
        } else {
            this.destroy();
        }
    },
    
	/**
     * Kills a jamal session
     *
     * Calls the url /logout/ to kill the session on the server side. It is 
     * expected to get back some information to be displayed in a modal dialog
	 *
	 * @example jamal.session.destroy();
     * @desc Destroys the current session 
	 *
	 * @private
	 * @name destroy
	 * @type Function
	 * @cat session
	 */
    destroy: function() {
        this.active = false;
        jamal.log('Session killed');
        
        var settings = {
            url: '/logout/',
            type: 'GET',
            dataType: 'json',
            global: 'false',
            success: function(response) {
                if (response.redirect) {
                    jamal.session.redirect();
                }
                
                jamal.modal(response.content);
                jamal.session.callback();
            }
        };

        jQuery.ajax(settings);
    },
    
    /**
     * Empty callback to customize the login screen handling
     *
     * @example jamal.session.callback = function() {
     *     $('#login').focus();
     *     $('form').form(function(response) {
     *         alert('logged in');
     *     });
     * };
     * 
     * @public
     * @name jamal.session.callback
     * @type Function
     * @cat session
     */
    callback: function() {
        return;
    },
     
    /**
     * Reloads the current page
     *
     * @example jamal.session.reload();
     * @desc Loads the current page again (full request, no xhr)
     *
     * @public
     * @name reload
     * @type jamal
     * @cat session
     */
    reload: function() {
        window.location.replace(window.location.href);
    },
    
	/**
     * Reset jamal's session timer
	 *
	 * @example jamal.reset();
	 *
	 * @private
	 * @name reset
	 * @type jamal
	 * @cat session
	 */
    reset: function() {
        this.since = 0;
    }    
});

/* SVN FILE: $Id: startup.js 40 2007-08-20 16:24:35Z teemow $ */
/**
 * This file handles the jamal object creation when the dom has finished.
 *
 * jQuery is required
 *
 * Jamal :  Javascript MVC Assembly Layout <http://jamal.moagil.de/>
 * Copyright (c)    2006, Timo Derstappen <http://teemow.com/>
 *
 * Licensed under The MIT License
 * Redistributions of files must retain the above copyright notice.
 *
 * @filesource
 * @copyright        Copyright (c) 2006, Timo Derstappen
 * @link            
 * @package          jamal
 * @subpackage       jamal.startup
 * @since            Jamal v 0.1
 * @version          $Revision: 40 $
 * @modifiedby       $LastChangedBy: teemow $
 * @lastmodified     $Date: 2007-08-20 18:24:35 +0200 (Mo, 20. Aug 2007) $
 * @license          http://www.opensource.org/licenses/mit-license.php The MIT License
 */

/**
 * Jamal startup
 *
 * Mapping jamal to the shorter $j namespace and register the onload event to
 * create an instance of jamal.
 *
 * This file sets the document.ready() function which is jQuery's replacement 
 * for the windows.onload event. 
 */

// Map over the $j in case of overwrite
if (typeof $j != "undefined") {
    jamal._$j = $j;
}

// Map the jamal namespace to '$j'
var $j = jamal;

/**
 * Window onload replacement of jquery
 *
 */
$(function(){
    $j = jamal = jamal();
    $j.start();
});
/*
 * Metadata - jQuery plugin for parsing metadata from elements
 *
 * Copyright (c) 2006 John Resig, Yehuda Katz, J�örn Zaefferer, Paul McLanahan
 *
 * Dual licensed under the MIT and GPL licenses:
 *   http://www.opensource.org/licenses/mit-license.php
 *   http://www.gnu.org/licenses/gpl.html
 *
 * Revision: $Id$
 *
 */

/**
 * Sets the type of metadata to use. Metadata is encoded in JSON, and each property
 * in the JSON will become a property of the element itself.
 *
 * There are three supported types of metadata storage:
 *
 *   attr:  Inside an attribute. The name parameter indicates *which* attribute.
 *          
 *   class: Inside the class attribute, wrapped in curly braces: { }
 *   
 *   elem:  Inside a child element (e.g. a script tag). The
 *          name parameter indicates *which* element.
 *          
 * The metadata for an element is loaded the first time the element is accessed via jQuery.
 *
 * As a result, you can define the metadata type, use $(expr) to load the metadata into the elements
 * matched by expr, then redefine the metadata type and run another $(expr) for other elements.
 * 
 * @name $.metadata.setType
 *
 * @example <p id="one" class="some_class {item_id: 1, item_label: 'Label'}">This is a p</p>
 * @before $.metadata.setType("class")
 * @after $("#one").metadata().item_id == 1; $("#one").metadata().item_label == "Label"
 * @desc Reads metadata from the class attribute
 * 
 * @example <p id="one" class="some_class" data="{item_id: 1, item_label: 'Label'}">This is a p</p>
 * @before $.metadata.setType("attr", "data")
 * @after $("#one").metadata().item_id == 1; $("#one").metadata().item_label == "Label"
 * @desc Reads metadata from a "data" attribute
 * 
 * @example <p id="one" class="some_class"><script>{item_id: 1, item_label: 'Label'}</script>This is a p</p>
 * @before $.metadata.setType("elem", "script")
 * @after $("#one").metadata().item_id == 1; $("#one").metadata().item_label == "Label"
 * @desc Reads metadata from a nested script element
 * 
 * @param String type The encoding type
 * @param String name The name of the attribute to be used to get metadata (optional)
 * @cat Plugins/Metadata
 * @descr Sets the type of encoding to be used when loading metadata for the first time
 * @type undefined
 * @see metadata()
 */

(function($) {

$.extend({
	metadata : {
		defaults : {
			type: 'class',
			name: 'metadata',
			cre: /({.*})/,
			single: 'metadata'
		},
		setType: function( type, name ){
			this.defaults.type = type;
			this.defaults.name = name;
		},
		get: function( elem, opts ){
			var settings = $.extend({},this.defaults,opts);
			// check for empty string in single property
			if ( !settings.single.length ) settings.single = 'metadata';
			
			var data = $.data(elem, settings.single);
			// returned cached data if it already exists
			if ( data ) return data;
			
			data = "{}";
			
			if ( settings.type == "class" ) {
				var m = settings.cre.exec( elem.className );
				if ( m )
					data = m[1];
			} else if ( settings.type == "elem" ) {
				if( !elem.getElementsByTagName ) return;
				var e = elem.getElementsByTagName(settings.name);
				if ( e.length )
					data = $.trim(e[0].innerHTML);
			} else if ( elem.getAttribute != undefined ) {
				var attr = elem.getAttribute( settings.name );
				if ( attr )
					data = attr;
			}
			
			if ( data.indexOf( '{' ) <0 )
			data = "{" + data + "}";
			
			data = eval("(" + data + ")");
			
			$.data( elem, settings.single, data );
			return data;
		}
	}
});

/**
 * Returns the metadata object for the first member of the jQuery object.
 *
 * @name metadata
 * @descr Returns element's metadata object
 * @param Object opts An object contianing settings to override the defaults
 * @type jQuery
 * @cat Plugins/Metadata
 */
$.fn.metadata = function( opts ){
	return $.metadata.get( this[0], opts );
};

})(jQuery);}
/* SVN FILE: $Id: jamal.js 18 2007-06-13 09:07:32Z teemow $ */
/**
 * To quote Dave Cardwell: 
 * Built on the shoulders of giants:
 *   * John Resig      - http://jquery.com/
 *
 * Jamal :  Javascript MVC Assembly Layout <http://jamal-mvc.com/>
 * Copyright (c)    2007, Timo Derstappen <http://teemow.com/>
 *
 * Licensed under The MIT License
 * Redistributions of files must retain the above copyright notice.
 *
 * @filesource
 * @copyright        Copyright (c) 2007, Timo Derstappen
 * @link            
 * @package          jamal
 * @subpackage       jamal.controller
 * @since            Jamal v 0.4
 * @version          $Revision: 40 $
 * @modifiedby       $LastChangedBy: teemow $
 * @lastmodified     $Date: 2007-08-20 18:24:35 +0200 (Mo, 20. Aug 2007) $
 * @license          http://www.opensource.org/licenses/mit-license.php The MIT License
 */

/**
 * Jamal app controller
 *
 * @public
 * @cat controller
 */
jamal.extend(jamal.fn.c.prototype, {
    components: ['session', 'modal'],
    
    beforeAction: function() {
    },
    afterAction: function() {
    }
    
});
/* SVN FILE: $Id: jamal.js 18 2007-06-13 09:07:32Z teemow $ */
/**
 * To quote Dave Cardwell: 
 * Built on the shoulders of giants:
 *   * John Resig      - http://jquery.com/
 *
 * Jamal :  Javascript MVC Assembly Layout <http://jamal-mvc.com/>
 * Copyright (c)    2007, Timo Derstappen <http://teemow.com/>
 *
 * Licensed under The MIT License
 * Redistributions of files must retain the above copyright notice.
 *
 * @filesource
 * @copyright        Copyright (c) 2007, Timo Derstappen
 * @link            
 * @package          jamal
 * @subpackage       jamal.model
 * @since            Jamal v 0.4
 * @version          $Revision: 40 $
 * @modifiedby       $LastChangedBy: teemow $
 * @lastmodified     $Date: 2007-08-20 18:24:35 +0200 (Mo, 20. Aug 2007) $
 * @license          http://www.opensource.org/licenses/mit-license.php The MIT License
 */

/**
 * Jamal app model
 *
 * @public
 * @cat model
 */
jamal.extend(jamal.fn.m.prototype, {
});
/* SVN FILE: $Id: jamal.js 18 2007-06-13 09:07:32Z teemow $ */
/**
 * To quote Dave Cardwell: 
 * Built on the shoulders of giants:
 *   * John Resig      - http://jquery.com/
 *
 * Jamal :  Javascript MVC Assembly Layout <http://jamal-mvc.com/>
 * Copyright (c)    2007, Timo Derstappen <http://teemow.com/>
 *
 * Licensed under The MIT License
 * Redistributions of files must retain the above copyright notice.
 *
 * @filesource
 * @copyright        Copyright (c) 2007, Timo Derstappen
 * @link            
 * @package          jamal
 * @subpackage       jamal.view
 * @since            Jamal v 0.4
 * @version          $Revision: 40 $
 * @modifiedby       $LastChangedBy: teemow $
 * @lastmodified     $Date: 2007-08-20 18:24:35 +0200 (Mo, 20. Aug 2007) $
 * @license          http://www.opensource.org/licenses/mit-license.php The MIT License
 */

/**
 * Jamal app view
 *
 * @public
 * @cat view
 */
jamal.extend(jamal.fn.v.prototype, {
});
