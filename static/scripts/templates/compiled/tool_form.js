(function() {
  var template = Handlebars.template, templates = Handlebars.templates = Handlebars.templates || {};
templates['tool_form'] = template(function (Handlebars,depth0,helpers,partials,data) {
  helpers = helpers || Handlebars.helpers;
  var buffer = "", stack1, foundHelper, functionType="function", escapeExpression=this.escapeExpression, self=this;

function program1(depth0,data) {
  
  var buffer = "", stack1, foundHelper;
  buffer += "\n        <div class=\"form-row\">\n            <label for=\"";
  foundHelper = helpers.name;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{}}); }
  else { stack1 = depth0.name; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  buffer += escapeExpression(stack1) + "\">";
  foundHelper = helpers.label;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{}}); }
  else { stack1 = depth0.label; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  buffer += escapeExpression(stack1) + ":</label>\n            <div class=\"form-row-input\">\n                ";
  foundHelper = helpers.html;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{}}); }
  else { stack1 = depth0.html; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n            </div>\n            <div class=\"toolParamHelp\" style=\"clear: both;\">\n                ";
  foundHelper = helpers.help;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{}}); }
  else { stack1 = depth0.help; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  buffer += escapeExpression(stack1) + "\n            </div>\n            <div style=\"clear: both;\"></div>\n        </div>\n        ";
  return buffer;}

  buffer += "<div class=\"toolFormTitle\">";
  foundHelper = helpers.name;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{}}); }
  else { stack1 = depth0.name; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  buffer += escapeExpression(stack1) + " (version ";
  foundHelper = helpers.version;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{}}); }
  else { stack1 = depth0.version; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  buffer += escapeExpression(stack1) + ")</div>\n    <div class=\"toolFormBody\">\n        ";
  stack1 = depth0.inputs;
  stack1 = helpers.each.call(depth0, stack1, {hash:{},inverse:self.noop,fn:self.program(1, program1, data)});
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n    </div>\n    <div class=\"form-row form-actions\">\n    <input type=\"submit\" class=\"btn btn-primary\" name=\"runtool_btn\" value=\"Execute\">\n</div>\n<div class=\"toolHelp\">\n    <div class=\"toolHelpBody\">";
  foundHelper = helpers.help;
  if (foundHelper) { stack1 = foundHelper.call(depth0, {hash:{}}); }
  else { stack1 = depth0.help; stack1 = typeof stack1 === functionType ? stack1() : stack1; }
  buffer += escapeExpression(stack1) + "</div>\n</div>";
  return buffer;});
})();