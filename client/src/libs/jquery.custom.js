/**
 * jQuery and all its horrible plugins. Bundled together and repackaged into a
 * single module, then aliased by webpack as "jquery"
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
require("imports-loader?jQuery=jqueryVendor!libs/farbtastic");
require("imports-loader?jQuery=jqueryVendor,$=jqueryVendor,define=>false!jquery.cookie");
require("imports-loader?jQuery=jqueryVendor!libs/jquery/jquery.dynatree");
require("imports-loader?jQuery=jqueryVendor!libs/jquery/jquery.wymeditor");
require("imports-loader?jQuery=jqueryVendor!jquery.complexify");
require("imports-loader?jQuery=jqueryVendor!jquery-migrate");

// require("imports-loader?jQuery=jqueryVendor!../ui/autocom_tagging");

module.exports = jQuery;
