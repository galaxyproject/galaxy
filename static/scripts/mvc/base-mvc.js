/**
 * Simple base model for any visible element. Includes useful attributes and ability 
 * to set and track visibility.
 */
var BaseModel = Backbone.RelationalModel.extend({
    defaults: {
        name: null,
        hidden: false
    },
    
    show: function() {
        this.set("hidden", false);
    },
    
    hide: function() {
        this.set("hidden", true);
    },
    
    is_visible: function() {
        return !this.attributes.hidden;
    }
});


/**
 * Base view that handles visibility based on model's hidden attribute.
 */
var BaseView = Backbone.View.extend({
    
    initialize: function() {
        this.model.on("change:hidden", this.update_visible, this);
        this.update_visible();
    },
    
    update_visible: function() {
        if( this.model.attributes.hidden ){
            this.$el.hide();
        } else {
            this.$el.show();
        }
    }    
});

//==============================================================================
/**
 * Adds logging capabilities to your Models/Views
 *  can be used with plain browser console (or something more complex like an AJAX logger)
 *
 *  add to your models/views at the definition using chaining:
 *      var MyModel = BaseModel.extend( LoggableMixin ).extend({ // ... });
 * 
 *  or - more explicitly AFTER the definition:
 *      var MyModel = BaseModel.extend({
 *          logger  : console
 *          // ...
 *          this.log( '$#%& it! - broken already...' );
 *      })
 *      _.extend( MyModel.prototype, LoggableMixin )
 *
 * NOTE: currently only uses the console.debug log function (as opposed to debug, error, warn, etc.)
 */
var LoggableMixin = {
    // replace null with console (if available) to see all logs
    logger      : null,
    
    log : function(){
        return ( this.logger )?( this.logger.log.apply( this, arguments ) )
                              :( undefined );
    }
};


//==============================================================================
/**
 * Base class for template loaders:
 *      The main interface is loader.getTemplates( templatesToLoad )
 *          where templatesToLoad is in the form:
 *              {
 *                  remoteTemplateFilename1: {
 *                      templateFunctionName1 : templateID1,
 *                      templateFunctionName2 : templateID2,
 *                      ...
 *                  },
 *                  remoteTemplateFilename2: {
 *                      templateFunctionName3 : templateID3,
 *                      templateFunctionName4 : templateID4,
 *                      ...
 *                  }
 *              }
 *      getTemplates will return a map of the templates in the form:
 *              {
 *                  templateFunctionName1 : compiledTemplateFn1(),
 *                  templateFunctionName2 : compiledTemplateFn2(),
 *                  templateFunctionName3 : compiledTemplateFn3(),
 *                  ...
 *              }
 *
 *      Generally meant to be called for Backbone views, etc like this:
 *          BackboneView.templates = CompiledTemplateLoader( templatesToLoad );
 */
var TemplateLoader = _.extend( {}, LoggableMixin, {
    //TODO: incorporate caching of template functions (for use across objects)
    //TODO: only require and use 2 level (or some variation) map templatesToLoad for the remote loader
    
    // comment next line out to suppress logging
    //logger : console,
    
    //cachedTemplates : {},
    
    getTemplateLoadFn : function(){
        throw( "There is no templateLoadFn. Make sure you're using a subclass of TemplateLoader" );
    },
    
    // loop through templatesToLoad assuming it is a map in the form mentioned above
    getTemplates : function( templatesToLoad, forceReload ){
        forceReload = forceReload || false;
        this.log( this, 'getTemplates:', templatesToLoad, ', forceReload:', forceReload );
        
        //!TODO: cache templates here
        var templates = {},
            loader = this,
            templateLoadFn = this.getTemplateLoadFn();
        
        if( !templatesToLoad ){ return templates; }
        jQuery.each( templatesToLoad, function( templateFile, templateData ){
            
            //TODO: handle flatter map versions of templatesToLoad ({ name : id })
            jQuery.each( templateData, function( templateName, templateID ){
                loader.log( loader + ', templateFile:', templateFile,
                            'templateName:', templateName, ', templateID:', templateID );
                templates[ templateName ] = templateLoadFn.call( loader, templateFile, templateName, templateID );
            });
        });
        return templates;
    }
});


//..............................................................................
/** find the compiled template in Handlebars.templates by templateName
 *  and return the entire, requested templates map
 */
var CompiledTemplateLoader = _.extend( {}, TemplateLoader, {
    getTemplateLoadFn : function(){ return this.loadCompiledHandlebarsTemplate; },
    
    // override if new compiler
    loadCompiledHandlebarsTemplate : function( templateFile, templateName, templateID ){
        //pre: compiled templates should have been loaded with the mako helper h.templates
        //  (although these could be dynamically loaded as well?)
        this.log( 'getInDomTemplates, templateFile:', templateFile,
                  'templateName:', templateName, ', templateID:', templateID );
        
        if( !Handlebars.templates || !Handlebars.templates[ templateID ] ){
            throw( 'Template not found: Handlebars.' + templateID
                   + '. Check your h.templates() call in the mako file that rendered this page' );
        }
        this.log( 'found template function:', templateID );
        // really this is just a lookup
        return Handlebars.templates[ templateID ];
    }
    
    //TEST: Handlebars.full NOT runtime
    //TEST: no Handlebars
    //TEST: bad id
    //TEST: Handlebars.runtime, good id
});

//..............................................................................
/** find the NON-compiled template templateID in the DOM, compile it (using Handlebars),
 *  and return the entire, requested templates map
 *  (Note: for use with Mako.include and multiple templates)
 */
var InDomTemplateLoader = _.extend( {}, TemplateLoader, {
    
    // override or change if a new compiler (Underscore, etc.) is being used
    compileTemplate : function( templateText ){
        // we'll need the compiler
        if( !Handlebars || !Handlebars.compile ){
            throw( 'No Handlebars.compile found. You may only have Handlebars.runtime loaded.'
                   + 'Include handlebars.full for this to work' );
        }
        // copy fn ref to this view under the templateName
        this.log( 'compiling template:', templateText );
        return Handlebars.compile( templateText );
    },
    
    findTemplateInDom : function( templateFile, templateName, templateID ){
        // assume the last is best
        return $( 'script#' + templateID ).last();
    },
    
    getTemplateLoadFn : function(){ return this.loadInDomTemplate; },
    
    loadInDomTemplate : function( templateFile, templateName, templateID ){
        this.log( 'getInDomTemplate, templateFile:', templateFile,
                  'templateName:', templateName, ', templateID:', templateID );
        
        // find it in the dom by the id and compile
        var template = this.findTemplateInDom( templateFile, templateName, templateID );
        if( !template || !template.length ){
            throw( 'Template not found within the DOM: ' + templateID
                   + '. Check that this template has been included in the page' );
        }
        this.log( 'found template in dom:', template.html() );
        return this.compileTemplate( template.html() );
    }

    //TEST: no compiler
    //TEST: good url, good id, in DOM
    //TEST: good url, good id, NOT in DOM
});

//..............................................................................
/** HTTP GET the NON-compiled templates, append into the DOM, compile them,
 *  and return the entire, requested templates map
 *  (for use with dynamically loaded views)
 */
var RemoteTemplateLoader = _.extend( {}, InDomTemplateLoader, {
    templateBaseURL : 'static/scripts/templates/',
    
    getTemplateLoadFn : function(){ return this.loadViaHttpGet; },
    
    loadViaHttpGet : function( templateFile, templateName, templateID ){
        var templateBaseURL = 'static/scripts/templates/';
        this.log( 'loadViaHttpGet, templateFile:', templateFile,
                  'templateName:', templateName, ', templateID:', templateID,
                  'templateBaseURL:', this.templateBaseURL );
        
        //??: possibly not the best pattern here...
        // try in-dom first (prevent loading the same templateFile for each of its templates)
        var template = null;
        try {
            template = this.loadInDomTemplate( templateFile, templateName, templateID );
            
        // if that didn't work, load the templateFile via GET,...
        } catch( exception ){
            this.log( 'getInDomTemplate exception:' + exception );
            // handle no compiler exception
            if( !Handlebars.compile ){ throw( exception ); }
            //TEST:
            
            this.log( "Couldn't locate template in DOM: " + templateID );
            var loader = this;
            var url = templateBaseURL + templateFile;
            //??: async : false may cause problems in the long run
            jQuery.ajax( url, {
                method : 'GET',
                async : false,
                success : function( data ){
                    loader.log( templateFile + ' loaded via GET. Attempting compile...' );
                    //...move the templateFile into the DOM and try that again
                    $( 'body' ).append( data );
                    template = loader.loadInDomTemplate( templateFile, templateName, templateID );
                },
                error : function( data, status, xhr ){
                    throw( 'Failed to fetch ' + url + ':' + status );
                }
            });
        }
        if( !template ){
            throw( "Couldn't load or fetch template: " + templateID );
        }
        return template;
    }
    
    //TEST: no compiler
    //TEST: good url, good id, already local
    //TEST: good url, good id, remote load
    //TEST: good url, bad template id
    //TEST: bad url, error from ajax
});
