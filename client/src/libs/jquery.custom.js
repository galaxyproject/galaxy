/**
 * jQuery and all its horrible plugins. Bundled together and repackaged into a
 * single module, then aliased by webpack as "jquery"
 */

var jQuery = require("jqueryVendor");

require("imports-loader?imports=default|jqueryVendor|jQuery!libs/jquery/jquery.autocomplete");
require("imports-loader?imports=default|jqueryVendor|jQuery!libs/jquery/jquery.event.hover");
require("imports-loader?imports=default|jqueryVendor|jQuery!libs/jquery/jquery.event.drag");
// TODO: replace mousewheel events
require("imports-loader?imports=default|jqueryVendor|jQuery!libs/jquery/jquery.form");
require("imports-loader?imports=default|jqueryVendor|jQuery!libs/jquery/jquery.rating");
require("imports-loader?imports=default|jqueryVendor|jQuery!libs/jquery/select2");
require("imports-loader?imports=default|jqueryVendor|jQuery!libs/jquery/jquery-ui");
require("imports-loader?imports=default|jqueryVendor|jQuery!libs/farbtastic");
// TODO: ensure unused
require("imports-loader?imports=default|jqueryVendor|jQuery!libs/jquery/jquery.dynatree");
require("imports-loader?imports=default|jqueryVendor|jQuery!jquery-migrate");

// Only used in reports
require("imports-loader?imports=default|jqueryVendor|jQuery!libs/jquery.sparklines");

module.exports = jQuery;
