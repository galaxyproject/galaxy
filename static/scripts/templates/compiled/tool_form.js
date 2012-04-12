(function() {
  var template = Handlebars.template, templates = Handlebars.templates = Handlebars.templates || {};
templates['tool_form'] = template(function (Handlebars,depth0,helpers,partials,data) {
  helpers = helpers || Handlebars.helpers;
  var buffer = "", stack1, stack2, foundHelper, tmp1, self=this, functionType="function", helperMissing=helpers.helperMissing, undef=void 0, escapeExpression=this.escapeExpression;

function program1(depth0,data) {
  
  var buffer = "", stack1;
  buffer += "\n        <div class=\"form-row\">\n            <label for=\"";
  foundHelper = helpers.name;
  stack1 = foundHelper || depth0.name;
  if(typeof stack1 === functionType) { stack1 = stack1.call(depth0, { hash: {} }); }
  else if(stack1=== undef) { stack1 = helperMissing.call(depth0, "name", { hash: {} }); }
  buffer += escapeExpression(stack1) + "\">";
  foundHelper = helpers.label;
  stack1 = foundHelper || depth0.label;
  if(typeof stack1 === functionType) { stack1 = stack1.call(depth0, { hash: {} }); }
  else if(stack1=== undef) { stack1 = helperMissing.call(depth0, "label", { hash: {} }); }
  buffer += escapeExpression(stack1) + ":</label>\n            <div class=\"form-row-input\">\n                ";
  foundHelper = helpers.html;
  stack1 = foundHelper || depth0.html;
  if(typeof stack1 === functionType) { stack1 = stack1.call(depth0, { hash: {} }); }
  else if(stack1=== undef) { stack1 = helperMissing.call(depth0, "html", { hash: {} }); }
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n            </div>\n            <div class=\"toolParamHelp\" style=\"clear: both;\">\n                ";
  foundHelper = helpers.help;
  stack1 = foundHelper || depth0.help;
  if(typeof stack1 === functionType) { stack1 = stack1.call(depth0, { hash: {} }); }
  else if(stack1=== undef) { stack1 = helperMissing.call(depth0, "help", { hash: {} }); }
  buffer += escapeExpression(stack1) + "\n            </div>\n            <div style=\"clear: both;\"></div>\n        </div>\n        ";
  return buffer;}

  buffer += "<div class=\"toolFormTitle\">";
  foundHelper = helpers.name;
  stack1 = foundHelper || depth0.name;
  if(typeof stack1 === functionType) { stack1 = stack1.call(depth0, { hash: {} }); }
  else if(stack1=== undef) { stack1 = helperMissing.call(depth0, "name", { hash: {} }); }
  buffer += escapeExpression(stack1) + " (version ";
  foundHelper = helpers.version;
  stack1 = foundHelper || depth0.version;
  if(typeof stack1 === functionType) { stack1 = stack1.call(depth0, { hash: {} }); }
  else if(stack1=== undef) { stack1 = helperMissing.call(depth0, "version", { hash: {} }); }
  buffer += escapeExpression(stack1) + ")</div>\n    <div class=\"toolFormBody\">\n        ";
  foundHelper = helpers.inputs;
  stack1 = foundHelper || depth0.inputs;
  stack2 = helpers.each;
  tmp1 = self.program(1, program1, data);
  tmp1.hash = {};
  tmp1.fn = tmp1;
  tmp1.inverse = self.noop;
  stack1 = stack2.call(depth0, stack1, tmp1);
  if(stack1 || stack1 === 0) { buffer += stack1; }
  buffer += "\n    </div>\n    <div class=\"form-row form-actions\">\n    <input type=\"submit\" class=\"btn btn-primary\" name=\"runtool_btn\" value=\"Execute\">\n</div>\n<div class=\"toolHelp\">\n    <div class=\"toolHelpBody\">";
  foundHelper = helpers.help;
  stack1 = foundHelper || depth0.help;
  if(typeof stack1 === functionType) { stack1 = stack1.call(depth0, { hash: {} }); }
  else if(stack1=== undef) { stack1 = helperMissing.call(depth0, "help", { hash: {} }); }
  buffer += escapeExpression(stack1) + "</div>\n</div>";
  return buffer;});
})();