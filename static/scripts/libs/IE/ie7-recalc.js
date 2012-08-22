
// =========================================================================
// ie7-recalc.js
// =========================================================================

(function() {
  /* ---------------------------------------------------------------------
  
    This allows refreshing of IE7 style rules. If you modify the DOM
    you can update IE7 by calling document.recalc().
  
    This should be the LAST module included.
  
  --------------------------------------------------------------------- */
  
  if (!IE7.loaded) return;
  
  // remove all IE7 classes from an element
  CLASSES = /\sie7_class\d+/g;
  
  IE7.CSS.extend({
    // store for elements that have style properties calculated
    elements: {},
    handlers: [],
    
    // clear IE7 classes and styles
    reset: function() {
      this.removeEventHandlers();
      // reset IE7 classes here
      var elements = this.elements;
      for (var i in elements) elements[i].runtimeStyle.cssText = "";
      this.elements = {};
      // reset runtimeStyle here
      var elements = IE7.Rule.elements;
      for (var i in elements) {
        with (elements[i]) className = className.replace(CLASSES, "");
      }
      IE7.Rule.elements = {};
    },
    
    reload: function() {
      this.rules = [];
      this.getInlineStyles();
      this.screen.load();
      if (this.print) this.print.load();
      this.refresh();
      this.trash();
    },
    
    addRecalc: function(propertyName, test, handler, replacement) {
      // call the ancestor method to add a wrapped recalc method
      this.base(propertyName, test, function(element) {
        // execute the original recalc method
        handler(element);
        // store a reference to this element so we can clear its style later
        IE7.CSS.elements[element.uniqueID] = element;
      }, replacement);
    },
    
    recalc: function() {
      // clear IE7 styles and classes
      this.reset();
      // execute the ancestor method to perform recalculations
      this.base();
    },
    
    addEventHandler: function(element, type, handler) {
      element.attachEvent(type, handler);
      // store the handler so it can be detached later
      this.handlers.push(arguments);
    },
    
    removeEventHandlers: function() {
      var handler;
       while (handler = this.handlers.pop()) {
         handler[0].detachEvent(handler[1], handler[2]);
       }
    },
    
    getInlineStyles: function() {
      // load inline styles
      var styleSheets = document.getElementsByTagName("style"), styleSheet;
      for (var i = styleSheets.length - 1; (styleSheet = styleSheets[i]); i--) {
        if (!styleSheet.disabled && !styleSheet.ie7) {
          var cssText = styleSheet.cssText || styleSheet.innerHTML;
          this.styles.push(cssText);
          styleSheet.cssText = cssText;
        }
      }
    },
    
    trash: function() {
      // trash the old style sheets
      var styleSheets = document.styleSheets, styleSheet, i;
      for (i = 0; i < styleSheets.length; i++) {
        styleSheet = styleSheets[i];
        if (!styleSheet.ie7 && !styleSheet.cssText) {
          styleSheet.cssText = styleSheet.cssText;
        }
      }
      this.base();
    },
    
    getText: function(styleSheet) {
      return styleSheet.cssText || this.base(styleSheet);
    }
  });
  
  // remove event handlers (they eat memory)
  IE7.CSS.addEventHandler(window, "onunload", function() {
     IE7.CSS.removeEventHandlers();
  });
  
  // store all elements with an IE7 class assigned
  IE7.Rule.elements = {};

  IE7.Rule.prototype.extend({
    add: function(element) {
      // execute the ancestor "add" method
      this.base(element);
      // store a reference to this element so we can clear its classes later
      IE7.Rule.elements[element.uniqueID] = element;
    }
  });

  // store created pseudo elements
  if (IE7.PseudoElement) {
    IE7.PseudoElement.hash = {};
  
    IE7.PseudoElement.prototype.extend({
      create: function(target) {
        var key = this.selector + ":" + target.uniqueID;
        if (!IE7.PseudoElement.hash[key]) {
          IE7.PseudoElement.hash[key] = true;
          this.base(target);
        }
      }
    });
  }
  
  IE7.HTML.extend({
    elements: {},
    
    addRecalc: function(selector, handler) {
      // call the ancestor method to add a wrapped recalc method
      this.base(selector, function(element) {
        if (!this.elements[element.uniqueID]) {
          // execute the original recalc method
          handler(element);
          // store a reference to this element so that
          //  it is not "fixed" again
          this.elements[element.uniqueID] = element;
        }
      });
    }
  });
  
  // allow refreshing of IE7 fixes
  document.recalc = function(reload) {
    if (IE7.CSS.screen) {
      if (reload) IE7.CSS.reload();
      IE7.recalc();
    }
  };

})();
