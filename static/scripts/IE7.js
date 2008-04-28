// timestamp: Sun, 03 Feb 2008 19:26:22
/*
  IE7/IE8.js - copyright 2004-2008, Dean Edwards
  http://dean.edwards.name/IE7/
  http://www.opensource.org/licenses/mit-license.php
*/

/* W3C compliance for Microsoft Internet Explorer */

/* credits/thanks:
  Shaggy, Martijn Wargers, Jimmy Cerra, Mark D Anderson,
  Lars Dieckow, Erik Arvidsson, Gellért Gyuris, James Denny,
  Unknown W Brackets, Benjamin Westfarer, Rob Eberhardt,
  Bill Edney, Kevin Newman, James Crompton, Matthew Mastracci,
  Doug Wright, Richard York, Kenneth Kolano, MegaZone,
  Thomas Verelst, Mark 'Tarquin' Wilton-Jones, Rainer Åhlfors,
  David Zulaica, Ken Kolano, Kevin Newman
*/

// =======================================================================
// TO DO
// =======================================================================

// PNG - unclickable content

// =======================================================================
// TEST/BUGGY
// =======================================================================

// hr{margin:1em auto} (doesn't look right in IE5)

(function() {

IE7 = {
  toString: function(){return "IE7 version 2.0 (beta3)"}
};
var appVersion = IE7.appVersion = navigator.appVersion.match(/MSIE (\d\.\d)/)[1];

if (/ie7_off/.test(top.location.search) || appVersion < 5) return;

var Undefined = K();
var quirksMode = document.compatMode != "CSS1Compat";
var documentElement = document.documentElement, body, viewport;
var ANON = "!";
var HEADER = ":link{ie7-link:link}:visited{ie7-link:visited}";

// -----------------------------------------------------------------------
// external
// -----------------------------------------------------------------------

var RELATIVE = /^[\w\.]+[^:]*$/;
function makePath(href, path) {
  if (RELATIVE.test(href)) href = (path || "") + href;
  return href;
};

function getPath(href, path) {
  href = makePath(href, path);
  return href.slice(0, href.lastIndexOf("/") + 1);
};

// get the path to this script
var script = document.scripts[document.scripts.length - 1];
var path = getPath(script.src);

// we'll use microsoft's http request object to load external files
try {
  var httpRequest = new ActiveXObject("Microsoft.XMLHTTP");
} catch (e) {
  // ActiveX disabled
}

var fileCache = {};
function loadFile(href, path) {
try {
  href = makePath(href, path);
  if (!fileCache[href]) {
    // easy to load a file huh?
    httpRequest.open("GET", href, false);
    httpRequest.send();
    if (httpRequest.status == 0 || httpRequest.status == 200) {
      fileCache[href] = httpRequest.responseText;
    }
  }
} catch (e) {
  // ignore errors
} finally {
  return fileCache[href] || "";
}};

// -----------------------------------------------------------------------
// IE5.0 compatibility
// -----------------------------------------------------------------------


if (appVersion < 5.5) {
  undefined = Undefined();

  ANON = "HTML:!"; // for anonymous content
  
  // Fix String.replace (Safari1.x/IE5.0).
  var GLOBAL = /(g|gi)$/;
  var _String_replace = String.prototype.replace; 
  String.prototype.replace = function(expression, replacement) {
    if (typeof replacement == "function") { // Safari doesn't like functions
      if (expression && expression.constructor == RegExp) {
        var regexp = expression;
        var global = regexp.global;
        if (global == null) global = GLOBAL.test(regexp);
        // we have to convert global RexpExps for exec() to work consistently
        if (global) regexp = new RegExp(regexp.source); // non-global
      } else {
        regexp = new RegExp(rescape(expression));
      }
      var match, string = this, result = "";
      while (string && (match = regexp.exec(string))) {
        result += string.slice(0, match.index) + replacement.apply(this, match);
        string = string.slice(match.index + match[0].length);
        if (!global) break;
      }
      return result + string;
    }
    return _String_replace.apply(this, arguments);
  };
  
  Array.prototype.pop = function() {
    if (this.length) {
      var i = this[this.length - 1];
      this.length--;
      return i;
    }
    return undefined;
  };
  
  Array.prototype.push = function() {
    for (var i = 0; i < arguments.length; i++) {
      this[this.length] = arguments[i];
    }
    return this.length;
  };
  
  var ns = this;
  Function.prototype.apply = function(o, a) {
    if (o === undefined) o = ns;
    else if (o == null) o = window;
    else if (typeof o == "string") o = new String(o);
    else if (typeof o == "number") o = new Number(o);
    else if (typeof o == "boolean") o = new Boolean(o);
    if (arguments.length == 1) a = [];
    else if (a[0] && a[0].writeln) a[0] = a[0].documentElement.document || a[0];
    var $ = "#ie7_apply", r;
    o[$] = this;
    switch (a.length) { // unroll for speed
      case 0: r = o[$](); break;
      case 1: r = o[$](a[0]); break;
      case 2: r = o[$](a[0],a[1]); break;
      case 3: r = o[$](a[0],a[1],a[2]); break;
      case 4: r = o[$](a[0],a[1],a[2],a[3]); break;
      case 5: r = o[$](a[0],a[1],a[2],a[3],a[4]); break;
      default:
        var b = [], i = a.length - 1;
        do b[i] = "a[" + i + "]"; while (i--);
        eval("r=o[$](" + b + ")");
    }
    if (typeof o.valueOf == "function") { // not a COM object
      delete o[$];
    } else {
      o[$] = undefined;
      if (r && r.writeln) r = r.documentElement.document || r;
    }
    return r;
  };
  
  Function.prototype.call = function(o) {
    return this.apply(o, _slice.apply(arguments, [1]));
  };

  // block elements are "inline" according to IE5.0 so we'll fix it
  HEADER += "address,blockquote,body,dd,div,dt,fieldset,form,"+
    "frame,frameset,h1,h2,h3,h4,h5,h6,iframe,noframes,object,p,"+
    "hr,applet,center,dir,menu,pre,dl,li,ol,ul{display:block}";
}

// -----------------------------------------------------------------------
// OO support
// -----------------------------------------------------------------------


// This is a cut-down version of base2 (http://code.google.com/p/base2/)

var _slice = Array.prototype.slice;

// private
var _FORMAT = /%([1-9])/g;
var _LTRIM = /^\s\s*/;
var _RTRIM = /\s\s*$/;
var _RESCAPE = /([\/()[\]{}|*+-.,^$?\\])/g;           // safe regular expressions
var _BASE = /\bbase\b/;
var _HIDDEN = ["constructor", "toString"];            // only override these when prototyping

var prototyping;

function Base(){};
Base.extend = function(_instance, _static) {
  // Build the prototype.
  prototyping = true;
  var _prototype = new this;
  extend(_prototype, _instance);
  prototyping = false;

  // Create the wrapper for the constructor function.
  var _constructor = _prototype.constructor;
  function klass() {
    // Don't call the constructor function when prototyping.
    if (!prototyping) _constructor.apply(this, arguments);
  };
  _prototype.constructor = klass;

  // Build the static interface.
  klass.extend = arguments.callee;
  extend(klass, _static);
  klass.prototype = _prototype;
  return klass;
};
Base.prototype.extend = function(source) {
  return extend(this, source);
};

// A collection of regular expressions and their associated replacement values.
// A Base class for creating parsers.

var _HASH   = "#";
var _KEYS   = "~";

var _RG_ESCAPE_CHARS    = /\\./g;
var _RG_ESCAPE_BRACKETS = /\(\?[:=!]|\[[^\]]+\]/g;
var _RG_BRACKETS        = /\(/g;

var RegGrp = Base.extend({
  constructor: function(values) {
    this[_KEYS] = [];
    this.merge(values);
  },

  exec: function(string) {
    var items = this, keys = this[_KEYS];    
    return String(string).replace(new RegExp(this, this.ignoreCase ? "gi" : "g"), function() {
      var item, offset = 1, i = 0;
      // Loop through the RegGrp items.
      while ((item = items[_HASH + keys[i++]])) {
        var next = offset + item.length + 1;
        if (arguments[offset]) { // do we have a result?
          var replacement = item.replacement;
          switch (typeof replacement) {
            case "function":
              return replacement.apply(items, _slice.call(arguments, offset, next));
            case "number":
              return arguments[offset + replacement];
            default:
              return replacement;
          }
        }
        offset = next;
      }
    });
  },

  add: function(expression, replacement) {
    if (expression instanceof RegExp) {
      expression = expression.source;
    }
    if (!this[_HASH + expression]) this[_KEYS].push(String(expression));
    this[_HASH + expression] = new RegGrp.Item(expression, replacement);
  },

  merge: function(values) {
    for (var i in values) this.add(i, values[i]);
  },

  toString: function() {
    // back references not supported in simple RegGrp
    return "(" + this[_KEYS].join(")|(") + ")";
  }
}, {
  IGNORE: "$0",

  Item: Base.extend({
    constructor: function(expression, replacement) {
      expression = expression instanceof RegExp ? expression.source : String(expression);

      if (typeof replacement == "number") replacement = String(replacement);
      else if (replacement == null) replacement = "";

      // does the pattern use sub-expressions?
      if (typeof replacement == "string" && /\$(\d+)/.test(replacement)) {
        // a simple lookup? (e.g. "$2")
        if (/^\$\d+$/.test(replacement)) {
          // store the index (used for fast retrieval of matched strings)
          replacement = parseInt(replacement.slice(1));
        } else { // a complicated lookup (e.g. "Hello $2 $1")
          // build a function to do the lookup
          var Q = /'/.test(replacement.replace(/\\./g, "")) ? '"' : "'";
          replacement = replacement.replace(/\n/g, "\\n").replace(/\r/g, "\\r").replace(/\$(\d+)/g, Q +
            "+(arguments[$1]||" + Q+Q + ")+" + Q);
          replacement = new Function("return " + Q + replacement.replace(/(['"])\1\+(.*)\+\1\1$/, "$1") + Q);
        }
      }

      this.length = RegGrp.count(expression);
      this.replacement = replacement;
      this.toString = K(expression);
    }
  }),

  count: function(expression) {
    // Count the number of sub-expressions in a RegExp/RegGrp.Item.
    expression = String(expression).replace(_RG_ESCAPE_CHARS, "").replace(_RG_ESCAPE_BRACKETS, "");
    return match(expression, _RG_BRACKETS).length;
  }
});

// =========================================================================
// lang/extend.js
// =========================================================================

function extend(object, source) { // or extend(object, key, value)
  if (object && source) {
    var proto = (typeof source == "function" ? Function : Object).prototype;
    // Add constructor, toString etc
    var i = _HIDDEN.length, key;
    if (prototyping) while (key = _HIDDEN[--i]) {
      var value = source[key];
      if (value != proto[key]) {
        if (_BASE.test(value)) {
          _override(object, key, value)
        } else {
          object[key] = value;
        }
      }
    }
    // Copy each of the source object's properties to the target object.
    for (key in source) if (proto[key] === undefined) {
      var value = source[key];
      // Check for method overriding.
      if (object[key] && typeof value == "function" && _BASE.test(value)) {
        _override(object, key, value);
      } else {
        object[key] = value;
      }
    }
  }
  return object;
};

function _override(object, name, method) {
  // Override an existing method.
  var ancestor = object[name];
  object[name] = function() {
    var previous = this.base;
    this.base = ancestor;
    var returnValue = method.apply(this, arguments);
    this.base = previous;
    return returnValue;
  };
};

function combine(keys, values) {
  // Combine two arrays to make a hash.
  if (!values) values = keys;
  var hash = {};
  for (var i in keys) hash[i] = values[i];
  return hash;
};

function format(string) {
  // Replace %n with arguments[n].
  // e.g. format("%1 %2%3 %2a %1%3", "she", "se", "lls");
  // ==> "she sells sea shells"
  // Only %1 - %9 supported.
  var args = arguments;
  var _FORMAT = new RegExp("%([1-" + arguments.length + "])", "g");
  return String(string).replace(_FORMAT, function(match, index) {
    return index < args.length ? args[index] : match;
  });
};

function match(string, expression) {
  // Same as String.match() except that this function will return an empty
  // array if there is no match.
  return String(string).match(expression) || [];
};

function rescape(string) {
  // Make a string safe for creating a RegExp.
  return String(string).replace(_RESCAPE, "\\$1");
};

// http://blog.stevenlevithan.com/archives/faster-trim-javascript
function trim(string) {
  return String(string).replace(_LTRIM, "").replace(_RTRIM, "");
};

function K(k) {
  return function() {
    return k;
  };
};

// -----------------------------------------------------------------------
// parsing
// -----------------------------------------------------------------------

var Parser = RegGrp.extend({ignoreCase: true});

var ENCODED = /\x01(\d+)/g,
    QUOTES  = /'/g, 
    STRING = /^\x01/,
    UNICODE = /\\([\da-fA-F]{1,4})/g;

var _strings = [];

var encoder = new Parser({
  // comments
  "<!\\-\\-|\\-\\->": "",
  "\\/\\*[^*]*\\*+([^\\/][^*]*\\*+)*\\/": "",
  // get rid
  "@(namespace|import)[^;\\n]+[;\\n]": "",
  // strings
  "'(\\\\.|[^'\\\\])*'": encodeString,
  '"(\\\\.|[^"\\\\])*"': encodeString,
  // white space
  "\\s+": " "
});

function encode(cssText) {
  return encoder.exec(cssText);
};

function decode(cssText) {
  return cssText.replace(ENCODED, function(match, index) {
    return _strings[index - 1];
  });
};

function encodeString(string) {
  return "\x01" + _strings.push(string.replace(UNICODE, function(match, chr) {
    return eval("'\\u" + "0000".slice(chr.length) + chr + "'");
  }).slice(1, -1).replace(QUOTES, "\\'"));
};

function getString(value) {
  return STRING.test(value) ? _strings[value.slice(1) - 1] : value;
};

// clone a "width" function to create a "height" function
var rotater = new RegGrp({
  Width: "Height",
  width: "height",
  Left:  "Top",
  left:  "top",
  Right: "Bottom",
  right: "bottom",
  onX:   "onY"
});

function rotate(fn) {
  return rotater.exec(fn);
};

// -----------------------------------------------------------------------
// event handling
// -----------------------------------------------------------------------

var eventHandlers = [];

function addResize(handler) {
  addRecalc(handler);
  addEventHandler(window, "onresize", handler);
};

// add an event handler (function) to an element
function addEventHandler(element, type, handler) {
  element.attachEvent(type, handler);
  // store the handler so it can be detached later
  eventHandlers.push(arguments);
};

// remove an event handler assigned to an element by IE7
function removeEventHandler(element, type, handler) {
try {
  element.detachEvent(type, handler);
} catch (ignore) {
  // write a letter of complaint to microsoft..
}};

// remove event handlers (they eat memory)
addEventHandler(window, "onunload", function() {
  var handler;
  while (handler = eventHandlers.pop()) {
    removeEventHandler(handler[0], handler[1], handler[2]);
  }
});

function register(handler, element, condition) { // -@DRE
  //var set = handler[element.uniqueID];
  if (!handler.elements) handler.elements = {};
  if (condition) handler.elements[element.uniqueID] = element;
  else delete handler.elements[element.uniqueID];
  //return !set && condition;
  return condition;
};

addEventHandler(window, "onbeforeprint", function() {
  if (!IE7.CSS.print) new StyleSheet("print");
  IE7.CSS.print.recalc();
});

// -----------------------------------------------------------------------
// pixel conversion
// -----------------------------------------------------------------------

// this is handy because it means that web developers can mix and match
//  measurement units in their style sheets. it is not uncommon to
//  express something like padding in "em" units whilst border thickness
//  is most often expressed in pixels.

var PIXEL = /^\d+(px)?$/i;
var PERCENT = /^\d+%$/;
var getPixelValue = function(element, value) {
  if (PIXEL.test(value)) return parseInt(value);
  var style = element.style.left;
  var runtimeStyle = element.runtimeStyle.left;
  element.runtimeStyle.left = element.currentStyle.left;
  element.style.left = value || 0;
  value = element.style.pixelLeft;
  element.style.left = style;
  element.runtimeStyle.left = runtimeStyle;
  return value;
};

// -----------------------------------------------------------------------
// generic
// -----------------------------------------------------------------------

var $IE7 = "ie7-";

var Fix = Base.extend({
  constructor: function() {
    this.fixes = [];
    this.recalcs = [];
  },
  init: Undefined
});

// a store for functions that will be called when refreshing IE7
var recalcs = [];
function addRecalc(recalc) {
  recalcs.push(recalc);
};

IE7.recalc = function() {
  IE7.HTML.recalc();
  // re-apply style sheet rules (re-calculate ie7 classes)
  IE7.CSS.recalc();
  // apply global fixes to the document
  for (var i = 0; i < recalcs.length; i++) recalcs[i]();
};

function isFixed(element) {
  return element.currentStyle["ie7-position"] == "fixed";
};

// original style
function getDefinedStyle(element, propertyName) {
  return element.currentStyle[$IE7 + propertyName] || element.currentStyle[propertyName];
};

function setOverrideStyle(element, propertyName, value) {
  if (element.currentStyle[$IE7 + propertyName] == null) {
    element.runtimeStyle[$IE7 + propertyName] = element.currentStyle[propertyName];
  }
  element.runtimeStyle[propertyName] = value;
};

// create a temporary element which is used to inherit styles
//  from the target element. the temporary element can be resized
//  to determine pixel widths/heights
function createTempElement(tagName) {
  var element = document.createElement(tagName || "object");
  element.style.cssText = "position:absolute;padding:0;display:block;border:none;clip:rect(0 0 0 0);left:-9999";
  element.ie7_anon = true;
  return element;
};


// =========================================================================
// ie7-cssQuery.js
// =========================================================================

function cssQuery(selector, context, single) {
  if (!_cache[selector]) {
    reg = []; // store for RegExp objects
    var fn = "";
    var selectors = cssParser.escape(selector).split(",");
    for (var i = 0; i < selectors.length; i++) {
      _wild = _index = _list = 0; // reset
      _duplicate = selectors.length > 1 ? 2 : 0; // reset
      var block = cssParser.exec(selectors[i]) || "if(0){";
      if (_wild) { // IE's pesky comment nodes
        block += format("if(e%1.nodeName!='!'){", _index);
      }
      // check for duplicates before storing results
      var store = _duplicate > 1 ? _TEST : "";
      block += format(store + _STORE, _index);
      // add closing braces
      block += Array(match(block, /\{/g).length + 1).join("}");
      fn += block;
    }
    eval(format(_FN, reg) + cssParser.unescape(fn) + "return s?null:r}");
    _cache[selector] = _selectorFunction;
  }
  return _cache[selector](context || document, single);
};

var _MSIE5 = appVersion < 6;

var _EVALUATED = /^(href|src)$/;
var _ATTRIBUTES = {
  "class": "className",
  "for": "htmlFor"
};

IE7._indexed = 1;

IE7._byId = function(document, id) {
  var result = document.all[id] || null;
  // returns a single element or a collection
  if (!result || result.id == id) return result;
  // document.all has returned a collection of elements with name/id
  for (var i = 0; i < result.length; i++) {
    if (result[i].id == id) return result[i];
  }
  return null;
};

IE7._getAttribute = function(element, name) {
  if (name == "src" && element.pngSrc) return element.pngSrc;
  
  var attribute = _MSIE5 ? (element.attributes[name] || element.attributes[_ATTRIBUTES[name.toLowerCase()]]) : element.getAttributeNode(name);
  if (attribute && (attribute.specified || name == "value")) {
    if (_EVALUATED.test(name)) {
      return element.getAttribute(name, 2);
    } else if (name == "class") {
     return element.className.replace(/\sie7_\w+/g, "");
    } else if (name == "style") {
     return element.style.cssText;
    } else {
     return attribute.nodeValue;
    }
  }
  return null;
};

var names = "colSpan,rowSpan,vAlign,dateTime,accessKey,tabIndex,encType,maxLength,readOnly,longDesc";
// Convert the list of strings to a hash, mapping the lowercase name to the camelCase name.
extend(_ATTRIBUTES, combine(names.toLowerCase().split(","), names.split(",")));

IE7._getNextElementSibling = function(node) {
  // return the next element to the supplied element
  //  nextSibling is not good enough as it might return a text or comment node
  while (node && (node = node.nextSibling) && (node.nodeType != 1 || node.nodeName == "!")) continue;
  return node;
};

IE7._getPreviousElementSibling = function(node) {
  // return the previous element to the supplied element
  while (node && (node = node.previousSibling) && (node.nodeType != 1 || node.nodeName == "!")) continue;
  return node;
};

// =========================================================================
// CSSParser
// =========================================================================

var IMPLIED_ASTERISK = /([\s>+~,]|[^(]\+|^)([#.:\[])/g,
    IMPLIED_SPACE =    /(^|,)([^\s>+~])/g,
    WHITESPACE =       /\s*([\s>+~(),]|^|$)\s*/g,
    WILD_CARD =        /\s\*\s/g;;

var CSSParser = RegGrp.extend({
  constructor: function(items) {
    this.base(items);
    this.sorter = new RegGrp;
    this.sorter.add(/:not\([^)]*\)/, RegGrp.IGNORE);
    this.sorter.add(/([ >](\*|[\w-]+))([^: >+~]*)(:\w+-child(\([^)]+\))?)([^: >+~]*)/, "$1$3$6$4");
  },
  
  ignoreCase: true,

  escape: function(selector) {
    return this.optimise(this.format(selector));
  },

  format: function(selector) {
    return selector
      .replace(WHITESPACE, "$1")
      .replace(IMPLIED_SPACE, "$1 $2")
      .replace(IMPLIED_ASTERISK, "$1*$2");
  },

  optimise: function(selector) {
    // optimise wild card descendant selectors
    return this.sorter.exec(selector.replace(WILD_CARD, ">* "));
  },

  unescape: function(selector) {
    return decode(selector);
  }
});

// some constants
var _OPERATORS = {
  "":   "%1!=null",
  "=":  "%1=='%2'",
  "~=": /(^| )%1( |$)/,
  "|=": /^%1(-|$)/,
  "^=": /^%1/,
  "$=": /%1$/,
  "*=": /%1/
};

var _PSEUDO_CLASSES = {
  "first-child": "!IE7._getPreviousElementSibling(e%1)",
  "link":        "e%1.currentStyle['ie7-link']=='link'",
  "visited":     "e%1.currentStyle['ie7-link']=='visited'"
};

var _VAR = "var p%2=0,i%2,e%2,n%2=e%1.";
var _ID = "e%1.sourceIndex";
var _TEST = "var g=" + _ID + ";if(!p[g]){p[g]=1;";
var _STORE = "r[r.length]=e%1;if(s)return e%1;";
var _FN = "var _selectorFunction=function(e0,s){IE7._indexed++;var r=[],p={},reg=[%1],d=document;";
var reg; // a store for RexExp objects
var _index;
var _wild; // need to flag certain _wild card selectors as MSIE includes comment nodes
var _list; // are we processing a node _list?
var _duplicate; // possible duplicates?
var _cache = {}; // store parsed selectors

// a hideous parser
var cssParser = new CSSParser({
  " (\\*|[\\w-]+)#([\\w-]+)": function(match, tagName, id) { // descendant selector followed by ID
    _wild = false;
    var replacement = "var e%2=IE7._byId(d,'%4');if(e%2&&";
    if (tagName != "*") replacement += "e%2.nodeName=='%3'&&";
    replacement += "(e%1==d||e%1.contains(e%2))){";
    if (_list) replacement += format("i%1=n%1.length;", _list);
    return format(replacement, _index++, _index, tagName.toUpperCase(), id);
  },
  
  " (\\*|[\\w-]+)": function(match, tagName) { // descendant selector
    _duplicate++; // this selector may produce duplicates
    _wild = tagName == "*";
    var replacement = _VAR;
    // IE5.x does not support getElementsByTagName("*");
    replacement += (_wild && _MSIE5) ? "all" : "getElementsByTagName('%3')";
    replacement += ";for(i%2=0;(e%2=n%2[i%2]);i%2++){";
    return format(replacement, _index++, _list = _index, tagName.toUpperCase());
  },
  
  ">(\\*|[\\w-]+)": function(match, tagName) { // child selector
    var children = _list;
    _wild = tagName == "*";
    var replacement = _VAR;
    // use the children property for MSIE as it does not contain text nodes
    //  (but the children collection still includes comments).
    // the document object does not have a children collection
    replacement += children ? "children": "childNodes";
    if (!_wild && children) replacement += ".tags('%3')";
    replacement += ";for(i%2=0;(e%2=n%2[i%2]);i%2++){";
    if (_wild) {
      replacement += "if(e%2.nodeType==1){";
      _wild = _MSIE5;
    } else {
      if (!children) replacement += "if(e%2.nodeName=='%3'){";
    }
    return format(replacement, _index++, _list = _index, tagName.toUpperCase());
  },
  
  "\\+(\\*|[\\w-]+)": function(match, tagName) { // direct adjacent selector
    var replacement = "";
    if (_wild) replacement += "if(e%1.nodeName!='!'){";
    _wild = false;
    replacement += "e%1=IE7._getNextElementSibling(e%1);if(e%1";
    if (tagName != "*") replacement += "&&e%1.nodeName=='%2'";
    replacement += "){";
    return format(replacement, _index, tagName.toUpperCase());
  },
  
  "~(\\*|[\\w-]+)": function(match, tagName) { // indirect adjacent selector
    var replacement = "";
    if (_wild) replacement += "if(e%1.nodeName!='!'){";
    _wild = false;
    _duplicate = 2; // this selector may produce duplicates
    replacement += "while(e%1=e%1.nextSibling){if(e%1.ie7_adjacent==IE7._indexed)break;if(";
    if (tagName == "*") {
      replacement += "e%1.nodeType==1";
      if (_MSIE5) replacement += "&&e%1.nodeName!='!'";
    } else replacement += "e%1.nodeName=='%2'";
    replacement += "){e%1.ie7_adjacent=IE7._indexed;";
    return format(replacement, _index, tagName.toUpperCase());
  },
  
  "#([\\w-]+)": function(match, id) { // ID selector
    _wild = false;
    var replacement = "if(e%1.id=='%2'){";
    if (_list) replacement += format("i%1=n%1.length;", _list);
    return format(replacement, _index, id);
  },
  
  "\\.([\\w-]+)": function(match, className) { // class selector
    _wild = false;
    // store RegExp objects - slightly faster on IE
    reg.push(new RegExp("(^|\\s)" + rescape(className) + "(\\s|$)"));
    return format("if(e%1.className&&reg[%2].test(e%1.className)){", _index, reg.length - 1);
  },
  
  "\\[([\\w-]+)\\s*([^=]?=)?\\s*([^\\]]*)\\]": function(match, attr, operator, value) { // attribute selectors
    var alias = _ATTRIBUTES[attr] || attr;
    if (operator) {
      var getAttribute = "e%1.getAttribute('%2',2)";
      if (!_EVALUATED.test(attr)) {
        getAttribute = "e%1.%3||" + getAttribute;
      }
      attr = format("(" + getAttribute + ")", _index, attr, alias);
    } else {
      attr = format("IE7._getAttribute(e%1,'%2')", _index, attr);
    }
    var replacement = _OPERATORS[operator || ""] || "0";
    if (replacement && replacement.source) {
      reg.push(new RegExp(format(replacement.source, rescape(cssParser.unescape(value)))));
      replacement = "reg[%2].test(%1)";
      value = reg.length - 1;
    }
    return "if(" + format(replacement, attr, value) + "){";
  },
  
  ":+([\\w-]+)(\\(([^)]+)\\))?": function(match, pseudoClass, $2, args) { // pseudo class selectors
    pseudoClass = _PSEUDO_CLASSES[pseudoClass];
    return "if(" + (pseudoClass ? format(pseudoClass, _index, args || "")  : "0") + "){";
  }
});

// =========================================================================
// ie7-css.js
// =========================================================================

var HYPERLINK = /a(#[\w-]+)?(\.[\w-]+)?:(hover|active)/i;
var BRACE1 = /\s*\{\s*/, BRACE2 = /\s*\}\s*/, COMMA = /\s*\,\s*/;
var FIRST_LINE_LETTER = /(.*)(:first-(line|letter))/;

//var UNKNOWN = /UNKNOWN|([:.])\w+\1/i;

var styleSheets = document.styleSheets;

IE7.CSS = new (Fix.extend({ // single instance
  parser: new Parser,
  screen: "",
  print: "",
  styles: [],
  rules: [],
  pseudoClasses: appVersion < 7 ? "first\\-child" : "",
  dynamicPseudoClasses: {
    toString: function() {
      var strings = [];
      for (var pseudoClass in this) strings.push(pseudoClass);
      return strings.join("|");
    }
  },
  
  init: function() {
    var NONE = "^\x01$";
    var CLASS = "\\[class=?[^\\]]*\\]";
    var pseudoClasses = [];
    if (this.pseudoClasses) pseudoClasses.push(this.pseudoClasses);
    var dynamicPseudoClasses = this.dynamicPseudoClasses.toString(); 
    if (dynamicPseudoClasses) pseudoClasses.push(dynamicPseudoClasses);
    pseudoClasses = pseudoClasses.join("|");
    var unknown = appVersion < 7 ? ["[>+~[(]|([:.])\\w+\\1"] : [CLASS];
    if (pseudoClasses) unknown.push(":(" + pseudoClasses + ")");
    this.UNKNOWN = new RegExp(unknown.join("|") || NONE, "i");
    var complex = appVersion < 7 ? ["\\[[^\\]]+\\]|[^\\s(\\[]+\\s*[+~]"] : [CLASS];
    var complexRule = complex.concat();
    if (pseudoClasses) complexRule.push(":(" + pseudoClasses + ")");
    Rule.COMPLEX = new RegExp(complexRule.join("|") || NONE, "ig");
    if (this.pseudoClasses) complex.push(":(" + this.pseudoClasses + ")");
    DynamicRule.COMPLEX = new RegExp(complex.join("|") || NONE, "i");
    DynamicRule.MATCH = new RegExp(dynamicPseudoClasses ? "(.*):(" + dynamicPseudoClasses + ")(.*)" : NONE, "i");
    
    this.createStyleSheet();
    this.refresh();
  },
  
	addEventHandler: function() {
		addEventHandler.apply(null, arguments);
	},
  
  addFix: function(expression, replacement) {
    this.parser.add(expression, replacement);
  },
  
  addRecalc: function(propertyName, test, handler, replacement) {
    // recalcs occur whenever the document is refreshed using document.recalc()
    test = new RegExp("([{;\\s])" + propertyName + "\\s*:\\s*" + test + "[^;}]*");
    var id = this.recalcs.length;
    if (replacement) replacement = propertyName + ":" + replacement;
    this.addFix(test, function(match, $1) {
      return (replacement ? $1 + replacement : match) + ";ie7-" + match.slice(1) + ";ie7_recalc" + id + ":1";
    });
    this.recalcs.push(arguments);
    return id;
  },
  
  apply: function() {
    this.getInlineStyles();
    new StyleSheet("screen");
    this.trash();
  },
  
  createStyleSheet: function() {
    // create the IE7 style sheet
    this.styleSheet = document.createStyleSheet();
    // flag it so we can ignore it during parsing
    this.styleSheet.ie7 = true;
    this.styleSheet.owningElement.ie7 = true;
    this.styleSheet.cssText = HEADER;
  },
  
  getInlineStyles: function() {
    // load inline styles
    var styleSheets = document.getElementsByTagName("style"), styleSheet;
    for (var i = styleSheets.length - 1; (styleSheet = styleSheets[i]); i--) {
      if (!styleSheet.disabled && !styleSheet.ie7) {
        this.styles.push(styleSheet.innerHTML);
      }
    }
  },
  
  getText: function(styleSheet, path) {
    // explorer will trash unknown selectors (it converts them to "UNKNOWN").
    // so we must reload external style sheets (internal style sheets can have their text
    //  extracted through the innerHTML property).
      // load the style sheet text from an external file
    try {
      var cssText = styleSheet.cssText;
    } catch (e) {
      cssText = "";
    }
    if (httpRequest) cssText = loadFile(styleSheet.href, path) || cssText;
    return cssText;
  },
  
  recalc: function() {
    this.screen.recalc();
    // we're going to read through all style rules.
    //  certain rules have had ie7 properties added to them.
    //   e.g. p{top:0; ie7_recalc2:1; left:0}
    //  this flags a property in the rule as needing a fix.
    //  the selector text is then used to query the document.
    //  we can then loop through the results of the query
    //  and fix the elements.
    // we ignore the IE7 rules - so count them in the header
    var RECALCS = /ie7_recalc\d+/g;
    var start = HEADER.match(/[{,]/g).length;
    // only calculate screen fixes. print fixes don't show up anyway
    var stop = start + (this.screen.cssText.match(/\{/g)||"").length;
    var rules = this.styleSheet.rules, rule;
    var calcs, calc, elements, element, i, j, k, id;
    // loop through all rules
    for (i = start; i < stop; i++) {
      rule = rules[i];
      var cssText = rule.style.cssText;
      // search for the "ie7_recalc" flag (there may be more than one)
      if (rule && (calcs = cssText.match(RECALCS))) {
        // use the selector text to query the document
        elements = cssQuery(rule.selectorText);
        // if there are matching elements then loop
        //  through the recalc functions and apply them
        //  to each element
        if (elements.length) for (j = 0; j < calcs.length; j++) {
          // get the matching flag (e.g. ie7_recalc3)
          id = calcs[j];
          // extract the numeric id from the end of the flag
          //  and use it to index the collection of recalc
          //  functions
          calc = IE7.CSS.recalcs[id.slice(10)][2];
          for (k = 0; (element = elements[k]); k++) {
            // apply the fix
            if (element.currentStyle[id]) calc(element, cssText);
          }
        }
      }
    }
  },
  
  refresh: function() {
    this.styleSheet.cssText = HEADER + this.screen + this.print;
  },
  
  trash: function() {
    // trash the old style sheets
    for (var i = 0; i < styleSheets.length; i++) {
      if (!styleSheets[i].ie7) {
        try {
          var cssText = styleSheets[i].cssText;
        } catch (e) {
          cssText = "";
        }
        if (cssText) styleSheets[i].cssText = "";
      }
    }
  }
}));

// -----------------------------------------------------------------------
//  IE7 StyleSheet class
// -----------------------------------------------------------------------

var StyleSheet = Base.extend({
  constructor: function(media) {
    this.media = media;
    this.load();
    IE7.CSS[media] = this;
    IE7.CSS.refresh();
  },
  
  createRule: function(selector, cssText) {
    if (IE7.CSS.UNKNOWN.test(selector)) {
      var match;
      if (PseudoElement && (match = selector.match(PseudoElement.MATCH))) {
        return new PseudoElement(match[1], match[2], cssText);
      } else if (match = selector.match(DynamicRule.MATCH)) {
        if (!HYPERLINK.test(match[0]) || DynamicRule.COMPLEX.test(match[0])) {
          return new DynamicRule(selector, match[1], match[2], match[3], cssText);
        }
      } else return new Rule(selector, cssText);
    }
    return selector + " {" + cssText + "}";
  },
  
  getText: function() {
    // store for style sheet text
    var _inlineStyles = [].concat(IE7.CSS.styles);
    // parse media decalarations
    var MEDIA = /@media\s+([^{]*)\{([^@]+\})\s*\}/gi;
    var ALL = /\ball\b|^$/i, SCREEN = /\bscreen\b/i, PRINT = /\bprint\b/i;
    function _parseMedia(cssText, media) {
      _filterMedia.value = media;
      return cssText.replace(MEDIA, _filterMedia);
    };
    function _filterMedia(match, media, cssText) {
      media = _simpleMedia(media);
      switch (media) {
        case "screen":
        case "print":
          if (media != _filterMedia.value) return "";
        case "all":
          return cssText;
      }
      return "";
    };
    function _simpleMedia(media) {
      if (ALL.test(media)) return "all";
      else if (SCREEN.test(media)) return (PRINT.test(media)) ? "all" : "screen";
      else if (PRINT.test(media)) return "print";
    };
    var self = this;
    function _getCSSText(styleSheet, path, media, level) {
      var cssText = "";
      if (!level) {
        media = _simpleMedia(styleSheet.media);
        level = 0;
      }
      if (media == "all" || media == self.media) {
        // IE only allows importing style sheets three levels deep.
        // it will crash if you try to access a level below this
        if (level < 3) {
          // loop through imported style sheets
          for (var i = 0; i < styleSheet.imports.length; i++) {
            // call this function recursively to get all imported style sheets
            cssText += _getCSSText(styleSheet.imports[i], getPath(styleSheet.href, path), media, level + 1);
          }
        }
        // retrieve inline style or load an external style sheet
        cssText += encode(styleSheet.href ? _loadStyleSheet(styleSheet, path) : _inlineStyles.pop() || "");
        cssText = _parseMedia(cssText, self.media);
      }
      return cssText;
    };
    // store loaded cssText URLs
    var fileCache = {};
    // load an external style sheet
    function _loadStyleSheet(styleSheet, path) {
      var url = makePath(styleSheet.href, path);
      // if the style sheet has already loaded then don't duplicate it
      if (fileCache[url]) return "";
      // load from source
      fileCache[url] = (styleSheet.disabled) ? "" :
        _fixUrls(IE7.CSS.getText(styleSheet, path), getPath(styleSheet.href, path));
      return fileCache[url];
    };
    // fix css paths
    // we're lumping all css text into one big style sheet so relative
    //  paths have to be fixed. this is necessary anyway because of other
    //  explorer bugs.
    var URL = /(url\s*\(\s*['"]?)([\w\.]+[^:\)]*['"]?\))/gi;
    function _fixUrls(cssText, pathname) {
      // hack & slash
      return cssText.replace(URL, "$1" + pathname.slice(0, pathname.lastIndexOf("/") + 1) + "$2");
    };

    // load all style sheets in the document
    for (var i = 0; i < styleSheets.length; i++) {
      if (!styleSheets[i].disabled && !styleSheets[i].ie7) {
        this.cssText += _getCSSText(styleSheets[i]);
      }
    }
  },
  
  load: function() {
    this.cssText = "";
    this.getText();
    this.parse();
    this.cssText = decode(this.cssText);
    fileCache = {};
  },
  
  parse: function() {
    this.cssText = IE7.CSS.parser.exec(this.cssText);
    
    // parse the style sheet
    var offset = IE7.CSS.rules.length;
    var rules = this.cssText.split(BRACE2), rule;
    var selectors, cssText, i, j;
    for (i = 0; i < rules.length; i++) {
      rule = rules[i].split(BRACE1);
      selectors = rule[0].split(COMMA);
      cssText = rule[1];
      for (j = 0; j < selectors.length; j++) {
        selectors[j] = cssText ? this.createRule(selectors[j], cssText) : "";
      }
      rules[i] = selectors.join("\n");
    }
    this.cssText = rules.join("\n");
    this.rules = IE7.CSS.rules.slice(offset);
  },
  
  recalc: function() {
    var rule, i;
    for (i = 0; (rule = this.rules[i]); i++) rule.recalc();
  },
  
  toString: function() {
    return "@media " + this.media + "{" + this.cssText + "}";
  }
});

var PseudoElement;

// -----------------------------------------------------------------------
// IE7 style rules
// -----------------------------------------------------------------------

var Rule = IE7.Rule = Base.extend({
  // properties
  constructor: function(selector, cssText) {
    this.id = IE7.CSS.rules.length;
    this.className = Rule.PREFIX + this.id;
    selector = selector.match(FIRST_LINE_LETTER) || selector || "*";
    this.selector = selector[1] || selector;
    this.selectorText = this.parse(this.selector) + (selector[2] || "");
    this.cssText = cssText;
    this.MATCH = new RegExp("\\s" + this.className + "(\\s|$)", "g");
    IE7.CSS.rules.push(this);
    this.init();
  },
  
  init: Undefined,
  
  add: function(element) {
    // allocate this class
    element.className += " " + this.className;
  },
  
  recalc: function() {
    // execute the underlying css query for this class
    var match = cssQuery(this.selector);
    // add the class name for all matching elements
    for (var i = 0; i < match.length; i++) this.add(match[i]);
  },

  parse: function(selector) {
    // attempt to preserve specificity for "loose" parsing by
    //  removing unknown tokens from a css selector but keep as
    //  much as we can..
    var simple = selector.replace(Rule.CHILD, " ").replace(Rule.COMPLEX, "");
    if (appVersion < 7) simple = simple.replace(Rule.MULTI, "");
    var tags = match(simple, Rule.TAGS).length - match(selector, Rule.TAGS).length;
    var classes = match(simple, Rule.CLASSES).length - match(selector, Rule.CLASSES).length + 1;
    while (classes > 0 && Rule.CLASS.test(simple)) {
      simple = simple.replace(Rule.CLASS, "");
      classes--;
    }
    while (tags > 0 && Rule.TAG.test(simple)) {
      simple = simple.replace(Rule.TAG, "$1*");
      tags--;
    }
    simple += "." + this.className;
    classes = Math.min(classes, 2);
    tags = Math.min(tags, 2);
    var score = -10 * classes - tags;
    if (score > 0) {
      simple = simple + "," + Rule.MAP[score] + " " + simple;
    }
    return simple;
  },
  
  remove: function(element) {
    // deallocate this class
    element.className = element.className.replace(this.MATCH, "$1");
  },
  
  toString: function() {
    return format("%1 {%2}", this.selectorText, this.cssText);
  }
}, {
  CHILD: />/g,
  CLASS: /\.[\w-]+/,
  CLASSES: /[.:\[]/g,
  MULTI: /(\.[\w-]+)+/g,
  PREFIX: "ie7_class",
  TAG: /^\w+|([\s>+~])\w+/,
  TAGS: /^\w|[\s>+~]\w/g,
  MAP: {
    1:  "html",
    2:  "html body",
    10: ".ie7_html",
    11: "html.ie7_html",
    12: "html.ie7_html body",
    20: ".ie7_html .ie7_body",
    21: "html.ie7_html .ie7_body",
    22: "html.ie7_html body.ie7_body"
  }
});

// -----------------------------------------------------------------------
// IE7 dynamic style
// -----------------------------------------------------------------------

// object properties:
// attach: the element that an event handler will be attached to
// target: the element that will have the IE7 class applied

var DynamicRule = Rule.extend({
  // properties
  constructor: function(selector, attach, dynamicPseudoClass, target, cssText) {
    // initialise object properties
    this.attach = attach || "*";
    this.dynamicPseudoClass = IE7.CSS.dynamicPseudoClasses[dynamicPseudoClass];
    this.target = target;
    this.base(selector, cssText);
  },
  
  recalc: function() {
    // execute the underlying css query for this class
    var attaches = cssQuery(this.attach), attach;
    // process results
    for (var i = 0; attach = attaches[i]; i++) {
      // retrieve the event handler's target element(s)
      var target = this.target ? cssQuery(this.target, attach) : [attach];
      // attach event handlers for dynamic pseudo-classes
      if (target.length) this.dynamicPseudoClass.apply(attach, target, this);
    }
  }
});

// -----------------------------------------------------------------------
//  IE7 dynamic pseudo-classes
// -----------------------------------------------------------------------

var DynamicPseudoClass = Base.extend({
  constructor: function(name, apply) {
    this.name = name;
    this.apply = apply;
    this.instances = {};
    IE7.CSS.dynamicPseudoClasses[name] = this;
  },
  
  register: function(instance) {
    // an "instance" is actually an Arguments object
    var _class = instance[2];
    instance.id = _class.id + instance[0].uniqueID;
    if (!this.instances[instance.id]) {
      var target = instance[1], j;
      for (j = 0; j < target.length; j++) _class.add(target[j]);
      this.instances[instance.id] = instance;
    }
  },
  
  unregister: function(instance) {
    if (this.instances[instance.id]) {
      var _class = instance[2];
      var target = instance[1], j;
      for (j = 0; j < target.length; j++) _class.remove(target[j]);
      delete this.instances[instance.id];
    }
  }
});
  
// -----------------------------------------------------------------------
// dynamic pseudo-classes
// -----------------------------------------------------------------------

if (appVersion < 7) {
  var Hover = new DynamicPseudoClass("hover", function(element) {
    var instance = arguments;
    IE7.CSS.addEventHandler(element, appVersion < 5.5 ? "onmouseover" : "onmouseenter", function() {
      Hover.register(instance);
    });
    IE7.CSS.addEventHandler(element, appVersion < 5.5 ? "onmouseout" : "onmouseleave", function() {
      Hover.unregister(instance);
    });
  });
  
  // globally trap the mouseup event (thanks Martijn!)
  addEventHandler(document, "onmouseup", function() {
    var instances = Hover.instances;
    for (var i in instances)
      if (!instances[i][0].contains(event.srcElement))
        Hover.unregister(instances[i]);
  });
}

// -----------------------------------------------------------------------
// propertyName: inherit;
// -----------------------------------------------------------------------

IE7.CSS.addRecalc("[\\w-]+", "inherit", function(element, cssText) {
  var inherited = cssText.match(/[\w-]+\s*:\s*inherit/g);
  for (var i = 0; i < inherited.length; i++) {
    var propertyName = inherited[i].replace(/ie7\-|\s*:\s*inherit/g, "").replace(/\-([a-z])/g, function(match, chr) {
      return chr.toUpperCase()
    });
    element.runtimeStyle[propertyName] = element.parentElement.currentStyle[propertyName];
  }
});

// =========================================================================
// ie7-html.js
// =========================================================================

// default font-sizes
//HEADER += "h1{font-size:2em}h2{font-size:1.5em;}h3{font-size:1.17em;}h4{font-size:1em}h5{font-size:.83em}h6{font-size:.67em}";

IE7.HTML = new (Fix.extend({ // single instance  
  fixed: {},
  
  init: Undefined,
  
  addFix: function() {
    // fixes are a one-off, they are applied when the document is loaded
    this.fixes.push(arguments);
  },
  
  apply: function() {
    for (var i = 0; i < this.fixes.length; i++) {
      var match = cssQuery(this.fixes[i][0]);
      var fix = this.fixes[i][1];
      for (var j = 0; j < match.length; j++) fix(match[j]);
    }
  },
  
  addRecalc: function() {
    // recalcs occur whenever the document is refreshed using document.recalc()
    this.recalcs.push(arguments);
  },
  
  recalc: function() {
    // loop through the fixes
    for (var i = 0; i < this.recalcs.length; i++) {
      var match = cssQuery(this.recalcs[i][0]);
      var recalc = this.recalcs[i][1], element;
      var key = Math.pow(2, i);
      for (var j = 0; (element = match[j]); j++) {
        var uniqueID = element.uniqueID;
        if ((this.fixed[uniqueID] & key) == 0) {
          element = recalc(element) || element;
          this.fixed[uniqueID] |= key;
        }
      }
    }
  }
}));

if (appVersion < 7) {  
  // provide support for the <abbr> tag.
  //  this is a proper fix, it preserves the DOM structure and
  //  <abbr> elements report the correct tagName & namespace prefix
  document.createElement("abbr");
  
  // bind to the first child control
  IE7.HTML.addRecalc("label", function(label) {
    if (!label.htmlFor) {
      var firstChildControl = cssQuery("input,textarea", label, true);
      if (firstChildControl) {
        addEventHandler(label, "onclick", function() {
          firstChildControl.click();
        });
      }
    }
  });
}

// =========================================================================
// ie7-layout.js
// =========================================================================

var NUMERIC = "[.\\d]";

new function(_) {
var layout = IE7.Layout = this;

  // big, ugly box-model hack + min/max stuff
  
  // #tantek > #erik > #dean { voice-family: hacker; }
  
  // -----------------------------------------------------------------------
  // "layout"
  // -----------------------------------------------------------------------
  
  HEADER += "*{boxSizing:content-box}";
  
  // does an element have "layout" ?
  IE7.hasLayout = appVersion < 5.5 ? function(element) {
    // element.currentStyle.hasLayout doesn't work for IE5.0
    return element.clientWidth;
  } : function(element) {
    return element.currentStyle.hasLayout;
  };
  
  // give an element "layout"
  layout.boxSizing = function(element) {
    if (!IE7.hasLayout(element)) {
    //#  element.runtimeStyle.fixedHeight =
      element.style.height = "0cm";
      if (element.currentStyle.verticalAlign == "auto")
        element.runtimeStyle.verticalAlign = "top";
      // when an element acquires "layout", margins no longer collapse correctly
      collapseMargins(element);
    }
  };
  
  // -----------------------------------------------------------------------
  // Margin Collapse
  // -----------------------------------------------------------------------
  
  function collapseMargins(element) {
    if (element != viewport && element.currentStyle.position != "absolute") {
      collapseMargin(element, "marginTop");
      collapseMargin(element, "marginBottom");
    }
  };
  
  function collapseMargin(element, type) {
    if (!element.runtimeStyle[type]) {
      var parentElement = element.parentElement;
      if (parentElement && IE7.hasLayout(parentElement) && !IE7[type == "marginTop" ? "_getPreviousElementSibling" : "_getNextElementSibling"](element)) return;
      var child = cssQuery(">*:" + (type == "marginTop" ? "first" : "last") + "-child", element, true);
      if (child && child.currentStyle.styleFloat == "none" && IE7.hasLayout(child)) {
        collapseMargin(child, type);
        margin = _getMargin(element, element.currentStyle[type]);
        childMargin = _getMargin(child, child.currentStyle[type]);
        if (margin < 0 || childMargin < 0) {
          element.runtimeStyle[type] = margin + childMargin;
        } else {
          element.runtimeStyle[type] = Math.max(childMargin, margin);
        }
        child.runtimeStyle[type] = "0px";
      }
    }
  };
  
  function _getMargin(element, value) {
    return value == "auto" ? 0 : getPixelValue(element, value);
  };
  
  // -----------------------------------------------------------------------
  // box-model
  // -----------------------------------------------------------------------
  
  // constants
  var UNIT = /^[.\d][\w%]*$/, AUTO = /^(auto|0cm)$/;
  
  var applyWidth, applyHeight;
  IE7.Layout.borderBox = function(element){
    applyWidth(element);
    applyHeight(element);
  };
  
  var fixWidth = function(HEIGHT) {
    applyWidth = function(element) {
      if (!PERCENT.test(element.currentStyle.width)) fixWidth(element);
      collapseMargins(element);
    };
  
    function fixWidth(element, value) {
      if (!element.runtimeStyle.fixedWidth) {
        if (!value) value = element.currentStyle.width;
        element.runtimeStyle.fixedWidth = (UNIT.test(value)) ? Math.max(0, getFixedWidth(element, value)) : value;
        setOverrideStyle(element, "width", element.runtimeStyle.fixedWidth);
      }
    };
  
    function layoutWidth(element) {
      if (!isFixed(element)) {
        var layoutParent = element.offsetParent;
        while (layoutParent && !IE7.hasLayout(layoutParent)) layoutParent = layoutParent.offsetParent;
      }
      return (layoutParent || viewport).clientWidth;
    };
  
    function getPixelWidth(element, value) {
      if (PERCENT.test(value)) return parseInt(parseFloat(value) / 100 * layoutWidth(element));
      return getPixelValue(element, value);
    };
  
    var getFixedWidth = function(element, value) {
      var borderBox = element.currentStyle["box-sizing"] == "border-box";
      var adjustment = 0;
      if (quirksMode && !borderBox)
        adjustment += getBorderWidth(element) + getWidth(element, "padding");
      else if (!quirksMode && borderBox)
        adjustment -= getBorderWidth(element) + getWidth(element, "padding");
      return getPixelWidth(element, value) + adjustment;
    };
  
    // easy way to get border thickness for elements with "layout"
    function getBorderWidth(element) {
      return element.offsetWidth - element.clientWidth;
    };
  
    // have to do some pixel conversion to get padding/margin thickness :-(
    function getWidth(element, type) {
      return getPixelWidth(element, element.currentStyle[type + "Left"]) + getPixelWidth(element, element.currentStyle[type + "Right"]);
    };
  
    // -----------------------------------------------------------------------
    // min/max
    // -----------------------------------------------------------------------
  
    HEADER += "*{minWidth:none;maxWidth:none;min-width:none;max-width:none}";
  
    // handle min-width property
    layout.minWidth = function(element) {
      // IE6 supports min-height so we frig it here
      //#if (element.currentStyle.minHeight == "auto") element.runtimeStyle.minHeight = 0;
      if (element.currentStyle["min-width"] != null) {
        element.style.minWidth = element.currentStyle["min-width"];
      }
      if (register(arguments.callee, element, element.currentStyle.minWidth != "none")) {
        layout.boxSizing(element);
        fixWidth(element);
        resizeWidth(element);
      }
    };
    
    // clone the minWidth function to make a maxWidth function
    eval("IE7.Layout.maxWidth=" + String(layout.minWidth).replace(/min/g, "max"));
    
    // apply min/max restrictions
    function resizeWidth(element) {
      // check boundaries
      var rect = element.getBoundingClientRect();
      var width = rect.right - rect.left;
  
      if (element.currentStyle.minWidth != "none" && width <= getFixedWidth(element, element.currentStyle.minWidth)) {
        element.runtimeStyle.width = element.currentStyle.minWidth;
      } else if (element.currentStyle.maxWidth != "none" && width >= getFixedWidth(element, element.currentStyle.maxWidth)) {
        element.runtimeStyle.width = element.currentStyle.maxWidth;
      } else {
        element.runtimeStyle.width = element.runtimeStyle.fixedWidth; // || "auto";
      }
    };
  
    // -----------------------------------------------------------------------
    // right/bottom
    // -----------------------------------------------------------------------
  
    function fixRight(element) {
      if (register(fixRight, element, /^(fixed|absolute)$/.test(element.currentStyle.position) &&
        getDefinedStyle(element, "left") != "auto" &&
        getDefinedStyle(element, "right") != "auto" &&
        AUTO.test(getDefinedStyle(element, "width")))) {
          resizeRight(element);
          IE7.Layout.boxSizing(element);
      }
    };
    IE7.Layout.fixRight = fixRight;
  
    function resizeRight(element) {
      var left = getPixelWidth(element, element.runtimeStyle._left || element.currentStyle.left);
      var width = layoutWidth(element) - getPixelWidth(element, element.currentStyle.right) -  left - getWidth(element, "margin");
      if (parseInt(element.runtimeStyle.width) == width) return;
      element.runtimeStyle.width = "";
      if (isFixed(element) || HEIGHT || element.offsetWidth < width) {
        if (!quirksMode) width -= getBorderWidth(element) + getWidth(element, "padding");
        if (width < 0) width = 0;
        element.runtimeStyle.fixedWidth = width;
        setOverrideStyle(element, "width", width);
      }
    };
  
  // -----------------------------------------------------------------------
  // window.onresize
  // -----------------------------------------------------------------------
  
    // handle window resize
    var clientWidth = 0;
    addResize(function() {
      if (!viewport) return;
      var i, wider = (clientWidth < viewport.clientWidth);
      clientWidth = viewport.clientWidth;
      // resize elements with "min-width" set
      var elements = layout.minWidth.elements;
      for (i in elements) {
        var element = elements[i];
        var fixedWidth = (parseInt(element.runtimeStyle.width) == getFixedWidth(element, element.currentStyle.minWidth));
        if (wider && fixedWidth) element.runtimeStyle.width = "";
        if (wider == fixedWidth) resizeWidth(element);
      }
      // resize elements with "max-width" set
      var elements = layout.maxWidth.elements;
      for (i in elements) {
        var element = elements[i];
        var fixedWidth = (parseInt(element.runtimeStyle.width) == getFixedWidth(element, element.currentStyle.maxWidth));
        if (!wider && fixedWidth) element.runtimeStyle.width = "";
        if (wider != fixedWidth) resizeWidth(element);
      }
      // resize elements with "right" set
      for (i in fixRight.elements) resizeRight(fixRight.elements[i]);
    });
  
  // -----------------------------------------------------------------------
  // fix CSS
  // -----------------------------------------------------------------------
    if (quirksMode) {
      IE7.CSS.addRecalc("width", NUMERIC, applyWidth);
    }
    if (appVersion < 7) {
      IE7.CSS.addRecalc("min-width", NUMERIC, layout.minWidth);
      IE7.CSS.addRecalc("max-width", NUMERIC, layout.maxWidth);
      IE7.CSS.addRecalc("right", NUMERIC, fixRight);
    }
  };
  
  eval("var fixHeight=" + rotate(fixWidth));
  
  // apply box-model + min/max fixes
  fixWidth();
  fixHeight(true);
};

// =========================================================================
// ie7-graphics.js
// =========================================================================

// a small transparent image used as a placeholder
var BLANK_GIF = makePath("blank.gif", path);

var ALPHA_IMAGE_LOADER = "DXImageTransform.Microsoft.AlphaImageLoader";
var PNG_FILTER = "progid:" + ALPHA_IMAGE_LOADER + "(src='%1',sizingMethod='%2')";
  
// regular expression version of the above
var PNG;

var filtered = [];

function fixImage(element) {
  if (PNG.test(element.src)) {
    // we have to preserve width and height
    var image = new Image(element.width, element.height);
    image.onload = function() {
      element.width = image.width;
      element.height = image.height;
      image = null;
    };
    image.src = element.src;
    // store the original url (we'll put it back when it's printed)
    element.pngSrc = element.src;
    // add the AlphaImageLoader thingy
    addFilter(element);
  }
};

if (appVersion >= 5.5 && appVersion < 7) {
  // ** IE7 VARIABLE
  // e.g. only apply the hack to files ending in ".png"
  // IE7_PNG_SUFFIX = ".png";

  // replace background(-image): url(..) ..  with background(-image): .. ;filter: ..;
  IE7.CSS.addFix(/background(-image)?\s*:\s*([^};]*)?url\(([^\)]+)\)([^;}]*)?/, function(match, $1, $2, url, $4) {
    url = getString(url);
    return PNG.test(url) ? "filter:" + format(PNG_FILTER, url, "crop") +
      ";zoom:1;background" + ($1||"") + ":" + ($2||"") + "none" + ($4||"") : match;
  });
  
  // -----------------------------------------------------------------------
  //  fix PNG transparency (HTML images)
  // -----------------------------------------------------------------------

  IE7.HTML.addRecalc("img,input", function(element) {
    if (element.tagName == "INPUT" && element.type != "image") return;
    fixImage(element);
    addEventHandler(element, "onpropertychange", function() {
      if (!printing && event.propertyName == "src" &&
        element.src.indexOf(BLANK_GIF) == -1) fixImage(element);
    });
  });

  // assume that background images should not be printed
  //  (if they are not transparent then they'll just obscure content)
  // but we'll put foreground images back...
  var printing = false;
  addEventHandler(window, "onbeforeprint", function() {
    printing = true;
    for (var i = 0; i < filtered.length; i++) removeFilter(filtered[i]);
  });
  addEventHandler(window, "onafterprint", function() {
    for (var i = 0; i < filtered.length; i++) addFilter(filtered[i]);
    printing = false;
  });
}

// apply a filter
function addFilter(element, sizingMethod) {
  var filter = element.filters[ALPHA_IMAGE_LOADER];
  if (filter) {
    filter.src = element.src;
    filter.enabled = true;
  } else {
    element.runtimeStyle.filter = format(PNG_FILTER, element.src, sizingMethod || "scale");
    filtered.push(element);
  }
  // remove the real image
  element.src = BLANK_GIF;
};

function removeFilter(element) {
  element.src = element.pngSrc;
  element.filters[ALPHA_IMAGE_LOADER].enabled = false;
};

// =========================================================================
// ie7-fixed.js
// =========================================================================

new function(_) {
  if (appVersion >= 7) return;
  
  // some things to consider for this hack.
  // the document body requires a fixed background. even if
  //  it is just a blank image.
  // you have to use setExpression instead of onscroll, this
  //  together with a fixed body background helps avoid the
  //  annoying screen flicker of other solutions.
  
  IE7.CSS.addRecalc("position", "fixed", _positionFixed, "absolute");
  IE7.CSS.addRecalc("background(-attachment)?", "[^};]*fixed", _backgroundFixed);
  
  // scrolling is relative to the documentElement (HTML tag) when in
  //  standards mode, otherwise it's relative to the document body
  var $viewport = quirksMode ? "body" : "documentElement";
  
  function _fixBackground() {
    // this is required by both position:fixed and background-attachment:fixed.
    // it is necessary for the document to also have a fixed background image.
    // we can fake this with a blank image if necessary
    if (body.currentStyle.backgroundAttachment != "fixed") {
      if (body.currentStyle.backgroundImage == "none") {
        body.runtimeStyle.backgroundRepeat = "no-repeat";
        body.runtimeStyle.backgroundImage = "url(" + BLANK_GIF + ")"; // dummy
      }
      body.runtimeStyle.backgroundAttachment = "fixed";
    }
    _fixBackground = Undefined;
  };
  
  var _tmp = createTempElement("img");
  
  function _isFixed(element) {
    return element ? isFixed(element) || _isFixed(element.parentElement) : false;
  };
  
  function _setExpression(element, propertyName, expression) {
    setTimeout("document.all." + element.uniqueID + ".runtimeStyle.setExpression('" + propertyName + "','" + expression + "')", 0);
  };
  
  // -----------------------------------------------------------------------
  //  backgroundAttachment: fixed
  // -----------------------------------------------------------------------
  
  function _backgroundFixed(element) {
    if (register(_backgroundFixed, element, element.currentStyle.backgroundAttachment == "fixed" && !element.contains(body))) {
      _fixBackground();
      bgLeft(element);
      bgTop(element);
      _backgroundPosition(element);
    }
  };
  
  function _backgroundPosition(element) {
    _tmp.src = element.currentStyle.backgroundImage.slice(5, -2);
    var parentElement = element.canHaveChildren ? element : element.parentElement;
    parentElement.appendChild(_tmp);
    setOffsetLeft(element);
    setOffsetTop(element);
    parentElement.removeChild(_tmp);
  };
  
  function bgLeft(element) {
    element.style.backgroundPositionX = element.currentStyle.backgroundPositionX;
    if (!_isFixed(element)) {
      _setExpression(element, "backgroundPositionX", "(parseInt(runtimeStyle.offsetLeft)+document." + $viewport + ".scrollLeft)||0");
    }
  };
  eval(rotate(bgLeft));
  
  function setOffsetLeft(element) {
    var propertyName = _isFixed(element) ? "backgroundPositionX" : "offsetLeft";
    element.runtimeStyle[propertyName] =
      getOffsetLeft(element, element.style.backgroundPositionX) -
      element.getBoundingClientRect().left - element.clientLeft + 2;
  };
  eval(rotate(setOffsetLeft));
  
  function getOffsetLeft(element, position) {
    switch (position) {
      case "left":
      case "top":
        return 0;
      case "right":
      case "bottom":
        return viewport.clientWidth - _tmp.offsetWidth;
      case "center":
        return (viewport.clientWidth - _tmp.offsetWidth) / 2;
      default:
        if (PERCENT.test(position)) {
          return parseInt((viewport.clientWidth - _tmp.offsetWidth) * parseFloat(position) / 100);
        }
        _tmp.style.left = position;
        return _tmp.offsetLeft;
    }
  };
  eval(rotate(getOffsetLeft));
  
  // -----------------------------------------------------------------------
  //  position: fixed
  // -----------------------------------------------------------------------
  
  function _positionFixed(element) {
    if (register(_positionFixed, element, isFixed(element))) {
      setOverrideStyle(element, "position",  "absolute");
      setOverrideStyle(element, "left",  element.currentStyle.left);
      setOverrideStyle(element, "top",  element.currentStyle.top);
      _fixBackground();
      IE7.Layout.fixRight(element);
      _foregroundPosition(element);
    }
  };
  
  function _foregroundPosition(element, recalc) {
    positionTop(element, recalc);
    positionLeft(element, recalc, true);
    if (!element.runtimeStyle.autoLeft && element.currentStyle.marginLeft == "auto" &&
      element.currentStyle.right != "auto") {
      var left = viewport.clientWidth - getPixelWidth(element, element.currentStyle.right) -
        getPixelWidth(element, element.runtimeStyle._left) - element.clientWidth;
      if (element.currentStyle.marginRight == "auto") left = parseInt(left / 2);
      if (_isFixed(element.offsetParent)) element.runtimeStyle.pixelLeft += left;
      else element.runtimeStyle.shiftLeft = left;
    }
    clipWidth(element);
    clipHeight(element);
  };

  function clipWidth(element) {
    var fixWidth = element.runtimeStyle.fixWidth;
    element.runtimeStyle.borderRightWidth = "";
    element.runtimeStyle.width = fixWidth ? getPixelWidth(element, fixWidth) : "";
    if (element.currentStyle.width != "auto") {
      var rect = element.getBoundingClientRect();
      var width = element.offsetWidth - viewport.clientWidth + rect.left - 2;
      if (width >= 0) {
        element.runtimeStyle.borderRightWidth = "0px";
        width = Math.max(getPixelValue(element, element.currentStyle.width) - width, 0);
        setOverrideStyle(element, "width",  width);
        return width;
      }
    }
  };
  eval(rotate(clipWidth));
  
  function positionLeft(element, recalc) {
    // if the element's width is in % units then it must be recalculated
    //  with respect to the viewport
    if (!recalc && PERCENT.test(element.currentStyle.width)) {
      element.runtimeStyle.fixWidth = element.currentStyle.width;
    }
    if (element.runtimeStyle.fixWidth) {
      element.runtimeStyle.width = getPixelWidth(element, element.runtimeStyle.fixWidth);
    }
    //if (recalc) {
    //  // if the element is fixed on the right then no need to recalculate
    //  if (!element.runtimeStyle.autoLeft) return;
    //} else {
      element.runtimeStyle.shiftLeft = 0;
      element.runtimeStyle._left = element.currentStyle.left;
      // is the element fixed on the right?
      element.runtimeStyle.autoLeft = element.currentStyle.right != "auto" &&
        element.currentStyle.left == "auto";
    //}
    // reset the element's "left" value and get it's natural position
    element.runtimeStyle.left = "";
    element.runtimeStyle.screenLeft = getScreenLeft(element);
    element.runtimeStyle.pixelLeft = element.runtimeStyle.screenLeft;
    // if the element is contained by another fixed element then there is no need to
    //  continually recalculate it's left position
    if (!recalc && !_isFixed(element.offsetParent)) {
      // onsrcoll produces jerky movement, so we use an expression
      _setExpression(element, "pixelLeft", "runtimeStyle.screenLeft+runtimeStyle.shiftLeft+document." + $viewport + ".scrollLeft");
    }
  };
  // clone this function so we can do "top"
  eval(rotate(positionLeft));
  
  // I've forgotten how this works...
  function getScreenLeft(element) { // thanks to kevin newman (captainn)
    var screenLeft = element.offsetLeft, nested = 1;
    if (element.runtimeStyle.autoLeft) {
      screenLeft = viewport.clientWidth - element.offsetWidth - getPixelWidth(element, element.currentStyle.right);
    }
    // accommodate margins
    if (element.currentStyle.marginLeft != "auto") {
      screenLeft -= getPixelWidth(element, element.currentStyle.marginLeft);
    }
    while (element = element.offsetParent) {
      if (element.currentStyle.position != "static") nested = -1;
      screenLeft += element.offsetLeft * nested;
    }
    return screenLeft;
  };
  eval(rotate(getScreenLeft));
  
  function getPixelWidth(element, value) {
    return PERCENT.test(value) ? parseInt(parseFloat(value) / 100 * viewport.clientWidth) : getPixelValue(element, value);
  };
  eval(rotate(getPixelWidth));
  
  // -----------------------------------------------------------------------
  //  capture window resize
  // -----------------------------------------------------------------------
  
  function _resize() {
    // if the window has been resized then some positions need to be
    //  recalculated (especially those aligned to "right" or "top"
    var elements = _backgroundFixed.elements;
    for (var i in elements) _backgroundPosition(elements[i]);
    elements = _positionFixed.elements;
    for (i in elements) {
      _foregroundPosition(elements[i], true);
      // do this twice to be sure - hackish, I know :-)
      _foregroundPosition(elements[i], true);
    }
    _timer = 0;
  };
  
  // use a timer for some reason.
  //  (sometimes this is a good way to prevent resize loops)
  var _timer;
  addResize(function() {
    if (!_timer) _timer = setTimeout(_resize, 0);
  });
};

// =========================================================================
// ie7-oveflow.js
// =========================================================================

/* ---------------------------------------------------------------------

  This module alters the structure of the document.
  It may adversely affect other CSS rules. Be warned.

--------------------------------------------------------------------- */

var WRAPPER_STYLE = {
  backgroundColor: "transparent",
  backgroundImage: "none",
  backgroundPositionX: null,
  backgroundPositionY: null,
  backgroundRepeat: null,
  borderTopWidth: 0,
  borderRightWidth: 0,
  borderBottomWidth: 0,
  borderLeftStyle: "none",
  borderTopStyle: "none",
  borderRightStyle: "none",
  borderBottomStyle: "none",
  borderLeftWidth: 0,
  height: null,
  marginTop: 0,
  marginBottom: 0,
  marginRight: 0,
  marginLeft: 0,
  width: "100%"
};

IE7.CSS.addRecalc("overflow", "visible", function(element) {
  // don't do this again
  if (element.parentNode.ie7_wrapped) return;

  // if max-height is applied, makes sure it gets applied first
  if (IE7.Layout && element.currentStyle["max-height"] != "auto") {
    IE7.Layout.maxHeight(element);
  }

  if (element.currentStyle.marginLeft == "auto") element.style.marginLeft = 0;
  if (element.currentStyle.marginRight == "auto") element.style.marginRight = 0;

  var wrapper = document.createElement(ANON);
  wrapper.ie7_wrapped = element;
  for (var propertyName in WRAPPER_STYLE) {
    wrapper.style[propertyName] = element.currentStyle[propertyName];
    if (WRAPPER_STYLE[propertyName] != null) {
      element.runtimeStyle[propertyName] = WRAPPER_STYLE[propertyName];
    }
  }
  wrapper.style.display = "block";
  wrapper.style.position = "relative";
  element.runtimeStyle.position = "absolute";
  element.parentNode.insertBefore(wrapper, element);
  wrapper.appendChild(element);
});

// =========================================================================
// ie7-quirks.js
// =========================================================================

function ie7Quirks() {
  var FONT_SIZES = "xx-small,x-small,small,medium,large,x-large,xx-large".split(",");
  for (var i = 0; i < FONT_SIZES.length; i++) {
    FONT_SIZES[FONT_SIZES[i]] = FONT_SIZES[i - 1] || "0.67em";
  }
  
  IE7.CSS.addFix(/(font(-size)?\s*:\s*)([\w.-]+)/, function(match, label, size, value) {
    return label + (FONT_SIZES[value] || value);
  });
  
  if (appVersion < 6) {
    var NEGATIVE = /^\-/, LENGTH = /(em|ex)$/i;
    var EM = /em$/i, EX = /ex$/i;
  
    getPixelValue = function(element, value) {
      if (PIXEL.test(value)) return parseInt(value)||0;
      var scale = NEGATIVE.test(value)? -1 : 1;
      if (LENGTH.test(value)) scale *= getFontScale(element);
      temp.style.width = (scale < 0) ? value.slice(1) : value;
      body.appendChild(temp);
      // retrieve pixel width
      value = scale * temp.offsetWidth;
      // remove the temporary element
      temp.removeNode();
      return parseInt(value);
    };

    var temp = createTempElement();
    function getFontScale(element) {
      var scale = 1;
      temp.style.fontFamily = element.currentStyle.fontFamily;
      temp.style.lineHeight = element.currentStyle.lineHeight;
      //temp.style.fontSize = "";
      while (element != body) {
        var fontSize = element.currentStyle["ie7-font-size"];
        if (fontSize) {
          if (EM.test(fontSize)) scale *= parseFloat(fontSize);
          else if (PERCENT.test(fontSize)) scale *= (parseFloat(fontSize) / 100);
          else if (EX.test(fontSize)) scale *= (parseFloat(fontSize) / 2);
          else {
            temp.style.fontSize = fontSize;
            return 1;
          }
        }
        element = element.parentElement;
      }
      return scale;
    };

    // cursor:pointer (IE5.x)
    IE7.CSS.addFix(/cursor\s*:\s*pointer/, "cursor:hand");
    // display:list-item (IE5.x)
    IE7.CSS.addFix(/display\s*:\s*list-item/, "display:block");
  }
  
  // -----------------------------------------------------------------------
  //  margin:auto
  // -----------------------------------------------------------------------
  
  function fixMargin(element) {
    if (appVersion < 5.5) IE7.Layout.boxSizing(element.parentElement);
    var parent = element.parentElement;
    var margin = parent.offsetWidth - element.offsetWidth - getPaddingWidth(parent);
    var autoRight = (element.currentStyle["ie7-margin"] && element.currentStyle.marginRight == "auto") ||
      element.currentStyle["ie7-margin-right"] == "auto";
    switch (parent.currentStyle.textAlign) {
      case "right":
        margin = autoRight ? parseInt(margin / 2) : 0;
        element.runtimeStyle.marginRight = margin + "px";
        break;
      case "center":
        if (autoRight) margin = 0;
      default:
        if (autoRight) margin /= 2;
        element.runtimeStyle.marginLeft = parseInt(margin) + "px";
    }
  };

  function getPaddingWidth(element) {
    return getPixelValue(element, element.currentStyle.paddingLeft) +
      getPixelValue(element, element.currentStyle.paddingRight);
  };
  
  IE7.CSS.addRecalc("margin(-left|-right)?", "[^};]*auto", function(element) {
    if (register(fixMargin, element,
      element.parentElement &&
      element.currentStyle.display == "block" &&
      element.currentStyle.marginLeft == "auto" &&
      element.currentStyle.position != "absolute")) {
        fixMargin(element);
    }
  });
  
  addResize(function() {
    for (var i in fixMargin.elements) {
      var element = fixMargin.elements[i];
      element.runtimeStyle.marginLeft =
      element.runtimeStyle.marginRight = "";
      fixMargin(element);
    }
  });
};


// -----------------------------------------------------------------------
// initialisation
// -----------------------------------------------------------------------

IE7.loaded = true;

(function() {
  try {
    // http://javascript.nwbox.com/IEContentLoaded/
    documentElement.doScroll("left");
  } catch (e) {
    setTimeout(arguments.callee, 1);
    return;
  }
  // execute the inner text of the IE7 script
  try {
    eval(script.innerHTML);
  } catch (e) {
    // ignore errors
  }
  PNG = new RegExp(rescape(typeof IE7_PNG_SUFFIX == "string" ? IE7_PNG_SUFFIX : "-trans.png") + "$", "i");

  // frequently used references
  body = document.body;
  viewport = quirksMode ? body : documentElement;

  // classes
  body.className += " ie7_body";
  documentElement.className += " ie7_html";

  if (quirksMode) ie7Quirks();

  IE7.CSS.init();
  IE7.HTML.init();

  IE7.HTML.apply();
  IE7.CSS.apply();

  IE7.recalc();
})();


})();
