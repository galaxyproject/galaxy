/**
 * jQuery and all its horrible plugins. Bundled together and repackaged into a
 * single module, then aliased by webpack as "jquery"
 */

var jQuery = require("jqueryVendor");

// Use webpack 5 imports-loader syntax to inject jQuery into plugins
require("imports-loader?wrapper=window&imports=default|jqueryVendor|jQuery!./jquery/jquery.autocomplete");
require("imports-loader?wrapper=window&imports=default|jqueryVendor|jQuery!./jquery/jquery.event.hover");
require("imports-loader?wrapper=window&imports=default|jqueryVendor|jQuery!./jquery/jquery.event.drag");
require("imports-loader?wrapper=window&imports=default|jqueryVendor|jQuery!./jquery/jquery.event.drop");
// TODO: replace mousewheel events
// require("imports-loader?imports=default|jquery|jqueryVendor,define=>false!jquery-mousewheel");
require("imports-loader?wrapper=window&imports=default|jqueryVendor|jQuery!./jquery/jquery.form");
require("imports-loader?wrapper=window&imports=default|jqueryVendor|jQuery!./jquery/jquery.rating");
require("imports-loader?wrapper=window&imports=default|jqueryVendor|jQuery!./jquery/select2");
require("imports-loader?wrapper=window&imports=default|jqueryVendor|jQuery!./jquery/jquery-ui");
require("imports-loader?wrapper=window&imports=default|jqueryVendor|jQuery!./farbtastic");
// TODO: ensure unused
//require("imports-loader?imports=default|jquery|jqueryVendor,define=>false!jquery.cookie");
require("imports-loader?wrapper=window&imports=default|jqueryVendor|jQuery!./jquery/jquery.dynatree");
require("imports-loader?wrapper=window&imports=default|jqueryVendor|jQuery!jquery-migrate");

// require("imports-loader?jQuery=jqueryVendor!../ui/autocom_tagging");

// Only used in reports
require("imports-loader?wrapper=window&imports=default|jqueryVendor|jQuery!./jquery.sparklines");

module.exports = jQuery;
