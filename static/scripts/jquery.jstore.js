/*!
 *  jStore 2.0 - Persistent Client Side Storage
 *
 *  Copyright (c) 2010 Eric Garside (http://eric.garside.name/)
 *  Dual licensed under:
 *      MIT: http://www.opensource.org/licenses/mit-license.php
 *      GPLv3: http://www.opensource.org/licenses/gpl-3.0.html
 *
 *  ---------------------------
 *
 *  jStore Flash Storage Component
 *
 *  Copyright (c) 2006 Jeff Lerman (jeff@blip.tv)
 *  Licensed under the Creative Commons Attribution 3.0 United States License:
 *      http://creativecommons.org/licenses/by/3.0/us
 */

//"use strict";

/*global Class, window, jQuery, ActiveXObject, google */

/*jslint white: true, browser: true, onevar: true, undef: true, eqeqeq: true, bitwise: true, regexp: false, strict: true, newcap: true, immed: true, maxerr: 50, indent: 4 */

(function ($, window) {
    
    //------------------------------
    //
    //  Constants
    //
    //------------------------------
    
    //------------------------------
    //  Exceptions
    //------------------------------
    
        /**
         *  An exception thrown by the StorageEngine class whenever its data accessor methods
         *  are called before the engine is ready to transact data.
         */
    var EX_UNSTABLE = 'JSTORE_ENGINE_UNSTABLE',
    
        /**
         *  An exception thrown by jStore whenever an undefined storage engine is referenced for
         *  some task by an invalid JRI (jStore Resource Identifier).
         */
        EX_UNKNOWN = 'JSTORE_UNKNOWN_ENGINE_REQUESTED',
        
        /**
         *  An exception thrown by jStore whenever a given flavor of storage is double defined.
         */
        EX_COLLISION = 'JSTORE_ENGINE_NAMESPACE_COLLISION',
        
        /**
         *  An exception thrown by jStore whenever a jri is double applied to a resource.
         */
        EX_DUPLICATE = 'JSTORE_RESOURCE_NAMESPACE_COLLISION',
        
        /**
         *  An exception thrown by jStore whenever a given flavor of storage has no defined engine.
         */
        EX_UNAVAILABLE = 'JSTORE_ENGINE_UNAVAILABLE',
        
        /**
         *  An exception thrown by jStore whenever an invalid flavor type is used.
         */
        EX_INVALID = 'JSTORE_INVALID_FLAVOR',
        
    //------------------------------
    //  Regular Expressions
    //------------------------------
    
        /**
         *  Regular expression to test property values for being JSON.
         */
        RX_JSON = (function ()
        {
            try 
            {
                return new RegExp('^("(\\\\.|[^"\\\\\\n\\r])*?"|[,:{}\\[\\]0-9.\\-+Eaeflnr-u \\n\\r\\t])+?$');
            }
            catch (e)
            {
                return (/^(true|false|null|\[.*\]|\{.*\}|".*"|\d+|\d+\.\d+)$/);
            }
        }()),
    
    //------------------------------
    //  Storage Flavors
    //------------------------------
        
        /**
         *  The storage flavor identifier for HTML5 local storage.
         */
        FLAVOR_LOCAL = 'jstore-html5-local',
        
        /**
         *  The storage flavor identifier for HTML5 database storage.
         */
        FLAVOR_SQL = 'jstore-html5-sql',
        
        /**
         *  The storage flavor identifier for Adobe Flash SharedObject storage.
         */
        FLAVOR_FLASH = 'jstore-flash',
        
        /**
         *  The storage flavor identifier for Google Gears storage.
         */
        FLAVOR_GEARS = 'jstore-google-gears',
        
        /**
         *  The storage flavor identifier for Internet Explorer storage, available to IE7 and IE6.
         */
        FLAVOR_MSIE = 'jstore-msie',
    
    //------------------------------
    //
    //  Property Declaration
    //
    //------------------------------
    
        /**
         *  The base StorageEngine class which each "storage flavor" will extend to meet the
         *  requirements for its specific implementation.
         */
        StorageEngine,
        
        /**
         *  The jStore object. Internal to this closure, jStore is referenced by "_". It is
         *  exposed to jQuery below, and made publicly accessible through jQuery.jStore
         */
        _ = {},
        
        /**
         *  The engines available to jStore for use. These are the class definitions for flavored
         *  storage engines.
         *
         *  Signature:
         *  {
         *      <storageFlavor>: <flavoredStorageEngineDefinition>,
         *
         *      ...
         *  }
         */
        definitions = {},
        
        /**
         *  Active engines instantiated by jStore, indexed by their JRI.
         *
         *  Signature:
         *  {
         *      <engineJRI>: <engineInstance>,
         *
         *      ...
         *  }
         */
        engines = {},
        
        /**
         *  If we are going to be using the flash storage engine, we want to postpone the jStore ready event until the jStore
         *  isFlashReady flag is also true. This property is set whenever flash is determined to be the storage engine.
         */
        waitForFlash = false,
        
        /**
         *  Storage for listeners, indexed by content and event type.
         *
         *  Signature:
         *  {
         *      <context>:
         *      {
         *          <eventType>: [<listener>, ...],
         *
         *          ...
         *      },
         *
         *      ...
         *  }
         */
        events = {},
        
        /**
         *  The configuration for this implementation.
         *
         *  Signature:
         *  {
         *      project: <defaultProjectName>,
         *
         *      flash: <pathToFlashBootloader>,
         *
         *      json: <pathToJSONFile>,
         *
         *      errorCallback: <listenerToNotifyOnError>
         *  }
         */
        configurations = 
        {
            project: undefined,
            
            flash: 'jStore.Flash.html',
            
            json: 'browser.json.js'
        },
        
        /**
         *  The active storage engine, being used to satisfy the get/set/remove functions on the jStore and jQuery
         *  objects.
         */
        active;
    
    //------------------------------
    //
    //  Internal Methods
    //
    //------------------------------
    
    /**
     *  Determine if the given flavor is valid.
     *
     *  @param flavor   The flavor to test.
     *
     *  @return True if the flavor is valid, false otherwise.
     */
    function validFlavor(flavor)
    {
        switch (flavor)
        {
        
        case FLAVOR_LOCAL:
        case FLAVOR_SQL:
        case FLAVOR_FLASH:
        case FLAVOR_GEARS:
        case FLAVOR_MSIE:
            return true;
        
        default:
            return false;
        
        }
    }

    /**
     *  Performs enhanced type comparison on an object. This is more reliable method
     *  of type checking a variable than a simple typeof comparison. The reason is that,
     *  typeof will reduce to the lowest common type. 
     *
     *  "typeof []" returns Object, and not Array.
     *  "typeof {}" returns Object as well.
     *
     *  typecheck( [], 'Array' )    :  returns true;
     *  typecheck( [], 'Object' )   :  returns false;
     *
     *  @param type     The variable type to check.
     *
     *  @param compare  A string representing the literal type to check.
     *
     *  @return True if the variable "type" matches the compare literal.
     */
    function typecheck(type, compare)
    {
        return !type ? false : type.constructor.toString().match(new RegExp(compare + '\\(\\)', 'i')) !== null; 
    }
    
    /**
     *  If the provided listener is a valid function, it will be triggered with the provided context
     *  and parameters.
     *
     *  @param listener     The listener being triggered.
     *  
     *  @param context      The context to provide to the listener.
     *
     *  @param parameters   The parameters to pass to the listener as arguments.
     *
     *  @return The response of the notified listener.
     */
    function notify(listener, context, parameters)
    {
        if (typecheck(listener, 'Function'))
        {
            return listener.apply(context || _, typecheck(parameters, 'Array') ? parameters : [parameters]);
        }
    }
    
    /**
     *  Load the given script.
     *
     *  @param path     The path to the file to include.
     *
     *  @param listener The listener to notify when the file finishes loading.
     */
    function loadScript(path, listener)
    {
        $.ajax(
        {
            url: path,
            complete: listener || $.noop(),
            type: 'GET',
            dataType: 'script',
            cache: false
        });  
    }
    
    /**
     *  Checks the type of the value, and returns a value safe to persist in any client-side mechanism.
     *
     *  @param value    The value which should be prepared for storage.
     *
     *  @return A value safe for storage.
     */
    function prepareForStorage(value)
    {
        if (value === undefined)
        {
            return '';
        }
        
        if (typecheck(value, 'Object') ||
            typecheck(value, 'Array') ||
            typecheck(value, 'Function'))
        {
            return JSON.stringify(value);
        }
        
        return value;
    }
    
    /**
     *  Checks the type of the value, and returns a value safe for access in any client-side mechanism.
     *
     *  @param value    The value which should be prepared for use.
     *
     *  @return A value safe for use.
     */
    function prepareForRevival(value)
    {
        return RX_JSON.test(value) ? JSON.parse(value) : value;
    }
    
    /**
     *	Normalize a key before using it, to ensure it's valid.
     *
     *  @param key  The key to normalize.
     *
     *  @return A normalized key, safe for storage.
     */
    function normalizeKey(key)
    {
        return key.replace(/^\s+|\s+$/g, "");
    }
    
    /**
     *  Define a flavored storage engine.
     *
     *  @throws EX_COLLISION, EX_INVALID
     *
     *  @param flavor       The flavor of engine being defined.
     *
     *  @param definition   An object containing the new properties and methods for the engine extension.
     *
     *  @param availability A function to invoke which must return a boolean value indicating the
     *                      availability of the storage flavor on this browser.
     */
    function define(flavor, definition, availability)
    {
        if (!validFlavor(flavor))
        {
            throw EX_INVALID;
        }
    
        if (availability[flavor] !== undefined)
        {
            throw EX_COLLISION;
        }
        
        /**
         *  The logic here has been reworked so unavailable flavors are discarded, so we don't needlessly
         *  bloat the runtime size of jStore.
         */
        if (notify(availability) === true)
        {
            _.available[flavor] = true;
            
            definition.flavor = flavor;
            
            definitions[flavor] = StorageEngine.extend(definition);
        }
        else
        {
            _.available[flavor] = false;
            
            //  Filter the invalid flavor out of the priority list.
            _.enginePriority = $.map(_.enginePriority, function (engine)
            {
                if (engine === flavor)
                {
                    return null;
                }
                else
                {
                    return engine;
                }
            });
        }
    }

    /**
     *  Make the jStore library ready.
     */
    function makeReady()
    {
        if (_.isReady)
        {
            return;
        }
        
        if ((waitForFlash && _.isFlashReady) || !waitForFlash)
        {
            _.isReady = true;
            _.trigger('jstore-ready', [engines[active]]);
        }
    }
    
    /**
     *  Create a best-fit engine.
     */
    function createBestFitEngine()
    {
        _.create(_.enginePriority[0], undefined, 'best-fit');
    }
    
    /**
     *  Get the flash version currently supported in this browser.
     *
     *  @return The flash version.
     */
    function flashVersion()
    {
        // MSIE
        try
        {
            // avoid fp6 minor version lookup issues
            // see: http://blog.deconcept.com/2006/01/11/getvariable-setvariable-crash-internet-explorer-flash-6/
            var axo = new ActiveXObject('ShockwaveFlash.ShockwaveFlash.6');
            
            try
            {
                axo.AllowScriptAccess = 'always';
            }
            catch (axo_e)
            {
                return '6,0,0';
            }
            
            return new ActiveXObject('ShockwaveFlash.ShockwaveFlash').GetVariable('$version').replace(/\D+/g, ',').match(/^,?(.+),?$/)[1];
        }
        
        //  Real browsers
        catch (e)
        {
            try
            {
                if (navigator.mimeTypes["application/x-shockwave-flash"].enabledPlugin)
                {
                    return (navigator.plugins["Shockwave Flash 2.0"] || navigator.plugins["Shockwave Flash"]).description.replace(/\D+/g, ",").match(/^,?(.+),?$/)[1];
                }
            }
            catch (flash_e)
            {}
        }
        
        return '0,0,0';
    }

    /**
     *  Flash Detection functions copied from the jQuery Flash Plugin
     * 
     *  Copyright (c) 2006 Luke Lutman (http://jquery.lukelutman.com/plugins/flash)
     * 
     *  Dual licensed under the MIT and GPL licenses.
     *      http://www.opensource.org/licenses/mit-license.php
     *      http://www.opensource.org/licenses/gpl-license.php 
     *
     *  @param version  The version to compare to.
     *
     *  @return True if the version is greater than or equal to the required version, false otherwise.
     */
    function hasFlashVersion(version)
    {
        var playerVersion = flashVersion().match(/\d+/g),
            requiredVersion = version.match(/\d+/g),
            index = 0,
            player, 
            required;
            
        for (; index < 3; index++)
        {
            player = parseInt(playerVersion[index], 10);
            required = parseInt(requiredVersion[index], 10);
        
            //  Player version is less than what is required.
            if (player < required)
            {
                return false;
            }
            
            //  Player version is greater than what is required.
            else if (player > required)
            {
                return true;
            }
        }
        
        //  Player and required version match exactly.
        return true;
    }

    //------------------------------
    //
    //  Plugin Definition
    //
    //------------------------------
    
    //------------------------------
    //  Error Declaration
    //------------------------------
    
    //------------------------------
    //  Plugin Creation
    //------------------------------
    
    /**
     *  The jStore object. Manages a collection of StorageEngines for particular "storage flavors", or the types
     *  of storage solutions available to each browser.
     *
     *  2.0 Version Notes:
     *
     *      - The user is now responsible for third-party script includes, with the exception of flash.
     *
     *      - jStore has been given sole responsibility for testing engine availability.
     *
     *      - For the sake of naming conventions, all property names now start with a lowercase, and are camel-cased.
     *
     *  The following properties have been changed since the 1.2.x release:
     *
     *      - EngineOrder:      For the sake of naming conventions, renamed to enginePriority.
     *
     *  The following properties and methods have been removed since the 1.2.x release:
     *
     *      - Availability:     jStore's engines would add their availability tests to this object, so jStore could test 
     *                          them. With the changes to how availability testing works, this property has been removed.
     *                          A new property, "available" on jStore contains a set of available engines.
     *
     *      - Engines:          Formerly contained the definitions of storage engines. This property has been removed, and
     *                          storage of these definitions has been moved internal to the closure.
     *     
     *      - Instances:        Formerly contained instantiated storage engines. This property has been removed, and storage
     *                          of instantiated engines has been moved internal to the closure.
     *
     *      - CurrentEngine:    Formerly contained the active storage engine being used for transacting data through the jStore
     *                          and/or jQuery objects. This property has been removed, and storage of the current engine has
     *                          been moved internal to the closure. A new method, "activeEngine" has been added to jQuery to
     *                          get and set the active engine to use.
     *
     *      - defaults:         Formerly used to set the implementation options for jStore. This property has been removed and
     *                          replaced with a new configuration metho on the jStore object.
     *
     *      - delegate:         The delegate class has been removed in favor of a much simpler bind/trigger accessor system, which
     *                          is accessible contextually through storage engines, or generically through jStore.
     *      
     *      + fail:             This registration class bound events on the delegate for jstore-fail events. Instead, use:
     *                              jStore.bind('jstore-failure', listener);
     *
     *      + flashReady:       This registration class bound events on the delegate for flash-ready events. The jstore-ready method
     *                          now accounts for waiting for flash readyness, if and only if the flash engine is being used. Simply
     *                          call to jStore.ready().
     *
     *      + load:             Replaced with the init() method, which performs the same basic functions as the old load() method. Also,
     *                          the init function is now domready safe, meaning it wraps itself in a domready listener, so the end user
     *                          doesn't have to.
     *
     *      + FindEngine:       Removed entirely. The functionality provided by this method now implicitly occurs with the new define()
     *                          system implemented for engine flavors.
     *
     *      + setCurrentEngine: Replaced by activeEngine(). Set the current active engine by passing in the JRI.
     *
     *      + safeStore:        Replaced by a method internal to this closure, "prepareForStorage".
     *
     *      + safeResurrect:    Replaced by a method internal to this closure, "prepareForRevival".
     *
     *      + use:              Replaced by "create".
     */
    $.extend(_, {
    
        //------------------------------
        //  Properties
        //------------------------------
    
        /**
         *  The priority order in which engines should be tested for use. The lower their index in the array, the higher
         *  their priority for use.
         *
         *  Be weary when reconfiguring the priority order of engines! jStore will use the first available engine it finds
         *  based on its priority when autoloading.
         *
         *  This array is filtered out as engines are defined, with invalid engines being removed.
         *
         *  Signature:
         *  [FLAVOR_<storageFlavor>, ...]
         */
        enginePriority: [FLAVOR_LOCAL, FLAVOR_SQL, FLAVOR_FLASH, FLAVOR_MSIE],
        
        /**
         *  A collection of the availability states of engines, indexed by their flavor.
         *
         *  Signature:
         *  {
         *      <storageFlavor>: true|false,
         *
         *      ...
         *  }
         */
        available: {},
        
        /**
         *  Flag to determine if the jStore library is ready. jStore becomes ready once the dom is ready and all necessary 
         *  startup procedures required by jStore to function properly are completed.
         */
        isReady: false,
        
        /**
         *  With the flash storage engine, we have to jump through a couple of hoops before the flash engine is ready to work.
         *  This flag tracks whether or not the flash storage is available.
         */
        isFlashReady: false,
        
        /**
         *  The available engine flavors.
         */
        flavors:
        {
            local: FLAVOR_LOCAL,
            
            sql: FLAVOR_SQL,
            
            flash: FLAVOR_FLASH,
            
            gears: FLAVOR_GEARS,
            
            msie: FLAVOR_MSIE
        },
        
        //------------------------------
        //  Constructor
        //------------------------------
        
        /**
         *  Constructor.
         *
         *  @throws EX_INVALID
         *
         *  @param project          The name of the jStore project. Used to generate a JRI for the engine we create.
         *
         *  @param configuration    Optionally, an object containing configuration options for this implementation.
         *
         *  @param flavor           Optionally, the flavor of storage to use. If not provided, jStore will pick the
         *                          best flavor, based on the current browser.
         *
         *  @return jStore
         */
        init: function (project, configuration, flavor)
        {   
            //  Extend our plugin configurations
            $.extend(configurations, {project: project}, configuration);
            
            $(function ()
            {
                //  If JSON parsing isn't defined in this browser, include it.
                if (window.JSON === undefined)
                {
                    loadScript(configurations.json);
                }
            
                //  If we have an explicit flavor to use, use it.
                if (flavor !== undefined)
                {
                    _.create(flavor, project, 'default');
                }
                
                //  Otherwise, attempt to create a best-fit engine.
                else
                {
                    createBestFitEngine();
                }
            });
        
            return _;
        },
    
        //------------------------------
        //  Methods
        //------------------------------
    
        /**
         *  Create an instance of a flavored engine.
         *
         *  @throws EX_INVALID, EX_UNAVAILABLE, EX_DUPLICATE
         *
         *  @param flavor       The flavor to create the engine with.
         *
         *  @param project      The project identifier for this instance.
         *
         *  @param identifier   Some arbitrary identifier for this project instance of the engine.
         *
         *  @return The created instance.
         */
        create: function (flavor, project, identifier)
        {
            project = project || configurations.project || location.hostname.replace(/\./g, '-') || 'unknown';
            
            if (!validFlavor(flavor))
            {
                throw EX_INVALID;
            }
            
            if (definitions[flavor] === undefined)
            {
                throw EX_UNAVAILABLE;            
            }
            
            var jri = (identifier !== undefined ? identifier + '.' : '') + project + '.' + flavor,
                engine;

            if (engines[jri] !== undefined)
            {
                throw EX_DUPLICATE;
            }
            
            //  Create our engine instance.
            engine = engines[jri] = new definitions[flavor](project, jri);
            
            //  Set up a listener for our jstore-engine-ready event.
            engine.ready(function ()
            {
                _.trigger('jstore-engine-ready', [engine]);
            });
            
            if (flavor === FLAVOR_FLASH && !_.isFlashReady)
            {
                if (active === undefined)
                {
                    waitForFlash = true;
                }
                
                //  Define a window-accessible function for flash to call via ExternalInterface
                window.jstore_ready = function ()
                {
                    _.isFlashReady = true;
                    _.trigger('flash-ready');
                    
                    if (active === undefined)
                    {
                        makeReady();
                    }
                    
                    //  Remove the callback from the window scope, as it is no longer necessary
                    window.flash_ready = undefined;
                };
                
                window.jstore_error = function (message)
                {
                    _.trigger('jstore-error', ['JSTORE_FLASH_EXCEPTION', null, message]);
                };
                
                $('<iframe style="height:1px;width:1px;position:absolute;left:0;top:0;margin-left:-100px;" id="jStoreFlashFrame" src="' + 
                    configurations.flash + '"></iframe>').appendTo('body');   
            }
            else if (active === undefined)
            {
                active = jri;
                makeReady();
            }
            
            return engine;
        },
        
        /**
         *  Fetch an engine by it's JRI.
         *
         *  @param jri  The JRI of the engine to retrieve.
         *
         *  @return The requested engine.
         */
        engine: function (jri)
        {
            return engines[jri];
        },
    
        /**
         *  Returns the active storage engine being used. If a value is passed, sets that engine as the active engine.
         *
         *  @throws EX_UNKNOWN
         *
         *  @param jri  Optionally, the JRI of the engine to make active, if it should be changed.
         *
         *  @return The active storage engine.
         */
        activeEngine: function (jri)
        {
            if (jri !== undefined)
            {
                if (engines[jri] === undefined)
                {
                    throw EX_UNKNOWN;
                }
                else
                {
                    active = jri;
                }
            }
            
            return engines[active];
        },
        
        /**
         *  Bind an event listener.
         *
         *  @param event    The event to bind a listener on.
         *
         *  @param listener The listener to notify when the event occurs.
         *
         *  @param context  The context of the binding. A string representing the engine flavor
         *                  binding the event, or undefined to indicate it's a jStore event.
         *
         *  @return jStore
         */
        bind: function (event, listener, context)
        {
            context = context || 'jstore';
            
            if (events[context] === undefined)
            {
                events[context] = {};
            }
            
            if (events[context][event] === undefined)
            {
                events[context][event] = [listener];
            }
            else
            {
                events[context][event].push(listener);
            }
            
            return _;
        },
        
        /**
         *  Trigger an event, notifying any bound listeners.
         *
         *  @param event        The event to trigger.
         *
         *  @param parameters   Any additional parameters to pass to the listeners being notified.
         *
         *  @param context      The context of the binding. A string representing the engine flavor
         *                      binding the event, or undefined to indicate it's a jStore event.
         *
         *  @return jStore
         */
        trigger: function (event, parameters, context)
        {
            context = context || 'jstore';
            
            if (events[context] !== undefined)
            {
                if (events[context][event] !== undefined)
                {
                    $.each(events[context][event], function ()
                    {
                        notify(this, _, parameters);
                    });
                }
            }
            
            return _;
        },
        
        /**
         *	Bind a listener to be notified when jStore causes a non-fatal exception.
         *
         *  @param listener The listener to notify when a failure occurs.
         */
        error: function (listener)
        {
            _.bind('jstore-error', listener);
        },
        
        /**
         *  Bind a listener to be notified when jStore is ready.
         *
         *  @param listener The listener to notify when jStore is ready.
         *
         *  @return jStore
         */
        ready: function (listener)
        {
            if (_.isReady)
            {
                notify(listener);
            }
            else
            {
                _.bind('jstore-ready', listener);
            }
            
            return _;
        },
        
        /**
         *  Bind a listener to be notified when jStore and the default engine are ready.
         *
         *  @param listener The listener to notify when jStore and it's default engine are ready.
         *
         *  @return jStore
         */
        engineReady: function (listener)
        {
            if (_.isReady)
            {
                notify(listener);
            }
            else
            {
                _.bind('jstore-engine-ready', listener);
            }
            
            return _;
        },
        
        /**
         *  A combined getter/setter for the active engine.
         *
         *  @param key      The key of the property to get, or set.
         *
         *  @param value    If a valid value is provided, sets the engine.
         *
         *  @return The requested property value.
         */
        store: function (key, value)
        {   
            return value === undefined ? _.get(key) : _.set(key, value);
        },
        
        /**
         *  Remove a property from the active engine.
         *
         *  @param key  The key of the property to remove.
         *
         *  @return The value of the property before removal.
         */
        remove: function (key)
        {
            return _.activeEngine().remove(key);
        },
        
        /**
         *  Get a property from the active engine.
         *
         *  @param key  The key of the property to get.
         *
         *  @return The value of the property.
         */
        get: function (key)
        {
            return _.activeEngine().get(key);
        },
        
        /**
         *  Set a property on the active engine.
         *
         *  @param key      The key of the property to set.
         *
         *  @param value    The value to set the property to.
         *
         *  @return The new value of the property.
         */
        set: function (key, value)
        {
            return _.activeEngine().set(key, value);
        }
    
    });
    
    //------------------------------
    //  Core Extension
    //------------------------------
    
    //------------------------------
    //
    //  Class Definition
    //
    //------------------------------
    
    /**
     *  The StorageEngine class is the unified API through which jStore accesses and manipulates
     *  the various storage flavors available.
     *
     *  2.0 Version Notes:
     *
     *      - All third-party loading is now the responsibility of the developer.
     *
     *      - The delegate class has been removed entirely. Engines have been given "bind" and "trigger" methods
     *          to interact directly with the delegate like-replacement that has been added to jStore.
     *
     *      - Engine availability has been moved out of the engines themselves, and elevated to a jStore
     *          responsibility.
     *
     *  The following methods have changed since the 1.2.x release:
     *
     *      - get:          When "get"ting a non-stored property, the get function will now return "undefined"
     *                      instead of "null". "null" can now be used as a valid property value.
     *
     *      - rem:          Renamed to "remove". I always felt dirty about "rem" being vaguely explicit.
     *
     *  The following properties have been removed since the 1.2.x release:
     *
     *      - autoload:     Part of the third-party loading logic.
     *
     *      - hasIncluded:  Part of the third-party loading logic.
     *  
     *      - includes:     Part of the third-party loading logic.
     *
     *      - isAvailable:  Part of the availability logic elevated to jStore.
     *
     *  @throws EX_UNSTABLE
     */
    StorageEngine = Class.extend({
    
        //------------------------------
        //  Properties
        //------------------------------
    
        /**
         *  The project which owns this storage engine.
         */
        project: undefined,
        
        /**
         *  The JRI (jStore Resource Identifier) acts as a uuid for this specific instance
         *  of the storage engine.
         */
        jri: undefined,
        
        /**
         *  The flavor of this engine.
         */
        flavor: undefined,
        
        /**
         *  The actual database object which data is transacted through.
         */
        database: undefined,
        
        /**
         *  A StorageEngine should always respond to fetch requests synchronously. However, some 
         *  of the storage flavors require callback-based asynchronous access. To get around this, 
         *  we simlpy require all engines to function off a primary data cache, to allow for 
         *  synchronous access across all implementations.
         *
         *  Signature:
         *  {
         *      <propertyKey>: <propertyValue>,
         *
         *      ...
         *  }
         */
        data: undefined,
        
        /**
         *  A number of storage engines enforce a size limit as to what they will persist for a given site.
         *  This limit is not monitored or computed by jStore currently, and this property will merely give
         *  a static indication of the total size alloted to the engine, as defined by the storage flavor.
         */
        limit: undefined,
        
        /**
         *  Each storage flavor has a different process to go through before it's "ready" to transact data. This
         *  property stores the state of the engine's readyness, and uses it to notify listeners whenever jStore
         *  is ready to function.
         */
        isReady: undefined,

        //------------------------------
        //  Constructor
        //------------------------------
        
        /**
         *  Constructor.
         *
         *  @param project  The project which instantiated this engine.
         *
         *  @param jri      The uuid assigned to this instance by jStore.
         */
        init: function (project, jri)
        {
            this.project = project;
            this.jri = jri;
            this.data = {};
            this.isReady = false;
            this.updateCache();
        },
        
        //------------------------------
        //  Methods
        //------------------------------
        
        /**
         *  Update the cache.
         */
        updateCache: function ()
        {
            this.isReady = true;
            this.trigger('engine-ready', [this]);
        },
        
        /**
         *  Bind a listener to an event dispatched by this engine.
         *
         *  @param event    The event to bind on.
         *
         *  @param listener The listener to notify when the event occurs.
         */
        bind: function (event, listener)
        {
            _.bind(event, listener, this.jri);
        },
        
        /**
         *  Trigger an event, notifying all bound listeners.
         *
         *  @param event        The event to trigger.
         *
         *  @param parameters   An optional Array of parameters to pass to the listeners.
         */
        trigger: function (event, parameters)
        {
            _.trigger(event, parameters, this.jri);
        },
        
        /**
         *  Bind a listener to the StorageEngine's ready event.
         *
         *  @param listener The listener to notify whenever this engine is ready to transact data.
         */
        ready: function (listener)
        {
            if (this.isReady)
            {
                notify(listener, this);
            }
            else
            {
                this.bind('engine-ready', listener);
            }
        },
        
        /**
         *  Get a property from the StorageEngine.
         *
         *  @param key  The property key of the data to retrieve.
         *
         *  @return The property value, or "undefined" if the property isn't stored.
         */
        get: function (key)
        {
            this.__interruptAccess();
            
            return this.data[key];
        },
        
        /**
         *  Sets a property in the StorageEngine.
         *
         *  @param key      The key of the property.
         *
         *  @param value    The value of the property.
         *
         *  @return The new value of the property.
         */
        set: function (key, value)
        {
            this.__interruptAccess();
            
            key = normalizeKey(key);
            
            try
            {
                this.__set(key, value);
            }
            catch (e)
            {
                _.trigger('jstore-error', ['JSTORE_STORAGE_FAILURE', this.jri, e]);
            }
            
            this.data[key] = value;
            
            return value;
        },
        
        /**
         *  Removes a property from the StorageEngine.
         *
         *  @param key  The property key of the data to remove.
         *
         *  @return The value of the property, before it was removed.
         */
        remove: function (key)
        {
            this.__interruptAccess();
            
            key = normalizeKey(key);
            
            try
            {
                this.__remove(key);
            }
            catch (e)
            {
                _.trigger('jstore-error', ['JSTORE_REMOVE_FAILURE', this.jri, e]);
            }
            
            var buffer = this.data[key];
            
            this.data[key] = undefined;
            
            return buffer;
        },
        
        //------------------------------
        //  Internal Methods
        //------------------------------
        
        /**
         *  Ensures the engine is in a stable state for transacting data.
         *
         *  @throws EX_UNSTABLE
         */
        __interruptAccess: function ()
        {
            if (!this.isReady)
            {
                throw EX_UNSTABLE;
            }
        },
        
        /**
         *  Sets a property in the StorageEngine. This method should be overloaded to provide actual
         *  storage flavor integration.
         *
         *  @param key      The key of the property.
         *
         *  @param value    The value of the property.
         *
         *  @return The new value of the property.
         */
        __set: function (key, value)
        {
            return;
        },
        
        /**
         *  Removes a property from the StorageEngine. This method should be overloaded to provide actual
         *  storage flavor integration.
         *
         *  @param key  The property key of the data to remove.
         *
         *  @return The value of the property, before it was removed.
         */
        __remove: function (key)
        {
            return;
        }
        
    });
        
    //------------------------------
    //
    //  jQuery Hooks
    //
    //------------------------------
    
    $.extend($.fn, {
    
        //------------------------------
        //  Methods
        //------------------------------
    
        /**
         *  A combined getter/setter for the active engine.
         *
         *  @param key      The key of the property to get, or set.
         *
         *  @param value    If a valid value is provided, sets the engine.
         *
         *  @return jQuery
         */
        store: function (key, value)
        {   
            if (value === undefined)
            {
                _.get(key);
            }
            else
            {
                _.set(key, value);
            }
            
            return this;
        },
        
        /**
         *  Remove a property from the active engine.
         *
         *  @param key  The key of the property to remove.
         *
         *  @return jQuery
         */
        removeStore: function (key)
        {
            _.activeEngine().remove(key);
            
            return this;
        },
        
        /**
         *  Get a property from the active engine.
         *
         *  @param key  The key of the property to get.
         *
         *  @return The value of the property.
         */
        getStore: function (key)
        {
            return _.activeEngine().get(key);
        },
        
        /**
         *  Set a property on the active engine.
         *
         *  @param key      The key of the property to set.
         *
         *  @param value    The value to set the property to.
         *
         *  @return jQuery
         */
        setStore: function (key, value)
        {
            _.activeEngine().set(key, value);
            
            return this;
        }
        
    });
    
    //------------------------------
    //
    //  Event Bindings
    //
    //------------------------------
    
    //------------------------------
    //
    //  Startup Code
    //
    //------------------------------
    
    //------------------------------
    //  Expose jStore through jQuery
    //------------------------------
    
    window.jStore = $.jStore = _;
    
    //------------------------------
    //
    //  Engine Definitions
    //
    //------------------------------

    //------------------------------
    //  Local
    //------------------------------
    
    define(FLAVOR_LOCAL, 
    {
        //------------------------------
        //  Properties
        //------------------------------
        
        limit: parseInt(5e5, 16),
        
        //------------------------------
        //  Constructor
        //------------------------------
    
        init: function (project, name)
        {   
            this.database = window.globalStorage === undefined ? window.localStorage : window.globalStorage[location.hostname];
            
            this._super(project, name);
        },
        
        //------------------------------
        //  Methods
        //------------------------------
        
        updateCache: function ()
        {
            var key, value;
        
            for (key in this.database)
            {
                var has_key = false;
                if (this.database.hasOwnProperty) {
                    if (this.database.hasOwnProperty(key)) {
                        has_key = true;
                    }
                } else { // IE 8
                    if (this.database.getItem(key) !== null) {
                        has_key = true;
                    }
                }
                        
                if (has_key) {
                    value = this.database.getItem(key);
            
                    //  Gecko's getItem returns {value: 'the value'}, WebKit returns 'the value'
                    this.data[key] = prepareForRevival(value && value.value ? value.value : value);
                }
            }
            
            this._super();
        },
        
        //------------------------------
        //  Internal methods
        //------------------------------
        
        __set: function (key, value)
        {
            this.database.setItem(key, prepareForStorage(value));
        },
        
        __remove: function (key)
        {
            this.database.removeItem(key);
        }
    },
    
    function ()
    {
        return window.localStorage !== undefined || window.globalStorage !== undefined;
    });
    
    //------------------------------
    //  SQL
    //------------------------------
    
    define(FLAVOR_SQL, 
    {
        //------------------------------
        //  Properties
        //------------------------------
        
        limit: parseInt(32e3, 16),
        
        //------------------------------
        //  Constructor
        //------------------------------
    
        init: function (project, name)
        {   
            this.database = window.openDatabase('jstore-' + project, '1.0', project, this.limit);

            if (!this.database)
            {
                throw 'JSTORE_SQL_NO_DB';
            }
            
            this.database.transaction(function (database)
            {
                database.executeSql('CREATE TABLE IF NOT EXISTS jstore (k TEXT UNIQUE NOT NULL PRIMARY KEY, v TEXT NOT NULL)');
            });
            
            this._super(project, name);
        },
        
        //------------------------------
        //  Methods
        //------------------------------
        
        updateCache: function ()
        {
            var self = this,
                _super = this._super;
        
            this.database.transaction(function (database)
            {
                database.executeSql('SELECT k,v FROM jstore', [], function (database, result)
                {
                    var rows = result.rows,
                        index = 0,
                        row;
                        
                    for (; index < rows.length; ++index)
                    {
                        row = rows.item(index);
                        self.data[row.k] = prepareForRevival(row.v);
                    }
                    
                    _super.apply(self);
                });
            });
        },
        
        //------------------------------
        //  Internal methods
        //------------------------------
        
        __set: function (key, value)
        {
            this.database.transaction(function (database)
            {
                database.executeSql('INSERT OR REPLACE INTO jstore(k, v) VALUES (?, ?)', [key, prepareForStorage(value)]);
            });
        },
        
        __remove: function (key)
        {
            this.database.transaction(function (database)
            {
                database.executeSql('DELETE FROM jstore WHERE k = ?', [key]);
            });
        }
    }, 
    
    function ()
    {
        return window.openDatabase !== undefined;
    });
    
    //------------------------------
    //  Flash
    //------------------------------
    
    define(FLAVOR_FLASH, 
    {
        //------------------------------
        //  Properties
        //------------------------------
        
        limit: -1,
        
        //------------------------------
        //  Constructor
        //------------------------------
    
        init: function (project, name)
        {   
            var self = this;
        
            _.bind('flash-ready', function ()
            {
                self.__flashReadyListener();
            });
            
            this._super(project, name);
        },
        
        //------------------------------
        //  Methods
        //------------------------------
        
        updateCache: function (enable)
        {
            /**
             *  The default call to updateCache passes no variable, so we can short circuit the
             *  ready state until we explictly call this after flash ready.
             */
            if (enable === true)
            {
                var key, 
                    dataset = this.database.jstore_get_all();
            
                for (key in dataset)
                {
                    if (dataset.hasOwnProperty(key))
                    {   
                        this.data[key] = prepareForRevival(this.database.jstore_get(key));
                    }
                }
            
                this._super();
            }
        },
        
        //------------------------------
        //  Internal methods
        //------------------------------
        
        __set: function (key, value)
        {
            if (!this.database.jstore_set(key, prepareForStorage(value)))
            {
                _.trigger('jstore-error', ['JSTORE_STORAGE_FAILURE', this.jri, 'Flash Exception']);
            }
        },
        
        __remove: function (key)
        {
            this.database.jstore_remove(key);
        },
        
        /**
         *  Triggered whenever flash is ready.
         */
        __flashReadyListener: function ()
        {
            var iFrame = $('#jStoreFlashFrame')[0],
                frameDocument;
            
            //  MSIE
            if (iFrame.Document !== undefined && typecheck(iFrame.Document.jStoreFlash.jstore_get, 'Function'))
            {
                this.database = iFrame.Document.jStoreFlash;
            }
            
            //  Real Browsers
            else if (iFrame.contentWindow && iFrame.contentWindow.document)
            {
                frameDocument = $(iFrame.contentWindow.document);
                
                //  Webkit
                if (typecheck($('object', frameDocument)[0].jstore_get, 'Function'))
                {
                    this.database = $('object', frameDocument)[0];
                }
                
                //  Gecko
                else if (typecheck($('embed', frameDocument)[0].jstore_get, 'Function'))
                {
                    this.database = $('embed', frameDocument)[0];
                }
            }
            
            if (this.database === undefined)
            {
                throw 'JSTORE_FLASH_REFERENCE_ISSUE';
            }
            else
            {
                this.updateCache(true);
            }
        }
    }, 
    
    function ()
    {
        return hasFlashVersion('9.0.0');
    });
    
    //------------------------------
    //  Gears
    //------------------------------
    
    define(FLAVOR_GEARS, 
    {
        //------------------------------
        //  Properties
        //------------------------------
        
        limit: -1,
        
        //------------------------------
        //  Constructor
        //------------------------------
    
        init: function (project, name)
        {   
            this.database = google.gears.factory.create('beta.database');
            this.database.open('jstore-' + project);
            this.database.execute('CREATE TABLE IF NOT EXISTS jstore (k TEXT UNIQUE NOT NULL PRIMARY KEY, v TEXT NOT NULL)');
            
            this._super(project, name);
        },
        
        //------------------------------
        //  Methods
        //------------------------------
        
        updateCache: function ()
        {
            var result = this.database.execute('SELECT k,v FROM jstore');
            
            while (result.isValidRow())
            {
                this.data[result.field(0)] = prepareForRevival(result.field(1));
                result.next();
            }
            
            result.close();
            
            this._super();
        },
        
        //------------------------------
        //  Internal methods
        //------------------------------
        
        __set: function (key, value)
        {
            this.database.execute('BEGIN');
            this.database.execute('INSERT OR REPLACE INTO jstore(k, v) VALUES (?, ?)', [key, prepareForStorage(value)]);
            this.database.execute('COMMIT');
        },
        
        __remove: function (key)
        {
            this.database.execute('BEGIN');
            this.database.execute('DELETE FROM jstore WHERE k = ?', [key]);
            this.database.execute('COMMIT');
        }
    }, 
    
    function ()
    {
        return window.google !== undefined && window.google.gears !== undefined;
    });
    
    //------------------------------
    //  MSIE
    //------------------------------
        
    define(FLAVOR_MSIE, 
    {
        //------------------------------
        //  Properties
        //------------------------------
        
        limit: parseInt(1e4, 16),
        
        //------------------------------
        //  Constructor
        //------------------------------
    
        init: function (project, name)
        {   
            this.database = $('<div style="display:none;behavior:url(\'#default#userData\')" id="jstore-' + project + '"></div>')
                .appendTo(document.body).get(0);
            
            this._super(project, name);
        },
        
        //------------------------------
        //  Methods
        //------------------------------
        
        updateCache: function ()
        {
            this.database.load(this.project);
            
            var node = document.getElementById('jstore-' + this.project),
                xmlDoc = node.XMLDocument,
                root,
                index = 0;
                
            if (xmlDoc && xmlDoc.documentElement && xmlDoc.documentElement.attributes)
            {
                root = xmlDoc.documentElement;
                
                for (; index < root.attributes.length; ++index)
                {
                    this.data[root.attributes.item(index).nodeName] = prepareForRevival(root.attributes.item(index).nodeValue);
                }  
            }
            
            this._super();
        },
        
        //------------------------------
        //  Internal methods
        //------------------------------
        
        __set: function (key, value)
        {
            this.database.setAttribute(key, prepareForStorage(value));
            this.database.save(this.project);
        },
        
        __remove: function (key)
        {
            this.database.removeAttribute(key);
            this.database.save(this.project);
        }
    }, 
    
    function ()
    {
        return window.ActiveXObject !== undefined;
    });
    
}(jQuery, window));
