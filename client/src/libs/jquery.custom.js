/**
 * jQuery and all its horrible plugins. Bundled together and repackaged into a
 * single module, then aliased by webpack as "jquery"
 */

var jQuery = require("jqueryVendor");

require("imports-loader?jQuery=jqueryVendor!./jquery/jquery.autocomplete");
require("imports-loader?jQuery=jqueryVendor!./jquery/jquery.event.hover");
require("imports-loader?jQuery=jqueryVendor!./jquery/jquery.event.drag");
require("imports-loader?jQuery=jqueryVendor!./jquery/jquery.event.drop");
// TODO: replace mousewheel events
// require("imports-loader?imports=default|jquery|jqueryVendor,define=>false!jquery-mousewheel");
require("imports-loader?jQuery=jqueryVendor!./jquery/jquery.form");
require("imports-loader?jQuery=jqueryVendor!./jquery/jquery.rating");
require("imports-loader?jQuery=jqueryVendor!./jquery/select2");
require("imports-loader?jQuery=jqueryVendor!./jquery/jquery-ui");
require("imports-loader?jQuery=jqueryVendor!./farbtastic");
// TODO: ensure unused
//require("imports-loader?imports=default|jquery|jqueryVendor,define=>false!jquery.cookie");
require("imports-loader?jQuery=jqueryVendor!./jquery/jquery.dynatree");
require("imports-loader?jQuery=jqueryVendor!jquery-migrate");

// require("imports-loader?jQuery=jqueryVendor!../ui/autocom_tagging");

// Only used in reports
require("imports-loader?jQuery=jqueryVendor!./jquery.sparklines");

module.exports = jQuery;
