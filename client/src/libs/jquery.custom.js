/**
 * jQuery and all its horrible plugins. Bundled together and repackaged into a
 * single module, then aliased by webpack as "jquery"
 */

var jQuery = require("jqueryVendor");

// Make jQuery available globally for plugins
window.jQuery = jQuery;
window.$ = jQuery;

require("./jquery/jquery.autocomplete");
require("./jquery/jquery.event.hover");
require("./jquery/jquery.event.drag");
require("./jquery/jquery.event.drop");
// TODO: replace mousewheel events
// require("imports-loader?imports=default|jquery|jqueryVendor,define=>false!jquery-mousewheel");
require("./jquery/jquery.form");
require("./jquery/jquery.rating");
require("./jquery/select2");
require("./jquery/jquery-ui");
require("./farbtastic");
// TODO: ensure unused
//require("imports-loader?imports=default|jquery|jqueryVendor,define=>false!jquery.cookie");
require("./jquery/jquery.dynatree");
require("jquery-migrate");

// require("imports-loader?jQuery=jqueryVendor!../ui/autocom_tagging");

// Only used in reports
require("./jquery.sparklines");

module.exports = jQuery;
