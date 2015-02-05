(function() {
  var template = Handlebars.template, templates = Handlebars.templates = Handlebars.templates || {};
templates['tool_form'] = template({"1":function(depth0,helpers,partials,data) {
  var stack1, helper, functionType="function", helperMissing=helpers.helperMissing, escapeExpression=this.escapeExpression, buffer = "        <div class=\"form-row\">\n            <label for=\""
    + escapeExpression(((helper = (helper = helpers.name || (depth0 != null ? depth0.name : depth0)) != null ? helper : helperMissing),(typeof helper === functionType ? helper.call(depth0, {"name":"name","hash":{},"data":data}) : helper)))
    + "\">"
    + escapeExpression(((helper = (helper = helpers.label || (depth0 != null ? depth0.label : depth0)) != null ? helper : helperMissing),(typeof helper === functionType ? helper.call(depth0, {"name":"label","hash":{},"data":data}) : helper)))
    + ":</label>\n            <div class=\"form-row-input\">\n                ";
  stack1 = ((helper = (helper = helpers.html || (depth0 != null ? depth0.html : depth0)) != null ? helper : helperMissing),(typeof helper === functionType ? helper.call(depth0, {"name":"html","hash":{},"data":data}) : helper));
  if (stack1 != null) { buffer += stack1; }
  return buffer + "\n            </div>\n            <div class=\"toolParamHelp\" style=\"clear: both;\">\n                "
    + escapeExpression(((helper = (helper = helpers.help || (depth0 != null ? depth0.help : depth0)) != null ? helper : helperMissing),(typeof helper === functionType ? helper.call(depth0, {"name":"help","hash":{},"data":data}) : helper)))
    + "\n            </div>\n            <div style=\"clear: both;\"></div>\n        </div>\n";
},"compiler":[6,">= 2.0.0-beta.1"],"main":function(depth0,helpers,partials,data) {
  var stack1, helper, functionType="function", helperMissing=helpers.helperMissing, escapeExpression=this.escapeExpression, buffer = "<div class=\"toolFormTitle\">"
    + escapeExpression(((helper = (helper = helpers.name || (depth0 != null ? depth0.name : depth0)) != null ? helper : helperMissing),(typeof helper === functionType ? helper.call(depth0, {"name":"name","hash":{},"data":data}) : helper)))
    + " (version "
    + escapeExpression(((helper = (helper = helpers.version || (depth0 != null ? depth0.version : depth0)) != null ? helper : helperMissing),(typeof helper === functionType ? helper.call(depth0, {"name":"version","hash":{},"data":data}) : helper)))
    + ")</div>\n    <div class=\"toolFormBody\">\n";
  stack1 = helpers.each.call(depth0, (depth0 != null ? depth0.inputs : depth0), {"name":"each","hash":{},"fn":this.program(1, data),"inverse":this.noop,"data":data});
  if (stack1 != null) { buffer += stack1; }
  return buffer + "    </div>\n    <div class=\"form-row form-actions\">\n    <input type=\"submit\" class=\"btn btn-primary\" name=\"runtool_btn\" value=\"Execute\">\n</div>\n<div class=\"toolHelp\">\n    <div class=\"toolHelpBody\">"
    + escapeExpression(((helper = (helper = helpers.help || (depth0 != null ? depth0.help : depth0)) != null ? helper : helperMissing),(typeof helper === functionType ? helper.call(depth0, {"name":"help","hash":{},"data":data}) : helper)))
    + "</div>\n</div>";
},"useData":true});
})();