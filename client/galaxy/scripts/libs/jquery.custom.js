/**
 * jQuery and all its horrible plugins. Bundled together and repackaged into a
 * single module, then aliased by webpack as "jquery";
 */

var jQuery = require("jqueryVendor");

require("imports-loader?jQuery=jqueryVendor!libs/jquery/jquery.autocomplete");
require("imports-loader?jQuery=jqueryVendor!libs/jquery/jquery.event.hover");
require("imports-loader?jQuery=jqueryVendor!libs/jquery/jquery.event.drag");
require("imports-loader?jQuery=jqueryVendor!libs/jquery/jquery.event.drop");
require("imports-loader?jQuery=jqueryVendor,define=>false!jquery-mousewheel");
require("imports-loader?jQuery=jqueryVendor!libs/jquery/jquery.form");
require("imports-loader?jQuery=jqueryVendor!libs/jquery/jquery.rating");
require("imports-loader?jQuery=jqueryVendor!libs/jquery/select2");
require("imports-loader?jQuery=jqueryVendor!libs/jquery/jquery-ui");

// This is probably the worst jquery plugin I've ever seen. It's basically
// unimportable except as a direct script tag. and there's absolutely no reason
// for this functionality to be bolted onto the side of jQuery. I'm going to
// replace it with something more standard like "store"
// https://www.npmjs.com/package/store
// require("imports-loader?jQuery=jqueryVendor!libs/jquery/jstorage");

require("imports-loader?jQuery=jqueryVendor!libs/farbtastic");
require("imports-loader?jQuery=jqueryVendor,$=jqueryVendor,define=>false!jquery.cookie");
require("imports-loader?jQuery=jqueryVendor!libs/jquery/jquery.dynatree");
require("imports-loader?jQuery=jqueryVendor!jquery.complexify");
require("imports-loader?jQuery=jqueryVendor!jquery-migrate");

module.exports = jQuery;