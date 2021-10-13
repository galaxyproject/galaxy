/**
 * jQuery and all its horrible plugins. Bundled together and repackaged into a
 * single module, then aliased by webpack as "jquery"
 */

var jQuery = require("jqueryVendor");

require("imports-loader?imports=default|jqueryVendor|jQuery!libs/jquery/jquery.autocomplete");
require("imports-loader?imports=default|jqueryVendor|jQuery!libs/jquery/jquery.event.hover");
require("imports-loader?imports=default|jqueryVendor|jQuery!libs/jquery/jquery.event.drag");
require("imports-loader?imports=default|jqueryVendor|jQuery!libs/jquery/jquery.event.drop");
// TODO: replace mousewheel events
// require("imports-loader?imports=default|jquery|jqueryVendor,define=>false!jquery-mousewheel");
require("imports-loader?imports=default|jqueryVendor|jQuery!libs/jquery/jquery.form");
require("imports-loader?imports=default|jqueryVendor|jQuery!libs/jquery/jquery.rating");
require("imports-loader?imports=default|jqueryVendor|jQuery!libs/jquery/select2");
require("imports-loader?imports=default|jqueryVendor|jQuery!libs/jquery/jquery-ui");
require("imports-loader?imports=default|jqueryVendor|jQuery!libs/farbtastic");
// TODO: ensure unused
//require("imports-loader?imports=default|jquery|jqueryVendor,define=>false!jquery.cookie");
require("imports-loader?imports=default|jqueryVendor|jQuery!libs/jquery/jquery.dynatree");
require("imports-loader?imports=default|jqueryVendor|jQuery!libs/jquery/jquery.wymeditor");
require("imports-loader?imports=default|jqueryVendor|jQuery!jquery.complexify");
require("imports-loader?imports=default|jqueryVendor|jQuery!jquery-migrate");

// require("imports-loader?jQuery=jqueryVendor!../ui/autocom_tagging");

module.exports = jQuery;
