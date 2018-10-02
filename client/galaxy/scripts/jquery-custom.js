/* eslint-env commonjs */

// Having a hard time making this work with standard es6 import/exports
var $ = require("jqueryVendor");

// Eww....
require("libs/jquery/jquery.migrate");
require("libs/jquery/jquery.autocomplete");
require("libs/jquery/jquery.event.hover");
require("libs/jquery/jquery.event.drag");
require("libs/jquery/jquery.mousewheel");
require("libs/jquery/jquery.form");
require("libs/jquery/jquery.rating");
require("libs/jquery/select2");
require("libs/jquery/jquery-ui");

// THIS ONE IS REALLY BAD, probably replace it, see if there's a more grown-up
// version or just refactor it out since there's really no sensible reason for
// an unholy marriage between localstorage and jquery
require("libs/jquery/jstorage");

require("libs/farbtastic");
require("libs/jquery/jquery.dynatree");

module.exports = $;
